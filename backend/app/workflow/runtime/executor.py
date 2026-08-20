from typing import Dict, Any, Optional
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec as BpmnWorkflowSpec
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.task import TaskState

from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.context import WorkflowContext

class SpiffWorkflowExecutor:
    """
    Coordinates process definition parsing, engine step execution, context handling, 
    and serialization for workflow activities.
    """
    def __init__(self, parser: SpiffBPMNParser, engine: SpiffWorkflowEngine):
        self.parser = parser
        self.engine = engine

    def start_process(self, xml_content: str, spec_id: str, context: WorkflowContext) -> Dict[str, Any]:
        """
        Parses a BPMN XML, initializes the workflow spec, creates a new execution context,
        runs automated steps until blocked by a User Task or finished, and returns 
        the serialized state and current task info.
        """
        try:
            # 1. Compile BPMN spec
            spec = self.parser.parse_xml(xml_content, spec_id)
            
            # 2. Create running BpmnWorkflow instance
            workflow = self.engine.create_workflow(spec, context)
            
            # 3. Execute all automatic actions
            workflow = self.engine.run_until_blocked(workflow)
            
            # 4. Serialize execution tree
            serialized_state = self.engine.serialize(workflow)
            
            # 5. Extract current task context
            ready_tasks = self.engine.get_ready_user_tasks(workflow)
            current_task_code = ready_tasks[0]["task_spec_id"] if ready_tasks else "APPROVED"
            
            return {
                "serialized_state": serialized_state,
                "current_task_code": current_task_code,
                "status": "Completed" if workflow.is_completed() else "Running",
                "ready_tasks": ready_tasks
            }
        except Exception as e:
            raise WorkflowException(f"Executor failed to start process '{spec_id}': {str(e)}")

    def execute_task(self, xml_content: str, spec_id: str, serialized_state: str, task_spec_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restores a workflow from JSON state, locates the active user task matching task_spec_id,
        completes it with data, runs engine steps, and serializes the new state.
        """
        try:
            # 1. Compile BPMN spec
            spec = self.parser.parse_xml(xml_content, spec_id)
            
            # 2. Reconstruct workflow instance
            workflow = self.engine.deserialize(serialized_state, spec)
            
            # 3. Locate target READY User Task
            target_task = None
            for task in workflow.get_tasks():
                if task.state == TaskState.READY and task.task_spec.name == task_spec_id:
                    target_task = task
                    break
                    
            if not target_task:
                raise WorkflowException(f"No task with spec_id '{task_spec_id}' is currently READY for execution.")
                
            # 4. Complete the user task with variables
            target_task.set_data(**payload)
            target_task.complete()
            
            # 5. Run automatic engine steps
            workflow = self.engine.run_until_blocked(workflow)
            
            # 6. Re-serialize state
            new_serialized_state = self.engine.serialize(workflow)
            
            # 7. Extract current task context
            ready_tasks = self.engine.get_ready_user_tasks(workflow)
            current_task_code = ready_tasks[0]["task_spec_id"] if ready_tasks else "APPROVED"
            
            return {
                "serialized_state": new_serialized_state,
                "current_task_code": current_task_code,
                "status": "Completed" if workflow.is_completed() else "Running",
                "ready_tasks": ready_tasks
            }
        except Exception as e:
            raise WorkflowException(f"Executor failed to complete task '{task_spec_id}' in '{spec_id}': {str(e)}")
