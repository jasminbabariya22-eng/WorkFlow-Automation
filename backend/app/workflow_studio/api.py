import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.workflow_studio.schemas import (
    StudioWorkflowCreate,
    StudioWorkflowUpdate,
    StudioWorkflowResponse,
    StudioWorkflowListItem,
    StudioValidationResponse
)
from app.workflow_studio.services import WorkflowStudioService

router = APIRouter(prefix="/workflow-studio/workflows", tags=["Workflow Studio Workflows"])
catalog_router = APIRouter(prefix="/workflow-studio", tags=["Workflow Studio Foundation"])


# ==========================================
# 1. WORKFLOW CRUD & LIFECYCLE
# ==========================================

@router.post("", response_model=StudioWorkflowResponse)
def create_workflow_draft(
    payload: StudioWorkflowCreate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new generic workflow definition in DRAFT status with initial canvas nodes & edges.
    """
    user_id = current_user.get("user_id") if current_user else None
    return WorkflowStudioService.create_workflow_draft(db, payload, user_id=user_id)


@router.get("", response_model=List[StudioWorkflowListItem])
def list_workflows(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (Risk, Audit, Incident, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, ACTIVE, ARCHIVED)"),
    db: Session = Depends(get_workflow_db)
):
    """
    Lists all workflows created in the Workflow Studio.
    """
    return WorkflowStudioService.list_workflows(db, entity_type=entity_type, status=status)


@router.get("/{workflow_id}", response_model=StudioWorkflowResponse)
def get_workflow_definition(
    workflow_id: int,
    version_id: Optional[int] = Query(None, description="Optional specific version ID to retrieve"),
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the visual graph definition (nodes, edges, configuration) of a workflow.
    """
    return WorkflowStudioService.get_workflow_definition(db, workflow_id, version_id=version_id)


@router.put("/{workflow_id}", response_model=StudioWorkflowResponse)
def update_workflow_draft(
    workflow_id: int,
    payload: StudioWorkflowUpdate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Saves and updates nodes, edges, and configurations for a DRAFT workflow version.
    Modifying a PUBLISHED version is rejected.
    """
    user_id = current_user.get("user_id") if current_user else None
    return WorkflowStudioService.update_workflow_draft(db, workflow_id, payload, user_id=user_id)


@router.delete("/{workflow_id}", response_model=Dict[str, Any])
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deletes or archives a workflow definition.
    """
    user_id = current_user.get("user_id") if current_user else None
    return WorkflowStudioService.delete_workflow(db, workflow_id, user_id=user_id)


@router.post("/{workflow_id}/validate", response_model=StudioValidationResponse)
def validate_workflow(
    workflow_id: int,
    version_id: Optional[int] = Query(None, description="Optional version ID to validate"),
    db: Session = Depends(get_workflow_db)
):
    """
    Runs the Studio graph validation engine against the workflow definition.
    Checks START/END presence, reachability, orphan nodes, role configurations, and branches.
    """
    return WorkflowStudioService.validate_workflow(db, workflow_id, version_id=version_id)


@router.post("/{workflow_id}/publish", response_model=StudioWorkflowResponse)
def publish_workflow(
    workflow_id: int,
    version_id: Optional[int] = Query(None, description="Optional version ID to publish"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Validates and publishes the workflow. Marks current version as PUBLISHED (immutable)
    and archives any previously published versions.
    """
    user_id = current_user.get("user_id") if current_user else None
    return WorkflowStudioService.publish_workflow(db, workflow_id, version_id=version_id, user_id=user_id)


@router.post("/{workflow_id}/unpublish", response_model=StudioWorkflowResponse)
def unpublish_workflow(
    workflow_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Reverts a published workflow version to DRAFT status.
    """
    user_id = current_user.get("user_id") if current_user else None
    return WorkflowStudioService.unpublish_workflow(db, workflow_id, user_id=user_id)


@router.post("/{workflow_id}/versions", response_model=StudioWorkflowResponse)
def create_workflow_version(
    workflow_id: int,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Creates a new draft version for a workflow, cloning previous version configuration if requested.
    """
    user_id = current_user.get("user_id") if current_user else None
    desc = (payload or {}).get("description")
    return WorkflowStudioService.create_version(db, workflow_id, user_id=user_id, description=desc)


@router.get("/{workflow_id}/versions", response_model=List[Dict[str, Any]])
def get_workflow_versions(
    workflow_id: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the version history and publication status for a workflow.
    """
    return WorkflowStudioService.get_workflow_versions(db, workflow_id)


@router.get("/{workflow_id}/versions/{version_number}", response_model=StudioWorkflowResponse)
def get_workflow_version_by_number(
    workflow_id: int,
    version_number: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves a specific historical version definition of a workflow.
    """
    return WorkflowStudioService.get_workflow_version_by_number(db, workflow_id, version_number)


@router.post("/{workflow_id}/execute", response_model=Dict[str, Any])
def execute_studio_workflow(
    workflow_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Directly executes a published Workflow Studio definition for testing or automated integration.
    """
    from app.workflow_studio.runtime.adapter import StudioExecutionAdapter

    entity_type = payload.get("entity_type", "StudioTest")
    entity_id = payload.get("entity_id", int(time.time()))
    action = payload.get("action")
    user_id = payload.get("user_id") or (current_user.get("user_id") if current_user else None)
    remarks = payload.get("remarks")
    variables = payload.get("variables", {})

    if action:
        # Resume existing instance with action
        return StudioExecutionAdapter.execute_action(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            remarks=remarks,
            variables=variables,
            db=db
        )
    else:
        # Start new instance
        return StudioExecutionAdapter.start_workflow(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            variables=variables,
            db=db,
            definition_id=workflow_id
        )


@router.post("/{workflow_id}/action", response_model=Dict[str, Any])
def execute_studio_action(
    workflow_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Executes a human action (APPROVE, REJECT, FORCE_APPROVE, etc.) on a running workflow instance.
    """
    from app.workflow_studio.runtime.adapter import StudioExecutionAdapter

    entity_type = payload.get("entity_type", "StudioTest")
    entity_id = payload.get("entity_id", int(time.time()))
    action = payload.get("action", "APPROVE")
    user_id = payload.get("user_id") or (current_user.get("user_id") if current_user else None)
    remarks = payload.get("remarks")
    variables = payload.get("variables", {})

    return StudioExecutionAdapter.execute_action(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        remarks=remarks,
        variables=variables,
        db=db
    )



# ==========================================
# 2. STUDIO DYNAMIC METADATA & DISCOVERY APIS
# ==========================================

@catalog_router.get("/roles", response_model=List[Dict[str, Any]])
def get_available_roles():
    """
    Retrieves active user roles dynamically from the Client Database.
    """
    try:
        return WorkflowStudioService.get_available_roles()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/actions", response_model=List[Dict[str, Any]])
def get_available_actions():
    """
    Retrieves the catalog of actions dynamically from the Client Database (mst_status).
    """
    try:
        return WorkflowStudioService.get_available_actions()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/roles", response_model=List[Dict[str, Any]])
def get_client_roles():
    """
    Retrieves all active roles dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_roles()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/users", response_model=List[Dict[str, Any]])
def get_client_users():
    """
    Retrieves users dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_users()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/departments", response_model=List[Dict[str, Any]])
def get_client_departments():
    """
    Retrieves departments dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_departments()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/entities", response_model=List[Dict[str, Any]])
def get_client_entities():
    """
    Introspects available business entities/tables from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_entities()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/entities/{entity_name}/fields", response_model=List[Dict[str, Any]])
def get_client_entity_fields(entity_name: str):
    """
    Introspects fields/columns for a specific entity from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_entity_fields(entity_name)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/tables", response_model=List[Dict[str, Any]])
def get_client_tables():
    """
    Dynamically discovers all available tables in the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_tables()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/tables/{table_name}/columns", response_model=Dict[str, Any])
def get_client_table_columns(table_name: str):
    """
    Dynamically discovers columns, data types, nullability, primary keys,
    and foreign keys for a specific table in the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_table_columns(table_name)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")



@catalog_router.get("/metadata/statuses", response_model=List[Dict[str, Any]])
def get_client_statuses(entity_name: Optional[str] = Query(None, description="Optional entity filter")):
    """
    Retrieves statuses dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_statuses(entity_name=entity_name)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/tasks/my-tasks", response_model=List[Dict[str, Any]])
def get_my_pending_tasks(
    user_id: int = Query(..., description="Client Database user ID"),
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves all pending human tasks that the specified user is authorized to perform
    based on dynamic assignment resolution against the Client Database.
    """
    from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
    return StudioExecutionAdapter.get_pending_tasks_for_user(db, user_id=user_id)


@catalog_router.get("/instances/{instance_id}/history", response_model=List[Dict[str, Any]])
def get_instance_workflow_history(
    instance_id: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the full audit timeline from workflow_history for a given workflow instance.
    """
    from app.workflow.models.history import WorkflowHistory
    records = (
        db.query(WorkflowHistory)
        .filter(WorkflowHistory.instance_id == instance_id)
        .order_by(WorkflowHistory.performed_on.asc(), WorkflowHistory.history_id.asc())
        .all()
    )
    return [
        {
            "history_id": r.history_id,
            "instance_id": r.instance_id,
            "from_state_id": r.from_state_id,
            "to_state_id": r.to_state_id,
            "from_state_code": r.from_state_code,
            "to_state_code": r.to_state_code,
            "action_name": r.action_name,
            "performed_by": r.performed_by,
            "performed_role": r.performed_role,
            "remarks": r.remarks,
            "performed_on": r.performed_on.isoformat() if r.performed_on else None
        }
        for r in records
    ]
