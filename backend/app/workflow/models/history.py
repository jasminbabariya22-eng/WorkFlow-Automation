from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class WorkflowHistory(WorkflowBase):
    __tablename__ = "workflow_history"
    __table_args__ = (
        Index("idx_history_instance", "instance_id"),
        Index("idx_history_states", "from_state_id", "to_state_id"),
        {"schema": settings.WORKFLOW_DB_SCHEMA}
    )

    history_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(Integer, nullable=False)
    from_state_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_state_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    action_name: Mapped[str] = mapped_column(String(50), nullable=False)

    performed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    performed_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    from_state_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

