import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException

from app.core.logger import logger
from app.workflow_definition.models import (
    GenericWorkflow,
    WorkflowVersion,
    WorkflowNode,
    WorkflowConnection
)
from app.workflow_studio.schemas import (
    StudioNode,
    StudioEdge,
    StudioWorkflowCreate,
    StudioWorkflowUpdate,
    StudioWorkflowResponse,
    StudioWorkflowListItem,
    StudioValidationResponse
)
from app.workflow_studio.validator import WorkflowStudioValidator


class WorkflowStudioService:
    """
    WorkflowStudioService provides the bridge between visual Studio graph JSON
    and persistent database workflow definitions and version lifecycle.
    """

    @classmethod
    def _serialize_studio_response(
        cls,
        workflow: GenericWorkflow,
        version: WorkflowVersion
    ) -> StudioWorkflowResponse:
        # Map db nodes to StudioNode list
        nodes_list: List[StudioNode] = []
        db_id_to_key: Dict[int, str] = {}

        for n in version.nodes:
            if not n.is_active:
                continue
            db_id_to_key[n.node_id] = n.node_key
            try:
                cfg = json.loads(n.configuration) if isinstance(n.configuration, str) else (n.configuration or {})
            except Exception:
                cfg = {}

            nodes_list.append(StudioNode(
                id=n.node_key,
                type=n.node_type,
                name=n.name,
                position_x=n.position_x,
                position_y=n.position_y,
                config=cfg
            ))

        # Map db connections to StudioEdge list
        edges_list: List[StudioEdge] = []
        for c in version.connections:
            src_key = db_id_to_key.get(c.source_node_id, str(c.source_node_id))
            tgt_key = db_id_to_key.get(c.target_node_id, str(c.target_node_id))
            try:
                cfg = json.loads(c.metadata_json) if isinstance(c.metadata_json, str) else (c.metadata_json or {})
            except Exception:
                cfg = {}

            edges_list.append(StudioEdge(
                id=c.connection_key or f"edge_{c.connection_id}",
                source=src_key,
                target=tgt_key,
                condition=c.condition,
                label=c.label,
                config=cfg
            ))

        try:
            meta = json.loads(version.definition_metadata) if isinstance(version.definition_metadata, str) else (version.definition_metadata or {})
        except Exception:
            meta = {}

        return StudioWorkflowResponse(
            workflow_id=workflow.workflow_id,
            workflow_key=workflow.workflow_key,
            name=workflow.name,
            description=workflow.description,
            entity_type=workflow.entity_type,
            connection_id=workflow.connection_id,
            status=workflow.status,
            version_id=version.workflow_version_id,
            version_number=version.version_number,
            version_status=version.status,
            nodes=nodes_list,
            edges=edges_list,
            metadata=meta,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            published_at=version.published_at
        )

    @classmethod
    def _save_nodes_and_edges(
        cls,
        db: Session,
        version_id: int,
        nodes: List[StudioNode],
        edges: List[StudioEdge]
    ) -> None:
        # Delete existing nodes and connections for this draft version
        db.query(WorkflowConnection).filter(WorkflowConnection.workflow_version_id == version_id).delete()
        db.query(WorkflowNode).filter(WorkflowNode.workflow_version_id == version_id).delete()
        db.flush()

        key_to_db_id: Dict[str, int] = {}

        # Insert nodes
        for node in nodes:
            db_node = WorkflowNode(
                workflow_version_id=version_id,
                node_key=str(node.id).strip(),
                node_type=str(node.type).strip().upper(),
                name=node.name,
                position_x=node.position_x,
                position_y=node.position_y,
                configuration=json.dumps(node.config or {}),
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(db_node)
            db.flush()
            key_to_db_id[str(node.id).strip()] = db_node.node_id

        # Insert connections
        for edge in edges:
            src_id = key_to_db_id.get(str(edge.source).strip())
            tgt_id = key_to_db_id.get(str(edge.target).strip())
            if src_id and tgt_id:
                db_conn = WorkflowConnection(
                    workflow_version_id=version_id,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    connection_key=edge.id or f"edge_{src_id}_{tgt_id}",
                    condition=edge.condition,
                    label=edge.label,
                    metadata_json=json.dumps(edge.config or {}),
                    created_at=datetime.now()
                )
                db.add(db_conn)

        db.flush()

    # ==========================================
    # CRUD & LIFECYCLE
    # ==========================================

    @classmethod
    def create_workflow_draft(
        cls,
        db: Session,
        data: StudioWorkflowCreate,
        user_id: Optional[int] = None
    ) -> StudioWorkflowResponse:
        wf_key = data.workflow_key or f"studio_flow_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        logger.info(f"WorkflowStudio: Creating workflow draft key='{wf_key}', name='{data.name}'")

        # Check unique key
        existing = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_key == wf_key).first()
        if existing:
            wf_key = f"{wf_key}_{uuid.uuid4().hex[:6]}"

        workflow = GenericWorkflow(
            workflow_key=wf_key,
            name=data.name,
            description=data.description,
            entity_type=data.entity_type,
            connection_id=data.connection_id,
            status="DRAFT",
            created_by=user_id,
            updated_by=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(workflow)
        db.flush()

        initial_version = WorkflowVersion(
            workflow_id=workflow.workflow_id,
            version_number=1,
            status="DRAFT",
            definition_metadata=json.dumps(data.metadata or {}),
            created_by=user_id,
            created_at=datetime.now()
        )
        db.add(initial_version)
        db.flush()

        if data.nodes or data.edges:
            cls._save_nodes_and_edges(db, initial_version.workflow_version_id, data.nodes, data.edges)

        db.commit()
        db.refresh(workflow)
        db.refresh(initial_version)

        logger.info(f"WorkflowStudio: Created workflow ID={workflow.workflow_id} (Version ID={initial_version.workflow_version_id})")
        return cls._serialize_studio_response(workflow, initial_version)

    @classmethod
    def get_workflow_definition(
        cls,
        db: Session,
        workflow_id: int,
        version_id: Optional[int] = None
    ) -> StudioWorkflowResponse:
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        if version_id:
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == version_id,
                WorkflowVersion.workflow_id == workflow_id
            ).first()
            if not version:
                raise HTTPException(status_code=404, detail=f"Workflow version {version_id} not found.")
        else:
            # Pick latest draft or latest published version
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == workflow_id
            ).order_by(WorkflowVersion.version_number.desc()).first()
            if not version:
                raise HTTPException(status_code=404, detail=f"No versions found for workflow ID {workflow_id}.")

        return cls._serialize_studio_response(workflow, version)

    @classmethod
    def update_workflow_draft(
        cls,
        db: Session,
        workflow_id: int,
        data: StudioWorkflowUpdate,
        user_id: Optional[int] = None
    ) -> StudioWorkflowResponse:
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        latest_version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        if not latest_version:
            raise HTTPException(status_code=404, detail=f"No version found for workflow ID {workflow_id}.")

        if latest_version.status == "PUBLISHED":
            raise HTTPException(
                status_code=400,
                detail="Cannot modify a published workflow version directly. Create a new draft version to make changes."
            )

        if data.name is not None:
            workflow.name = data.name
        if data.description is not None:
            workflow.description = data.description
        if data.entity_type is not None:
            workflow.entity_type = data.entity_type
        if data.connection_id is not None:
            workflow.connection_id = data.connection_id
        if data.metadata is not None:
            latest_version.definition_metadata = json.dumps(data.metadata)

        if data.nodes is not None or data.edges is not None:
            nodes_to_save = data.nodes if data.nodes is not None else []
            edges_to_save = data.edges if data.edges is not None else []
            cls._save_nodes_and_edges(db, latest_version.workflow_version_id, nodes_to_save, edges_to_save)

        workflow.updated_by = user_id
        workflow.updated_at = datetime.now()

        db.commit()
        db.refresh(workflow)
        db.refresh(latest_version)

        logger.info(f"WorkflowStudio: Updated workflow draft ID={workflow_id} (v{latest_version.version_number})")
        return cls._serialize_studio_response(workflow, latest_version)

    @classmethod
    def validate_workflow(
        cls,
        db: Session,
        workflow_id: int,
        version_id: Optional[int] = None
    ) -> StudioValidationResponse:
        studio_def = cls.get_workflow_definition(db, workflow_id, version_id)
        val_res = WorkflowStudioValidator.validate_graph(studio_def.nodes, studio_def.edges)
        logger.info(f"WorkflowStudio: Validated workflow ID={workflow_id}, is_valid={val_res.is_valid}")
        return val_res

    @classmethod
    def publish_workflow(
        cls,
        db: Session,
        workflow_id: int,
        version_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> StudioWorkflowResponse:
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        if version_id:
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == version_id,
                WorkflowVersion.workflow_id == workflow_id
            ).first()
        else:
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == workflow_id
            ).order_by(WorkflowVersion.version_number.desc()).first()

        if not version:
            raise HTTPException(status_code=404, detail="No version found to publish.")

        # 1. Run Validation
        studio_def = cls._serialize_studio_response(workflow, version)
        val_res = WorkflowStudioValidator.validate_graph(studio_def.nodes, studio_def.edges)
        if not val_res.is_valid:
            error_details = "; ".join([e.message for e in val_res.errors])
            raise HTTPException(
                status_code=400,
                detail=f"Workflow cannot be published due to validation errors: {error_details}"
            )

        # 2. Archive prior published versions
        prior_published = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.status == "PUBLISHED",
            WorkflowVersion.workflow_version_id != version.workflow_version_id
        ).all()
        for prev in prior_published:
            prev.status = "ARCHIVED"

        # 3. Mark current version as PUBLISHED
        version.status = "PUBLISHED"
        version.published_at = datetime.now()

        # 4. Activate workflow definition
        workflow.status = "ACTIVE"
        workflow.updated_by = user_id
        workflow.updated_at = datetime.now()

        db.commit()
        db.refresh(workflow)
        db.refresh(version)

        # 5. Compile to BPMN XML for SpiffWorkflow runtime compatibility
        try:
            from app.workflow.runtime.compiler import WorkflowGraphCompiler
            bpmn_xml = WorkflowGraphCompiler.compile_graph_to_bpmn(
                spec_id=workflow.workflow_key,
                graph_data={
                    "nodes": [n.model_dump() for n in studio_def.nodes],
                    "edges": [e.model_dump() for e in studio_def.edges]
                }
            )
            from app.workflow.persistence.models import BPMNDefinition
            bpmn_def = db.query(BPMNDefinition).filter(
                BPMNDefinition.spec_id == workflow.workflow_key,
                BPMNDefinition.version == version.version_number
            ).first()
            if not bpmn_def:
                bpmn_def = BPMNDefinition(
                    spec_id=workflow.workflow_key,
                    version=version.version_number,
                    xml_content=bpmn_xml,
                    is_active=True,
                    created_on=datetime.now()
                )
                db.add(bpmn_def)
            else:
                bpmn_def.xml_content = bpmn_xml
                bpmn_def.is_active = True
            db.commit()
        except Exception as bpmn_err:
            logger.warning(f"WorkflowStudio: BPMN compilation adapter notice: {bpmn_err}")

        logger.info(f"WorkflowStudio: Successfully published workflow '{workflow.workflow_key}' (v{version.version_number})")
        return cls._serialize_studio_response(workflow, version)


    @classmethod
    def list_workflows(
        cls,
        db: Session,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200
    ) -> List[StudioWorkflowListItem]:
        from sqlalchemy.orm import selectinload
        query = db.query(GenericWorkflow).options(selectinload(GenericWorkflow.versions))
        if entity_type:
            query = query.filter(GenericWorkflow.entity_type == entity_type)
        if status:
            query = query.filter(GenericWorkflow.status == status)

        workflows = query.order_by(GenericWorkflow.updated_at.desc(), GenericWorkflow.workflow_id.desc()).limit(limit).all()
        results: List[StudioWorkflowListItem] = []

        for wf in workflows:
            versions = wf.versions
            latest_v = max([v.version_number for v in versions]) if versions else 1
            pub_v = next((v.version_number for v in versions if v.status == "PUBLISHED"), None)

            results.append(StudioWorkflowListItem(
                workflow_id=wf.workflow_id,
                workflow_key=wf.workflow_key,
                name=wf.name,
                description=wf.description,
                entity_type=wf.entity_type,
                connection_id=wf.connection_id,
                status=wf.status,
                latest_version=latest_v,
                published_version=pub_v,
                created_at=wf.created_at,
                updated_at=wf.updated_at
            ))

        return results

    @classmethod
    def delete_workflow(cls, db: Session, workflow_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Deletes or archives a workflow definition.
        """
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        # Check if active instances exist
        from app.workflow.persistence.models import SpiffWorkflowInstance
        active_instances = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == workflow.entity_type,
            SpiffWorkflowInstance.status == "Running"
        ).count()

        if active_instances > 0:
            workflow.status = "ARCHIVED"
            db.commit()
            return {"message": f"Workflow {workflow_id} has running instances and was marked ARCHIVED."}

        db.delete(workflow)
        db.commit()
        return {"message": f"Workflow {workflow_id} deleted successfully."}

    @classmethod
    def unpublish_workflow(cls, db: Session, workflow_id: int, user_id: Optional[int] = None) -> StudioWorkflowResponse:
        """
        Reverts the current published version back to DRAFT or ARCHIVED status.
        """
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        published_version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.status == "PUBLISHED"
        ).first()

        if not published_version:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} has no currently published version.")

        published_version.status = "DRAFT"
        published_version.published_at = None
        workflow.status = "DRAFT"
        workflow.updated_by = user_id
        workflow.updated_at = datetime.now()

        db.commit()
        db.refresh(workflow)
        db.refresh(published_version)

        logger.info(f"WorkflowStudio: Unpublished workflow {workflow_id} (v{published_version.version_number})")
        return cls._serialize_studio_response(workflow, published_version)

    @classmethod
    def get_workflow_versions(cls, db: Session, workflow_id: int) -> List[Dict[str, Any]]:
        """
        Lists all versions for a given workflow with version metadata and publication dates.
        """
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        versions = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).all()

        return [
            {
                "version_id": v.workflow_version_id,
                "version_number": v.version_number,
                "status": v.status,
                "node_count": len([n for n in v.nodes if n.is_active]),
                "connection_count": len(v.connections),
                "created_at": v.created_at,
                "published_at": v.published_at
            }
            for v in versions
        ]

    @classmethod
    def create_version(cls, db: Session, workflow_id: int, user_id: Optional[int] = None, description: Optional[str] = None) -> StudioWorkflowResponse:
        """
        Creates a new draft version for a workflow, cloning nodes from the previous published version if present.
        """
        from app.workflow_definition.schemas import WorkflowVersionCreate
        from app.workflow_definition.services import WorkflowDefinitionService

        latest_version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id
        ).order_by(WorkflowVersion.version_number.desc()).first()

        next_v_num = (latest_version.version_number + 1) if latest_version else 1
        clone_id = latest_version.workflow_version_id if (latest_version and latest_version.status == "PUBLISHED") else None

        version_data = WorkflowVersionCreate(
            version_number=next_v_num,
            clone_from_version_id=clone_id,
            definition_metadata={"description": description} if description else {}
        )
        new_v = WorkflowDefinitionService.create_version(db, workflow_id, version_data, user_id=user_id)
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        return cls._serialize_studio_response(workflow, new_v)

    @classmethod
    def get_workflow_version_by_number(cls, db: Session, workflow_id: int, version_number: int) -> StudioWorkflowResponse:
        """
        Fetches the complete studio definition for a specific version number.
        """
        workflow = db.query(GenericWorkflow).filter(GenericWorkflow.workflow_id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow with ID {workflow_id} not found.")

        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == version_number
        ).first()

        if not version:
            raise HTTPException(status_code=404, detail=f"Version {version_number} of workflow {workflow_id} not found.")

        return cls._serialize_studio_response(workflow, version)

    @classmethod
    def get_available_roles(cls) -> List[Dict[str, Any]]:
        """
        Returns candidate roles dynamically loaded from the Client Database.
        """
        from app.core.database import ClientDatabaseAdapter
        return ClientDatabaseAdapter.get_roles()

    @classmethod
    def get_available_actions(cls) -> List[Dict[str, Any]]:
        """
        Returns workflow actions dynamically discovered from Client DB action tables or Workflow DB permissions.
        """
        from app.core.database import ClientDatabaseAdapter
        client_actions = ClientDatabaseAdapter.get_actions()
        if client_actions:
            return client_actions

        try:
            from app.workflow.database import workflow_engine
            from sqlalchemy import text
            with workflow_engine.connect() as conn:
                rows = conn.execute(text("SELECT DISTINCT actions FROM workflow.workflow_task_permission WHERE is_active = true")).fetchall()
                distinct_codes = set()
                for r in rows:
                    if r.actions:
                        for act in r.actions.split(','):
                            code = act.strip().upper()
                            if code:
                                distinct_codes.add(code)
                if distinct_codes:
                    return [
                        {
                            "id": code,
                            "action_code": code,
                            "name": code.replace("_", " ").title(),
                            "description": f"Workflow decision action {code}"
                        }
                        for code in sorted(distinct_codes)
                    ]
        except Exception as e:
            logger.warning(f"WorkflowStudioService: Error discovering actions: {e}")

        return []

