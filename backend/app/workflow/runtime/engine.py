from typing import List, Dict, Any, Optional
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec as BpmnWorkflowSpec
from SpiffWorkflow.bpmn.serializer import BpmnWorkflowSerializer
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.task import TaskState
from SpiffWorkflow.bpmn.specs.defaults import UserTask
from app.workflow.runtime.context import WorkflowContext

class SpiffWorkflowEngine:
    """
    SpiffWorkflowEngine abstracts execution paths, task completions, and serialization 
    of running BpmnWorkflow instances.
    """
    def __init__(self, serializer: Optional[BpmnWorkflowSerializer] = None):
        self.serializer = serializer or BpmnWorkflowSerializer()

    def create_workflow(self, spec: BpmnWorkflowSpec, context: WorkflowContext) -> BpmnWorkflow:
        """
        Creates a new running workflow instance initialized with context variables.
        """
        try:
            workflow = BpmnWorkflow(spec)
            # Inject context variables as top-level execution parameters
            workflow.data.update(context.variables)
            return workflow
        except Exception as e:
            raise WorkflowException(f"Error creating workflow instance: {str(e)}")

    def serialize(self, workflow: BpmnWorkflow) -> str:
        """
        Serializes the active workflow instance state to a JSON string.
        """
        try:
            return self.serializer.serialize_json(workflow)
        except Exception as e:
            raise WorkflowException(f"Failed to serialize workflow instance: {str(e)}")

    def deserialize(self, serialized_state: str, spec: BpmnWorkflowSpec) -> BpmnWorkflow:
        """
        Restores a workflow instance from its serialized JSON state.
        """
        try:
            return self.serializer.deserialize_json(serialized_state)
        except Exception as e:
            raise WorkflowException(f"Failed to deserialize workflow instance: {str(e)}")

    def run_until_blocked(self, workflow: BpmnWorkflow) -> BpmnWorkflow:
        """
        Tells the engine to execute all non-interactive tasks (scripts, service tasks, gateways)
        until it hits a task that requires human intervention (User Task) or reaches the END event.
        """
        try:
            workflow.do_engine_steps()
            return workflow
        except Exception as e:
            raise WorkflowException(f"Error executing engine steps: {str(e)}")

    def get_ready_user_tasks(self, workflow: BpmnWorkflow) -> List[Dict[str, Any]]:
        """
        Returns a list of User Tasks that are currently waiting for interaction.
        """
        tasks = []
        for task in workflow.get_tasks():
            # Check if task is active and requires user input (is instance of UserTask)
            if task.state == TaskState.READY and isinstance(task.task_spec, UserTask):
                tasks.append({
                    "task_id": task.id,
                    "task_spec_id": task.task_spec.name,
                    "state": str(task.state),
                    "lane": getattr(task.task_spec, "lane", None)
                })
        return tasks
