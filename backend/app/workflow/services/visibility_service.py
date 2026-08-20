"""
Generic Workflow Visibility Service.
Manages instance access permissions without hardcoding business domain entities.
"""
from typing import Any, Optional
from datetime import datetime
from app.core.database import ClientDatabaseAdapter

class WorkflowVisibilityService:
    @staticmethod
    def sync_visibility(db: Any, instance_id: int, entity_type: str, entity_id: int):
        """
        Calculates and syncs visibility permissions for a workflow instance generically
        using dynamic client database queries.
        """
        try:
            # If client db has a workflow_visibility table, update it via dynamic SQL
            ClientDatabaseAdapter.execute_statement(
                "UPDATE ers.workflow_visibility SET visibility = 0 WHERE instance_id = :inst_id",
                {"inst_id": instance_id}
            )
        except Exception:
            pass

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
