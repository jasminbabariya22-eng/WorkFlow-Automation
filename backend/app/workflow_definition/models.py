from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings


class GenericWorkflow(WorkflowBase):
    """
    SQLAlchemy model representing a high-level generic workflow definition.
    Entity-agnostic design-time template.
    """
    __tablename__ = "wf_definition"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    workflow_id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    entity_type = Column(String(100), nullable=True, index=True)  # Generic metadata: e.g. "Risk", "Audit", "Incident", "Purchase"
    connection_id = Column(Integer, nullable=True)  # Target Database Connection ID
    status = Column(String(20), default="DRAFT", nullable=False)   # "DRAFT", "ACTIVE", "ARCHIVED"
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    versions = relationship("WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan", order_by="WorkflowVersion.version_number")


class WorkflowVersion(WorkflowBase):
    """
    SQLAlchemy model representing an immutable/draft version of a workflow definition.
    """
    __tablename__ = "wf_version"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    workflow_version_id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(Integer, ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.wf_definition.workflow_id" if settings.WORKFLOW_DB_SCHEMA else "wf_definition.workflow_id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    status = Column(String(20), default="DRAFT", nullable=False)  # "DRAFT", "VALIDATED", "PUBLISHED", "ARCHIVED"
    definition_metadata = Column(Text, default="{}", nullable=True)  # Flexible JSON metadata
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    workflow = relationship("GenericWorkflow", back_populates="versions")
    nodes = relationship("WorkflowNode", back_populates="version", cascade="all, delete-orphan")
    connections = relationship("WorkflowConnection", back_populates="version", cascade="all, delete-orphan")


class WorkflowNode(WorkflowBase):
    """
    SQLAlchemy model representing a generic node step in a workflow version graph.
    """
    __tablename__ = "wf_node"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    node_id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_version_id = Column(Integer, ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.wf_version.workflow_version_id" if settings.WORKFLOW_DB_SCHEMA else "wf_version.workflow_version_id"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False)
    node_type = Column(String(50), nullable=False)  # "START", "END", "APPROVAL", "CONDITION", "ACTION", "EMAIL", "FORM", "WAIT", "WEBHOOK"
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    position_x = Column(Float, default=0.0, nullable=False)
    position_y = Column(Float, default=0.0, nullable=False)
    configuration = Column(Text, default="{}", nullable=False)  # JSON configuration
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # Relationships
    version = relationship("WorkflowVersion", back_populates="nodes")
    outgoing_connections = relationship("WorkflowConnection", foreign_keys="WorkflowConnection.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    incoming_connections = relationship("WorkflowConnection", foreign_keys="WorkflowConnection.target_node_id", back_populates="target_node", cascade="all, delete-orphan")


class WorkflowConnection(WorkflowBase):
    """
    SQLAlchemy model representing a directed edge connecting two workflow nodes.
    """
    __tablename__ = "wf_connection"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    connection_id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_version_id = Column(Integer, ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.wf_version.workflow_version_id" if settings.WORKFLOW_DB_SCHEMA else "wf_version.workflow_version_id"), nullable=False, index=True)
    source_node_id = Column(Integer, ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.wf_node.node_id" if settings.WORKFLOW_DB_SCHEMA else "wf_node.node_id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey(f"{settings.WORKFLOW_DB_SCHEMA}.wf_node.node_id" if settings.WORKFLOW_DB_SCHEMA else "wf_node.node_id"), nullable=False, index=True)
    connection_key = Column(String(100), nullable=True)
    condition = Column(Text, nullable=True)  # Condition expression, action name, or port code
    label = Column(String(200), nullable=True)  # e.g. "Approve", "Reject", "Submit", "True", "False"
    metadata_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    version = relationship("WorkflowVersion", back_populates="connections")
    source_node = relationship("WorkflowNode", foreign_keys=[source_node_id], back_populates="outgoing_connections")
    target_node = relationship("WorkflowNode", foreign_keys=[target_node_id], back_populates="incoming_connections")


# Alias for backward-compatible imports
WorkflowDefinition = GenericWorkflow
