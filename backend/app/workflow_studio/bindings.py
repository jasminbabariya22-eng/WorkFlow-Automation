"""
bindings.py
Single Declarative Python Workflow Binding Registry.
Binds client modules (leaves, expenses, purchase orders, etc.) to workflow definitions,
database connections, and entity tables with zero hardcoded frontend logic.
"""

from typing import Dict, Any, Optional

WORKFLOW_BINDINGS: Dict[str, Dict[str, Any]] = {
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


def get_binding(module_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves the declarative workflow binding for a given module key."""
    return WORKFLOW_BINDINGS.get(module_key)


def list_bindings() -> Dict[str, Any]:
    """Lists all registered workflow bindings."""
    return {
        key: {
            "module_key": b["module_key"],
            "title": b["title"],
            "workflow_id": b["workflow_id"],
            "connection_id": b["connection_id"],
            "table_name": b["table_name"],
            "status_column": b["status_column"],
            "fields": b.get("fields", [])
        }
        for key, b in WORKFLOW_BINDINGS.items()
    }
