from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class WorkflowState(WorkflowBase):
    __tablename__ = "workflow_state"
    __table_args__ = (
        UniqueConstraint("workflow_id", "state_code", name="uq_workflow_state_code"),
        Index("idx_state_workflow", "workflow_id"),
        {"schema": settings.WORKFLOW_DB_SCHEMA}
    )

    state_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_definition.workflow_id"),
        nullable=False
    )
    state_code: Mapped[str] = mapped_column(String(50), nullable=False)
    state_name: Mapped[str] = mapped_column(String(200), nullable=False)
    state_type: Mapped[str] = mapped_column(String(20), default="NORMAL", nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    workflow: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="states"
    )
