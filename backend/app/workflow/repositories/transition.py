from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workflow.models.transition import WorkflowTransition

class WorkflowTransitionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_transition(
        self,
        workflow_id: int,
        current_state_id: int,
        action_name: str,
        role_code: str
    ) -> Optional[WorkflowTransition]:
        return self.db.execute(
            select(WorkflowTransition).where(
                WorkflowTransition.workflow_id == workflow_id,
                WorkflowTransition.current_state_id == current_state_id,
                WorkflowTransition.action_name == action_name,
                WorkflowTransition.role_code == role_code,
                WorkflowTransition.is_active == True
            )
        ).scalar_one_or_none()

    def get_available_transitions(self, current_state_id: int) -> List[WorkflowTransition]:
        return list(
            self.db.scalars(
                select(WorkflowTransition).where(
                    WorkflowTransition.current_state_id == current_state_id,
                    WorkflowTransition.is_active == True
                )
            ).all()
        )
