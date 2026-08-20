from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.workflow.persistence.models import SpiffHumanTask, SpiffWorkflowInstance, BPMNDefinition
from app.workflow.persistence.repository import SpiffWorkflowRepository
from app.workflow.runtime.parser import SpiffBPMNParser
from app.workflow.runtime.engine import SpiffWorkflowEngine
from app.workflow.runtime.bpmn_execution import BPMNExecutionLayer

router = APIRouter(prefix="/workflow", tags=["Workflow Human Tasks"])


# Helper to instantiate the BPMN execution layers dynamically per request
def get_execution_layer(db: Session = Depends(get_workflow_db)) -> BPMNExecutionLayer:
    parser = SpiffBPMNParser()
    engine = SpiffWorkflowEngine()
    repo = SpiffWorkflowRepository(db)
    return BPMNExecutionLayer(parser, engine, repo)


# Schemas for requests
class TaskCompletionRequest(BaseModel):
    variables: Dict[str, Any] = {}
    remark: Optional[str] = None


# GET /workflow/tasks
@router.get("/tasks")
def get_pending_tasks(
    role_code: Optional[str] = Query(None, description="Filter by role code (e.g. FUNCTIONAL_HEAD)"),
    status: str = Query("READY", description="Filter by status (default READY)"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a list of active or completed Human Tasks filtered by role.
    """
    try:
        query = db.query(SpiffHumanTask).filter(SpiffHumanTask.status == status)
        if role_code:
            query = query.filter(SpiffHumanTask.role_code == role_code)
            
        tasks = query.order_by(SpiffHumanTask.created_on.desc()).all()
        
        result = []
        for t in tasks:
            result.append({
                "task_id": t.task_id,
                "instance_id": t.instance_id,
                "task_spec_id": t.task_spec_id,
                "role_code": t.role_code,
                "assignee_id": t.assignee_id,
                "status": t.status,
                "created_on": t.created_on,
                "completed_on": t.completed_on
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# POST /workflow/tasks/{id}/complete
@router.post("/tasks/{id}/complete")
def complete_task(
    id: int,
    payload: TaskCompletionRequest,
    db: Session = Depends(get_workflow_db),
    execution_layer: BPMNExecutionLayer = Depends(get_execution_layer),
    current_user: dict = Depends(get_current_user)
):
    """
    Completes a human task, resumes the execution loop, and transitions to the next state.
    """
    try:
        # 1. Fetch Human Task record
        task_record = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.task_id == id,
            SpiffHumanTask.status == "READY"
        ).first()
        
        if not task_record:
            raise HTTPException(status_code=404, detail="Task not found or already completed")

        # 2. Fetch associated Workflow Instance
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.instance_id == task_record.instance_id
        ).first()
        
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")

        # 3. Supply variables for execution
        execution_payload = {
            "approved": True,
            "user_id": current_user["id"],
            "role_code": task_record.role_code,
            **payload.variables
        }
        if payload.remark:
            execution_payload["remark"] = payload.remark

        # 4. Resolve process XML from bpmn_definition table using instance's bpmn_definition_id
        definition = db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        
        if not definition:
            raise HTTPException(status_code=404, detail="BPMN Definition not found")
            
        xml_content = definition.xml_content
        spec_id = definition.spec_id

        # 5. Resume execution layer
        result = execution_layer.resume_workflow(
            xml_content=xml_content,
            spec_id=spec_id,
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            task_spec_id=task_record.task_spec_id,
            payload=execution_payload,
            db_session=db
        )

        # 6. Update Human Task record
        task_record.status = "COMPLETED"
        task_record.completed_on = datetime.now()
        task_record.assignee_id = current_user["id"]
        
        db.commit()
        
        return success_response(data=result, message="Task completed successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)


# POST /workflow/tasks/{id}/reject
@router.post("/tasks/{id}/reject")
def reject_task(
    id: int,
    payload: TaskCompletionRequest,
    db: Session = Depends(get_workflow_db),
    execution_layer: BPMNExecutionLayer = Depends(get_execution_layer),
    current_user: dict = Depends(get_current_user)
):
    """
    Rejects the task, feeding a rejection payload back to resume SpiffWorkflow routing.
    """
    try:
        # 1. Fetch Human Task record
        task_record = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.task_id == id,
            SpiffHumanTask.status == "READY"
        ).first()
        
        if not task_record:
            raise HTTPException(status_code=404, detail="Task not found or already completed")

        # 2. Fetch associated Workflow Instance
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.instance_id == task_record.instance_id
        ).first()
        
        if not instance:
            raise HTTPException(status_code=404, detail="Workflow instance not found")

        # 3. Supply variables for execution
        execution_payload = {
            "approved": False,
            "user_id": current_user["id"],
            "role_code": task_record.role_code,
            **payload.variables
        }
        if payload.remark:
            execution_payload["remark"] = payload.remark

        # 4. Resolve process XML from bpmn_definition table using instance's bpmn_definition_id
        definition = db.query(BPMNDefinition).filter(
            BPMNDefinition.id == instance.bpmn_definition_id
        ).first()
        
        if not definition:
            raise HTTPException(status_code=404, detail="BPMN Definition not found")
            
        xml_content = definition.xml_content
        spec_id = definition.spec_id

        # 5. Resume execution layer
        result = execution_layer.resume_workflow(
            xml_content=xml_content,
            spec_id=spec_id,
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            task_spec_id=task_record.task_spec_id,
            payload=execution_payload,
            db_session=db
        )

        # 6. Update Human Task record
        task_record.status = "REJECTED"
        task_record.completed_on = datetime.now()
        task_record.assignee_id = current_user["id"]
        
        db.commit()
        
        return success_response(data=result, message="Task rejected successfully")
    except Exception as e:
        db.rollback()
        return error_response(message=str(e), status_code=400)
