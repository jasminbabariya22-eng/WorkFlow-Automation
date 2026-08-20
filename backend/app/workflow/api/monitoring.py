import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response

from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask, SpiffActivityHistory
from app.workflow.models.history import WorkflowHistory

router = APIRouter(prefix="/workflow/monitoring", tags=["Workflow Monitoring"])


# 1. List Workflow Instances with status filter
@router.get("/instances")
def list_instances(
    status: Optional[str] = Query(None, description="Filter by status: 'Running', 'Completed', 'Failed'"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g., 'Risk')"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists workflow execution instances, with status and entity filters.
    """
    try:
        query = db.query(SpiffWorkflowInstance)
        if status:
            query = query.filter(SpiffWorkflowInstance.status == status)
        if entity_type:
            query = query.filter(SpiffWorkflowInstance.entity_type == entity_type)
            
        instances = query.order_by(SpiffWorkflowInstance.started_on.desc()).all()
        
        result = []
        for inst in instances:
            result.append({
                "instance_id": inst.instance_id,
                "entity_type": inst.entity_type,
                "entity_id": inst.entity_id,
                "bpmn_definition_id": inst.bpmn_definition_id,
                "status": inst.status,
                "current_task_code": inst.current_task_code,
                "started_on": inst.started_on,
                "completed_on": inst.completed_on
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 2. Get Workflow Instance details
@router.get("/instances/{id}")
def get_instance_details(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Instance not found")
            
        return success_response(data={
            "instance_id": inst.instance_id,
            "entity_type": inst.entity_type,
            "entity_id": inst.entity_id,
            "bpmn_definition_id": inst.bpmn_definition_id,
            "status": inst.status,
            "current_task_code": inst.current_task_code,
            "started_on": inst.started_on,
            "completed_on": inst.completed_on
        })
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 3. Get Process Variables of a specific instance
@router.get("/instances/{id}/variables")
def get_instance_variables(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Instance not found")
            
        # Parse process variables from serialized JSON string payload
        variables = {}
        if inst.serialized_state:
            try:
                state_data = json.loads(inst.serialized_state)
                # Merge data from all tasks in order of execution
                tasks = state_data.get("tasks", {})
                sorted_tasks = sorted(
                    tasks.values(),
                    key=lambda t: t.get("last_state_change", 0)
                )
                for task in sorted_tasks:
                    if isinstance(task.get("data"), dict):
                        variables.update(task["data"])
            except Exception:
                variables = {"error": "Failed to parse workflow variables from serialized state."}
                
        return success_response(data=variables)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 4. Get High-Level Transition History of a specific instance
@router.get("/instances/{id}/history")
def get_instance_history(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns audit trails of user transitions for the process instance.
    """
    try:
        history_records = db.query(WorkflowHistory).filter(
            WorkflowHistory.instance_id == id
        ).order_by(WorkflowHistory.performed_on.asc()).all()
        
        result = []
        for h in history_records:
            result.append({
                "history_id": h.history_id,
                "instance_id": h.instance_id,
                "from_state_code": getattr(h, "from_state_code", None),
                "to_state_code": getattr(h, "to_state_code", None),
                "action_name": h.action_name,
                "performed_by": h.performed_by,
                "performed_role": h.performed_role,
                "remarks": h.remarks,
                "performed_on": h.performed_on
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 5. Get Fine-Grained Activity Execution Logs of a specific instance
@router.get("/instances/{id}/logs")
def get_instance_activity_logs(
    id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns step-by-step activity traces (Service Tasks, scripts, gateways).
    """
    try:
        logs = db.query(SpiffActivityHistory).filter(
            SpiffActivityHistory.instance_id == id
        ).order_by(SpiffActivityHistory.timestamp.asc()).all()
        
        result = []
        for log in logs:
            parsed_vars = {}
            if log.variables:
                try:
                    parsed_vars = json.loads(log.variables) if isinstance(log.variables, str) else log.variables
                except Exception:
                    pass
            result.append({
                "activity_history_id": log.activity_history_id,
                "instance_id": log.instance_id,
                "activity_id": log.activity_id,
                "activity_name": log.activity_name,
                "activity_type": log.activity_type,
                "status": log.status,
                "variables": parsed_vars,
                "error_message": log.error_message,
                "timestamp": log.timestamp
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)


# 6. List Pending Human Tasks in the entire system
@router.get("/tasks/pending")
def list_pending_tasks(
    role_code: Optional[str] = Query(None, description="Filter pending tasks by role"),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        query = db.query(SpiffHumanTask).filter(SpiffHumanTask.status == "READY")
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
                "status": t.status,
                "created_on": t.created_on
            })
            
        return success_response(data=result)
    except Exception as e:
        return error_response(message=str(e), status_code=400)
