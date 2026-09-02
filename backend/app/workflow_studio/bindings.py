"""
bindings.py
Universal Database-Driven Workflow Binding Registry.
Binds client modules (leaves, expenses, purchase orders, KYC, IT tickets, etc.)
to workflow definitions, database connections, and entity tables dynamically.
Supports 50+ workflows with zero hardcoded code changes.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from app.workflow.database import WorkflowBase, WorkflowSessionLocal
from app.core.logger import logger


class WorkflowModuleBinding(WorkflowBase):
    __tablename__ = "wf_module_bindings"
    __table_args__ = {"schema": "workflow"}

    binding_id = Column(Integer, primary_key=True, index=True)
    module_key = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    workflow_id = Column(Integer, nullable=False)
    connection_id = Column(Integer, nullable=False, default=4)
    table_name = Column(String(100), nullable=False)
    primary_key = Column(String(100), nullable=False, default="id")
    status_column = Column(String(100), nullable=False, default="status")
    default_status = Column(String(50), nullable=False, default="PENDING")
    approval_roles = Column(JSONB, default=["MANAGER", "HR"])
    fields = Column(JSONB, default=[])
    form_schema = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "module_key": self.module_key,
            "title": self.title,
            "workflow_id": self.workflow_id,
            "connection_id": self.connection_id,
            "table_name": self.table_name,
            "primary_key": self.primary_key,
            "status_column": self.status_column,
            "default_status": self.default_status,
            "approval_roles": self.approval_roles or [],
            "fields": self.fields or [],
            "form_schema": self.form_schema or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# In-memory defaults as instant fallback
FALLBACK_BINDINGS: Dict[str, Dict[str, Any]] = {
    "leave_requests": {
        "module_key": "leave_requests",
        "title": "Employee Leave Management",
        "workflow_id": 112,
        "connection_id": 4,
        "table_name": "leave_requests",
        "primary_key": "leave_request_id",
        "status_column": "status",
        "default_status": "PENDING",
        "approval_roles": ["MANAGER", "FUNCTION_HEAD", "APPROVER", "HR"],
        "fields": [
            {"name": "employee_id", "type": "int", "required": True},
            {"name": "leave_type_id", "type": "int", "required": True},
            {"name": "start_date", "type": "str", "required": True},
            {"name": "end_date", "type": "str", "required": True},
            {"name": "reason", "type": "str", "required": False}
        ]
    },
    "leave_cancellation": {
        "module_key": "leave_cancellation",
        "title": "Leave Cancellation Request",
        "workflow_id": 1122,
        "connection_id": 4,
        "table_name": "leave_requests",
        "primary_key": "leave_request_id",
        "status_column": "status",
        "default_status": "PENDING_CANCELLATION",
        "approval_roles": ["MANAGER", "FUNCTION_HEAD", "APPROVER", "HR"]
    }
}


def get_binding(module_key: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the workflow binding dynamically from PostgreSQL table workflow.wf_module_bindings.
    Falls back safely to FALLBACK_BINDINGS if DB is not available.
    """
    own_db = False
    if db is None:
        try:
            db = WorkflowSessionLocal()
            own_db = True
        except Exception:
            return FALLBACK_BINDINGS.get(module_key)

    try:
        record = db.query(WorkflowModuleBinding).filter(
            WorkflowModuleBinding.module_key == module_key,
            WorkflowModuleBinding.is_active == True
        ).first()

        if record:
            return record.to_dict()
    except Exception as e:
        logger.warning(f"Error reading wf_module_bindings from DB: {e}")
    finally:
        if own_db and db:
            db.close()

    return FALLBACK_BINDINGS.get(module_key)


def list_bindings(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Lists all registered workflow bindings from PostgreSQL database.
    """
    own_db = False
    if db is None:
        try:
            db = WorkflowSessionLocal()
            own_db = True
        except Exception:
            return FALLBACK_BINDINGS

    try:
        records = db.query(WorkflowModuleBinding).filter(
            WorkflowModuleBinding.is_active == True
        ).order_by(WorkflowModuleBinding.binding_id.asc()).all()

        if records:
            return {r.module_key: r.to_dict() for r in records}
    except Exception as e:
        logger.warning(f"Error listing wf_module_bindings from DB: {e}")
    finally:
        if own_db and db:
            db.close()

    return FALLBACK_BINDINGS


def upsert_binding(data: Dict[str, Any], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Creates or updates a module binding dynamically without touching code.
    """
    own_db = False
    if db is None:
        db = WorkflowSessionLocal()
        own_db = True

    try:
        module_key = data["module_key"]
        record = db.query(WorkflowModuleBinding).filter(
            WorkflowModuleBinding.module_key == module_key
        ).first()

        if not record:
            record = WorkflowModuleBinding(
                module_key=module_key,
                title=data.get("title", module_key.replace("_", " ").title()),
                workflow_id=int(data["workflow_id"]),
                connection_id=int(data.get("connection_id", 4)),
                table_name=data["table_name"],
                primary_key=data.get("primary_key", "id"),
                status_column=data.get("status_column", "status"),
                default_status=data.get("default_status", "PENDING"),
                approval_roles=data.get("approval_roles", ["MANAGER", "HR"]),
                fields=data.get("fields", []),
                form_schema=data.get("form_schema", {}),
                is_active=data.get("is_active", True)
            )
            db.add(record)
        else:
            record.title = data.get("title", record.title)
            record.workflow_id = int(data.get("workflow_id", record.workflow_id))
            record.connection_id = int(data.get("connection_id", record.connection_id))
            record.table_name = data.get("table_name", record.table_name)
            record.primary_key = data.get("primary_key", record.primary_key)
            record.status_column = data.get("status_column", record.status_column)
            record.default_status = data.get("default_status", record.default_status)
            if "approval_roles" in data:
                record.approval_roles = data["approval_roles"]
            if "fields" in data:
                record.fields = data["fields"]
            if "form_schema" in data:
                record.form_schema = data["form_schema"]
            record.is_active = data.get("is_active", record.is_active)
            record.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(record)
        return record.to_dict()
    finally:
        if own_db and db:
            db.close()


def delete_binding(module_key: str, db: Optional[Session] = None) -> bool:
    """
    Deactivates a module binding.
    """
    own_db = False
    if db is None:
        db = WorkflowSessionLocal()
        own_db = True

    try:
        record = db.query(WorkflowModuleBinding).filter(
            WorkflowModuleBinding.module_key == module_key
        ).first()
        if record:
            record.is_active = False
            record.updated_at = datetime.utcnow()
            db.commit()
            return True
        return False
    finally:
        if own_db and db:
            db.close()
