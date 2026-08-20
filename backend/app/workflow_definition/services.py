import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.core.logger import logger
from app.workflow_definition.models import (
    WorkflowDefinition,
    WorkflowVersion,
    WorkflowNode,
    WorkflowConnection
)
from app.workflow_definition.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowVersionCreate,
    WorkflowNodeCreate,
    WorkflowNodeUpdate,
    WorkflowConnectionCreate,
    WorkflowValidationResponse
)
from app.workflow_definition.validator import WorkflowDefinitionValidator


class WorkflowDefinitionService:
    """
    Service managing generic workflow definitions, version lifecycle,
    node graph manipulation, validation, and version immutability.
    """

    # ==========================================
    # 1. WORKFLOW DEFINITIONS
    # ==========================================

    @staticmethod
    def create_workflow(db: Session, data: WorkflowCreate, user_id: Optional[int] = None) -> WorkflowDefinition:
        logger.info(f"Creating workflow definition key='{data.workflow_key}', name='{data.name}'")

        # Check unique workflow_key
        existing = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.workflow_key == data.workflow_key
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Workflow with key '{data.workflow_key}' already exists.")

        workflow = WorkflowDefinition(
            workflow_key=data.workflow_key,
            name=data.name,
            description=data.description,
            entity_type=data.entity_type,
            status="DRAFT",
            created_by=user_id,
            updated_by=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(workflow)
        db.flush()

        # Automatically create initial Version 1 in DRAFT
        initial_version = WorkflowVersion(
            workflow_id=workflow.workflow_id,
            version_number=1,
            status="DRAFT",
            definition_metadata=json.dumps({}),
            created_by=user_id,
            created_at=datetime.now()
        )
        db.add(initial_version)
        db.commit()
        db.refresh(workflow)

        logger.info(f"Workflow created ID={workflow.workflow_id}, key='{workflow.workflow_key}' with initial Version 1")
        return workflow

    @staticmethod
    def list_workflows(
        db: Session,
        entity_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = db.query(WorkflowDefinition)
        if entity_type:
            query = query.filter(WorkflowDefinition.entity_type == entity_type)
        if status:
            query = query.filter(WorkflowDefinition.status == status)

        workflows = query.order_by(WorkflowDefinition.updated_at.desc()).all()
        results = []

        for wf in workflows:
            versions = wf.versions
            latest_version = max([v.version_number for v in versions]) if versions else None
            published_v = next((v.version_number for v in versions if v.status == "PUBLISHED"), None)

            wf_dict = {
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
                "latest_version": latest_version,
                "published_version": published_v
            }
            results.append(wf_dict)

        return results

    @staticmethod
    def get_workflow(db: Session, workflow_id: int) -> WorkflowDefinition:
        workflow = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.workflow_id == workflow_id
        ).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")
        return workflow

    @staticmethod
    def update_workflow(db: Session, workflow_id: int, data: WorkflowUpdate, user_id: Optional[int] = None) -> WorkflowDefinition:
        workflow = WorkflowDefinitionService.get_workflow(db, workflow_id)

        if data.name is not None:
            workflow.name = data.name
        if data.description is not None:
            workflow.description = data.description
        if data.entity_type is not None:
            workflow.entity_type = data.entity_type
        if data.status is not None:
            workflow.status = data.status

        workflow.updated_by = user_id
        workflow.updated_at = datetime.now()
        db.commit()
        db.refresh(workflow)
        logger.info(f"Workflow ID={workflow_id} metadata updated by user={user_id}")
        return workflow

    @staticmethod
    def delete_workflow(db: Session, workflow_id: int) -> Dict[str, Any]:
        workflow = WorkflowDefinitionService.get_workflow(db, workflow_id)
        workflow.status = "ARCHIVED"
        workflow.updated_at = datetime.now()
        db.commit()
        logger.info(f"Workflow ID={workflow_id} marked as ARCHIVED")
        return {"message": f"Workflow '{workflow.workflow_key}' archived successfully.", "workflow_id": workflow_id}

    # ==========================================
    # 2. WORKFLOW VERSIONS
    # ==========================================

    @staticmethod
    def create_version(db: Session, workflow_id: int, data: WorkflowVersionCreate, user_id: Optional[int] = None) -> WorkflowVersion:
        workflow = WorkflowDefinitionService.get_workflow(db, workflow_id)

        # Determine version number
        if data.version_number:
            existing_v = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == workflow_id,
                WorkflowVersion.version_number == data.version_number
            ).first()
            if existing_v:
                raise HTTPException(status_code=400, detail=f"Version {data.version_number} already exists for this workflow.")
            version_number = data.version_number
        else:
            max_v = db.query(func.max(WorkflowVersion.version_number)).filter(
                WorkflowVersion.workflow_id == workflow_id
            ).scalar() or 0
            version_number = max_v + 1

        new_version = WorkflowVersion(
            workflow_id=workflow_id,
            version_number=version_number,
            status="DRAFT",
            definition_metadata=json.dumps(data.definition_metadata or {}),
            created_by=user_id,
            created_at=datetime.now()
        )
        db.add(new_version)
        db.flush()

        # Clone from existing version if requested
        if data.clone_from_version_id:
            source_version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == data.clone_from_version_id,
                WorkflowVersion.workflow_id == workflow_id
            ).first()
            if not source_version:
                raise HTTPException(status_code=404, detail=f"Source version ID {data.clone_from_version_id} not found to clone from.")

            node_id_map: Dict[int, int] = {}

            # Clone Nodes
            for src_node in source_version.nodes:
                cloned_node = WorkflowNode(
                    workflow_version_id=new_version.workflow_version_id,
                    node_key=src_node.node_key,
                    node_type=src_node.node_type,
                    name=src_node.name,
                    description=src_node.description,
                    position_x=src_node.position_x,
                    position_y=src_node.position_y,
                    configuration=src_node.configuration,
                    is_active=src_node.is_active,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(cloned_node)
                db.flush()
                node_id_map[src_node.node_id] = cloned_node.node_id

            # Clone Connections with remapped node IDs
            for src_conn in source_version.connections:
                if src_conn.source_node_id in node_id_map and src_conn.target_node_id in node_id_map:
                    cloned_conn = WorkflowConnection(
                        workflow_version_id=new_version.workflow_version_id,
                        source_node_id=node_id_map[src_conn.source_node_id],
                        target_node_id=node_id_map[src_conn.target_node_id],
                        connection_key=src_conn.connection_key,
                        condition=src_conn.condition,
                        label=src_conn.label,
                        metadata_json=src_conn.metadata_json,
                        created_at=datetime.now()
                    )
                    db.add(cloned_conn)

        db.commit()
        db.refresh(new_version)
        logger.info(f"Created version {new_version.version_number} for workflow ID={workflow_id} (Version ID={new_version.workflow_version_id})")
        return new_version

    @staticmethod
    def list_versions(db: Session, workflow_id: int) -> List[WorkflowVersion]:
        WorkflowDefinitionService.get_workflow(db, workflow_id)
        return db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).all()

    @staticmethod
    def get_version(db: Session, workflow_id: int, version_id: int) -> WorkflowVersion:
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == version_id,
            WorkflowVersion.workflow_id == workflow_id
        ).first()
        if not version:
            raise HTTPException(status_code=404, detail=f"Workflow version {version_id} not found for workflow {workflow_id}.")
        return version

    @staticmethod
    def _assert_version_editable(version: WorkflowVersion) -> None:
        """Enforces version immutability once published or archived."""
        if version.status == "PUBLISHED":
            raise HTTPException(status_code=400, detail="Cannot modify a published workflow version. Create a new draft version instead.")
        if version.status == "ARCHIVED":
            raise HTTPException(status_code=400, detail="Cannot modify an archived workflow version.")

    # ==========================================
    # 3. NODES
    # ==========================================

    @staticmethod
    def add_node(db: Session, workflow_id: int, version_id: int, data: WorkflowNodeCreate) -> WorkflowNode:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        WorkflowDefinitionService._assert_version_editable(version)

        # Check duplicate node_key
        existing = db.query(WorkflowNode).filter(
            WorkflowNode.workflow_version_id == version_id,
            WorkflowNode.node_key == data.node_key
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Node with key '{data.node_key}' already exists in this version.")

        node = WorkflowNode(
            workflow_version_id=version_id,
            node_key=data.node_key,
            node_type=data.node_type.upper(),
            name=data.name,
            description=data.description,
            position_x=data.position_x,
            position_y=data.position_y,
            configuration=json.dumps(data.configuration or {}),
            is_active=data.is_active,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        logger.info(f"Added node '{node.name}' ({node.node_type}) to version ID={version_id}")
        return node

    @staticmethod
    def update_node(db: Session, workflow_id: int, version_id: int, node_id: int, data: WorkflowNodeUpdate) -> WorkflowNode:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        WorkflowDefinitionService._assert_version_editable(version)

        node = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == node_id,
            WorkflowNode.workflow_version_id == version_id
        ).first()
        if not node:
            raise HTTPException(status_code=404, detail=f"Node ID {node_id} not found in version {version_id}.")

        if data.node_key is not None:
            # Check unique key
            existing = db.query(WorkflowNode).filter(
                WorkflowNode.workflow_version_id == version_id,
                WorkflowNode.node_key == data.node_key,
                WorkflowNode.node_id != node_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Duplicate node_key '{data.node_key}' in version {version_id}.")
            node.node_key = data.node_key

        if data.node_type is not None:
            node.node_type = data.node_type.upper()
        if data.name is not None:
            node.name = data.name
        if data.description is not None:
            node.description = data.description
        if data.position_x is not None:
            node.position_x = data.position_x
        if data.position_y is not None:
            node.position_y = data.position_y
        if data.configuration is not None:
            node.configuration = json.dumps(data.configuration)
        if data.is_active is not None:
            node.is_active = data.is_active

        node.updated_at = datetime.now()
        db.commit()
        db.refresh(node)
        logger.info(f"Updated node ID={node_id} in version ID={version_id}")
        return node

    @staticmethod
    def delete_node(db: Session, workflow_id: int, version_id: int, node_id: int) -> Dict[str, Any]:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        WorkflowDefinitionService._assert_version_editable(version)

        node = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == node_id,
            WorkflowNode.workflow_version_id == version_id
        ).first()
        if not node:
            raise HTTPException(status_code=404, detail=f"Node ID {node_id} not found in version {version_id}.")

        db.delete(node)
        db.commit()
        logger.info(f"Deleted node ID={node_id} from version ID={version_id}")
        return {"message": "Node deleted successfully", "node_id": node_id}

    # ==========================================
    # 4. CONNECTIONS
    # ==========================================

    @staticmethod
    def add_connection(db: Session, workflow_id: int, version_id: int, data: WorkflowConnectionCreate) -> WorkflowConnection:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        WorkflowDefinitionService._assert_version_editable(version)

        # Validate nodes exist in the same version
        source = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == data.source_node_id,
            WorkflowNode.workflow_version_id == version_id
        ).first()
        if not source:
            raise HTTPException(status_code=400, detail=f"Source node ID {data.source_node_id} does not exist in version {version_id}.")

        target = db.query(WorkflowNode).filter(
            WorkflowNode.node_id == data.target_node_id,
            WorkflowNode.workflow_version_id == version_id
        ).first()
        if not target:
            raise HTTPException(status_code=400, detail=f"Target node ID {data.target_node_id} does not exist in version {version_id}.")

        connection = WorkflowConnection(
            workflow_version_id=version_id,
            source_node_id=data.source_node_id,
            target_node_id=data.target_node_id,
            connection_key=data.connection_key,
            condition=data.condition,
            label=data.label,
            metadata_json=json.dumps(data.metadata_json or {}),
            created_at=datetime.now()
        )
        db.add(connection)
        db.commit()
        db.refresh(connection)
        logger.info(f"Added connection ID={connection.connection_id} ({source.node_key} -> {target.node_key}) to version ID={version_id}")
        return connection

    @staticmethod
    def delete_connection(db: Session, workflow_id: int, version_id: int, connection_id: int) -> Dict[str, Any]:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        WorkflowDefinitionService._assert_version_editable(version)

        connection = db.query(WorkflowConnection).filter(
            WorkflowConnection.connection_id == connection_id,
            WorkflowConnection.workflow_version_id == version_id
        ).first()
        if not connection:
            raise HTTPException(status_code=404, detail=f"Connection ID {connection_id} not found in version {version_id}.")

        db.delete(connection)
        db.commit()
        logger.info(f"Deleted connection ID={connection_id} from version ID={version_id}")
        return {"message": "Connection deleted successfully", "connection_id": connection_id}

    # ==========================================
    # 5. LIFECYCLE & VALIDATION
    # ==========================================

    @staticmethod
    def validate_version(db: Session, workflow_id: int, version_id: int) -> WorkflowValidationResponse:
        logger.info(f"Validating workflow ID={workflow_id}, version ID={version_id}")
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        validation_result = WorkflowDefinitionValidator.validate_version(version)

        if validation_result.is_valid:
            if version.status == "DRAFT":
                version.status = "VALIDATED"
                db.commit()
            logger.info(f"Workflow ID={workflow_id}, version ID={version_id} validation succeeded")
        else:
            logger.warning(f"Workflow ID={workflow_id}, version ID={version_id} validation failed with {len(validation_result.errors)} errors")

        return validation_result

    @staticmethod
    def publish_version(db: Session, workflow_id: int, version_id: int, user_id: Optional[int] = None) -> WorkflowVersion:
        logger.info(f"Publishing workflow ID={workflow_id}, version ID={version_id}")
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)

        # 1. Run validation
        validation_result = WorkflowDefinitionValidator.validate_version(version)
        if not validation_result.is_valid:
            error_msgs = "; ".join([e.message for e in validation_result.errors])
            raise HTTPException(status_code=400, detail=f"Workflow version is not valid for publishing: {error_msgs}")

        # 2. Archive previously published versions for this workflow
        prev_published = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.status == "PUBLISHED",
            WorkflowVersion.workflow_version_id != version_id
        ).all()
        for prev in prev_published:
            prev.status = "ARCHIVED"
            logger.info(f"Archived previous version ID={prev.workflow_version_id} (v{prev.version_number})")

        # 3. Mark current version as PUBLISHED
        version.status = "PUBLISHED"
        version.published_at = datetime.now()

        # 4. Activate workflow definition
        workflow = WorkflowDefinitionService.get_workflow(db, workflow_id)
        workflow.status = "ACTIVE"
        workflow.updated_at = datetime.now()

        db.commit()
        db.refresh(version)
        logger.info(f"Successfully published version ID={version_id} (v{version.version_number}) for workflow '{workflow.workflow_key}'")
        return version

    @staticmethod
    def archive_version(db: Session, workflow_id: int, version_id: int) -> WorkflowVersion:
        version = WorkflowDefinitionService.get_version(db, workflow_id, version_id)
        version.status = "ARCHIVED"
        db.commit()
        db.refresh(version)
        logger.info(f"Archived version ID={version_id} (v{version.version_number}) for workflow ID={workflow_id}")
        return version
