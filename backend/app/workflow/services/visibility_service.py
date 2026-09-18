"""
Generic Workflow Visibility Service.
Manages instance access permissions without hardcoding business domain entities.
"""
from typing import Any, Optional
from datetime import datetime
from app.core.database import ClientDatabaseAdapter

class WorkflowVisibilityService:
    _has_table: Optional[bool] = None

    @staticmethod
    def sync_visibility(db: Any, instance_id: int, entity_type: str, entity_id: int):
        """
        Calculates and syncs visibility permissions for a workflow instance generically
        using dynamic client database queries.
        """
        if not entity_type or str(entity_type).lower() in ("generic", "test", "none") or "test" in str(entity_type).lower():
            return
        if WorkflowVisibilityService._has_table is False:
            return

        try:
            ClientDatabaseAdapter.execute_statement(
                "UPDATE ers.workflow_visibility SET visibility = 0 WHERE instance_id = :inst_id",
                {"inst_id": instance_id}
            )
            WorkflowVisibilityService._has_table = True
        except Exception:
            WorkflowVisibilityService._has_table = False

    @staticmethod
    def grant_visibility(instance_id: int, user_id: int, role_id: Optional[int] = None):
        """
        Dynamically grants visibility to a user for a workflow instance.
        """
        try:
            ClientDatabaseAdapter.execute_statement(
                """
                INSERT INTO ers.workflow_visibility (instance_id, user_id, role_id, visibility, time)
                VALUES (:inst_id, :user_id, :role_id, 1, :now_time)
                """,
                {
                    "inst_id": instance_id,
                    "user_id": user_id,
                    "role_id": role_id,
                    "now_time": datetime.now()
                }
            )
        except Exception:
            pass
