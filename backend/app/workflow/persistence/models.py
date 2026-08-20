from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.workflow.workflow_base import WorkflowBase
from app.core.config import settings

class BPMNDefinition(WorkflowBase):
    """
    SQLAlchemy model representing versioned BPMN 2.0 XML process configurations.
    """
    __tablename__ = "bpmn_definition"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    spec_id = Column(String(100), nullable=False)
    name = Column(String(200))
    version = Column(Integer, nullable=False)
    description = Column(Text)
    xml_content = Column(Text, nullable=False)
    json_content = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="Draft", nullable=False)
    tags = Column(String(500))
    created_by = Column(Integer)
    created_on = Column(DateTime, default=datetime.now, nullable=False)
    updated_on = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    published_on = Column(DateTime)


class SpiffWorkflowInstance(WorkflowBase):
    """
    SQLAlchemy model representing a serialized SpiffWorkflow execution instance.
    """
    __tablename__ = "spiff_workflow_instance"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    instance_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    bpmn_definition_id = Column(Integer, nullable=False)
    status = Column(String(20), default="Running", nullable=False)
    serialized_state = Column(Text, nullable=False)
    current_task_code = Column(String(50))
    started_on = Column(DateTime, default=datetime.now, nullable=False)
    completed_on = Column(DateTime)


class SpiffHumanTask(WorkflowBase):
    """
    SQLAlchemy model acting as an index for active and completed human approval tasks.
    """
    __tablename__ = "workflow_human_task"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False)
    task_spec_id = Column(String(100), nullable=False)
    role_code = Column(String(50), nullable=False)
    assignee_id = Column(Integer)
    status = Column(String(20), default="READY", nullable=False)  # 'READY', 'COMPLETED', 'REJECTED'
    created_on = Column(DateTime, default=datetime.now, nullable=False)
    completed_on = Column(DateTime)


class SpiffActivityHistory(WorkflowBase):
    """
    SQLAlchemy model tracking fine-grained activity execution traces inside SpiffWorkflow.
    """
    __tablename__ = "workflow_activity_history"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    activity_history_id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False)
    activity_id = Column(String(100), nullable=False)
    activity_name = Column(String(200))
    activity_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    variables = Column(Text, default="{}", nullable=False)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)


class WorkflowEntityConfig(WorkflowBase):
    """
    SQLAlchemy model representing dynamic workflow mapping configuration for entities.
    """
    __tablename__ = "workflow_entity_config"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    config_id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(100), nullable=False)
    specification_id = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_on = Column(DateTime, default=datetime.now, nullable=False)
    modified_on = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorkflowTaskPermission(WorkflowBase):
    """
    SQLAlchemy model representing configuration-driven role action permissions per task.
    """
    __tablename__ = "workflow_task_permission"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    permission_id = Column(Integer, primary_key=True, autoincrement=True)
    spec_id = Column(String(100), nullable=False)
    task_spec_id = Column(String(100), nullable=False)
    role_code = Column(String(50), nullable=False)
    actions = Column(Text, nullable=False) # e.g. "APPROVE,REJECT"
    is_active = Column(Boolean, default=True, nullable=False)
    created_on = Column(DateTime, default=datetime.now, nullable=False)

