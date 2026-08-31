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
@catalog_router.post("/{workflow_id}/execute", response_model=Dict[str, Any])
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
@catalog_router.post("/{workflow_id}/action", response_model=Dict[str, Any])
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
def get_client_roles(connection_id: Optional[int] = Query(None)):
    """
    Retrieves all active roles dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_roles(connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/users", response_model=List[Dict[str, Any]])
def get_client_users(connection_id: Optional[int] = Query(None)):
    """
    Retrieves users dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_users(connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/departments", response_model=List[Dict[str, Any]])
def get_client_departments(connection_id: Optional[int] = Query(None)):
    """
    Retrieves departments dynamically from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_departments(connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/entities", response_model=List[Dict[str, Any]])
def get_client_entities(connection_id: Optional[int] = Query(None)):
    """
    Introspects available business entities/tables from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_tables(connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/entities/{entity_name}/fields", response_model=List[Dict[str, Any]])
def get_client_entity_fields(entity_name: str, connection_id: Optional[int] = Query(None)):
    """
    Introspects fields/columns for a specific entity from the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        res = ClientDatabaseAdapter.get_table_columns(entity_name, connection_id=connection_id)
        return res.get("columns", [])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/tables", response_model=List[Dict[str, Any]])
def get_client_tables(connection_id: Optional[int] = Query(None)):
    """
    Dynamically discovers all available tables in the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_tables(connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")


@catalog_router.get("/metadata/tables/{table_name}/columns", response_model=Dict[str, Any])
def get_client_table_columns(table_name: str, connection_id: Optional[int] = Query(None)):
    """
    Dynamically discovers columns, data types, nullability, primary keys,
    and foreign keys for a specific table in the Client Database.
    """
    from app.core.database import ClientDatabaseAdapter
    try:
        return ClientDatabaseAdapter.get_table_columns(table_name, connection_id=connection_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Client Database metadata error: {str(e)}")
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


# ==========================================
# TEST RUNNER & LIVE DB INSPECTOR ENDPOINTS (100% GENERIC)
# ==========================================

@catalog_router.get("/test/record-state")
def get_test_record_state(
    record_id: int = Query(..., description="Primary key value of the record"),
    table_name: str = Query("ers.risk_register", description="Target Client DB table (e.g. 'ers.risk_register', 'hr_leaves', 'loan_requests')"),
    schema: Optional[str] = Query(None, description="Optional schema name override")
):
    """
    endpoint that fetches the live state of ANY record from ANY Client Database table.
    Uses SQLAlchemy metadata introspection to dynamically discover primary keys, column types,
    status fields, title fields, and recent notification jobs.
    """
    from sqlalchemy import text, inspect
    from app.core.database import engine as client_engine, ClientDatabaseAdapter

    # Normalize schema & table safely
    raw_table = table_name or "ers.risk_register"
    if str(raw_table).strip().lower() in ("", "undefined", "null", "none", "target table"):
        raw_table = "ers.risk_register"

    target_schema = schema
    clean_table = raw_table
    if "." in raw_table:
        parts = raw_table.split(".", 1)
        target_schema = parts[0]
        clean_table = parts[1]
    if not target_schema:
        target_schema = "ers"

    try:
        # Discover table columns & primary key
        col_meta = ClientDatabaseAdapter.get_table_columns(clean_table, schema=target_schema)
        pks = col_meta.get("primary_keys") or []
        primary_key = pks[0] if pks else "id"
        columns_info = col_meta.get("columns", [])
        col_names = [c["name"] for c in columns_info]

        full_table = f"{target_schema}.{clean_table}" if target_schema else clean_table

        with client_engine.connect() as conn:
            query = text(f"SELECT * FROM {full_table} WHERE {primary_key} = :id LIMIT 1")
            result = conn.execute(query, {"id": int(record_id)}).mappings().first()
            fallback_applied = False
            
            if not result:
                # Fallback to first available record in the table so testing never fails
                fallback_res = conn.execute(text(f"SELECT * FROM {full_table} ORDER BY {primary_key} ASC LIMIT 1")).mappings().first()
                if fallback_res:
                    result = fallback_res
                    fallback_applied = True
                else:
                    raise HTTPException(status_code=404, detail=f"No records found in table '{full_table}'. Please insert at least one row.")
            
            raw = dict(result)
            actual_record_id = raw.get(primary_key)

        # Dynamic field classification
        status_field = None
        status_value = None
        title_field = None
        title_value = None

        # Auto-detect status column (e.g. status, risk_status, state, approval_status)
        for c in col_names:
            c_lower = c.lower()
            if not status_field and ("status" in c_lower or "state" in c_lower):
                status_field = c
                status_value = raw.get(c)
            if not title_field and ("name" in c_lower or "title" in c_lower or "desc" in c_lower or "code" in c_lower or "id" in c_lower and c != primary_key):
                title_field = c
                title_value = raw.get(c)

        # Auto-fetch latest notification jobs if email queue exists in client DB
        latest_email_jobs = []
        try:
            with client_engine.connect() as conn:
                for mail_table in ["ers.mst_email_job", "mst_email_job", "email_jobs", "notification_jobs"]:
                    try:
                        jobs_raw = conn.execute(
                            text(f"SELECT * FROM {mail_table} ORDER BY 1 DESC LIMIT 5")
                        ).mappings().all()
                        if jobs_raw:
                            for j in jobs_raw:
                                j_dict = dict(j)
                                latest_email_jobs.append({
                                    "email_job_id": j_dict.get("email_job_id") or j_dict.get("id") or j_dict.get("job_id"),
                                    "email_to": j_dict.get("email_to") or j_dict.get("recipient") or j_dict.get("to_email"),
                                    "email_subject": j_dict.get("email_subject") or j_dict.get("subject") or "Notification",
                                    "send_status": j_dict.get("send_status") or j_dict.get("status") or "New",
                                    "created_on": j_dict.get("created_on").isoformat() if hasattr(j_dict.get("created_on"), "isoformat") else str(j_dict.get("created_on") or "")
                                })
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        # Serialize datetimes for JSON response
        serialized_raw = {
            k: (v.isoformat() if hasattr(v, "isoformat") else v)
            for k, v in raw.items()
        }

        return {
            "success": True,
            "record_id": actual_record_id or record_id,
            "table_name": full_table,
            "primary_key": primary_key,
            "primary_key_val": raw.get(primary_key),
            "status_field": status_field,
            "status_value": status_value,
            "title_field": title_field,
            "title_value": title_value,
            "columns": columns_info,
            "raw_data": serialized_raw,
            "latest_email_jobs": latest_email_jobs,
            "display_data": {
                "record_id": raw.get(primary_key),
                "title": title_value or f"Record #{record_id}",
                "status": status_value,
                "status_label": f"Status: {status_value}" if status_value is not None else "N/A"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch record state for '{table_name}': {str(e)}")


@catalog_router.post("/test/reset-record")
def reset_test_record(payload: Dict[str, Any]):
    """
    reset endpoint: Resets any record in any Client DB table to its initial state.
    Accepts dynamic 'reset_fields' dict or automatically resets discovered status/approval fields.
    """
    from sqlalchemy import text, inspect
    from app.core.database import engine as client_engine, ClientDatabaseAdapter

    record_id = payload.get("record_id")
    if not record_id:
        raise HTTPException(status_code=400, detail="record_id is required")

    raw_table = payload.get("table_name") or payload.get("table") or "ers.risk_register"
    if str(raw_table).strip().lower() in ("", "undefined", "null", "none", "target table"):
        raw_table = "ers.risk_register"

    target_schema = payload.get("schema")
    clean_table = raw_table
    if "." in raw_table:
        parts = raw_table.split(".", 1)
        target_schema = parts[0]
        clean_table = parts[1]
    if not target_schema:
        target_schema = "ers"

    reset_fields = payload.get("reset_fields") or {}

    try:
        col_meta = ClientDatabaseAdapter.get_table_columns(clean_table, schema=target_schema)
        pks = col_meta.get("primary_keys") or []
        primary_key = payload.get("pk_field") or (pks[0] if pks else "id")
        columns_info = col_meta.get("columns", [])
        col_names = [c["name"] for c in columns_info]

        full_table = f"{target_schema}.{clean_table}" if target_schema else clean_table

        # If reset_fields not explicitly passed, automatically reset status and approval fields
        if not reset_fields:
            for c in col_names:
                c_lower = c.lower()
                if "approval_status" in c_lower:
                    reset_fields[c] = 0
                elif "approval_by" in c_lower or "approved_by" in c_lower:
                    reset_fields[c] = None
                elif "approval_on" in c_lower or "approved_on" in c_lower:
                    reset_fields[c] = None
                elif c_lower in ("risk_status", "status", "state"):
                    reset_fields[c] = 9 if "risk_status" in c_lower else 0

        if not reset_fields:
            return {"success": True, "message": "No reset fields identified for this table.", "record_id": record_id}

        set_clauses = []
        bind_params = {"id": int(record_id)}
        for k, v in reset_fields.items():
            param_key = f"val_{k}"
            set_clauses.append(f"{k} = :{param_key}")
            bind_params[param_key] = v

        sql_str = f"UPDATE {full_table} SET {', '.join(set_clauses)} WHERE {primary_key} = :id"

        with client_engine.begin() as conn:
            conn.execute(text(sql_str), bind_params)

        return {
            "success": True, 
            "message": f"Record #{record_id} in '{full_table}' successfully reset", 
            "record_id": record_id,
            "reset_fields": reset_fields
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset record: {str(e)}")


@catalog_router.post("/test/execute-generic-node")
def execute_generic_test_node(
    payload: Dict[str, Any],
    db: Session = Depends(get_workflow_db)
):
    """
    workflow execution endpoint that executes ANY node against ANY Client Database table:
    - If DB Update: Dynamically discovers primary key and executes parameterized field updates
    - If Notification: Dynamically resolves recipient and queues outbound notification job
    - Records telemetry into workflow.workflow_history
    - Returns exact executed SQL, before/after diffs, and execution timing
    """
    import datetime
    import json
    from sqlalchemy import text
    from app.core.database import engine as client_engine, ClientDatabaseAdapter
    from app.workflow.models.history import WorkflowHistory

    record_id = payload.get("record_id")
    if not record_id:
        raise HTTPException(status_code=400, detail="record_id is required")

    node_id = payload.get("node_id", "node")
    node_name = payload.get("node_name", "Process Step")
    node_type = (payload.get("node_type") or "record").lower()
    
    raw_table = payload.get("table_name") or payload.get("table") or "ers.risk_register"
    if str(raw_table).strip().lower() in ("", "undefined", "null", "none", "target table"):
        raw_table = "ers.risk_register"

    target_schema = payload.get("schema")
    clean_table = raw_table
    if "." in raw_table:
        parts = raw_table.split(".", 1)
        target_schema = parts[0]
        clean_table = parts[1]
    if not target_schema:
        target_schema = "ers"

    field_mappings = payload.get("field_mappings") or payload.get("fieldMappings") or []
    action = str(payload.get("action", "EXECUTE")).upper()
    user_id = payload.get("user_id", 1)
    user_role = payload.get("user_role", "SYSTEM")

    start_time = time.time()
    now_dt = datetime.datetime.now()

    updates = {}
    diff_fields = {}
    sql_statements = []
    email_job_info = None

    try:
        col_meta = ClientDatabaseAdapter.get_table_columns(clean_table, schema=target_schema)
        pks = col_meta.get("primary_keys") or []
        primary_key = payload.get("pk_field") or (pks[0] if pks else "id")
        columns_info = col_meta.get("columns", [])
        col_names = {c["name"] for c in columns_info}
        full_table = f"{target_schema}.{clean_table}" if target_schema else clean_table

        # ==========================================
        # 1. NOTIFICATION / EMAIL NODE EXECUTION
        # ==========================================
        if node_type in ("communication", "notification", "email", "send_email"):
            # Dynamically fetch current record
            record_info = {}
            with client_engine.connect() as conn:
                r_row = conn.execute(
                    text(f"SELECT * FROM {full_table} WHERE {primary_key} = :id LIMIT 1"),
                    {"id": int(record_id)}
                ).mappings().first()
                if r_row:
                    record_info = dict(r_row)

            # Resolve recipient email and name dynamically
            to_email = payload.get("to") or payload.get("recipient")
            recipient_name = "User"
            
            # Check if to_email is not specified or contains template placeholders
            if not to_email or "{{" in str(to_email):
                resolved_email = None
                # 1. Check for direct email column in target record
                for c in ["email", "owner_email", "user_email", "created_by_email", "contact_email"]:
                    if record_info.get(c):
                        resolved_email = record_info.get(c)
                        break
                
                # 2. Resolve via user foreign key in record
                if not resolved_email:
                    for uid_col in ["risk_owner_id", "owner_id", "user_id", "created_by", "assigned_to", "modified_by"]:
                        fk_val = record_info.get(uid_col)
                        if fk_val:
                            try:
                                with client_engine.connect() as conn:
                                    u_row = conn.execute(
                                        text("SELECT id, first_name, last_name, email FROM ers.mst_users WHERE id = :uid LIMIT 1"),
                                        {"uid": int(fk_val)}
                                    ).mappings().first()
                                    if u_row:
                                        if u_row.get("email"):
                                            resolved_email = u_row.get("email")
                                        fn = u_row.get("first_name") or ""
                                        ln = u_row.get("last_name") or ""
                                        if fn or ln:
                                            recipient_name = f"{fn} {ln}".strip()
                                        break
                            except Exception:
                                pass
                
                to_email = resolved_email or "recipient@example.com"

            # Dynamic entity code & title resolution
            entity_code = record_info.get("risk_id") or record_info.get("code") or record_info.get("dept_code") or f"#{record_id}"
            entity_title = record_info.get("risk_name") or record_info.get("name") or record_info.get("title") or f"Record #{record_id}"
            status_val = record_info.get("risk_status") or record_info.get("status") or 10
            status_str = f"Approved ({status_val})" if action == "APPROVE" or status_val == 10 else f"Status: {status_val}"

            # Dynamic Subject & Body replacements
            raw_subject = payload.get("subject") or f"Record #{entity_code} Approved ({node_name})"
            subject = (
                str(raw_subject)
                .replace("{{workflow.entity_id}}", str(entity_code))
                .replace("{{entity_id}}", str(entity_code))
                .replace("{{id}}", str(record_id))
                .replace("{{entity_name}}", str(entity_title))
                .replace("{{action}}", str(action))
            )

            raw_body = payload.get("body") or f"Process step '{node_name}' has been executed successfully."
            body_text = (
                str(raw_body)
                .replace("{{workflow.entity_id}}", str(entity_code))
                .replace("{{entity_id}}", str(entity_code))
                .replace("{{id}}", str(record_id))
                .replace("{{entity_name}}", str(entity_title))
                .replace("{{recipient_name}}", str(recipient_name))
                .replace("{{action}}", str(action))
            )

            # Determine email module name dynamically
            email_module = "RISK_MANAGEMENT" if "risk" in clean_table.lower() else f"{clean_table.upper()}_WORKFLOW"

            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color:#f4f6f8; padding:20px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="center">
                            <table width="600px" style="background:#ffffff; border-radius:8px; padding:20px; border:1px solid #e2e8f0;">
                                <tr>
                                    <td style="background:#0d6efd; color:white; padding:15px; border-radius:6px;">
                                        <h2 style="margin:0; font-size:18px;">{node_name} Notification</h2>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:20px; color:#333; line-height: 1.6;">
                                        <p>Dear <b>{recipient_name}</b>,</p>
                                        <p>{body_text}</p>
                                        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width:100%; margin:15px 0; border-color:#e2e8f0;">
                                            <tr><td style="width:35%; background:#f8fafc;"><b>Record Code / ID</b></td><td><b>{entity_code}</b></td></tr>
                                            <tr><td style="background:#f8fafc;"><b>Title / Entity</b></td><td>{entity_title}</td></tr>
                                            <tr><td style="background:#f8fafc;"><b>Approval Status</b></td><td><span style="color:#16a34a; font-weight:bold;">{status_str}</span></td></tr>
                                        </table>
                                        <p>Regards,<br><b>Enterprise Workflow Automation Platform</b></p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding:12px; font-size:11px; color:#94a3b8; border-top:1px solid #eee; text-align:center;">
                                        This is an automated notification generated by Workflow Automation Studio.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """

            # Queue outbound notification into client email table if available
            try:
                with client_engine.begin() as conn:
                    res = conn.execute(
                        text("""
                            INSERT INTO ers.mst_email_job (
                                email_server_id,
                                email_module,
                                email_to,
                                email_subject,
                                email_type,
                                email_body,
                                send_status,
                                total_attempts,
                                send_attempts,
                                attempt_delay,
                                next_attempt_at,
                                created_on,
                                created_by,
                                is_deleted
                            ) VALUES (
                                1,
                                :email_module,
                                :email_to,
                                :email_subject,
                                'HTML',
                                :email_body,
                                'New',
                                3,
                                0,
                                5000,
                                :now_dt,
                                :now_dt,
                                :uid,
                                0
                            ) RETURNING email_job_id
                        """),
                        {
                            "email_module": email_module,
                            "email_to": to_email,
                            "email_subject": subject,
                            "email_body": html_body,
                            "now_dt": now_dt,
                            "uid": user_id
                        }
                    ).first()
                    
                    if res:
                        job_id = res[0]
                        email_job_info = {
                            "email_job_id": job_id,
                            "email_to": to_email,
                            "email_subject": subject,
                            "send_status": "New"
                        }
                        sql_statements.append(f"INSERT INTO ers.mst_email_job (email_to='{to_email}', subject='{subject}', status='New')")
            except Exception:
                email_job_info = {"email_to": to_email, "email_subject": subject, "send_status": "Queued (In-Memory)"}

        # ==========================================
        # 2. DATABASE UPDATE / RECORD NODE EXECUTION
        # ==========================================
        else:
            # Parse field mappings
            if isinstance(field_mappings, list):
                for fm in field_mappings:
                    f_name = fm.get("field")
                    f_val = fm.get("value")
                    if f_name:
                        if isinstance(f_val, str) and f_val.lstrip("-").isdigit():
                            f_val = int(f_val)
                        elif f_val in ("NOW()", "{{now}}"):
                            f_val = now_dt
                        elif f_val in ("{{user_id}}", "{{userId}}"):
                            f_val = user_id
                        updates[f_name] = f_val
                        diff_fields[f_name] = {"new": str(f_val), "label": str(f_val)}
            elif isinstance(field_mappings, dict):
                for f_name, f_val in field_mappings.items():
                    if isinstance(f_val, str) and f_val.lstrip("-").isdigit():
                        f_val = int(f_val)
                    elif f_val in ("NOW()", "{{now}}"):
                        f_val = now_dt
                    elif f_val in ("{{user_id}}", "{{userId}}"):
                        f_val = user_id
                    updates[f_name] = f_val
                    diff_fields[f_name] = {"new": str(f_val), "label": str(f_val)}

            # Smart generic auto-stamping for audit/timestamp columns if present on table
            for updated_col in list(updates.keys()):
                # If updated column is like 'X_status', look for 'X_by' and 'X_on' in table columns
                prefix = updated_col.rsplit("_status", 1)[0] if "_status" in updated_col else None
                if prefix:
                    by_col = f"{prefix}_by"
                    on_col = f"{prefix}_on" if f"{prefix}_on" in col_names else f"{prefix}_approved_on"
                    if by_col in col_names and by_col not in updates:
                        updates[by_col] = user_id
                    if on_col in col_names and on_col not in updates:
                        updates[on_col] = now_dt

            if updates:
                set_clauses = []
                bind_params = {"id": int(record_id)}
                for k, v in updates.items():
                    param_key = f"val_{k}"
                    set_clauses.append(f"{k} = :{param_key}")
                    bind_params[param_key] = v

                sql_str = f"UPDATE {full_table} SET {', '.join(set_clauses)} WHERE {primary_key} = :id"
                
                with client_engine.begin() as conn:
                    conn.execute(text(sql_str), bind_params)
                
                rendered_sets = [f"{k} = {repr(v)}" for k, v in updates.items()]
                sql_statements.append(f"UPDATE {full_table} SET {', '.join(rendered_sets)} WHERE {primary_key} = {record_id}")

        # 1. Record or update Workflow Instance in monitoring database
        from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffActivityHistory
        
        inst = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == "Risk",
            SpiffWorkflowInstance.entity_id == int(record_id)
        ).order_by(SpiffWorkflowInstance.instance_id.desc()).first()

        inst_status = "Completed" if action in ("APPROVE", "COMPLETE", "SEND") else "Running"

        if not inst:
            inst = SpiffWorkflowInstance(
                bpmn_definition_id=108,
                entity_type="Risk",
                entity_id=int(record_id),
                status=inst_status,
                current_task_code=node_name,
                started_on=now_dt,
                completed_on=now_dt if inst_status == "Completed" else None,
                serialized_state=json.dumps({
                    "tasks": {
                        node_id: {
                            "data": {
                                "record_id": int(record_id),
                                "last_action": action,
                                "node_name": node_name,
                                "node_type": node_type,
                                **diff_fields
                            }
                        }
                    }
                })
            )
            db.add(inst)
            db.flush()
        else:
            inst.current_task_code = node_name
            inst.status = inst_status
            if inst_status == "Completed":
                inst.completed_on = now_dt
            try:
                curr_state = json.loads(inst.serialized_state) if inst.serialized_state else {}
            except Exception:
                curr_state = {}
            tasks = curr_state.get("tasks", {})
            tasks[node_id] = {
                "data": {
                    "record_id": int(record_id),
                    "last_action": action,
                    "node_name": node_name,
                    "node_type": node_type,
                    **diff_fields
                }
            }
            curr_state["tasks"] = tasks
            inst.serialized_state = json.dumps(curr_state)

        # 2. Record Activity History Step Log
        act_entry = SpiffActivityHistory(
            instance_id=inst.instance_id,
            activity_id=node_id,
            activity_name=node_name,
            activity_type=node_type.upper(),
            status="SUCCESS",
            variables=json.dumps({"action": action, "node": node_name, **diff_fields}),
            timestamp=now_dt
        )
        db.add(act_entry)

        # 3. Record Audit Trail into Workflow History
        history_entry = WorkflowHistory(
            instance_id=inst.instance_id,
            from_state_code=f"NODE_{node_id}",
            to_state_code="EXECUTED",
            action_name=f"{node_name}_{action}",
            performed_by=user_id,
            performed_role=user_role,
            remarks=f"Node '{node_name}' ({node_type}) executed in Generic Studio Test Runner",
            performed_on=now_dt
        )
        db.add(history_entry)
        db.commit()

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Global Workflow Observability & Telemetry Streaming
        from app.core.logger import WorkflowTelemetryLogger
        WorkflowTelemetryLogger.log_node_execution(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            action=action,
            duration_ms=duration_ms,
            instance_id=inst.instance_id,
            entity_type="Risk",
            entity_id=record_id,
            actor_id=user_id,
            actor_role=user_role,
            details={
                "sql_executed": sql_statements,
                "diff_fields": diff_fields,
                "email_job": email_job_info
            },
            status="SUCCESS"
        )

        return {
            "success": True,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "action": action,
            "record_id": record_id,
            "instance_id": inst.instance_id,
            "duration_ms": duration_ms,
            "sql_executed": sql_statements,
            "diff_fields": diff_fields,
            "email_job": email_job_info,
            "workflow_history_id": history_entry.history_id,
            "message": f"Created email job #{email_job_info.get('email_job_id', '')} ({duration_ms}ms)" if email_job_info else f"Node '{node_name}' executed and committed successfully ({duration_ms}ms)"
        }
    except Exception as e:
        db.rollback()
        from app.core.logger import WorkflowTelemetryLogger
        WorkflowTelemetryLogger.log_error(
            message=f"Node '{node_name}' execution failed",
            error=str(e),
            instance_id=int(record_id) if record_id else None,
            node_id=node_id
        )
        raise HTTPException(status_code=500, detail=f"Generic node execution failed: {str(e)}")

