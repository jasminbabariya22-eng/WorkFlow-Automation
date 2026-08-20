from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class WorkflowDefinition(WorkflowBase):
    __tablename__ = "workflow_definition"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    workflow_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_on: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_on: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    states: Mapped[List["WorkflowState"]] = relationship(
        "WorkflowState",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    transitions: Mapped[List["WorkflowTransition"]] = relationship(
        "WorkflowTransition",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
    instances: Mapped[List["WorkflowInstance"]] = relationship(
        "WorkflowInstance",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )
