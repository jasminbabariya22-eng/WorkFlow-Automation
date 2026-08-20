from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workflow.models.definition import WorkflowDefinition

class WorkflowDefinitionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, workflow_id: int) -> Optional[WorkflowDefinition]:
        return self.db.execute(
            select(WorkflowDefinition).where(WorkflowDefinition.workflow_id == workflow_id)
        ).scalar_one_or_none()

    def get_by_name(self, workflow_name: str) -> Optional[WorkflowDefinition]:
        return self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.workflow_name == workflow_name,
                WorkflowDefinition.is_active == True
            )
        ).scalar_one_or_none()

    def get_active_workflow(self, workflow_id: int) -> Optional[WorkflowDefinition]:
        return self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.workflow_id == workflow_id,
                WorkflowDefinition.is_active == True
            )
        ).scalar_one_or_none()
