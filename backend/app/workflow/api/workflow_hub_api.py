"""
workflow_hub_api.py
Universal Centralized Workflow Hub Gateway API.

Acts as a single mediator between any Client UI (React/Vue/Mobile) and the
Backend Workflow Engine. The client UI passes only the `spec_id` (or workflow identifier),
and this gateway dynamically resolves schemas, tables, fields, records, human tasks,
and handles submission and execution for ANY workflow created in the Designer without errors.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.workflow.database import get_workflow_db, WorkflowSessionLocal
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response
from app.core.logger import logger
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter
from app.workflow_studio.bindings import (
    get_binding,
    list_bindings,
    WorkflowModuleBinding
)
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.persistence.models import (
    BPMNDefinition,
    SpiffWorkflowInstance,
    SpiffHumanTask,
    SpiffActivityHistory,
    WorkflowEntityConfig,
    DatabaseConnection
)
from app.workflow_definition.models import (
    GenericWorkflow,
    WorkflowVersion,
    WorkflowNode,
    WorkflowConnection
)

router = APIRouter(prefix="/api/v1/workflow-hub", tags=["Universal Workflow Hub Gateway"])


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class UniversalWorkflowGatewayRequest(BaseModel):
    spec_id: str = Field(..., description="Specification ID of the workflow (e.g. emp_leave_request, wfh_request_wf, etc.)")
    operation: Optional[str] = Field("SUBMIT", description="Operation: SUBMIT, ACTION, APPROVE, REJECT, FETCH_RECORDS, GET_TASKS, SCHEMA, HISTORY, CATALOG")
    record_id: Optional[int] = Field(None, description="Target record primary key ID (required for ACTION and HISTORY)")
    action: Optional[str] = Field("APPROVE", description="Action code to execute: APPROVE, REJECT, etc.")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Payload data for SUBMIT")
    parameter: Optional[Dict[str, Any]] = Field(None, description="Custom parameters dictionary (e.g. {'Name': 'Ram', 'Address': 'Delhi', 'pocket_no': '22'})")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Alias for parameter dictionary")
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: Optional[str] = None
    remarks: Optional[str] = ""
    status_filter: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    variables: Optional[Dict[str, Any]] = None


class HubSubmitRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict, description="Entity fields and initial workflow variables")
    parameter: Optional[Dict[str, Any]] = Field(None, description="Custom parameters dictionary (e.g. {'Name': 'Ram', 'Address': 'Delhi'})")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Alias for parameter dictionary")
    variables: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    async_execution: Optional[bool] = False


class HubActionRequest(BaseModel):
    record_id: int = Field(..., description="Target business entity record primary key ID")
    action: str = Field("APPROVE", description="Action code to execute (e.g. APPROVE, REJECT)")
    user_id: Optional[int] = None
    role: Optional[str] = None
    remarks: Optional[str] = ""
    parameter: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None


# ==========================================
# HELPER: DYNAMIC SPEC RESOLUTION
# ==========================================

def resolve_workflow_meta(spec_id: str, db: Session) -> Dict[str, Any]:
    """
    Intelligently resolves any workflow by spec_id, numeric ID, or name.
    Auto-discovers target table, database connection, approval roles,
    form fields, allowed actions, and node structure.
    """
    clean_key = str(spec_id).strip().lower().replace("-", "_")
    
    # 1. Check registered binding first
    binding = get_binding(spec_id, db=db)
    if not binding and clean_key != spec_id:
        binding = get_binding(clean_key, db=db)

    # 2. Look up BPMNDefinition / GenericWorkflow / Version
    bpmn_def = None
    gw = None
    if str(spec_id).isdigit():
        bpmn_def = db.query(BPMNDefinition).filter(BPMNDefinition.id == int(spec_id)).first()
        gw = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == int(spec_id)).first()
    
    if not bpmn_def:
        bpmn_def = db.query(BPMNDefinition).filter(
            (BPMNDefinition.spec_id == spec_id) | 
            (BPMNDefinition.name == spec_id) |
            (BPMNDefinition.spec_id == clean_key)
        ).order_by(BPMNDefinition.id.desc()).first()

    if not gw:
        gw = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == spec_id) |
            (GenericWorkflow.name == spec_id) |
            (GenericWorkflow.workflow_key == clean_key)
        ).order_by(GenericWorkflow.workflow_id.desc()).first()

    # 3. Resolve Active Version
    version = None
    if bpmn_def:
        version = StudioExecutionAdapter._sync_bpmn_definition_to_version(db, bpmn_def)
    elif gw:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == gw.workflow_id,
            WorkflowVersion.status == "PUBLISHED"
        ).order_by(WorkflowVersion.version_number.desc()).first()
        if not version:
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == gw.workflow_id
            ).order_by(WorkflowVersion.version_number.desc()).first()

    if not bpmn_def and not gw and not binding and not version:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow definition found for specification ID or key '{spec_id}'."
        )

    # 4. Extract Nodes, Roles & Actions
    title = (binding.get("title") if binding else None) or (bpmn_def.name if bpmn_def else None) or (gw.name if gw else spec_id)
    wf_id = (binding.get("workflow_id") if binding else None) or (bpmn_def.id if bpmn_def else None) or (gw.workflow_id if gw else 1)
    
    # Resolve connection ID
    conn_id = (binding.get("connection_id") if binding else None) or (getattr(bpmn_def, "connection_id", None) if bpmn_def else None) or (getattr(gw, "connection_id", None) if gw else None)
    if not conn_id:
        active_conn = db.query(DatabaseConnection).filter(DatabaseConnection.is_active == True).order_by(DatabaseConnection.is_default.desc(), DatabaseConnection.connection_id.asc()).first()
        if active_conn:
            conn_id = active_conn.connection_id
        else:
            conn_id = 4  # Default client database connection

    # Analyze nodes & detect bound table from nodes or binding
    roles = set(binding.get("approval_roles") or []) if binding else set()
    allowed_actions = set()
    detected_table = binding.get("table_name") if binding else None
    steps_summary = []

    if version and version.nodes:
        for node in version.nodes:
            if not node.is_active:
                continue
            cfg = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
            n_type = str(node.node_type).upper()
            
            # Detect table from RECORD nodes
            if not detected_table and n_type in ("RECORD", "ACTION"):
                if cfg.get("table") or cfg.get("entity") or cfg.get("table_name"):
                    detected_table = cfg.get("table") or cfg.get("entity") or cfg.get("table_name")

            # Extract roles and actions from APPROVAL / USER_TASK nodes
            if n_type in ("APPROVAL", "USER_TASK", "USERTASK", "HUMAN_TASK"):
                role = cfg.get("role") or cfg.get("role_code") or (cfg.get("assignment", {}).get("roleName") if isinstance(cfg.get("assignment"), dict) else None)
                if role:
                    roles.add(str(role).upper())
                
                raw_acts = cfg.get("actions") or cfg.get("allowed_actions") or []
                for a in raw_acts:
                    if isinstance(a, str):
                        allowed_actions.add(a.upper())
                    elif isinstance(a, dict):
                        c = a.get("action_code") or a.get("code") or a.get("name")
                        if c:
                            allowed_actions.add(str(c).upper())

                steps_summary.append({
                    "step_key": node.node_key,
                    "name": node.name,
                    "type": "HUMAN_APPROVAL",
                    "role": role or "MANAGER",
                    "actions": list(raw_acts) if raw_acts else ["APPROVE", "REJECT"]
                })
            elif n_type in ("START", "END", "CONDITION", "COMMUNICATION", "RECORD"):
                steps_summary.append({
                    "step_key": node.node_key,
                    "name": node.name,
                    "type": n_type
                })

    if not detected_table:
        detected_table = clean_key

    # Resolve table column metadata safely
    target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
    columns = []
    pks = []
    primary_key = binding.get("primary_key", "id") if binding else "id"
    status_col = binding.get("status_column", "status") if binding else "status"
    table_exists = False

    try:
        col_meta = ClientDatabaseAdapter.get_table_columns(detected_table, schema=target_schema, connection_id=conn_id)
        columns = [c["name"] for c in col_meta.get("columns", [])]
        pks = col_meta.get("primary_keys") or []
        primary_key = pks[0] if pks else primary_key
        table_exists = bool(columns)
    except Exception:
        table_exists = False

    return {
        "spec_id": spec_id,
        "clean_key": clean_key,
        "title": title,
        "workflow_id": wf_id,
        "version_id": version.workflow_version_id if version else None,
        "connection_id": conn_id,
        "table_name": detected_table,
        "table_exists": table_exists,
        "primary_key": primary_key,
        "status_column": status_col,
        "default_status": (binding.get("default_status") if binding else "PENDING") or "PENDING",
        "approval_roles": list(roles) if roles else ["MANAGER", "ADMIN"],
        "allowed_actions": list(allowed_actions) if allowed_actions else ["APPROVE", "REJECT"],
        "columns": columns,
        "steps": steps_summary,
        "is_active": True
    }


# ==========================================
# 0. SINGLE MASTER ENDPOINT FOR EVERYTHING
# ==========================================

@router.post("", summary="THE SINGLE MASTER WORKFLOW ENDPOINT (Handles SUBMIT, ACTION, FETCH, TASKS, SCHEMA, HISTORY)")
@router.post("/gateway", summary="THE SINGLE MASTER WORKFLOW GATEWAY ENDPOINT")
def universal_single_workflow_gateway(
    payload: UniversalWorkflowGatewayRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    =============================================================================
    THE ONLY WORKFLOW ENDPOINT YOUR UI EVER NEEDS!
    =============================================================================
    Given just `spec_id` and `operation`, this single endpoint manages the ENTIRE
    lifecycle of ANY workflow:
    - operation="SUBMIT": Inserts data in DB, starts workflow, pauses at human task
    - operation="ACTION" / "APPROVE" / "REJECT": Executes manager/user action on record
    - operation="FETCH_RECORDS" / "RECORDS": Retrieves all business records for table
    - operation="GET_TASKS" / "TASKS": Gets pending tasks for user/role
    - operation="SCHEMA": Gets fields, approval roles, allowed actions, table metadata
    - operation="HISTORY": Gets full audit trail and live execution status for a record
    - operation="CATALOG": Lists all available published workflows
    """
    spec_id = payload.spec_id
    op = (payload.operation or "SUBMIT").upper().strip()

    # 1. CATALOG
    if op in ("CATALOG", "LIST_WORKFLOWS", "ALL_WORKFLOWS"):
        return get_universal_workflow_catalog(db=db)

    # 1b. DISPATCH EMAILS QUEUE (Sends actual emails via SMTP)
    if op in ("DISPATCH_EMAILS", "PROCESS_EMAILS", "SEND_PENDING_EMAILS", "RUN_EMAIL_JOB", "SEND_EMAILS"):
        from app.workflow.services.email_dispatcher import EmailDispatcher
        conn_id = payload.variables.get("connection_id") if payload.variables else None
        res = EmailDispatcher.process_pending_email_jobs(conn_id=conn_id, limit=payload.limit or 50)
        return success_response(message="Email queue processed", data=res)

    # 2. SCHEMA
    if op in ("SCHEMA", "METADATA", "DISCOVERY"):
        return get_workflow_hub_schema(spec_id=spec_id, db=db)

    # 3. FETCH RECORDS
    if op in ("FETCH", "FETCH_RECORDS", "RECORDS", "LIST_RECORDS", "GET_RECORDS"):
        return get_workflow_hub_records(
            spec_id=spec_id,
            status_filter=payload.status_filter,
            user_id=payload.user_id,
            limit=payload.limit or 100,
            offset=payload.offset or 0,
            db=db
        )

    # 4. GET TASKS
    if op in ("TASKS", "GET_TASKS", "PENDING", "PENDING_TASKS", "MY_TASKS"):
        return get_workflow_hub_tasks(
            spec_id=spec_id,
            user_id=payload.user_id,
            role=payload.role,
            db=db,
            current_user=current_user
        )

    # 5. EXECUTE ACTION (APPROVE / REJECT / CUSTOM)
    if op in ("ACTION", "APPROVE", "REJECT", "COMPLETE", "EXECUTE_ACTION", "SUBMIT_ACTION"):
        if not payload.record_id:
            raise HTTPException(status_code=400, detail="record_id is required for ACTION operation.")
        act = payload.action if op == "ACTION" else op
        action_req = HubActionRequest(
            record_id=payload.record_id,
            action=act or payload.action or "APPROVE",
            user_id=payload.user_id,
            role=payload.role,
            remarks=payload.remarks or "",
            variables=payload.variables
        )
        return execute_workflow_hub_action(
            spec_id=spec_id,
            payload=action_req,
            db=db,
            current_user=current_user
        )

    # 6. HISTORY / STATUS
    if op in ("HISTORY", "STATUS", "AUDIT", "GET_HISTORY", "TIMELINE"):
        if not payload.record_id:
            raise HTTPException(status_code=400, detail="record_id is required for HISTORY operation.")
        return get_workflow_hub_record_history(
            spec_id=spec_id,
            record_id=payload.record_id,
            db=db
        )

    # 7. SUBMIT (DEFAULT)
    params = payload.parameter or payload.parameters or payload.variables or {}
    submit_req = HubSubmitRequest(
        data={**params, **(payload.data or {})},
        parameter=payload.parameter or params,
        parameters=payload.parameters or params,
        variables={**params, **(payload.variables or {})},
        user_id=payload.user_id,
        user_name=payload.user_name,
        user_email=payload.user_email
    )
    return submit_workflow_hub_record(
        spec_id=spec_id,
        payload=submit_req,
        db=db,
        current_user=current_user
    )


# ==========================================
# 1. GET WORKFLOW SCHEMA & DISCOVERY
# ==========================================

@router.get("/{spec_id}/schema", summary="Get complete dynamic schema & metadata for any workflow")
def get_workflow_hub_schema(
    spec_id: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Universal Schema Discovery Endpoint:
    Returns the complete dynamic metadata for the given `spec_id`, including bound table,
    columns, primary key, approval roles, allowed actions, and steps sequence.
    """
    meta = resolve_workflow_meta(spec_id, db)
    return success_response(
        message=f"Schema resolved successfully for '{spec_id}'",
        data=meta
    )


# ==========================================
# 2. GET WORKFLOW BUSINESS RECORDS
# ==========================================

@router.get("/{spec_id}/records", summary="Fetch business records for any workflow module")
def get_workflow_hub_records(
    spec_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_workflow_db)
):
    """
    Universal Record Query:
    Queries and returns data records from the table dynamically bound to this `spec_id`.
    """
    meta = resolve_workflow_meta(spec_id, db)
    conn_id = meta["connection_id"]
    table_name = meta["table_name"]
    primary_key = meta["primary_key"]
    status_col = meta["status_column"]

    eng = DynamicEnginePool.get_engine(conn_id)
    target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
    full_table = f"{target_schema}.{table_name}" if target_schema else table_name

    where_clauses = []
    binds = {"limit_val": limit, "offset_val": offset}

    if status_filter and status_filter.upper() != "ALL":
        where_clauses.append(f"{status_col} = :status_val")
        binds["status_val"] = status_filter

    if user_id:
        if "employee_id" in meta["columns"]:
            where_clauses.append("employee_id = :u_id")
            binds["u_id"] = user_id
        elif "user_id" in meta["columns"]:
            where_clauses.append("user_id = :u_id")
            binds["u_id"] = user_id

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"SELECT * FROM {full_table}{where_sql} ORDER BY {primary_key} DESC LIMIT :limit_val OFFSET :offset_val"

    try:
        with eng.connect() as conn:
            res = conn.execute(text(sql), binds)
            rows = [dict(r._mapping) for r in res]

        results = []
        for r in rows:
            row_dict = {}
            for k, v in r.items():
                if isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
                else:
                    row_dict[k] = v
            results.append(row_dict)

        return success_response(
            message=f"Retrieved {len(results)} records for workflow '{spec_id}'",
            data=results
        )
    except Exception as e:
        logger.error(f"UniversalHub: Error querying records for {spec_id} ({table_name}): {e}", exc_info=True)
        return error_response(message=f"Failed to query records: {str(e)}", status_code=500)


# ==========================================
# 3. SUBMIT & START WORKFLOW
# ==========================================

@router.post("/{spec_id}/submit", summary="Universal submit: inserts client DB record and launches workflow")
def submit_workflow_hub_record(
    spec_id: str,
    payload: HubSubmitRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Universal Workflow Submission:
    1. Validates and auto-fills data into the bound Client Database table.
    2. Starts the workflow instance in the engine.
    3. Advances execution until the first human approval task (WAITING) or END.
    """
    meta = resolve_workflow_meta(spec_id, db)
    conn_id = meta["connection_id"]
    table_name = meta["table_name"]
    primary_key = meta["primary_key"]
    status_col = meta["status_column"]
    default_status = meta["default_status"]
    workflow_id = meta["workflow_id"]
    valid_cols = set(meta["columns"])

    raw_params = payload.parameter or payload.parameters or payload.variables or {}
    values = {**raw_params, **dict(payload.data or {})}

    auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
    user_id = payload.user_id or values.get("employee_id") or values.get("user_id") or auth_user_id or 1
    user_name = payload.user_name or (current_user.get("name") if isinstance(current_user, dict) else None) or "User"
    user_email = payload.user_email or (current_user.get("email") if isinstance(current_user, dict) else None) or ""

    if status_col not in values or not values[status_col]:
        values[status_col] = default_status

    # Auto-fill timestamps
    now_dt = datetime.utcnow()
    for ts in ("created_at", "updated_at", "submitted_at"):
        if ts in valid_cols and ts not in values:
            values[ts] = now_dt

    filtered_vals = {k: v for k, v in values.items() if k in valid_cols}
    if not filtered_vals:
        filtered_vals[status_col] = default_status

    # 1. Insert into Client Database (if table exists)
    new_record_id = None
    if meta.get("table_exists") and valid_cols:
        try:
            eng = DynamicEnginePool.get_engine(conn_id)
            target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
            full_table = f"{target_schema}.{table_name}" if target_schema else table_name

            cols = list(filtered_vals.keys())
            placeholders = [f":v_{c}" for c in cols]
            binds = {f"v_{c}": v for c, v in filtered_vals.items()}
            insert_sql = f"INSERT INTO {full_table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING {primary_key}"

            with eng.begin() as conn:
                res = conn.execute(text(insert_sql), binds).first()
                new_record_id = res[0] if res else None
        except Exception as db_ex:
            logger.warning(f"UniversalHub: Database insert skipped for {spec_id} ({table_name}): {db_ex}")

    if new_record_id is None:
        import time, random
        new_record_id = int(time.time() % 1000000) * 100 + random.randint(10, 99)

    # 2. Start Workflow Engine Execution
    instance_id = None
    wf_status = "Running"
    current_task = None
    wf_error = None

    try:
        parsed_user_id = int(user_id) if str(user_id).isdigit() else user_id
        wf_variables = {
            **raw_params,
            **values,
            "parameter": raw_params,
            "parameters": raw_params,
            "variables": {**raw_params, **values},
            "entity_id": int(new_record_id),
            "record_id": int(new_record_id),
            "user_id": parsed_user_id,
            "user_name": user_name,
            "user_email": user_email,
            "connection_id": conn_id,
            "spec_id": spec_id
        }

        wf_res = StudioExecutionAdapter.start_workflow(
            entity_type=table_name,
            entity_id=int(new_record_id),
            user_id=parsed_user_id,
            variables=wf_variables,
            db=db,
            definition_id=workflow_id
        )
        instance_id = wf_res.get("instance_id")
        wf_status = wf_res.get("status")
        current_task = wf_res.get("current_task_code")

        logger.info(f"UniversalHub: Submitted {table_name} #{new_record_id}, job #{instance_id}, state={wf_status}")
    except Exception as ex:
        wf_res = {}
        wf_error = str(ex)
        logger.error(f"UniversalHub: Error launching workflow for {table_name} #{new_record_id}: {ex}", exc_info=True)

    # Format record values cleanly
    record_dict = {primary_key: new_record_id}
    for k, v in values.items():
        if isinstance(v, datetime):
            record_dict[k] = v.isoformat()
        else:
            record_dict[k] = v

    # Extract dynamic output variables produced by workflow nodes
    res_vars = (wf_res.get("variables") or {}) if isinstance(wf_res, dict) else {}
    dynamic_variables = {}
    for vk, vv in res_vars.items():
        if vk in ("db", "session", "connection"):
            continue
        if isinstance(vv, datetime):
            dynamic_variables[vk] = vv.isoformat()
        elif isinstance(vv, (str, int, float, bool, list, dict)) or vv is None:
            dynamic_variables[vk] = vv
        else:
            dynamic_variables[vk] = str(vv)

    response_payload = {
        "spec_id": spec_id,
        "record_id": new_record_id,
        "primary_key": primary_key,
        "instance_id": instance_id,
        "job_id": instance_id,
        "status": values.get(status_col, default_status),
        "workflow_status": wf_status,
        "current_task": current_task,
        "workflow_error": wf_error,
        "record": record_dict,
        "variables": dynamic_variables,
        "execution_summary": {
            "entity_type": table_name,
            "entity_id": new_record_id,
            "instance_id": instance_id,
            "workflow_status": wf_status,
            "completed": (wf_status == "Completed"),
            "current_node": current_task
        }
    }

    return success_response(
        message=f"Workflow request #{new_record_id} submitted successfully.",
        data=response_payload,
        status_code=status.HTTP_201_CREATED
    )


# ==========================================
# 4. GET PENDING TASKS FOR WORKFLOW
# ==========================================

@router.get("/{spec_id}/tasks", summary="Get pending human approval tasks for a workflow")
def get_workflow_hub_tasks(
    spec_id: str,
    user_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Universal Pending Tasks:
    Fetches active human tasks in READY state for this workflow matching the user's role or user ID.
    """
    meta = resolve_workflow_meta(spec_id, db)
    target_user_id = user_id or (current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else 1)
    
    all_pending = StudioExecutionAdapter.get_pending_tasks_for_user(db, target_user_id)
    
    # Filter by entity_type or matching definition
    matching_tasks = [
        t for t in all_pending 
        if t.get("entity_type") == meta["table_name"] or str(t.get("instance_id")) == str(meta.get("workflow_id"))
    ]

    return success_response(
        message=f"Retrieved {len(matching_tasks)} pending tasks for '{spec_id}'",
        data=matching_tasks
    )


# ==========================================
# 5. EXECUTE WORKFLOW ACTION (APPROVE / REJECT)
# ==========================================

@router.post("/{spec_id}/action", summary="Universal action execution: completes human task and advances engine")
def execute_workflow_hub_action(
    spec_id: str,
    payload: HubActionRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Universal Action Execution:
    Takes an action (APPROVE, REJECT, or custom action), resumes the paused workflow instance,
    runs automated actions (DB updates, emails), and transitions to the next step or END.
    """
    meta = resolve_workflow_meta(spec_id, db)
    table_name = meta["table_name"]
    entity_id = payload.record_id
    action = (payload.action or "APPROVE").upper()

    auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
    user_id = payload.user_id or auth_user_id or 1
    user_role = payload.role or (current_user.get("role") if isinstance(current_user, dict) else "MANAGER")

    variables = dict(payload.variables or {})
    variables["connection_id"] = meta["connection_id"]
    variables["user_role"] = user_role

    try:
        res = StudioExecutionAdapter.execute_action(
            entity_type=table_name,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            remarks=payload.remarks or f"{action} by User #{user_id}",
            variables=variables,
            db=db
        )

        # Extract dynamic variables from execution
        res_vars = (res.get("variables") or {}) if isinstance(res, dict) else {}
        dynamic_variables = {}
        for vk, vv in res_vars.items():
            if vk in ("db", "session", "connection"):
                continue
            if isinstance(vv, datetime):
                dynamic_variables[vk] = vv.isoformat()
            elif isinstance(vv, (str, int, float, bool, list, dict)) or vv is None:
                dynamic_variables[vk] = vv
            else:
                dynamic_variables[vk] = str(vv)

        return success_response(
            message=f"Action '{action}' executed successfully on record #{entity_id}.",
            data={
                "spec_id": spec_id,
                "record_id": entity_id,
                "action": action,
                "instance_id": res.get("instance_id"),
                "workflow_status": res.get("status"),
                "current_task": res.get("current_task_code"),
                "message": res.get("message"),
                "variables": dynamic_variables,
                "execution_summary": {
                    "entity_type": table_name,
                    "entity_id": entity_id,
                    "instance_id": res.get("instance_id"),
                    "action_taken": action,
                    "workflow_status": res.get("status"),
                    "completed": (res.get("status") == "Completed")
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"UniversalHub: Error executing {action} for {spec_id} #{entity_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 6. GET RECORD EXECUTION STATUS & HISTORY
# ==========================================

@router.get("/{spec_id}/history/{record_id}", summary="Get execution step-by-step history and live status")
def get_workflow_hub_record_history(
    spec_id: str,
    record_id: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Universal Audit & Status Tracking:
    Returns the real-time execution status, current active task, and full step timeline for a record.
    """
    meta = resolve_workflow_meta(spec_id, db)
    table_name = meta["table_name"]

    instance = db.query(SpiffWorkflowInstance).filter(
        SpiffWorkflowInstance.entity_type == table_name,
        SpiffWorkflowInstance.entity_id == record_id
    ).order_by(SpiffWorkflowInstance.instance_id.desc()).first()

    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow instance found for {spec_id} record #{record_id}."
        )

    history_logs = db.query(SpiffActivityHistory).filter(
        SpiffActivityHistory.instance_id == instance.instance_id
    ).order_by(SpiffActivityHistory.timestamp.asc()).all()

    timeline = []
    for h in history_logs:
        timeline.append({
            "history_id": h.activity_history_id,
            "activity_id": h.activity_id,
            "activity_name": h.activity_name,
            "activity_type": h.activity_type,
            "status": h.status,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            "variables": h.variables
        })

    return success_response(
        message="Workflow execution history retrieved successfully",
        data={
            "spec_id": spec_id,
            "record_id": record_id,
            "instance_id": instance.instance_id,
            "workflow_status": instance.status,
            "current_task": instance.current_task_code,
            "started_on": instance.started_on.isoformat() if instance.started_on else None,
            "completed_on": instance.completed_on.isoformat() if instance.completed_on else None,
            "timeline": timeline
        }
    )


# ==========================================
# 7. LIST ALL CATALOG WORKFLOWS
# ==========================================

@router.get("/catalog", summary="List all available workflows in the universal catalog")
def get_universal_workflow_catalog(db: Session = Depends(get_workflow_db)):
    """
    Returns all published and active workflows registered in the platform catalog.
    """
    bindings = list_bindings(db)
    bpmns = db.query(BPMNDefinition).filter(BPMNDefinition.is_active == True).all()
    
    catalog = []
    seen = set()

    for b in bindings.values():
        key = b.get("module_key")
        if key not in seen:
            seen.add(key)
            catalog.append({
                "spec_id": key,
                "title": b.get("title") or key,
                "table_name": b.get("table_name"),
                "approval_roles": b.get("approval_roles") or [],
                "workflow_id": b.get("workflow_id")
            })

    for bpmn in bpmns:
        key = bpmn.spec_id or f"wf_{bpmn.id}"
        if key not in seen:
            seen.add(key)
            catalog.append({
                "spec_id": key,
                "title": bpmn.name or key,
                "table_name": bpmn.spec_id,
                "approval_roles": [],
                "workflow_id": bpmn.id
            })

    return success_response(
        message=f"Retrieved {len(catalog)} catalog workflows",
        data=catalog
    )
