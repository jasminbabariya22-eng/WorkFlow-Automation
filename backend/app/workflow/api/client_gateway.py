import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response
from app.core.logger import logger
from app.core.database import DynamicEnginePool, ClientDatabaseAdapter
from app.workflow_studio.bindings import (
    list_bindings,
    get_binding,
    WorkflowModuleBinding
)
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter

router = APIRouter(prefix="/client", tags=["Client Application Gateway"])


# ==========================================
# PYDANTIC SCHEMAS
# ==========================================

class QueryFilter(BaseModel):
    field: str
    operator: str = "="  # =, !=, >, <, >=, <=, LIKE, ILIKE, IN
    value: Any


class ClientQueryRequest(BaseModel):
    table_name: str = Field(..., description="Target database table name")
    connection_id: Optional[int] = Field(None, description="Database connection ID (defaults to active connection)")
    operation: str = Field("SELECT", description="Operation: SELECT, INSERT, UPDATE, DELETE")
    columns: Optional[List[str]] = Field(None, description="List of columns to retrieve (defaults to all)")
    filters: Optional[List[QueryFilter]] = Field(None, description="WHERE filter clauses")
    order_by: Optional[str] = Field(None, description="Column to order by")
    order_direction: Optional[str] = Field("ASC", description="ASC or DESC")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="Max rows to return")
    offset: Optional[int] = Field(0, ge=0)
    values: Optional[Dict[str, Any]] = Field(None, description="Values for INSERT or UPDATE operations")


class ClientSubmitRequest(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict, description="Entity fields to insert")
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    async_execution: Optional[bool] = False


class ClientActionRequest(BaseModel):
    record_id: int
    action: str = "APPROVE"
    user_id: Optional[int] = None
    role: Optional[str] = "MANAGER"
    remarks: Optional[str] = ""
    variables: Optional[Dict[str, Any]] = None


# ==========================================
# 1. CLIENT-SIDE DB QUERY GATEWAY
# ==========================================

@router.post("/query", summary="Generic client-side database query (SELECT, INSERT, UPDATE, DELETE)")
def execute_client_query(
    payload: ClientQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Standardized Client DB Query API:
    Allows client applications to query, filter, sort, update, or insert business records
    cleanly through a parameterized database abstraction without raw SQL exposure.
    """
    conn_id = payload.connection_id
    table_name = payload.table_name
    operation = (payload.operation or "SELECT").upper()

    # Automatically resolve connection_id if not provided
    if conn_id is None:
        try:
            bindings = list_bindings()
            for b in bindings.values():
                if b.get("table_name") == table_name and b.get("connection_id"):
                    conn_id = b.get("connection_id")
                    break
        except Exception:
            pass

    if conn_id is None:
        try:
            from app.workflow.database import WorkflowSessionLocal
            from app.workflow.persistence.models import DatabaseConnection
            with WorkflowSessionLocal() as wf_db:
                active_conn = wf_db.query(DatabaseConnection).filter(
                    DatabaseConnection.is_active == True
                ).order_by(DatabaseConnection.is_default.desc(), DatabaseConnection.connection_id.asc()).first()
                if active_conn:
                    conn_id = active_conn.connection_id
        except Exception:
            pass

    try:
        eng = DynamicEnginePool.get_engine(conn_id)
        target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
        full_table = f"{target_schema}.{table_name}" if target_schema else table_name

        # Resolve columns metadata
        col_meta = ClientDatabaseAdapter.get_table_columns(table_name, schema=target_schema, connection_id=conn_id)
        valid_cols = {c["name"] for c in col_meta.get("columns", [])}
        pks = col_meta.get("primary_keys") or ["id"]
        primary_key = pks[0] if pks else "id"

        # -------------------------------------------------------------
        # A. SELECT QUERY
        # -------------------------------------------------------------
        if operation == "SELECT":
            # Columns
            selected = [c for c in (payload.columns or []) if c in valid_cols]
            cols_clause = ", ".join(selected) if selected else "*"

            # Filters
            where_clauses = []
            binds: Dict[str, Any] = {}
            if payload.filters:
                for idx, f in enumerate(payload.filters):
                    if f.field in valid_cols:
                        param_name = f"p_filter_{idx}"
                        op = f.operator.upper()
                        if op in ("=", "!=", ">", "<", ">=", "<=", "LIKE", "ILIKE"):
                            where_clauses.append(f"{f.field} {op} :{param_name}")
                            binds[param_name] = f.value
                        elif op == "IN" and isinstance(f.value, list):
                            where_clauses.append(f"{f.field} IN (:{param_name})")
                            binds[param_name] = tuple(f.value)

            where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Order by
            order_str = ""
            if payload.order_by and payload.order_by in valid_cols:
                direction = "DESC" if (payload.order_direction or "").upper() == "DESC" else "ASC"
                order_str = f" ORDER BY {payload.order_by} {direction}"
            elif primary_key in valid_cols:
                order_str = f" ORDER BY {primary_key} DESC"

            limit_str = f" LIMIT {payload.limit} OFFSET {payload.offset}"
            sql = f"SELECT {cols_clause} FROM {full_table}{where_str}{order_str}{limit_str}"

            with eng.connect() as conn:
                res = conn.execute(text(sql), binds)
                rows = [dict(row._mapping) for row in res]

            # Serialize datetime objects to ISO strings
            for r in rows:
                for k, v in r.items():
                    if isinstance(v, datetime):
                        r[k] = v.isoformat()

            return success_response(data={
                "table": table_name,
                "count": len(rows),
                "limit": payload.limit,
                "offset": payload.offset,
                "records": rows
            })

        # -------------------------------------------------------------
        # B. INSERT QUERY
        # -------------------------------------------------------------
        elif operation == "INSERT":
            vals = payload.values or {}
            filtered_vals = {k: v for k, v in vals.items() if k in valid_cols}
            if not filtered_vals:
                raise HTTPException(status_code=400, detail="No valid column values provided for INSERT.")

            cols = list(filtered_vals.keys())
            placeholders = [f":v_{c}" for c in cols]
            binds = {f"v_{c}": v for c, v in filtered_vals.items()}
            sql = f"INSERT INTO {full_table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING {primary_key}"

            with eng.begin() as conn:
                res = conn.execute(text(sql), binds).first()
                new_id = res[0] if res else None

            return success_response(
                message=f"Record created successfully in {table_name}",
                data={"record_id": new_id, "primary_key": primary_key}
            )

        # -------------------------------------------------------------
        # C. UPDATE QUERY
        # -------------------------------------------------------------
        elif operation == "UPDATE":
            vals = payload.values or {}
            filtered_vals = {k: v for k, v in vals.items() if k in valid_cols}
            if not filtered_vals:
                raise HTTPException(status_code=400, detail="No valid column values provided for UPDATE.")

            set_clauses = [f"{c} = :set_{c}" for c in filtered_vals.keys()]
            binds = {f"set_{c}": v for c, v in filtered_vals.items()}

            where_clauses = []
            if payload.filters:
                for idx, f in enumerate(payload.filters):
                    if f.field in valid_cols:
                        param_name = f"upd_f_{idx}"
                        where_clauses.append(f"{f.field} = :{param_name}")
                        binds[param_name] = f.value
            else:
                raise HTTPException(status_code=400, detail="UPDATE operation requires at least one filter.")

            sql = f"UPDATE {full_table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"

            with eng.begin() as conn:
                res = conn.execute(text(sql), binds)
                affected = res.rowcount

            return success_response(
                message=f"Updated {affected} record(s) in {table_name}",
                data={"affected_rows": affected}
            )

        # -------------------------------------------------------------
        # D. DELETE QUERY
        # -------------------------------------------------------------
        elif operation == "DELETE":
            where_clauses = []
            binds = {}
            if payload.filters:
                for idx, f in enumerate(payload.filters):
                    if f.field in valid_cols:
                        param_name = f"del_f_{idx}"
                        where_clauses.append(f"{f.field} = :{param_name}")
                        binds[param_name] = f.value
            else:
                raise HTTPException(status_code=400, detail="DELETE operation requires at least one filter.")

            sql = f"DELETE FROM {full_table} WHERE {' AND '.join(where_clauses)}"
            with eng.begin() as conn:
                res = conn.execute(text(sql), binds)
                affected = res.rowcount

            return success_response(
                message=f"Deleted {affected} record(s) from {table_name}",
                data={"affected_rows": affected}
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: '{operation}'.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing client query on {table_name}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 2. CLIENT MODULE BINDINGS
# ==========================================

@router.get("/bindings", summary="List registered business workflow modules")
def list_client_bindings():
    """
    Returns registered client modules (leaves, expenses, purchase orders, etc.)
    with form schemas, bound tables, and workflow definitions.
    """
    return list_bindings()


@router.get("/bindings/{module_key}/records", summary="Fetch records for a client module")
def get_module_records(
    module_key: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Fetches business records from the bound client database table for the module.
    """
    binding = get_binding(module_key)
    if not binding:
        raise HTTPException(status_code=404, detail=f"No binding registered for '{module_key}'")

    conn_id = binding.get("connection_id")
    table_name = binding["table_name"]

    eng = DynamicEnginePool.get_engine(conn_id)
    target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
    full_table = f"{target_schema}.{table_name}" if target_schema else table_name
    primary_key = binding.get("primary_key", "id")
    status_col = binding.get("status_column", "status")

    sql = f"SELECT * FROM {full_table}"
    binds = {}
    if status_filter:
        sql += f" WHERE {status_col} = :status"
        binds["status"] = status_filter
    sql += f" ORDER BY {primary_key} DESC LIMIT {limit}"

    try:
        with eng.connect() as conn:
            res = conn.execute(text(sql), binds)
            rows = [dict(row._mapping) for row in res]

        result = []
        for r in rows:
            row_dict = {}
            for k, v in r.items():
                if isinstance(v, datetime):
                    row_dict[k] = v.isoformat()
                else:
                    row_dict[k] = v
            result.append(row_dict)

        return success_response(data=result)
    except Exception as e:
        logger.error(f"Failed to query records for module {module_key}: {e}", exc_info=True)
        return error_response(message=f"Failed to query records: {str(e)}", status_code=500)


# ==========================================
# 3. DECOUPLED CLIENT WORKFLOW SUBMISSION
# ==========================================

@router.post("/bindings/{module_key}/submit", summary="Submit business entity & dispatch workflow job")
def submit_client_workflow_record(
    module_key: str,
    payload: ClientSubmitRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Decoupled Gateway:
    1. Writes business entity record to Client Database.
    2. Dispatches workflow execution cleanly via Workflow Job API / Executor.
    """
    binding = get_binding(module_key)
    if not binding:
        raise HTTPException(status_code=404, detail=f"No binding registered for '{module_key}'")

    conn_id = binding.get("connection_id")
    table_name = binding["table_name"]
    workflow_id = binding["workflow_id"]
    values = payload.data or {}

    auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
    user_id = payload.user_id or values.get("employee_id") or values.get("user_id") or auth_user_id or 1
    user_name = payload.user_name or (current_user.get("name") if isinstance(current_user, dict) else None) or "User"
    user_email = payload.user_email or (current_user.get("email") if isinstance(current_user, dict) else None) or ""

    status_col = binding.get("status_column", "status")
    if status_col not in values:
        values[status_col] = binding.get("default_status", "PENDING")

    # 1. Insert into Client Database
    eng = DynamicEnginePool.get_engine(conn_id)
    target_schema = ClientDatabaseAdapter._resolve_target_schema(None, conn_id)
    full_table = f"{target_schema}.{table_name}" if target_schema else table_name
    col_meta = ClientDatabaseAdapter.get_table_columns(table_name, schema=target_schema, connection_id=conn_id)
    pks = col_meta.get("primary_keys") or []
    primary_key = pks[0] if pks else binding.get("primary_key", "id")

    col_names = {c["name"]: c for c in col_meta.get("columns", [])}
    filtered_vals = {k: v for k, v in values.items() if k in col_names}
    if not filtered_vals:
        raise HTTPException(status_code=400, detail="No matching columns found to insert.")

    cols = list(filtered_vals.keys())
    placeholders = [f":val_{c}" for c in cols]
    binds = {f"val_{c}": v for c, v in filtered_vals.items()}
    insert_sql = f"INSERT INTO {full_table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)}) RETURNING {primary_key}"

    with eng.begin() as conn:
        res = conn.execute(text(insert_sql), binds).first()
        new_record_id = res[0] if res else None

    # 2. Dispatch Workflow Execution
    instance_id = None
    wf_error = None
    try:
        parsed_user_id = int(user_id) if str(user_id).isdigit() else user_id
        wf_variables = {
            **values,
            "entity_id": int(new_record_id),
            "user_id": parsed_user_id,
            "user_name": user_name,
            "user_email": user_email,
            "employee_id": parsed_user_id,
            "employee_name": user_name,
            "employee_email": user_email,
            "connection_id": conn_id
        }

        # Check if async execution requested
        if payload.async_execution:
            from app.workflow.runtime.executor_service import workflow_executor
            async_res = workflow_executor.submit_job_async(
                entity_type=table_name,
                entity_id=int(new_record_id),
                definition_id=workflow_id,
                user_id=parsed_user_id,
                variables=wf_variables
            )
            instance_id = async_res.get("job_id")
        else:
            wf_res = StudioExecutionAdapter.start_workflow(
                entity_type=table_name,
                entity_id=int(new_record_id),
                user_id=parsed_user_id,
                variables=wf_variables,
                db=db,
                definition_id=workflow_id
            )
            instance_id = wf_res.get("instance_id")

        logger.info(f"Client Gateway: Successfully submitted {table_name} record #{new_record_id}, job #{instance_id}")

    except Exception as wf_err:
        wf_error = str(wf_err)
        logger.error(f"Client Gateway: Error launching workflow for {table_name} #{new_record_id}: {wf_err}", exc_info=True)

    result = {
        "module_key": module_key,
        "record_id": new_record_id,
        "job_id": instance_id,
        "instance_id": instance_id,
        "status": values.get(status_col, "PENDING")
    }
    if wf_error:
        result["workflow_error"] = wf_error

    return success_response(
        message="Workflow record submitted successfully",
        data=result,
        status_code=status.HTTP_201_CREATED
    )


# ==========================================
# 4. CLIENT ACTION EXECUTION
# ==========================================

@router.post("/bindings/{module_key}/action", summary="Execute approval/rejection action for a bound entity")
def execute_client_workflow_action(
    module_key: str,
    payload: ClientActionRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Executes human approval task action (APPROVE, REJECT) for a bound entity.
    """
    binding = get_binding(module_key)
    if not binding:
        raise HTTPException(status_code=404, detail=f"No binding registered for '{module_key}'")

    table_name = binding["table_name"]
    entity_id = payload.record_id
    action = (payload.action or "APPROVE").upper()

    auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
    user_id = payload.user_id or auth_user_id or 1
    user_role = payload.role or (current_user.get("role_code") if isinstance(current_user, dict) else None) or "MANAGER"

    variables = payload.variables or {}
    conn_id = binding.get("connection_id")
    if conn_id is not None:
        variables["connection_id"] = conn_id
    if user_role:
        variables["user_role"] = user_role
    variables["status"] = "APPROVED" if action == "APPROVE" else "REJECTED"

    parsed_user_id = int(user_id) if str(user_id).isdigit() else user_id
    try:
        res = StudioExecutionAdapter.execute_action(
            entity_type=table_name,
            entity_id=int(entity_id),
            action=action,
            user_id=parsed_user_id,
            remarks=payload.remarks or "",
            variables=variables,
            db=db
        )
        logger.info(f"Client Gateway: Action {action} executed on {table_name} #{entity_id} by user {parsed_user_id}")
        return success_response(data=res)
    except Exception as e:
        logger.error(f"Client Gateway: Error executing action on {table_name} #{entity_id}: {e}", exc_info=True)
        return error_response(message=f"Failed to execute action: {str(e)}", status_code=500)


# ==========================================
# 5. CLIENT USER TASK INBOX
# ==========================================

@router.get("/tasks/my-tasks", summary="Get pending approval tasks for user")
def get_user_tasks(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves all pending human tasks in READY state authorized for this user.
    """
    try:
        tasks = StudioExecutionAdapter.get_pending_tasks_for_user(db=db, user_id=user_id)
        return success_response(data=tasks)
    except Exception as e:
        logger.error(f"Error fetching tasks for user {user_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)

