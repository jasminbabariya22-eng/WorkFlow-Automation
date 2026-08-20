import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.workflow_definition.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowDetailResponse,
    WorkflowVersionCreate,
    WorkflowVersionResponse,
    WorkflowVersionDetailResponse,
    WorkflowNodeCreate,
    WorkflowNodeUpdate,
    WorkflowNodeResponse,
    WorkflowConnectionCreate,
    WorkflowConnectionResponse,
    WorkflowValidationResponse
)
from app.workflow_definition.services import WorkflowDefinitionService
from app.workflow_definition.models import WorkflowNode, WorkflowConnection

router = APIRouter(prefix="/workflows", tags=["Generic Workflow Definitions"])


# Helper to convert node model to schema response
def _serialize_node(node: WorkflowNode) -> Dict[str, Any]:
    try:
        config_dict = json.loads(node.configuration) if isinstance(node.configuration, str) else (node.configuration or {})
    except Exception:
        config_dict = {}

    return {
        "node_id": node.node_id,
        "workflow_version_id": node.workflow_version_id,
        "node_key": node.node_key,
        "node_type": node.node_type,
        "name": node.name,
        "description": node.description,
        "position_x": node.position_x,
        "position_y": node.position_y,
        "configuration": config_dict,
        "is_active": node.is_active,
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }


# Helper to convert connection model to schema response
def _serialize_connection(conn: WorkflowConnection) -> Dict[str, Any]:
    try:
        meta_dict = json.loads(conn.metadata_json) if isinstance(conn.metadata_json, str) else (conn.metadata_json or {})
    except Exception:
        meta_dict = {}

    return {
        "connection_id": conn.connection_id,
        "workflow_version_id": conn.workflow_version_id,
        "source_node_id": conn.source_node_id,
        "target_node_id": conn.target_node_id,
        "connection_key": conn.connection_key,
        "condition": conn.condition,
        "label": conn.label,
        "metadata_json": meta_dict,
        "created_at": conn.created_at
    }


# ==========================================
# 1. WORKFLOW CRUD
# ==========================================

@router.post("", response_model=Dict[str, Any])
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id") if current_user else None
    wf = WorkflowDefinitionService.create_workflow(db, payload, user_id=user_id)
    return {
        "workflow_id": wf.workflow_id,
        "workflow_key": wf.workflow_key,
        "name": wf.name,
        "description": wf.description,
        "entity_type": wf.entity_type,
        "status": wf.status,
        "created_by": wf.created_by,
        "created_at": wf.created_at,
        "updated_by": wf.updated_by,
        "updated_at": wf.updated_at,
        "latest_version": 1,
        "published_version": None
    }


@router.get("", response_model=List[Dict[str, Any]])
def list_workflows(
    entity_type: Optional[str] = Query(None, description="Filter by entity type, e.g. Risk, Audit"),
    status: Optional[str] = Query(None, description="Filter by status, e.g. DRAFT, ACTIVE, ARCHIVED"),
    db: Session = Depends(get_workflow_db)
):
    return WorkflowDefinitionService.list_workflows(db, entity_type=entity_type, status=status)


@router.get("/{workflow_id}", response_model=Dict[str, Any])
def get_workflow(
    workflow_id: int,
    db: Session = Depends(get_workflow_db)
):
    wf = WorkflowDefinitionService.get_workflow(db, workflow_id)
    versions_data = []
    for v in wf.versions:
        try:
            meta = json.loads(v.definition_metadata) if isinstance(v.definition_metadata, str) else (v.definition_metadata or {})
        except Exception:
            meta = {}
        versions_data.append({
            "workflow_version_id": v.workflow_version_id,
            "workflow_id": v.workflow_id,
            "version_number": v.version_number,
            "status": v.status,
            "definition_metadata": meta,
            "created_by": v.created_by,
            "created_at": v.created_at,
            "published_at": v.published_at
        })

    published_v = next((v.version_number for v in wf.versions if v.status == "PUBLISHED"), None)
    latest_v = max([v.version_number for v in wf.versions]) if wf.versions else None

    return {
        "workflow_id": wf.workflow_id,
        "workflow_key": wf.workflow_key,
        "name": wf.name,
        "description": wf.description,
        "entity_type": wf.entity_type,
        "status": wf.status,
        "created_by": wf.created_by,
        "created_at": wf.created_at,
        "updated_by": wf.updated_by,
        "updated_at": wf.updated_at,
        "latest_version": latest_v,
        "published_version": published_v,
        "versions": versions_data
    }


@router.put("/{workflow_id}", response_model=Dict[str, Any])
def update_workflow(
    workflow_id: int,
    payload: WorkflowUpdate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id") if current_user else None
    wf = WorkflowDefinitionService.update_workflow(db, workflow_id, payload, user_id=user_id)
    return {
        "workflow_id": wf.workflow_id,
        "workflow_key": wf.workflow_key,
        "name": wf.name,
        "description": wf.description,
        "entity_type": wf.entity_type,
        "status": wf.status,
        "updated_by": wf.updated_by,
        "updated_at": wf.updated_at
    }


@router.delete("/{workflow_id}", response_model=Dict[str, Any])
def delete_workflow(
    workflow_id: int,
    db: Session = Depends(get_workflow_db)
):
    return WorkflowDefinitionService.delete_workflow(db, workflow_id)


# ==========================================
# 2. VERSION MANAGEMENT
# ==========================================

@router.post("/{workflow_id}/versions", response_model=Dict[str, Any])
def create_workflow_version(
    workflow_id: int,
    payload: WorkflowVersionCreate,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id") if current_user else None
    v = WorkflowDefinitionService.create_version(db, workflow_id, payload, user_id=user_id)
    try:
        meta = json.loads(v.definition_metadata) if isinstance(v.definition_metadata, str) else (v.definition_metadata or {})
    except Exception:
        meta = {}
    return {
        "workflow_version_id": v.workflow_version_id,
        "workflow_id": v.workflow_id,
        "version_number": v.version_number,
        "status": v.status,
        "definition_metadata": meta,
        "created_by": v.created_by,
        "created_at": v.created_at,
        "published_at": v.published_at
    }


@router.get("/{workflow_id}/versions", response_model=List[Dict[str, Any]])
def list_workflow_versions(
    workflow_id: int,
    db: Session = Depends(get_workflow_db)
):
    versions = WorkflowDefinitionService.list_versions(db, workflow_id)
    res = []
    for v in versions:
        try:
            meta = json.loads(v.definition_metadata) if isinstance(v.definition_metadata, str) else (v.definition_metadata or {})
        except Exception:
            meta = {}
        res.append({
            "workflow_version_id": v.workflow_version_id,
            "workflow_id": v.workflow_id,
            "version_number": v.version_number,
            "status": v.status,
            "definition_metadata": meta,
            "created_by": v.created_by,
            "created_at": v.created_at,
            "published_at": v.published_at
        })
    return res


@router.get("/{workflow_id}/versions/{version_id}", response_model=Dict[str, Any])
def get_workflow_version(
    workflow_id: int,
    version_id: int,
    db: Session = Depends(get_workflow_db)
):
    v = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
    try:
        meta = json.loads(v.definition_metadata) if isinstance(v.definition_metadata, str) else (v.definition_metadata or {})
    except Exception:
        meta = {}

    nodes_data = [_serialize_node(n) for n in v.nodes if n.is_active]
    connections_data = [_serialize_connection(c) for c in v.connections]

    return {
        "workflow_version_id": v.workflow_version_id,
        "workflow_id": v.workflow_id,
        "version_number": v.version_number,
        "status": v.status,
        "definition_metadata": meta,
        "created_by": v.created_by,
        "created_at": v.created_at,
        "published_at": v.published_at,
        "nodes": nodes_data,
        "connections": connections_data
    }


# ==========================================
# 3. NODE MANAGEMENT
# ==========================================

@router.post("/{workflow_id}/versions/{version_id}/nodes", response_model=Dict[str, Any])
def add_workflow_node(
    workflow_id: int,
    version_id: int,
    payload: WorkflowNodeCreate,
    db: Session = Depends(get_workflow_db)
):
    node = WorkflowDefinitionService.add_node(db, workflow_id, version_id, payload)
    return _serialize_node(node)


@router.put("/{workflow_id}/versions/{version_id}/nodes/{node_id}", response_model=Dict[str, Any])
def update_workflow_node(
    workflow_id: int,
    version_id: int,
    node_id: int,
    payload: WorkflowNodeUpdate,
    db: Session = Depends(get_workflow_db)
):
    node = WorkflowDefinitionService.update_node(db, workflow_id, version_id, node_id, payload)
    return _serialize_node(node)


@router.delete("/{workflow_id}/versions/{version_id}/nodes/{node_id}", response_model=Dict[str, Any])
def delete_workflow_node(
    workflow_id: int,
    version_id: int,
    node_id: int,
    db: Session = Depends(get_workflow_db)
):
    return WorkflowDefinitionService.delete_node(db, workflow_id, version_id, node_id)


# ==========================================
# 4. CONNECTION MANAGEMENT
# ==========================================

@router.post("/{workflow_id}/versions/{version_id}/connections", response_model=Dict[str, Any])
def add_workflow_connection(
    workflow_id: int,
    version_id: int,
    payload: WorkflowConnectionCreate,
    db: Session = Depends(get_workflow_db)
):
    conn = WorkflowDefinitionService.add_connection(db, workflow_id, version_id, payload)
    return _serialize_connection(conn)


@router.delete("/{workflow_id}/versions/{version_id}/connections/{connection_id}", response_model=Dict[str, Any])
def delete_workflow_connection(
    workflow_id: int,
    version_id: int,
    connection_id: int,
    db: Session = Depends(get_workflow_db)
):
    return WorkflowDefinitionService.delete_connection(db, workflow_id, version_id, connection_id)


# ==========================================
# 5. LIFECYCLE OPERATIONS
# ==========================================

@router.post("/{workflow_id}/versions/{version_id}/validate", response_model=WorkflowValidationResponse)
def validate_workflow_version(
    workflow_id: int,
    version_id: int,
    db: Session = Depends(get_workflow_db)
):
    return WorkflowDefinitionService.validate_version(db, workflow_id, version_id)


@router.post("/{workflow_id}/versions/{version_id}/publish", response_model=Dict[str, Any])
def publish_workflow_version(
    workflow_id: int,
    version_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user.get("user_id") if current_user else None
    v = WorkflowDefinitionService.publish_version(db, workflow_id, version_id, user_id=user_id)
    try:
        meta = json.loads(v.definition_metadata) if isinstance(v.definition_metadata, str) else (v.definition_metadata or {})
    except Exception:
        meta = {}
    return {
        "message": f"Version {v.version_number} successfully published.",
        "workflow_version_id": v.workflow_version_id,
        "workflow_id": v.workflow_id,
        "version_number": v.version_number,
        "status": v.status,
        "definition_metadata": meta,
        "published_at": v.published_at
    }


@router.post("/{workflow_id}/versions/{version_id}/archive", response_model=Dict[str, Any])
def archive_workflow_version(
    workflow_id: int,
    version_id: int,
    db: Session = Depends(get_workflow_db)
):
    v = WorkflowDefinitionService.archive_version(db, workflow_id, version_id)
    return {
        "message": f"Version {v.version_number} archived successfully.",
        "workflow_version_id": v.workflow_version_id,
        "status": v.status
    }
