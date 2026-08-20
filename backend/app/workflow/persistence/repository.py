from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.workflow.runtime.bpmn_execution import WorkflowPersistenceInterface
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask, BPMNDefinition, SpiffActivityHistory
from app.workflow.runtime.bpmn_utils import get_candidate_role_from_xml

class SpiffWorkflowRepository(WorkflowPersistenceInterface):
    """
    Implements the WorkflowPersistenceInterface using SQLAlchemy sessions.
    Handles saving process serialization states and indexing human task states.
    """
    def __init__(self, db: Session):
        self.db = db

    def save_state(self, entity_type: str, entity_id: int, bpmn_definition_id: int, serialized_state: str, current_task_code: str, status: str) -> None:
        # 1. Check for existing instance record
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        current_time = datetime.now()

        if not instance:
            instance = SpiffWorkflowInstance(
                entity_type=entity_type,
                entity_id=entity_id,
                bpmn_definition_id=bpmn_definition_id,
                status=status,
                serialized_state=serialized_state,
                current_task_code=current_task_code,
                started_on=current_time
            )
            self.db.add(instance)
        else:
            instance.status = status
            instance.serialized_state = serialized_state
            instance.current_task_code = current_task_code
            if status == "Completed":
                instance.completed_on = current_time

        self.db.flush()

        # 2. Automatically seed Human Task Index when execution hits a Human task block
        if status == "Running" and current_task_code not in ["DRAFT", "APPROVED"]:
            existing_task = self.db.query(SpiffHumanTask).filter(
                SpiffHumanTask.instance_id == instance.instance_id,
                SpiffHumanTask.task_spec_id == current_task_code,
                SpiffHumanTask.status == "READY"
            ).first()

            if not existing_task:
                # Default role
                role_code = "INITIATOR"
                
                # Fetch BPMN XML dynamically to resolve candidateGroups configurations
                definition = self.db.query(BPMNDefinition).filter(BPMNDefinition.id == bpmn_definition_id).first()
                if definition and definition.xml_content:
                    extracted_role = get_candidate_role_from_xml(definition.xml_content, current_task_code)
                    if extracted_role:
                        role_code = extracted_role

                human_task = SpiffHumanTask(
                    instance_id=instance.instance_id,
                    task_spec_id=current_task_code,
                    role_code=role_code,
                    status="READY",
                    created_on=current_time
                )
                self.db.add(human_task)
                self.db.flush()

    def load_state(self, entity_type: str, entity_id: int) -> Optional[Dict[str, Any]]:
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        if not instance:
            return None

        return {
            "bpmn_definition_id": instance.bpmn_definition_id,
            "serialized_state": instance.serialized_state,
            "status": instance.status,
            "current_task_code": instance.current_task_code
        }

    def log_activity(self, entity_type: str, entity_id: int, activity_id: str, activity_name: str, activity_type: str, status: str, variables: str) -> None:
        instance = self.db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()
        
        instance_id = instance.instance_id if instance else 0
        
        log_entry = SpiffActivityHistory(
            instance_id=instance_id,
            activity_id=activity_id,
            activity_name=activity_name,
            activity_type=activity_type,
            status=status,
            variables=variables,
            timestamp=datetime.now()
        )
        self.db.add(log_entry)
        self.db.flush()
