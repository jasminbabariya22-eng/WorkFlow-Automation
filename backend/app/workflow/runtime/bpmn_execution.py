from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

import json

from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec as BpmnWorkflowSpec
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.task import TaskState

from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.registry import registry
from app.workflow.runtime.bpmn_utils import get_extension_properties_from_xml

class WorkflowPersistenceInterface(ABC):
    """
    Interface defining database operations for workflow state persistence.
    Isolates the execution layer from SQLAlchemy DB models.
    """
    @abstractmethod
    def save_state(self, entity_type: str, entity_id: int, bpmn_definition_id: int, serialized_state: str, current_task_code: str, status: str) -> None:
        pass

    @abstractmethod
    def load_state(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def log_activity(self, entity_type: str, entity_id: int, activity_id: str, activity_name: str, activity_type: str, status: str, variables: str) -> None:
        pass


class BPMNExecutionLayer:
    """
    BPMNExecutionLayer orchestrates loading process specs, executing automated steps 
    and service task activities, updating contexts, persisting states at transaction boundaries,
    and resuming execution after process sleep or restart.
    """
    def __init__(self, parser: SpiffBPMNParser, engine: SpiffWorkflowEngine, persistence_repo: WorkflowPersistenceInterface):
        self.parser = parser
        self.engine = engine
        self.persistence_repo = persistence_repo

    def start_workflow(self, xml_content: str, spec_id: str, definition_db_id: int, context: WorkflowContext, db_session: Any) -> Dict[str, Any]:
        """
        Loads the BPMN XML, instantiates the workflow, executes all automated tasks,
        persists the initial blocked/active state, and returns current task info.
        """
        try:
            # 1. Parse BPMN spec blueprint
            spec = self.parser.parse_xml(xml_content, spec_id)

            # 2. Instantiate workflow execution instance
            workflow = self.engine.create_workflow(spec, context)

            # Store XML content in context for extension properties loading
            context.xml_content = xml_content

            # 3. Run execution loop (automations & registered service tasks)
            self._run_execution_loop(workflow, context, db_session)

            # 4. Save final state to database
            serialized_state = self.engine.serialize(workflow)
            ready_tasks = self.engine.get_ready_user_tasks(workflow)
            current_task_code = ready_tasks[0]["task_spec_id"] if ready_tasks else "APPROVED"
            status = "Completed" if workflow.is_completed() else "Running"

            entity_type = context.get_variable("entity_type")
            entity_id = context.get_variable("entity_id")

            self.persistence_repo.save_state(
                entity_type=entity_type,
                entity_id=entity_id,
                bpmn_definition_id=definition_db_id,
                serialized_state=serialized_state,
                current_task_code=current_task_code,
                status=status
            )

            return {
                "serialized_state": serialized_state,
                "current_task_code": current_task_code,
                "status": status,
                "ready_tasks": ready_tasks
            }
        except Exception as e:
            raise WorkflowException(f"BPMN Execution Layer failed to start workflow '{spec_id}': {str(e)}")

    def resume_workflow(self, xml_content: str, spec_id: str, entity_type: str, entity_id: int, task_spec_id: str, payload: Dict[str, Any], db_session: Any) -> Dict[str, Any]:
        """
        Loads the workflow instance from the database, completes the active User Task,
        resumes the automated execution loop, and persists the updated state.
        """
        try:
            # 1. Load serialized state from DB
            db_record = self.persistence_repo.load_state(entity_type, entity_id)
            if not db_record:
                raise WorkflowException(f"No active workflow instance found for entity '{entity_type}' ID {entity_id}")

            serialized_state = db_record["serialized_state"]
            definition_db_id = db_record["bpmn_definition_id"]

            # 2. Re-compile BPMN spec and deserialize instance
            spec = self.parser.parse_xml(xml_content, spec_id)
            workflow = self.engine.deserialize(serialized_state, spec)

            # 3. Find target active Human Task in SpiffWorkflow
            target_task = None
            for task in workflow.get_tasks():
                if task.state == TaskState.READY and task.task_spec.name == task_spec_id:
                    target_task = task
                    break

            if not target_task:
                raise WorkflowException(f"Task '{task_spec_id}' is not in a READY state in the reconstructed workflow.")

            # 4. Supply payloads and complete task
            target_task.set_data(**payload)
            target_task.complete()

            # 5. Initialize WorkflowContext from deserialized variables
            context = WorkflowContext(
                variables=workflow.data,
                user_id=payload.get("user_id"),
                user_role=payload.get("role_code")
            )
            context.set_variable("entity_type", entity_type)
            context.set_variable("entity_id", entity_id)

            # Store XML content in context for extension properties loading
            context.xml_content = xml_content

            # 6. Execute next steps
            self._run_execution_loop(workflow, context, db_session)

            # 7. Persist updated state
            new_serialized_state = self.engine.serialize(workflow)
            ready_tasks = self.engine.get_ready_user_tasks(workflow)
            current_task_code = ready_tasks[0]["task_spec_id"] if ready_tasks else "APPROVED"
            status = "Completed" if workflow.is_completed() else "Running"

            self.persistence_repo.save_state(
                entity_type=entity_type,
                entity_id=entity_id,
                bpmn_definition_id=definition_db_id,
                serialized_state=new_serialized_state,
                current_task_code=current_task_code,
                status=status
            )

            return {
                "serialized_state": new_serialized_state,
                "current_task_code": current_task_code,
                "status": status,
                "ready_tasks": ready_tasks
            }
        except Exception as e:
            raise WorkflowException(f"BPMN Execution Layer failed to resume task '{task_spec_id}' in '{spec_id}': {str(e)}")

    def _run_execution_loop(self, workflow: BpmnWorkflow, context: WorkflowContext, db_session: Any) -> None:
        """
        Low-level engine loop: runs engine steps, intercepts Service/Script Task nodes,
        matches them against the Activity Registry, resolves dependencies, and persists 
        states immediately after execution.
        """
        while True:
            # Execute automated engine paths (Gateways, Script Tasks, timers)
            workflow.do_engine_steps()

            service_task_executed = False
            for task in workflow.get_tasks():
                # Detect active Service Tasks mapped to registry items
                if task.state == TaskState.READY:
                    task_name = task.task_spec.name
                    if task_name in registry.get_registered_activities():
                        service_task_executed = True
                        
                        # 1. Resolve activity configuration from BPMN XML properties
                        xml_content = getattr(context, "xml_content", None)
                        activity_config = {}
                        if xml_content:
                            activity_config = get_extension_properties_from_xml(xml_content, task.task_spec.id)
                        
                        # 2. Bind configs and database session to context
                        context.activity_config = activity_config
                        context.db = db_session
                        
                        # 3. Resolve and run the activity
                        activity_outputs = registry.resolve_and_execute(task_name, context)
                        
                        # Log activity execution dynamically to the trace repository
                        self.persistence_repo.log_activity(
                            entity_type=context.get_variable("entity_type"),
                            entity_id=context.get_variable("entity_id"),
                            activity_id=task_name,
                            activity_name=task_name,
                            activity_type="ServiceTask",
                            status="COMPLETED",
                            variables=json.dumps(activity_outputs)
                        )

                        # Update task variable scopes
                        task.set_data(**activity_outputs)
                        context.variables.update(activity_outputs)
                        
                        # Mark this service task completed inside SpiffWorkflow
                        task.complete()
                        break  # Break to re-execute engine steps from the beginning
            
            # If no automated service task was run in this pass, the engine is waiting on human tasks or finished
            if not service_task_executed:
                break
