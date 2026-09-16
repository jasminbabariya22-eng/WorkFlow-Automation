import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response
from app.core.logger import logger
from app.workflow_definition.models import GenericWorkflow, WorkflowVersion
from app.workflow_studio.services import WorkflowStudioService

router = APIRouter(prefix="/workflows", tags=["Workflow Retrieval & Inspection"])


from app.workflow.persistence.models import DatabaseConnection

# =========================================================================
# HELPER: Resolve Workflow by numeric ID or Code / Name
# =========================================================================
def _find_workflow_and_version(
    db: Session,
    id_or_code: str,
    version_id: Optional[int] = None,
    version_number: Optional[int] = None,
    published_only: bool = False
):
    workflow = None
    if isinstance(id_or_code, str) and id_or_code.isdigit():
        workflow = db.query(GenericWorkflow).filter(
            GenericWorkflow.workflow_id == int(id_or_code),
            (GenericWorkflow.is_deleted == 0) | (GenericWorkflow.is_deleted == None)
        ).first()

    if not workflow:
        key = str(id_or_code).strip()
        workflow = db.query(GenericWorkflow).filter(
            ((GenericWorkflow.workflow_key == key) |
            (GenericWorkflow.name == key) |
            (GenericWorkflow.workflow_key.ilike(key)) |
            (GenericWorkflow.name.ilike(key))),
            (GenericWorkflow.is_deleted == 0) | (GenericWorkflow.is_deleted == None)
        ).first()

    if not workflow:
        return None, None

    target_wf_id = workflow.workflow_id
    
    # Sanitize version_id / version_number if passed as query objects or non-integers
    v_id = version_id if isinstance(version_id, int) else None
    v_num = version_number if isinstance(version_number, int) else None
    is_pub = bool(published_only) if not hasattr(published_only, 'default') else False

    if v_id is not None:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == v_id,
            WorkflowVersion.workflow_id == target_wf_id
        ).first()
    elif v_num is not None:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.version_number == v_num,
            WorkflowVersion.workflow_id == target_wf_id
        ).first()
    elif is_pub:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == target_wf_id,
            WorkflowVersion.status == "PUBLISHED"
        ).order_by(WorkflowVersion.version_number.desc()).first()
    else:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == target_wf_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

    return workflow, version


# =========================================================================
# 1. GET ALL WORKFLOWS (GET /workflows)
# =========================================================================
@router.get("", summary="1. Get all workflows with optional filters")
def get_all_workflows(
    entity_type: Optional[str] = Query(None, description="Filter by entity / table name (e.g. leave_requests)"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PUBLISHED, ACTIVE, ARCHIVED)"),
    search: Optional[str] = Query(None, description="Search term for name or key"),
    connection_id: Optional[int] = Query(None, description="Filter by Client Database Connection ID"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: Optional[int] = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves all workflows in the system with metadata, active versions, node/edge counts, and connection details.
    """
    query = db.query(GenericWorkflow).filter(
        (GenericWorkflow.is_deleted == 0) | (GenericWorkflow.is_deleted == None)
    )
    if entity_type:
        query = query.filter(GenericWorkflow.entity_type.ilike(f"%{entity_type}%"))
    if status:
        query = query.filter(GenericWorkflow.status == status.upper())
    if connection_id is not None:
        query = query.filter(GenericWorkflow.connection_id == connection_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(GenericWorkflow.name.ilike(s), GenericWorkflow.workflow_key.ilike(s)))

    total_count = query.count()
    workflows = query.order_by(GenericWorkflow.updated_at.desc()).offset(offset).limit(limit).all()

    results = []
    for wf in workflows:
        latest_ver = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == wf.workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        results.append({
            "workflow_id": wf.workflow_id,
            "workflow_code": wf.workflow_key,
            "name": wf.name,
            "description": wf.description or "",
            "entity_type": wf.entity_type or "",
            "connection_id": wf.connection_id,
            "status": wf.status,
            "version_number": latest_ver.version_number if latest_ver else 1,
            "version_status": latest_ver.status if latest_ver else "DRAFT",
            "is_published": latest_ver.status == "PUBLISHED" if latest_ver else False,
            "total_nodes": len(latest_ver.nodes) if latest_ver else 0,
            "total_edges": len(latest_ver.connections) if latest_ver else 0,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None
        })

    return success_response(data={
        "total": total_count,
        "count": len(results),
        "workflows": results
    })


# =========================================================================
# 2. GET WORKFLOWS BASED ON CLIENT DB (GET /workflows/by-client-db/{connection_id_or_name})
# =========================================================================
@router.get("/by-client-db/{connection_id_or_name}", summary="2. Get all workflows for a specific Client Database")
def get_workflows_by_client_db(
    connection_id_or_name: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves all workflows linked to a specific client database, queried by either:
    - Connection ID (e.g. `4` or `1`)
    - Connection Name / DB Name (e.g. `Production DB`, `ers_db`)
    """
    target_conn_id = None
    conn_info = None

    if connection_id_or_name.isdigit():
        target_conn_id = int(connection_id_or_name)
        conn_record = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == target_conn_id).first()
        if conn_record:
            conn_info = {
                "connection_id": conn_record.connection_id,
                "connection_name": conn_record.connection_name,
                "db_type": conn_record.db_type,
                "database_name": conn_record.database_name,
                "host": conn_record.host
            }
    else:
        term = connection_id_or_name.strip()
        conn_record = db.query(DatabaseConnection).filter(
            (DatabaseConnection.connection_name.ilike(term)) |
            (DatabaseConnection.database_name.ilike(term)) |
            (DatabaseConnection.connection_name.ilike(f"%{term}%"))
        ).first()

        if conn_record:
            target_conn_id = conn_record.connection_id
            conn_info = {
                "connection_id": conn_record.connection_id,
                "connection_name": conn_record.connection_name,
                "db_type": conn_record.db_type,
                "database_name": conn_record.database_name,
                "host": conn_record.host
            }

    if target_conn_id is None:
        return error_response(message=f"Client database connection '{connection_id_or_name}' not found.", status_code=404)

    workflows = db.query(GenericWorkflow).filter(
        GenericWorkflow.connection_id == target_conn_id
    ).order_by(GenericWorkflow.updated_at.desc()).all()

    results = []
    for wf in workflows:
        latest_ver = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == wf.workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        results.append({
            "workflow_id": wf.workflow_id,
            "workflow_code": wf.workflow_key,
            "name": wf.name,
            "description": wf.description or "",
            "entity_type": wf.entity_type or "",
            "status": wf.status,
            "version_number": latest_ver.version_number if latest_ver else 1,
            "version_status": latest_ver.status if latest_ver else "DRAFT",
            "is_published": latest_ver.status == "PUBLISHED" if latest_ver else False,
            "total_nodes": len(latest_ver.nodes) if latest_ver else 0,
            "total_edges": len(latest_ver.connections) if latest_ver else 0,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None
        })

    return success_response(data={
        "client_db": conn_info,
        "total": len(results),
        "workflows": results
    })


# =========================================================================
# 3. GET WORKFLOWS BASED ON STATUS (GET /workflows/by-status/{status})
# =========================================================================
@router.get("/by-status/{status_val}", summary="3. Get workflows based on status")
def get_workflows_by_status(
    status_val: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves all workflows matching a specific lifecycle status:
    - `ACTIVE`: Currently active and executable workflows
    - `PUBLISHED`: Workflows with validated & published versions
    - `DRAFT`: Workflows currently in design/draft phase
    - `ARCHIVED`: Deprecated or archived workflows
    """
    clean_status = status_val.strip().upper()
    query = db.query(GenericWorkflow).filter(GenericWorkflow.status == clean_status)
    workflows = query.order_by(GenericWorkflow.updated_at.desc()).all()

    results = []
    for wf in workflows:
        latest_ver = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == wf.workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        results.append({
            "workflow_id": wf.workflow_id,
            "workflow_code": wf.workflow_key,
            "name": wf.name,
            "description": wf.description or "",
            "entity_type": wf.entity_type or "",
            "connection_id": wf.connection_id,
            "status": wf.status,
            "version_number": latest_ver.version_number if latest_ver else 1,
            "version_status": latest_ver.status if latest_ver else "DRAFT",
            "is_published": latest_ver.status == "PUBLISHED" if latest_ver else False,
            "total_nodes": len(latest_ver.nodes) if latest_ver else 0,
            "total_edges": len(latest_ver.connections) if latest_ver else 0,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None
        })

    return success_response(data={
        "status_filter": clean_status,
        "total": len(results),
        "workflows": results
    })


# =========================================================================
# 4. GET ACTIVE WORKFLOW FOR A DATABASE TABLE (GET /workflows/by-table/{table_name})
# =========================================================================
@router.get("/by-table/{table_name}", summary="Get active workflow bound to a specific table")
def get_workflow_by_table(
    table_name: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the currently active or published workflow configured for a specific database entity/table.
    """
    clean_table = table_name.strip()
    workflow = db.query(GenericWorkflow).filter(
        (GenericWorkflow.entity_type.ilike(clean_table)) &
        (GenericWorkflow.status.in_(["ACTIVE", "PUBLISHED"]))
    ).order_by(GenericWorkflow.updated_at.desc()).first()

    if not workflow:
        workflow = db.query(GenericWorkflow).filter(
            GenericWorkflow.entity_type.ilike(f"%{clean_table}%")
        ).order_by(GenericWorkflow.updated_at.desc()).first()

    if not workflow:
        return error_response(message=f"No workflow found for table '{table_name}'.", status_code=404)

    return get_workflow_by_id_or_code(id_or_code=str(workflow.workflow_id), version_id=None, published_only=False, db=db)


# =========================================================================
# 5. WORKFLOW CATALOG FOR CLIENT APP (GET /workflows/catalog)
# =========================================================================
@router.get("/catalog", summary="Get complete workflow catalog for ClientApp")
def get_workflow_catalog_for_client_app(
    status: Optional[str] = Query(None, description="Optional status filter: PUBLISHED, ACTIVE, DRAFT"),
    connection_id: Optional[int] = Query(None, description="Filter by Client Database Connection ID"),
    db: Session = Depends(get_workflow_db)
):
    """
    Returns a unified catalog of all workflows with connection details and active bindings ready for ClientApp integration.
    """
    from app.workflow.persistence.models import BPMNDefinition, DatabaseConnection
    from app.workflow_studio.bindings import WorkflowModuleBinding

    # Preload connections
    connections = {c.connection_id: c.connection_name for c in db.query(DatabaseConnection).all()}
    
    # Preload active bindings
    all_bindings = db.query(WorkflowModuleBinding).all()
    wf_to_bindings = {}
    for b in all_bindings:
        wf_to_bindings.setdefault(b.workflow_id, []).append({
            "module_key": b.module_key,
            "title": b.title,
            "table_name": b.table_name
        })

    # Query definitions
    bpmn_query = db.query(BPMNDefinition)
    if status:
        bpmn_query = bpmn_query.filter(BPMNDefinition.status.ilike(status))
    if connection_id is not None:
        bpmn_query = bpmn_query.filter(BPMNDefinition.connection_id == connection_id)
    definitions = bpmn_query.order_by(BPMNDefinition.id.desc()).all()

    catalog = []
    for d in definitions:
        node_count = 0
        if d.json_content:
            try:
                g = json.loads(d.json_content) if isinstance(d.json_content, str) else d.json_content
                node_count = len(g.get("nodes", []))
            except Exception:
                node_count = 0

        catalog.append({
            "workflow_id": d.id,
            "workflow_code": d.spec_id,
            "name": d.name,
            "description": d.description or "",
            "version": d.version,
            "status": d.status,
            "is_active": d.is_active,
            "connection_id": d.connection_id,
            "connection_name": connections.get(d.connection_id, "Default DB"),
            "nodes_count": node_count,
            "bound_modules": wf_to_bindings.get(d.id, []),
            "can_bind_to_client_app": d.status in ["Published", "Active", "PUBLISHED", "ACTIVE"] or node_count > 0,
            "published_on": d.published_on.isoformat() if d.published_on else None,
            "updated_on": d.updated_on.isoformat() if d.updated_on else None
        })

    return success_response(data={
        "total": len(catalog),
        "workflows": catalog
    })


# =========================================================================
# 6. WORKFLOW DEEP INSPECTION (GET /workflows/inspect/{id_or_code})
# =========================================================================
@router.get("/inspect/{id_or_code}", summary="Deep inspect workflow roles, actions, tables, and bindings")
def inspect_workflow_for_client_app(
    id_or_code: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Comprehensive Workflow Inspection API for ClientApp.
    Inspects any workflow by numeric ID or workflow_code to extract:
    - Target Client Database & Connection Name
    - Configured Approval Roles across all nodes (e.g. ['Manager', 'HR'])
    - Allowed Outcome Actions (e.g. ['APPROVE', 'REJECT'])
    - Target Tables Detected
    - Active Module Bindings in ClientApp
    """
    from app.workflow.persistence.models import BPMNDefinition, DatabaseConnection
    from app.workflow_studio.bindings import WorkflowModuleBinding

    bpmn_def = None
    if id_or_code.isdigit():
        bpmn_def = db.query(BPMNDefinition).filter(BPMNDefinition.id == int(id_or_code)).first()
    if not bpmn_def:
        bpmn_def = db.query(BPMNDefinition).filter(
            (BPMNDefinition.spec_id == id_or_code) | (BPMNDefinition.name == id_or_code)
        ).order_by(BPMNDefinition.id.desc()).first()

    if not bpmn_def:
        return error_response(message=f"Workflow '{id_or_code}' not found in registry.", status_code=404)

    # Parse nodes and analyze graph
    nodes = []
    edges = []
    if bpmn_def.json_content:
        try:
            graph = json.loads(bpmn_def.json_content) if isinstance(bpmn_def.json_content, str) else bpmn_def.json_content
            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])
        except Exception as e:
            logger.warning(f"Error parsing json_content in inspect_workflow: {e}")

    approval_roles = set()
    allowed_actions = set()
    target_tables = set()
    has_email = False
    has_timer = False

    for n in nodes:
        ntype = str(n.get("type", "")).lower()
        data = n.get("data", {})
        config = n.get("config", {})

        if ntype in ["approval", "usertask", "approval_node"]:
            role = data.get("role") or data.get("role_code") or data.get("approver_role") or config.get("role_code")
            if role:
                approval_roles.add(str(role))
            acts = data.get("actions") or config.get("actions") or ["APPROVE", "REJECT"]
            if isinstance(acts, list):
                for a in acts:
                    allowed_actions.add(str(a).upper())
            elif isinstance(acts, str):
                for a in acts.split(","):
                    allowed_actions.add(a.strip().upper())

        elif ntype in ["communication", "notification", "email"]:
            has_email = True
        elif ntype in ["timer", "delay", "wait"]:
            has_timer = True
        elif ntype in ["database", "action", "crud", "db_action"]:
            tbl = data.get("table") or data.get("table_name") or config.get("table")
            if tbl:
                target_tables.add(str(tbl))

    for e in edges:
        lbl = e.get("label") or (e.get("data", {}).get("label") if isinstance(e.get("data"), dict) else None)
        if lbl and str(lbl).upper() in ["APPROVE", "REJECT", "SUBMIT", "RESUBMIT", "CANCEL"]:
            allowed_actions.add(str(lbl).upper())

    if not allowed_actions:
        allowed_actions = {"APPROVE", "REJECT"}

    conn_info = None
    if bpmn_def.connection_id:
        db_conn = db.query(DatabaseConnection).filter(DatabaseConnection.connection_id == bpmn_def.connection_id).first()
        if db_conn:
            conn_info = {
                "connection_id": db_conn.connection_id,
                "connection_name": db_conn.connection_name,
                "db_type": db_conn.db_type,
                "database_name": db_conn.database_name,
                "default_schema": db_conn.default_schema
            }

    active_bindings = []
    bindings_query = db.query(WorkflowModuleBinding).filter(
        (WorkflowModuleBinding.workflow_id == bpmn_def.id) | 
        (WorkflowModuleBinding.module_key == bpmn_def.spec_id)
    ).all()
    for b in bindings_query:
        active_bindings.append({
            "binding_id": b.binding_id,
            "module_key": b.module_key,
            "title": b.title,
            "table_name": b.table_name,
            "status_column": b.status_column,
            "is_active": b.is_active
        })

    return success_response(data={
        "workflow_id": bpmn_def.id,
        "workflow_code": bpmn_def.spec_id,
        "name": bpmn_def.name,
        "description": bpmn_def.description or "",
        "status": bpmn_def.status,
        "is_active": bpmn_def.is_active,
        "version": bpmn_def.version,
        "tags": bpmn_def.tags,
        "connection": conn_info,
        "statistics": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "has_email_notification": has_email,
            "has_timer_escalation": has_timer
        },
        "inspection": {
            "approval_roles": sorted(list(approval_roles)),
            "allowed_actions": sorted(list(allowed_actions)),
            "target_tables_detected": sorted(list(target_tables)),
            "can_bind_to_client_app": bpmn_def.status in ["Published", "Active", "PUBLISHED", "ACTIVE"] or len(nodes) > 0
        },
        "active_client_bindings": active_bindings
    })


# =========================================================================
# 7. GET FULL WORKFLOW DEFINITION (GET /workflows/{id_or_code})
# =========================================================================
@router.get("/{id_or_code}", summary="Get workflow definition by ID or code")
def get_workflow_by_id_or_code(
    id_or_code: str,
    version_id: Optional[int] = Query(None, description="Optional specific version ID to retrieve"),
    published_only: Optional[bool] = Query(False, description="Return only published version"),
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the complete workflow definition (metadata, full visual node graph,
    edges, configurations, and summary statistics) using either a numeric workflow ID
    (e.g. `122`) or a workflow code / name (e.g. `Emp_Leave`, `API_Call_Test`, `LEAVE_APPROVAL_FLOW`).
    """
    workflow, version = _find_workflow_and_version(
        db=db,
        id_or_code=id_or_code,
        version_id=version_id,
        published_only=published_only
    )

    if not workflow:
        return error_response(message=f"Workflow '{id_or_code}' not found.", status_code=404)
    if not version:
        return error_response(message=f"No matching version found for workflow '{id_or_code}'.", status_code=404)

    studio_data = WorkflowStudioService._serialize_studio_response(workflow, version)

    nodes = []
    node_types_count = {}
    has_approval_gate = False
    has_db_actions = False
    has_api_calls = False
    entry_node = None
    terminal_nodes = []

    for n in (studio_data.nodes or []):
        t = (n.type or "generic").lower()
        node_types_count[t] = node_types_count.get(t, 0) + 1

        cfg = n.config or {}
        sub_type = cfg.get("subType") or cfg.get("actionType") or ("API" if "url" in cfg or "endpoint" in cfg else None)

        if "start" in t:
            entry_node = n.id
        elif "end" in t:
            terminal_nodes.append(n.id)
        elif "approval" in t or "user" in t:
            has_approval_gate = True
        elif "action" in t:
            if sub_type == "API" or "url" in cfg or "endpoint" in cfg:
                has_api_calls = True
            else:
                has_db_actions = True

        nodes.append({
            "id": n.id,
            "type": n.type,
            "sub_type": sub_type,
            "name": n.name,
            "position": {"x": n.position_x, "y": n.position_y},
            "configuration": cfg
        })

    edges = []
    for e in (studio_data.edges or []):
        edges.append({
            "id": e.id,
            "source": e.source,
            "target": e.target,
            "label": e.label or "",
            "condition": e.condition,
            "config": e.config or {}
        })

    payload = {
        "workflow_id": workflow.workflow_id,
        "workflow_code": workflow.workflow_key,
        "name": workflow.name,
        "description": workflow.description or "",
        "entity_type": workflow.entity_type or "",
        "connection_id": workflow.connection_id,
        "status": workflow.status,
        "version_id": version.workflow_version_id,
        "version_number": version.version_number,
        "version_status": version.status,
        "is_published": version.status == "PUBLISHED",
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entry_node": entry_node,
            "terminal_nodes": terminal_nodes,
            "node_types": node_types_count,
            "has_approval_gate": has_approval_gate,
            "has_database_actions": has_db_actions,
            "has_api_calls": has_api_calls
        }
    }

    return success_response(data=payload)


# =========================================================================
# 5. GET WORKFLOW VERSION HISTORY (GET /workflows/{id_or_code}/versions)
# =========================================================================
@router.get("/{id_or_code}/versions", summary="Get all versions history for a workflow")
def get_workflow_versions(
    id_or_code: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Returns the complete version history for a workflow (version numbers, status, node counts, published dates).
    """
    workflow, _ = _find_workflow_and_version(db=db, id_or_code=id_or_code)
    if not workflow:
        return error_response(message=f"Workflow '{id_or_code}' not found.", status_code=404)

    versions = db.query(WorkflowVersion).filter(
        WorkflowVersion.workflow_id == workflow.workflow_id
    ).order_by(WorkflowVersion.version_number.desc()).all()

    version_list = []
    for v in versions:
        version_list.append({
            "version_id": v.workflow_version_id,
            "version_number": v.version_number,
            "status": v.status,
            "is_published": v.status == "PUBLISHED",
            "total_nodes": len(v.nodes) if v.nodes else 0,
            "total_edges": len(v.connections) if v.connections else 0,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "published_at": v.published_at.isoformat() if v.published_at else None
        })

    return success_response(data={
        "workflow_id": workflow.workflow_id,
        "workflow_code": workflow.workflow_key,
        "name": workflow.name,
        "total_versions": len(version_list),
        "versions": version_list
    })


# =========================================================================
# 6. GET WORKFLOW BASED ON SPECIFIC VERSION (GET /workflows/{id_or_code}/versions/{version_number})
# =========================================================================
@router.get("/{id_or_code}/versions/{version_number}", summary="Get workflow definition for a specific version number")
def get_workflow_by_version(
    id_or_code: str,
    version_number: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves the complete workflow definition graph specifically for the given version number (e.g. version 1, 2).
    """
    workflow, version = _find_workflow_and_version(
        db=db,
        id_or_code=id_or_code,
        version_number=version_number
    )

    if not workflow:
        return error_response(message=f"Workflow '{id_or_code}' not found.", status_code=404)
    if not version:
        return error_response(message=f"Version {version_number} not found for workflow '{id_or_code}'.", status_code=404)

    return get_workflow_by_id_or_code(
        id_or_code=str(workflow.workflow_id),
        version_id=version.workflow_version_id,
        published_only=False,
        db=db
    )


# =========================================================================
# 7. GET WORKFLOW APPROVAL STEPS (GET /workflows/{id_or_code}/steps)
# =========================================================================
@router.get("/{id_or_code}/steps", summary="Get simplified workflow approval steps")
def get_workflow_steps(
    id_or_code: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Returns an ordered sequence of human decision and task steps in the workflow,
    including assigned roles, decision actions (e.g. APPROVE, REJECT), and SLA times.
    """
    workflow, version = _find_workflow_and_version(db=db, id_or_code=id_or_code)

    if not workflow:
        return error_response(message=f"Workflow '{id_or_code}' not found.", status_code=404)
    if not version:
        return error_response(message=f"No versions found for workflow '{id_or_code}'.", status_code=404)

    steps = []
    step_number = 1
    for node in version.nodes:
        if not node.is_active:
            continue
        t = (node.node_type or "").upper()
        if t in ["USER_TASK", "USERTASK", "APPROVAL", "TASK"]:
            try:
                cfg = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
            except Exception:
                cfg = {}

            assignment = cfg.get("assignment") or {}
            actions = cfg.get("actions") or ["APPROVE", "REJECT"]

            steps.append({
                "step_number": step_number,
                "node_id": node.node_key,
                "title": node.name or node.node_key,
                "type": t,
                "assigned_to": {
                    "type": assignment.get("type", "role"),
                    "role_name": assignment.get("roleName") or cfg.get("role"),
                    "user_name": assignment.get("userName") or cfg.get("user"),
                    "department_name": assignment.get("departmentName") or cfg.get("department")
                },
                "available_actions": actions,
                "due_in_hours": cfg.get("slaHours") or cfg.get("dueInHours") or 24
            })
            step_number += 1

    return success_response(data={
        "workflow_code": workflow.workflow_key,
        "name": workflow.name,
        "total_human_steps": len(steps),
        "steps": steps
    })


# =========================================================================
# 8. GET WORKFLOW NODES ONLY (GET /workflows/{id_or_code}/nodes)
# =========================================================================
@router.get("/{id_or_code}/nodes", summary="Get only the nodes list of a workflow")
def get_workflow_nodes(
    id_or_code: str,
    db: Session = Depends(get_workflow_db)
):
    """
    Returns only the list of nodes and configurations for the requested workflow.
    """
    workflow, version = _find_workflow_and_version(db=db, id_or_code=id_or_code)
    if not workflow or not version:
        return error_response(message=f"Workflow '{id_or_code}' not found.", status_code=404)

    nodes = []
    for node in version.nodes:
        if not node.is_active:
            continue
        try:
            cfg = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
        except Exception:
            cfg = {}

        nodes.append({
            "id": node.node_key,
            "type": node.node_type,
            "name": node.name,
            "position": {"x": node.position_x, "y": node.position_y},
            "configuration": cfg
        })

    return success_response(data={
        "workflow_code": workflow.workflow_key,
        "name": workflow.name,
        "total_nodes": len(nodes),
        "nodes": nodes
    })
