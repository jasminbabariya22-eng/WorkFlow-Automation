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


# =========================================================================
# HELPER: Resolve Workflow by numeric ID or Code / Name
# =========================================================================
def _find_workflow_and_version(
    db: Session,
    id_or_code: str,
    version_id: Optional[int] = None,
    published_only: bool = False
):
    workflow = None
    if isinstance(id_or_code, str) and id_or_code.isdigit():
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == int(id_or_code)).first()

    if not workflow:
        key = str(id_or_code).strip()
        workflow = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == key) |
            (GenericWorkflow.name == key) |
            (GenericWorkflow.workflow_key.ilike(key)) |
            (GenericWorkflow.name.ilike(key))
        ).first()

    if not workflow:
        return None, None

    target_wf_id = workflow.workflow_id
    
    # Sanitize version_id if not integer
    v_id = version_id if isinstance(version_id, int) else None
    is_pub = bool(published_only) if not hasattr(published_only, 'default') else False

    if v_id is not None:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == v_id,
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
# 1. LIST ALL WORKFLOWS (GET /workflows)
# =========================================================================
@router.get("", summary="List all workflows with filters")
def list_workflows(
    entity_type: Optional[str] = Query(None, description="Filter by entity / table name (e.g. leave_requests)"),
    status: Optional[str] = Query(None, description="Filter by status (DRAFT, PUBLISHED, ACTIVE, ARCHIVED)"),
    search: Optional[str] = Query(None, description="Search term for name or key"),
    connection_id: Optional[int] = Query(None, description="Filter by Client Database Connection ID"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max results to return"),
    offset: Optional[int] = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_workflow_db)
):
    """
    Lists all workflow definitions with metadata, current version, status, and bound entity tables.
    """
    query = db.query(GenericWorkflow)
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
# 2. GET ACTIVE WORKFLOW FOR A DATABASE TABLE (GET /workflows/by-table/{table_name})
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
# 3. GET FULL WORKFLOW DEFINITION (GET /workflows/{id_or_code})
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
# 4. GET WORKFLOW APPROVAL STEPS (GET /workflows/{id_or_code}/steps)
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
# 5. GET WORKFLOW NODES ONLY (GET /workflows/{id_or_code}/nodes)
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
