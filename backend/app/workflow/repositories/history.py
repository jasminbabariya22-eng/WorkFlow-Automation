from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.workflow.models.history import WorkflowHistory

class WorkflowHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        instance_id: int,
        from_state_id: Optional[int],
        to_state_id: Optional[int],
        action_name: str,
        performed_by: Optional[int] = None,
        performed_role: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> WorkflowHistory:
        history = WorkflowHistory(
            instance_id=instance_id,
            from_state_id=from_state_id,
            to_state_id=to_state_id,
            action_name=action_name,
            performed_by=performed_by,
            performed_role=performed_role,
            remarks=remarks,
            performed_on=datetime.now()
        )
        self.db.add(history)
        self.db.flush()
        return history

    def get_history(self, instance_id: int) -> List[WorkflowHistory]:
        return list(
            self.db.scalars(
                select(WorkflowHistory)
                .where(WorkflowHistory.instance_id == instance_id)
                .order_by(WorkflowHistory.performed_on.asc())
            ).all()
        )
