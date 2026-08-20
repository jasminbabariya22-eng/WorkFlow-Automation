from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workflow.models.instance import WorkflowInstance

class WorkflowInstanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        workflow_id: int,
        entity_type: str,
        entity_id: int,
        current_state_id: int,
        started_by: Optional[int] = None
    ) -> WorkflowInstance:
        instance = WorkflowInstance(
            workflow_id=workflow_id,
            entity_type=entity_type,
            entity_id=entity_id,
            current_state_id=current_state_id,
            status="Running",
            started_by=started_by,
            started_on=datetime.now()
        )
        self.db.add(instance)
        self.db.flush()
        return instance

    def get_by_id(self, instance_id: int) -> Optional[WorkflowInstance]:
        return self.db.execute(
            select(WorkflowInstance).where(WorkflowInstance.instance_id == instance_id)
        ).scalar_one_or_none()

    def get_by_entity(self, entity_type: str, entity_id: int) -> Optional[WorkflowInstance]:
        return self.db.execute(
            select(WorkflowInstance).where(
                WorkflowInstance.entity_type == entity_type,
                WorkflowInstance.entity_id == entity_id
            )
        ).scalar_one_or_none()

    def update_current_state(self, instance_id: int, next_state_id: int) -> Optional[WorkflowInstance]:
        instance = self.get_by_id(instance_id)
        if instance:
            instance.current_state_id = next_state_id
            self.db.flush()
        return instance

    def complete_workflow(self, instance_id: int, final_state_id: int) -> Optional[WorkflowInstance]:
        instance = self.get_by_id(instance_id)
        if instance:
            instance.current_state_id = final_state_id
            instance.status = "Completed"
            instance.completed_on = datetime.now()
            self.db.flush()
        return instance
