from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class WorkflowTransition(WorkflowBase):
    __tablename__ = "workflow_transition"
    __table_args__ = (
        UniqueConstraint("current_state_id", "action_name", "role_code", name="uq_transition"),
        Index("idx_transition_lookup", "workflow_id", "current_state_id"),
        {"schema": settings.WORKFLOW_DB_SCHEMA}
    )

    transition_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_definition.workflow_id"),
        nullable=False
    )
    current_state_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_state.state_id"),
        nullable=False
    )
    action_name: Mapped[str] = mapped_column(String(50), nullable=False)
    next_state_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_state.state_id"),
        nullable=False
    )
    role_code: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    workflow: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="transitions"
    )
    current_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState",
        foreign_keys=[current_state_id]
    )
    next_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState",
        foreign_keys=[next_state_id]
    )
