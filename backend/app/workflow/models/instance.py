from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class WorkflowInstance(WorkflowBase):
    __tablename__ = "workflow_instance"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_workflow_entity"),
        Index("idx_instance_state", "current_state_id"),
        {"schema": settings.WORKFLOW_DB_SCHEMA}
    )

    instance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_definition.workflow_id"),
        nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_state_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.workflow_state.state_id"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="Running", nullable=False)

    started_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    completed_on: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    workflow: Mapped["WorkflowDefinition"] = relationship(
        "WorkflowDefinition",
        back_populates="instances"
    )
    current_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState"
    )
    history: Mapped[List["WorkflowHistory"]] = relationship(
        "WorkflowHistory",
        primaryjoin="WorkflowInstance.instance_id == foreign(WorkflowHistory.instance_id)",
        cascade="all, delete-orphan"
    )

