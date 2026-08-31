import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

import time
from app.workflow.persistence.models import BPMNDefinition, SpiffWorkflowInstance, SpiffHumanTask, SpiffActivityHistory, WorkflowEntityConfig
from app.workflow.runtime.compiler import WorkflowGraphCompiler
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.bpmn_execution import BPMNExecutionLayer
from app.workflow.persistence.repository import SpiffWorkflowRepository
from app.workflow_management.schemas import (
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowDefinitionResponse,
    ValidationResponse,
    WorkflowExecuteRequest
)
from app.workflow_management.services import WorkflowManagementService

from app.workflow_definition.models import GenericWorkflow, WorkflowVersion

router = APIRouter(prefix="/workflow/definitions", tags=["Workflow Management Platform"])



# 1. GET /workflow/definitions
@router.get("", response_model=Dict[str, Any])
def list_workflow_definitions(
    status: Optional[str] = Query(None, description="Filter by status: 'Draft', 'Published', 'Active', 'Archived'"),
    spec_id: Optional[str] = Query(None, description="Filter by specification ID"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        query = db.query(BPMNDefinition)
        if status:
            query = query.filter(BPMNDefinition.status == status)
        if spec_id:
            query = query.filter(BPMNDefinition.spec_id == spec_id)
            
        definitions = query.order_by(BPMNDefinition.spec_id.asc(), BPMNDefinition.version.desc()).all()
        
        result = []
        for d in definitions:
            result.append({
                "id": d.id,
                "spec_id": d.spec_id,
                "name": d.name or d.spec_id,
                "version": d.version,
                "description": d.description,
                "xml_content": d.xml_content,
                "json_content": d.json_content,
                "is_active": d.is_active,
                "status": d.status,
                "tags": d.tags,
                "connection_id": d.connection_id,
                "created_by": d.created_by,
                "created_on": d.created_on,
                "updated_on": getattr(d, "updated_on", d.created_on),
                "published_on": getattr(d, "published_on", None)
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 2. GET /workflow/definitions/{id}
@router.get("/{id}")
def get_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        d = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not d:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
            
        return success_response(data={
            "id": d.id,
            "spec_id": d.spec_id,
            "name": d.name or d.spec_id,
            "version": d.version,
            "description": d.description,
            "xml_content": d.xml_content,
            "json_content": d.json_content,
            "is_active": d.is_active,
            "status": d.status,
            "tags": d.tags,
            "connection_id": d.connection_id,
            "created_by": d.created_by,
            "created_on": d.created_on,
            "updated_on": getattr(d, "updated_on", d.created_on),
            "published_on": getattr(d, "published_on", None)
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 3. POST /workflow/definitions
@router.post("")
def create_workflow_definition(
    payload: WorkflowCreateRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Check if version 1 for this spec_id already exists
        exists = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == payload.spec_id,
            BPMNDefinition.version == 1
        ).first()
        
        if exists:
            raise HTTPException(status_code=400, detail=f"Draft Version 1 for specification ID '{payload.spec_id}' already exists.")

        # Determine visual json graph and xml content
        json_content_str = payload.json_content
        xml_content = payload.xml_content

        if json_content_str:
            try:
                graph = json.loads(json_content_str)
                xml_content = WorkflowGraphCompiler.compile_graph_to_bpmn(payload.spec_id, graph)
            except Exception as compile_err:
                print(f"Compilation warning: {compile_err}")

        if not json_content_str and not xml_content:
            default_graph = {"nodes": [], "edges": []}
            json_content_str = json.dumps(default_graph)
            xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Definitions_{payload.spec_id}" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="{payload.spec_id}" name="{payload.name}" isExecutable="true">
  </bpmn:process>
</bpmn:definitions>"""

        new_def = BPMNDefinition(
            spec_id=payload.spec_id,
            name=payload.name,
            version=1,
            description=payload.description or "Workflow Draft Definition",
            xml_content=xml_content,
            json_content=json_content_str,
            is_active=False,
            status="Draft",
            tags=payload.tags,
            connection_id=payload.connection_id,
            created_by=current_user.get("id", 1),
            created_on=datetime.now()
        )
        db.add(new_def)
        db.commit()
        db.refresh(new_def)
        
        return success_response(data={"id": new_def.id, "spec_id": new_def.spec_id}, message="Workflow Draft created successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 4. PUT /workflow/definitions/{id}
@router.put("/{id}")
def update_workflow_definition(
    id: int,
    payload: WorkflowUpdateRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Draft versions can be updated in-place. Published versions are read-only.
        if definition.status != "Draft" and definition.version != 1:
            raise HTTPException(status_code=400, detail="Only Draft / Version 1 specifications can be edited in-place.")

        if payload.name:
            definition.name = payload.name
        if payload.description:
            definition.description = payload.description
        if payload.json_content:
            definition.json_content = payload.json_content
            try:
                graph = json.loads(payload.json_content)
                definition.xml_content = WorkflowGraphCompiler.compile_graph_to_bpmn(definition.spec_id, graph)
            except Exception as compile_err:
                print(f"Compilation warning: {compile_err}")
        elif payload.xml_content:
            definition.xml_content = payload.xml_content

        if payload.tags:
            definition.tags = payload.tags
        if payload.connection_id is not None:
            definition.connection_id = payload.connection_id
            
        definition.updated_on = datetime.now()
        db.commit()
        
        return success_response(message="Draft workflow updated successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 5. DELETE /workflow/definitions/{id}
@router.delete("/{id}")
def delete_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Active production workflows cannot be deleted directly
        if definition.is_active:
            raise HTTPException(status_code=400, detail="Active production workflow versions cannot be deleted. Deactivate it first.")

        db.delete(definition)
        db.commit()
        return success_response(message="Workflow version deleted successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 6. POST /workflow/definitions/{id}/validate
@router.post("/{id}/validate")
def validate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        errors = WorkflowManagementService.validate_bpmn(definition.xml_content, definition.spec_id)
        is_valid = len([e for e in errors if e.severity == "Error"]) == 0
        
        return success_response(data={
            "is_valid": is_valid,
            "errors": [e.dict() for e in errors]
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 7. POST /workflow/definitions/{id}/publish
@router.post("/{id}/publish")
def publish_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        published = WorkflowManagementService.publish_workflow(db, id, current_user["id"])
        
        # Synchronize wf_definition and wf_version
        wf_records = db.query(GenericWorkflow).filter(
            (GenericWorkflow.workflow_key == published.spec_id) | (GenericWorkflow.workflow_id == published.id)
        ).all()
        for wf in wf_records:
            wf.status = "ACTIVE"
            wf.updated_at = datetime.now()
            db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_id == wf.workflow_id
            ).update({"status": "PUBLISHED", "published_at": datetime.now()})
        db.commit()

        return success_response(
            data={"id": published.id, "version": published.version}, 
            message=f"Workflow successfully published as Version {published.version}"
        )
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 8. POST /workflow/definitions/{id}/activate
@router.post("/{id}/activate")
def activate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        # Deactivate all versions of this spec_id
        db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == definition.spec_id
        ).update({"is_active": False, "status": "Published"})

        # Mark this version active
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

        # Update active entity mapping for this specification
        target_entity = definition.spec_id or "DefaultEntity"
        entity_config = db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.entity_type == target_entity
        ).first()
        if entity_config:
            entity_config.specification_id = definition.spec_id
            entity_config.is_active = True
            entity_config.modified_on = datetime.now()
        else:
            entity_config = WorkflowEntityConfig(
                entity_type=target_entity,
                specification_id=definition.spec_id,
                is_active=True,
                created_on=datetime.now()
            )
            db.add(entity_config)

        db.commit()
        
        return success_response(message=f"Workflow version {definition.version} activated and set as active process for '{target_entity}'")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 9. POST /workflow/definitions/{id}/deactivate
@router.post("/{id}/deactivate")
def deactivate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

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
        target_entity = definition.spec_id
        entity_config = db.query(WorkflowEntityConfig).filter(
            WorkflowEntityConfig.specification_id == target_entity
        ).first()
        if entity_config:
            entity_config.is_active = False
            entity_config.modified_on = datetime.now()

        db.commit()
        return success_response(message=f"Workflow version {definition.version} deactivated successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 10. POST /workflow/definitions/{id}/duplicate
@router.post("/{id}/duplicate")
def duplicate_workflow_definition(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        cloned = WorkflowManagementService.duplicate_workflow(db, id, current_user["id"])
        return success_response(
            data={"id": cloned.id, "spec_id": cloned.spec_id},
            message=f"Cloned into new draft specification '{cloned.spec_id}' successfully"
        )
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 10. POST /workflow/definitions/import
@router.post("/import")
def import_workflow_bpmn(
    spec_id: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    connection_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        xml_bytes = file.file.read()
        xml_content = xml_bytes.decode("utf-8")
        
        # Validate XML structure
        errors = WorkflowManagementService.validate_bpmn(xml_content, spec_id)
        critical_errors = [e for e in errors if e.severity == "Error"]
        if critical_errors:
            raise HTTPException(status_code=400, detail=f"Imported BPMN is structurally invalid: {[e.message for e in critical_errors]}")

        # Check duplicate Version 1 draft
        exists = db.query(BPMNDefinition).filter(
            BPMNDefinition.spec_id == spec_id,
            BPMNDefinition.version == 1
        ).first()

        if exists:
            raise HTTPException(status_code=400, detail=f"Draft Version 1 for specification ID '{spec_id}' already exists.")

        new_def = BPMNDefinition(
            spec_id=spec_id,
            name=name,
            version=1,
            description=description or "Imported BPMN specification",
            xml_content=xml_content,
            is_active=False,
            status="Draft",
            tags=tags,
            connection_id=connection_id,
            created_by=current_user["id"],
            created_on=datetime.now()
        )
        db.add(new_def)
        db.commit()
        db.refresh(new_def)
        
        return success_response(data={"id": new_def.id, "spec_id": new_def.spec_id}, message="BPMN imported successfully as Draft Version 1")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# 11. GET /workflow/definitions/{id}/export
@router.get("/{id}/export")
def export_workflow_bpmn(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
            
        headers = {
            "Content-Disposition": f"attachment; filename={definition.spec_id}_v{definition.version}.bpmn"
        }
        return Response(content=definition.xml_content, media_type="application/xml", headers=headers)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 12. POST /workflow/definitions/{id}/execute
@router.post("/{id}/execute")
def execute_workflow_definition(
    id: int,
    payload: WorkflowExecuteRequest = WorkflowExecuteRequest(),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Executes a workflow definition with custom input variables.
    Automated activities and script tasks run synchronously.
    If a Human Task is encountered, execution pauses in 'Running' state and returns the ready human task.
    """
    try:
        definition = db.query(BPMNDefinition).filter(BPMNDefinition.id == id).first()
        if not definition:
            raise HTTPException(status_code=404, detail="Workflow definition not found")

        if not definition.xml_content:
            raise HTTPException(status_code=400, detail="Workflow definition contains no BPMN XML content.")

        # Setup execution layer
        parser = SpiffBPMNParser()
        engine = SpiffWorkflowEngine()
        repo = SpiffWorkflowRepository(db)
        execution_layer = BPMNExecutionLayer(parser, engine, repo)

        # Generate unique entity ID if not provided
        entity_type = payload.entity_type or "TestExecution"
        entity_id = payload.entity_id or (int(time.time() * 1000) % 2147483647)

        # Build execution context
        init_vars = dict(payload.initial_variables or {})
        init_vars["entity_type"] = entity_type
        init_vars["entity_id"] = entity_id
        init_vars["user_id"] = current_user.get("id", 1)

        context = WorkflowContext(
            variables=init_vars,
            user_id=current_user.get("id", 1),
            db=db
        )

        # Execute workflow
        start_result = execution_layer.start_workflow(
            xml_content=definition.xml_content,
            spec_id=definition.spec_id,
            definition_db_id=definition.id,
            context=context,
            db_session=db
        )
        db.commit()

        # Query created instance details
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.entity_type == entity_type,
            SpiffWorkflowInstance.entity_id == entity_id
        ).first()

        instance_id = instance.instance_id if instance else None

        # Fetch ready human tasks if any
        tasks = []
        if instance_id:
            db_tasks = db.query(SpiffHumanTask).filter(
                SpiffHumanTask.instance_id == instance_id,
                SpiffHumanTask.status == "READY"
            ).all()
            for t in db_tasks:
                tasks.append({
                    "task_id": t.task_id,
                    "task_spec_id": t.task_spec_id,
                    "role_code": t.role_code,
                    "status": t.status,
                    "created_on": t.created_on
                })

        # Extract current process variables from serialized state
        variables = {}
        if instance and instance.serialized_state:
            try:
                state_data = json.loads(instance.serialized_state)
                tasks_dict = state_data.get("tasks", {})
                for t in tasks_dict.values():
                    if "data" in t and isinstance(t["data"], dict):
                        variables.update(t["data"])
            except Exception:
                pass

        # Fetch execution logs
        logs = []
        if instance_id:
            db_logs = db.query(SpiffActivityHistory).filter(
                SpiffActivityHistory.instance_id == instance_id
            ).order_by(SpiffActivityHistory.timestamp.asc()).all()
            for l in db_logs:
                logs.append({
                    "activity_id": l.activity_id,
                    "activity_name": l.activity_name,
                    "activity_type": l.activity_type,
                    "status": l.status,
                    "timestamp": l.timestamp
                })

        return success_response(data={
            "instance_id": instance_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "definition_id": definition.id,
            "spec_id": definition.spec_id,
            "status": start_result.get("status", "Running"),
            "current_task_code": start_result.get("current_task_code"),
            "ready_tasks": tasks,
            "variables": variables,
            "logs": logs
        }, message="Workflow execution initiated successfully")

    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)

