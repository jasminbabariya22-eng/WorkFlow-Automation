from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.workflow.persistence.models import BPMNDefinition, WorkflowEntityConfig
from app.workflow_definition.models import GenericWorkflow, WorkflowVersion
from SpiffWorkflow.bpmn.parser import BpmnParser, BpmnValidator

router = APIRouter(prefix="/workflow/definitions", tags=["Workflow Definitions"])

class SaveDefinitionRequest(BaseModel):
    spec_id: str
    xml_content: str
    description: Optional[str] = None

class PublishDefinitionRequest(BaseModel):
    spec_id: str
    xml_content: str
    description: Optional[str] = None


@router.get("")
def list_workflow_definitions(
    db: Session = Depends(get_workflow_db)
):
    """
    Returns recent active and draft workflow definitions for the dashboard in a single fast query.
    """
    try:
        from sqlalchemy.orm import selectinload
        wfs = (
            db.query(GenericWorkflow)
            .options(selectinload(GenericWorkflow.versions))
            .order_by(GenericWorkflow.updated_at.desc().nullslast(), GenericWorkflow.workflow_id.desc())
            .limit(50)
            .all()
        )
        result = []
        for w in wfs:
            latest_v = max([v.version_number for v in w.versions]) if w.versions else 1
            result.append({
                "id": w.workflow_id,
                "spec_id": w.workflow_key or f"workflow_{w.workflow_id}",
                "name": w.name,
                "description": w.description or "",
                "connection_id": w.connection_id,
                "version": latest_v,
                "status": "Active" if w.status == "ACTIVE" else "Draft",
                "is_active": (w.status == "ACTIVE"),
                "created_on": w.created_at.isoformat() if w.created_at else None,
                "updated_on": w.updated_at.isoformat() if w.updated_at else None,
                "tags": [w.entity_type] if w.entity_type else []
            })
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=500)


@router.get("/{id}")
def get_workflow_definition_by_id(
    id: int,
    db: Session = Depends(get_workflow_db)
):
    """
    Retrieves workflow definition by ID from wf_definition with full nodes and connections.
    """
    try:
        from app.workflow_studio.services import WorkflowStudioService
        wf_resp = WorkflowStudioService.get_workflow_definition(db, id)
        return success_response(data={
            "id": wf_resp.workflow_id,
            "spec_id": wf_resp.workflow_key,
            "name": wf_resp.name,
            "description": wf_resp.description,
            "connection_id": wf_resp.connection_id,
            "version": wf_resp.version_number,
            "status": "Active" if wf_resp.status == "ACTIVE" else "Draft",
            "is_active": (wf_resp.status == "ACTIVE"),
            "json_content": {
                "nodes": [n.dict() for n in wf_resp.nodes],
                "edges": [e.dict() for e in wf_resp.edges]
            }
        })
    except Exception as e:
        return error_response(message=str(e), status_code=404)


@router.post("/save")
def save_workflow_definition(
    payload: SaveDefinitionRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Saves a draft version (version 1) of the BPMN XML in the database.
    """
    try:
        # Check if there is already a draft version 1
        record = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == payload.spec_id,
            BPMNDefinition.version == 1
        ).first()

        if not record:
            record = BPMNDefinition(
                spec_id=payload.spec_id,
                version=1,
                xml_content=payload.xml_content,
                description=payload.description or "Draft definition",
                is_active=False,  # Draft is inactive by default
                created_by=current_user["id"],
                created_on=datetime.now()
            )
            db.add(record)
        else:
            record.xml_content = payload.xml_content
            record.description = payload.description or record.description
            record.created_on = datetime.now()

        db.commit()
        return success_response(message="Draft workflow saved successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


@router.post("/publish")
def publish_workflow_definition(
    payload: PublishDefinitionRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Validates the BPMN XML structure, compiles and increments version, and publishes it.
    """
    try:
        # 1. Run dynamic BpmnParser validation to reject structural errors
        try:
            parser = BpmnParser(validator=BpmnValidator())
            parser.add_bpmn_xml(payload.xml_content, filename=f"{payload.spec_id}.bpmn")
            parser.get_spec(payload.spec_id)
        except Exception as parser_err:
            raise HTTPException(status_code=400, detail=f"BPMN Validation Failed: {str(parser_err)}")

        # 2. Get the latest version number to increment it
        latest_version = db.query(BPMNDefinition.version).filter(
            BPMNDefinition.spec_id == payload.spec_id
        ).order_by(BPMNDefinition.version.desc()).first()

        next_version = (latest_version[0] + 1) if latest_version else 2 # Start version 2 if draft is 1

        # 3. Deactivate all existing versions
        db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == payload.spec_id
        ).update({"is_active": False})

        # 4. Insert the new active published version
        new_def = BPMNDefinition(
            spec_id=payload.spec_id,
            version=next_version,
            xml_content=payload.xml_content,
            description=payload.description or f"Version {next_version}",
            is_active=True,
            created_by=current_user["id"],
            created_on=datetime.now()
        )
        db.add(new_def)
        db.commit()

        return success_response(data={"version": next_version}, message="Workflow published successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


@router.post("/{id}/activate")
def activate_workflow_version(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Activates a specific version by its ID and deactivates all other versions of that spec.
    """
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow version not found")

        # Deactivate all versions of this spec
        db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == definition.spec_id
        ).update({"is_active": False, "status": "Published"})

        # Activate target version
        definition.is_active = True
        definition.status = "Active"

        # Synchronize GenericWorkflow (workflow.wf_definition) and wf_version
        wf_records = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == definition.spec_id) | (GenericWorkflow.workflow_id == definition.id)
        ).all()
        for wf in wf_records:
            wf.status = "ACTIVE"
            wf.updated_at = datetime.now()
            db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == wf.workflow_id
            ).update({"status": "PUBLISHED", "published_at": datetime.now()})

        # Update active entity mapping for 'Risk' entity
        entity_config = db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == "Risk"
        ).first()
        if entity_config:
            entity_config.specification_id = definition.spec_id
            entity_config.is_active = True
            entity_config.modified_on = datetime.now()
        else:
            entity_config = WorkflowEntityConfig(
                entity_type="Risk",
                specification_id=definition.spec_id,
                is_active=True,
                created_on=datetime.now()
            )
            db.add(entity_config)

        db.commit()

        return success_response(message=f"Workflow version {definition.version} activated and bound to Risk entity")

    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


@router.post("/{id}/deactivate")
def deactivate_workflow_version(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Deactivates a specific version.
    """
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow version not found")

        definition.is_active = False
        definition.status = "Inactive"

        # Synchronize GenericWorkflow (workflow.wf_definition) and wf_version
        wf_records = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == definition.spec_id) | (GenericWorkflow.workflow_id == definition.id)
        ).all()
        for wf in wf_records:
            wf.status = "INACTIVE"
            wf.updated_at = datetime.now()
            db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == wf.workflow_id
            ).update({"status": "ARCHIVED"})

        # Also deactivate entity config if linked
        entity_config = db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.specification_id == definition.spec_id
        ).first()
        if entity_config:
            entity_config.is_active = False
            entity_config.modified_on = datetime.now()

        db.commit()

        return success_response(message=f"Workflow version {definition.version} deactivated successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


@router.get("/{spec_id}/versions")
def list_workflow_versions(
    spec_id: str,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists all available versions for a process definition.
    """
    try:
        versions = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == spec_id
        ).order_by(BPMNDefinition.version.desc()).all()

        result = []
        for v in versions:
            result.append({
                "id": v.id,
                "spec_id": v.spec_id,
                "version": v.version,
                "description": v.description,
                "is_active": v.is_active,
                "created_on": v.created_on
            })

        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


@router.get("/{spec_id}/latest")
def get_latest_definition(
    spec_id: str,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetches the latest active BPMN XML definition. Falls back to default XML skeleton if empty.
    """
    try:
        definition = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == spec_id,
            BPMNDefinition.is_active == True
        ).first()

        if not definition:
            definition = db.query(BPMNDefinition).filter(
                BPMNDefinition.spec_id == spec_id
            ).order_by(BPMNDefinition.version.desc()).first()

        if not definition:
            # Default empty BPMN 2.0 XML Canvas to load in BPMN.io Modeler
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
            <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                              xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                              xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                              xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                              id="Definitions_1"
                              targetNamespace="http://bpmn.io/schema/bpmn">
              <bpmn:process id="{spec_id}" isExecutable="true">
                <bpmn:startEvent id="StartEvent_1"/>
              </bpmn:process>
              <bpmndi:BPMNDiagram id="BPMNDiagram_1">
                <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{spec_id}">
                  <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
                    <dc:Bounds x="173" y="102" width="36" height="36"/>
                  </bpmndi:BPMNShape>
                </bpmndi:BPMNPlane>
              </bpmndi:BPMNDiagram>
            </bpmn:definitions>
            """
            return success_response(data={"xml_content": xml_content, "version": 0, "is_active": False})

        return success_response(data={
            "id": definition.id,
            "spec_id": definition.spec_id,
            "version": definition.version,
            "xml_content": definition.xml_content,
            "is_active": definition.is_active
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)
