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


import xml.etree.ElementTree as ET


def parse_bpmn_to_reactflow(xml_str: Optional[str], wf_key: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Parses BPMN XML and/or GenericWorkflow database definitions into React Flow compatible nodes & edges.
    """
    # 1. Check if matching GenericWorkflow exists in wf_definition
    if db and wf_key:
        gw = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == wf_key) | 
            (GenericWorkflow.name.ilike(f"%{wf_key}%")) |
            (GenericWorkflow.workflow_id == (int(wf_key) if str(wf_key).isdigit() else -1))
        ).first()
        if gw and gw.versions:
            v = gw.versions[-1]
            nodes = []
            for i, n in enumerate(v.nodes):
                raw_type = str(n.node_type).lower()
                rf_type = 'start' if 'start' in raw_type else ('end' if 'end' in raw_type else ('userTask' if 'approval' in raw_type or 'user' in raw_type else ('condition' if 'cond' in raw_type or 'gate' in raw_type else ('email' if 'email' in raw_type else ('record' if 'rec' in raw_type or 'action' in raw_type else 'generic')))))
                px = n.position_x if n.position_x and n.position_x != 0 else (200 + (i % 2) * 260)
                py = n.position_y if n.position_y and n.position_y != 0 else (50 + i * 130)
                nodes.append({
                    'id': n.node_key,
                    'type': rf_type,
                    'position': {'x': px, 'y': py},
                    'data': {'label': n.name or n.node_key, 'name': n.name or n.node_key, 'actions': ['APPROVE', 'REJECT']}
                })
            edges = []
            node_map = {n.node_id: n.node_key for n in v.nodes}
            for c in v.connections:
                edges.append({
                    'id': c.connection_key or f"e-{c.source_node_id}-{c.target_node_id}",
                    'source': node_map.get(c.source_node_id, str(c.source_node_id)),
                    'target': node_map.get(c.target_node_id, str(c.target_node_id)),
                    'type': 'workflow',
                    'data': {'label': c.label or c.condition or '', 'action': c.condition or c.label or ''}
                })
            if len(nodes) > 0:
                return {'nodes': nodes, 'edges': edges}

    # 2. Parse standard BPMN XML
    if not xml_str:
        return {'nodes': [], 'edges': []}
    try:
        root = ET.fromstring(xml_str)
        ns = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC'
        }
        process = root.find('.//bpmn:process', ns)
        if process is None:
            for elem in root.iter():
                if elem.tag.endswith('process'):
                    process = elem
                    break
        if process is None:
            return {'nodes': [], 'edges': []}

        bounds = {}
        for shape in root.findall('.//bpmndi:BPMNShape', ns):
            bpmn_el = shape.attrib.get('bpmnElement')
            b = shape.find('.//dc:Bounds', ns)
            if bpmn_el and b is not None:
                bounds[bpmn_el] = {'x': float(b.attrib.get('x', 200)), 'y': float(b.attrib.get('y', 100))}

        nodes = []
        edges = []
        idx = 0
        for child in process:
            tag = child.tag.split('}')[-1]
            cid = child.attrib.get('id')
            cname = child.attrib.get('name') or cid
            if tag in ['startEvent', 'userTask', 'serviceTask', 'sendTask', 'exclusiveGateway', 'inclusiveGateway', 'parallelGateway', 'endEvent', 'task', 'callActivity']:
                rf_type = 'start' if tag == 'startEvent' else ('end' if tag == 'endEvent' else ('userTask' if tag in ['userTask', 'task', 'callActivity'] else ('condition' if 'Gateway' in tag else ('email' if tag == 'sendTask' else ('record' if tag == 'serviceTask' else 'generic')))))
                pos = bounds.get(cid, {'x': 200 + (idx % 2) * 260, 'y': 50 + idx * 130})
                nodes.append({
                    'id': cid,
                    'type': rf_type,
                    'position': pos,
                    'data': {'label': cname, 'name': cname, 'actions': ['APPROVE', 'REJECT']}
                })
                idx += 1
            elif tag == 'sequenceFlow':
                edges.append({
                    'id': cid,
                    'source': child.attrib.get('sourceRef'),
                    'target': child.attrib.get('targetRef'),
                    'type': 'workflow',
                    'data': {'label': cname if cname != cid else '', 'action': cname or ''}
                })
        return {'nodes': nodes, 'edges': edges}
    except Exception as e:
        return {'nodes': [], 'edges': []}


@router.get("")
def list_workflow_definitions(
    db: Session = Depends(get_workflow_db)
):
    """
    Returns all workflow definitions directly from workflow.bpmn_definition table.
    """
    try:
        bpmn_defs = db.query(BPMNDefinition).order_by(BPMNDefinition.id.desc()).all()
        seen_specs = {}
        for b in bpmn_defs:
            if b.spec_id not in seen_specs or (b.is_active and not seen_specs[b.spec_id].is_active):
                seen_specs[b.spec_id] = b

        result = []
        for b in seen_specs.values():
            name_label = b.description.split('->')[0].split('(')[0].strip() if b.description else b.spec_id.replace('_', ' ').title()
            parsed_graph = parse_bpmn_to_reactflow(b.xml_content, b.spec_id, db)
            result.append({
                "id": b.id,
                "workflow_id": b.id,
                "spec_id": b.spec_id,
                "name": name_label if len(name_label) < 60 else b.spec_id.replace('_', ' ').title(),
                "description": b.description or "",
                "connection_id": 4 if 'leave' in b.spec_id else None,
                "version": b.version or 1,
                "status": "Active" if b.is_active or b.status == "Active" else (b.status or "Draft"),
                "is_active": bool(b.is_active),
                "created_on": b.created_on.isoformat() if b.created_on else None,
                "updated_on": b.created_on.isoformat() if b.created_on else None,
                "tags": [b.spec_id.split('_')[0].upper()],
                "nodes_count": len(parsed_graph['nodes']) or 3,
                "xml_content": b.xml_content,
                "json_content": parsed_graph
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
    Retrieves workflow definition by ID with complete parsed React Flow graph.
    """
    try:
        b = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not b:
            b = db.query(BPMNDefinition).filter(BPMNDefinition.spec_id == str(id)).first()

        if b:
            name_label = b.description.split('->')[0].split('(')[0].strip() if b.description else b.spec_id.replace('_', ' ').title()
            parsed_graph = parse_bpmn_to_reactflow(b.xml_content, b.spec_id, db)
            return success_response(data={
                "id": b.id,
                "workflow_id": b.id,
                "spec_id": b.spec_id,
                "name": name_label if len(name_label) < 60 else b.spec_id.replace('_', ' ').title(),
                "description": b.description or "",
                "connection_id": 4 if 'leave' in b.spec_id else None,
                "version": b.version or 1,
                "status": "Active" if b.is_active or b.status == "Active" else (b.status or "Draft"),
                "is_active": bool(b.is_active),
                "xml_content": b.xml_content,
                "json_content": parsed_graph
            })

        raise HTTPException(status_code=404, detail="Workflow definition not found")
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
