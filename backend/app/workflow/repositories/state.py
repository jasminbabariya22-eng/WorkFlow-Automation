from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workflow.models.state import WorkflowState

class WorkflowStateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, state_id: int) -> Optional[WorkflowState]:
        return self.db.execute(
            select(WorkflowState).where(WorkflowState.state_id == state_id)
        ).scalar_one_or_none()

    def get_by_code(self, workflow_id: int, state_code: str) -> Optional[WorkflowState]:
        return self.db.execute(
            select(WorkflowState).where(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_code == state_code
            )
        ).scalar_one_or_none()

    def get_start_state(self, workflow_id: int) -> Optional[WorkflowState]:
        return self.db.execute(
            select(WorkflowState).where(
                WorkflowState.workflow_id == workflow_id,
                WorkflowState.state_type == "START"
            )
        ).scalar_one_or_none()

    def get_states_by_workflow(self, workflow_id: int) -> List[WorkflowState]:
        return list(
            self.db.scalars(
                select(WorkflowState)
                .where(WorkflowState.workflow_id == workflow_id)
                .order_by(WorkflowState.sequence_no)
            ).all()
        )
