import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response
from app.core.logger import logger, WorkflowTelemetryLogger
from app.core.websocket import ws_manager

from app.workflow.persistence.models import (
    SpiffWorkflowInstance,
    SpiffHumanTask,
    SpiffActivityHistory,
    BPMNDefinition
)
from app.workflow.models.history import WorkflowHistory
from app.workflow_definition.models import (
    GenericWorkflow,
    WorkflowVersion,
    WorkflowNode
)
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.schemas.jobs import (
    JobCreateRequest,
    JobActionRequest,
    JobRestartRequest,
    JobSummaryResponse,
    JobStatusResponse,
    JobHistoryResponse
)

router = APIRouter(prefix="/workflow/jobs", tags=["Workflow Jobs & Execution"])


# ==========================================
# 1. CREATE & LAUNCH WORKFLOW JOB
# ==========================================

@router.post("/create", summary="Create and launch a new workflow execution job")
@router.post("", summary="Create and launch a new workflow execution job (alias)")
def create_job(
    payload: JobCreateRequest,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Standardized entrypoint to create and trigger a new workflow job.
    Accepts workflow_id or workflow_key, optional entity metadata, and initial variables.
    """
    try:
        # 1. Resolve workflow definition
        definition_id = payload.workflow_id
        if not definition_id and payload.workflow_key:
            # Look up by workflow_key
            gw = db.query(GenericWorkflow).filter(
                (GenericWorkflow.workflow_key == payload.workflow_key) |
                (GenericWorkflow.name == payload.workflow_key)
            ).first()
            if gw:
                definition_id = gw.workflow_id
            else:
                bpmn = db.query(BPMNDefinition).filter(
                    (BPMNDefinition.spec_id == payload.workflow_key) |
                    (BPMNDefinition.name == payload.workflow_key)
                ).first()
                if bpmn:
                    definition_id = bpmn.id

        if not definition_id:
            raise HTTPException(
                status_code=400,
                detail="Either 'workflow_id' or 'workflow_key' must be provided."
            )

        # 2. Resolve entity identifier
        entity_type = payload.entity_type or "generic_job"
        entity_id = payload.entity_id
        if not entity_id:
            # Generate unique sequence ID if not linked to a specific DB entity
            entity_id = int(time.time() * 1000) % 2147483647

        # 3. Resolve user details
        auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
        user_id = auth_user_id or 1
        user_name = (
            (current_user.get("name") if isinstance(current_user, dict) else None) or
            (current_user.get("username") if isinstance(current_user, dict) else None) or
            "System User"
        )
        user_email = (current_user.get("email") if isinstance(current_user, dict) else None) or ""

        # 4. Prepare context variables
        vars_dict = dict(payload.variables or {})
        vars_dict.setdefault("job_title", payload.title or f"Job #{entity_id}")
        vars_dict.setdefault("created_by_user_id", user_id)
        vars_dict.setdefault("created_by_name", user_name)
        vars_dict.setdefault("created_by_email", user_email)
        vars_dict.setdefault("created_at", datetime.now().isoformat())

        # 5. Check if Async Execution is requested
        if payload.async_execution:
            from app.workflow.runtime.executor_service import workflow_executor
            async_res = workflow_executor.submit_job_async(
                entity_type=entity_type,
                entity_id=entity_id,
                definition_id=definition_id,
                user_id=user_id,
                variables=vars_dict
            )
            return success_response(
                message="Workflow job queued for asynchronous background execution",
                data=async_res,
                status_code=status.HTTP_202_ACCEPTED
            )

        # 5b. Synchronous execution through StudioExecutionAdapter
        execution_result = StudioExecutionAdapter.start_workflow(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            variables=vars_dict,
            db=db,
            definition_id=definition_id
        )

        instance_id = execution_result.get("instance_id")
        instance = db.query(SpiffWorkflowInstance).filter(
            SpiffWorkflowInstance.instance_id == instance_id
        ).first()

        # 6. Broadcast real-time WebSocket event
        try:
            ws_manager.broadcast_event("JOB_CREATED", {
                "job_id": instance_id,
                "workflow_id": definition_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": instance.status if instance else "Running",
                "current_node": instance.current_task_code if instance else None,
                "user_id": user_id
            })
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast error: {ws_err}")

        logger.info(f"Job #{instance_id} created and started successfully for workflow definition #{definition_id}")

        return success_response(
            message="Workflow job created and started successfully",
            data={
                "job_id": instance_id,
                "workflow_id": definition_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": instance.status if instance else "Running",
                "current_node_key": instance.current_task_code if instance else None,
                "started_on": instance.started_on if instance else datetime.now(),
                "variables": vars_dict
            },
            status_code=status.HTTP_201_CREATED
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow job: {e}", exc_info=True)
        return error_response(message=f"Failed to create workflow job: {str(e)}", status_code=500)


# ==========================================
# 2. LIST WORKFLOW JOBS
# ==========================================

@router.get("", summary="List workflow execution jobs")
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status: 'Running', 'Paused', 'Completed', 'Stopped', 'Failed'"),
    workflow_id: Optional[int] = Query(None, description="Filter by workflow definition ID"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Search by workflow name or entity"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists execution jobs with status, progress, and metadata.
    """
    try:
        query = db.query(SpiffWorkflowInstance)
        if status:
            query = query.filter(SpiffWorkflowInstance.status.ilike(status))
        if workflow_id:
            query = query.filter(SpiffWorkflowInstance.bpmn_definition_id == workflow_id)
        if entity_type:
            query = query.filter(SpiffWorkflowInstance.entity_type == entity_type)

        total_count = query.count()
        instances = query.order_by(SpiffWorkflowInstance.started_on.desc()).offset(offset).limit(limit).all()

        # Build workflow name cache
        wf_map = {}
        try:
            ver_rows = db.execute(text('''
                SELECT v.workflow_version_id, w.name, w.workflow_key, w.workflow_id
                FROM workflow.wf_version v 
                JOIN workflow.wf_definition w ON v.workflow_id = w.workflow_id
            ''')).fetchall()
            for r in ver_rows:
                wf_map[r[0]] = {"name": r[1], "key": r[2], "workflow_id": r[3]}
        except Exception:
            pass

        try:
            bpmn_rows = db.execute(text('SELECT id, name, spec_id FROM workflow.bpmn_definition')).fetchall()
            for r in bpmn_rows:
                if r[0] not in wf_map:
                    wf_map[r[0]] = {"name": r[1] or r[2], "key": r[2], "workflow_id": r[0]}
        except Exception:
            pass

        jobs_data = []
        for inst in instances:
            wf_info = wf_map.get(inst.bpmn_definition_id, {"name": f"Workflow #{inst.bpmn_definition_id}", "key": "", "workflow_id": inst.bpmn_definition_id})

            # Calculate rough progress percentage
            progress = 100.0 if inst.status in ["Completed", "APPROVED"] else (
                0.0 if inst.status == "Stopped" else 50.0
            )

            jobs_data.append({
                "job_id": inst.instance_id,
                "entity_type": inst.entity_type,
                "entity_id": inst.entity_id,
                "workflow_id": wf_info.get("workflow_id"),
                "workflow_name": wf_info.get("name"),
                "workflow_key": wf_info.get("key"),
                "status": inst.status,
                "current_node_key": inst.current_task_code,
                "progress_percent": progress,
                "started_on": inst.started_on,
                "completed_on": inst.completed_on
            })

        return success_response(data={
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "jobs": jobs_data
        })
    except Exception as e:
        logger.error(f"Error listing workflow jobs: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 3. GET JOB STATUS & DETAILS
# ==========================================

@router.get("/{job_id}/status", summary="Get real-time job execution status and active node")
def get_job_status(
    job_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieves the detailed execution status of a job, including active node information,
    progress percentage, pending human tasks, and current variables.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        # 1. Resolve workflow version & metadata
        wf_name = f"Workflow #{inst.bpmn_definition_id}"
        wf_key = ""
        nodes_list = []
        total_nodes_count = 1

        try:
            version = db.query(WorkflowVersion).filter(
                WorkflowVersion.workflow_version_id == inst.bpmn_definition_id
            ).first()
            if version:
                wf_name = version.workflow.name if version.workflow else wf_name
                wf_key = version.workflow.workflow_key if version.workflow else ""
                nodes_list = version.nodes or []
                total_nodes_count = max(len(nodes_list), 1)
        except Exception:
            pass

        # 2. Extract current node details
        current_node_meta = None
        for n in nodes_list:
            if n.node_key == inst.current_task_code:
                current_node_meta = {
                    "node_id": n.node_id,
                    "node_key": n.node_key,
                    "name": n.name,
                    "node_type": n.node_type,
                    "config": n.configuration or {}
                }
                break

        # 3. Calculate progress percentage
        completed_activities = db.query(SpiffActivityHistory).filter(
            SpiffActivityHistory.instance_id == job_id,
            SpiffActivityHistory.status == "COMPLETED"
        ).count()

        if inst.status in ["Completed", "APPROVED"]:
            progress = 100.0
        elif inst.status in ["Stopped", "Cancelled"]:
            progress = round((completed_activities / total_nodes_count) * 100.0, 1)
        else:
            progress = min(round((completed_activities / total_nodes_count) * 100.0, 1), 95.0)

        # 4. Fetch pending human tasks
        pending_tasks = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == job_id,
            SpiffHumanTask.status == "READY"
        ).all()
        tasks_data = [
            {
                "task_id": t.task_id,
                "task_spec_id": t.task_spec_id,
                "role_code": t.role_code,
                "status": t.status,
                "created_on": t.created_on
            }
            for t in pending_tasks
        ]

        # 5. Extract variables from serialized state
        variables = {}
        if inst.serialized_state:
            try:
                state_data = json.loads(inst.serialized_state)
                variables = state_data.get("variables", {})
            except Exception:
                pass

        # Calculate duration
        duration_seconds = None
        if inst.started_on:
            end_time = inst.completed_on or datetime.now()
            duration_seconds = round((end_time - inst.started_on).total_seconds(), 2)

        return success_response(data={
            "job_id": inst.instance_id,
            "entity_type": inst.entity_type,
            "entity_id": inst.entity_id,
            "workflow_id": inst.bpmn_definition_id,
            "workflow_name": wf_name,
            "workflow_key": wf_key,
            "status": inst.status,
            "current_node_key": inst.current_task_code,
            "current_node": current_node_meta,
            "progress_percent": progress,
            "pending_tasks": tasks_data,
            "variables": variables,
            "started_on": inst.started_on,
            "completed_on": inst.completed_on,
            "duration_seconds": duration_seconds
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status for #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 4. GET JOB EXECUTION HISTORY
# ==========================================

@router.get("/{job_id}/history", summary="Get step-by-step execution history and audit log")
def get_job_history(
    job_id: int,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the complete step-by-step execution traces, node transition logs,
    and human approvals audit history for a job.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        # 1. Fetch step activities from SpiffActivityHistory
        activities = db.query(SpiffActivityHistory).filter(
            SpiffActivityHistory.instance_id == job_id
        ).order_by(SpiffActivityHistory.timestamp.asc()).all()

        activity_records = []
        for a in activities:
            parsed_vars = {}
            if a.variables:
                try:
                    parsed_vars = json.loads(a.variables) if isinstance(a.variables, str) else a.variables
                except Exception:
                    pass

            activity_records.append({
                "activity_history_id": a.activity_history_id,
                "activity_id": a.activity_id,
                "activity_name": a.activity_name,
                "activity_type": a.activity_type,
                "status": a.status,
                "variables": parsed_vars,
                "error_message": a.error_message,
                "timestamp": a.timestamp
            })

        # 2. Fetch human transitions from WorkflowHistory
        transitions = db.query(WorkflowHistory).filter(
            WorkflowHistory.instance_id == job_id
        ).order_by(WorkflowHistory.performed_on.asc()).all()

        transition_records = [
            {
                "history_id": t.history_id,
                "action_name": t.action_name,
                "performed_by": t.performed_by,
                "performed_role": t.performed_role,
                "remarks": t.remarks,
                "from_state_code": t.from_state_code,
                "to_state_code": t.to_state_code,
                "performed_on": t.performed_on
            }
            for t in transitions
        ]

        return success_response(data={
            "job_id": job_id,
            "status": inst.status,
            "activity_count": len(activity_records),
            "activities": activity_records,
            "transition_count": len(transition_records),
            "transitions": transition_records
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history for job #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 5. PAUSE WORKFLOW JOB
# ==========================================

@router.post("/{job_id}/pause", summary="Pause a running workflow job")
def pause_job(
    job_id: int,
    payload: Optional[JobActionRequest] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Halts execution of a running workflow job. Prevents automated task progression.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        active_statuses = ["RUNNING", "WAITING", "PENDING", "READY"]
        if inst.status.upper() not in active_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Only active jobs ({', '.join(active_statuses)}) can be paused. Current status is '{inst.status}'."
            )

        auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
        reason = payload.reason if payload and payload.reason else "Paused by operator"

        # Preserve previous status so it can be restored on resume
        prev_status = inst.status
        try:
            if inst.serialized_state:
                st = json.loads(inst.serialized_state)
                st["_pre_pause_status"] = prev_status
                inst.serialized_state = json.dumps(st, default=str)
        except Exception:
            pass

        # Update status
        inst.status = "Paused"

        # Record activity history
        audit_log = SpiffActivityHistory(
            instance_id=job_id,
            activity_id="LIFECYCLE_PAUSE",
            activity_name="Job Paused",
            activity_type="SYSTEM",
            status="PAUSED",
            variables=json.dumps({"reason": reason, "paused_by": auth_user_id, "prev_status": prev_status}),
            timestamp=datetime.now()
        )
        db.add(audit_log)
        db.commit()

        # Telemetry & WebSocket broadcast
        WorkflowTelemetryLogger.log_audit_event(
            action_name="JOB_PAUSED",
            message=f"Job #{job_id} paused: {reason}",
            instance_id=job_id,
            actor_id=auth_user_id
        )

        try:
            ws_manager.broadcast_event("JOB_PAUSED", {
                "job_id": job_id,
                "status": "Paused",
                "reason": reason,
                "user_id": auth_user_id
            })
        except Exception:
            pass

        logger.info(f"Job #{job_id} paused successfully.")
        return success_response(
            message=f"Job #{job_id} has been paused successfully.",
            data={"job_id": job_id, "status": "Paused", "reason": reason}
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error pausing job #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 6. START / RESUME WORKFLOW JOB
# ==========================================

@router.post("/{job_id}/start", summary="Start or resume a paused workflow job")
@router.post("/{job_id}/resume", summary="Resume a paused workflow job (alias)")
def resume_job(
    job_id: int,
    payload: Optional[JobActionRequest] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Resumes execution of a paused workflow job from its current state.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        if inst.status.lower() != "paused":
            raise HTTPException(
                status_code=400,
                detail=f"Only 'Paused' jobs can be resumed. Current status is '{inst.status}'."
            )

        auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
        reason = payload.reason if payload and payload.reason else "Resumed by operator"

        # Determine restored status: restore previous status or check if pending human tasks exist
        restored_status = "Running"
        try:
            if inst.serialized_state:
                st = json.loads(inst.serialized_state)
                if "_pre_pause_status" in st:
                    restored_status = st.pop("_pre_pause_status")
                    inst.serialized_state = json.dumps(st, default=str)
        except Exception:
            pass

        has_pending_tasks = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == job_id,
            SpiffHumanTask.status == "READY"
        ).first() is not None

        if has_pending_tasks:
            restored_status = "WAITING"

        # Update status
        inst.status = restored_status

        # Record activity history
        audit_log = SpiffActivityHistory(
            instance_id=job_id,
            activity_id="LIFECYCLE_RESUME",
            activity_name="Job Resumed",
            activity_type="SYSTEM",
            status="RESUMED",
            variables=json.dumps({"reason": reason, "resumed_by": auth_user_id, "restored_status": restored_status}),
            timestamp=datetime.now()
        )
        db.add(audit_log)
        db.commit()

        # Telemetry & WebSocket broadcast
        WorkflowTelemetryLogger.log_audit_event(
            action_name="JOB_RESUMED",
            message=f"Job #{job_id} resumed: {reason}",
            instance_id=job_id,
            actor_id=auth_user_id
        )

        try:
            ws_manager.broadcast_event("JOB_RESUMED", {
                "job_id": job_id,
                "status": restored_status,
                "current_node": inst.current_task_code,
                "user_id": auth_user_id
            })
        except Exception:
            pass

        logger.info(f"Job #{job_id} resumed successfully (status: {restored_status}).")
        return success_response(
            message=f"Job #{job_id} has been resumed successfully.",
            data={"job_id": job_id, "status": restored_status, "current_node_key": inst.current_task_code}
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error resuming job #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 7. STOP / CANCEL WORKFLOW JOB
# ==========================================

@router.post("/{job_id}/stop", summary="Stop and cancel a workflow job")
def stop_job(
    job_id: int,
    payload: Optional[JobActionRequest] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Forcefully terminates an active or paused job, marks it 'Stopped', and cancels all pending tasks.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        if inst.status in ["Completed", "Stopped", "Cancelled", "APPROVED", "REJECTED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Job is already finished with status '{inst.status}'."
            )

        auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
        reason = payload.reason if payload and payload.reason else "Stopped by operator"

        # Update instance status
        now_dt = datetime.now()
        inst.status = "Stopped"
        inst.completed_on = now_dt

        # Cancel open human tasks
        cancelled_tasks_count = db.query(SpiffHumanTask).filter(
            SpiffHumanTask.instance_id == job_id,
            SpiffHumanTask.status == "READY"
        ).update({"status": "CANCELLED", "completed_on": now_dt})

        # Record activity history
        audit_log = SpiffActivityHistory(
            instance_id=job_id,
            activity_id="LIFECYCLE_STOP",
            activity_name="Job Terminated",
            activity_type="SYSTEM",
            status="STOPPED",
            variables=json.dumps({"reason": reason, "stopped_by": auth_user_id, "cancelled_tasks": cancelled_tasks_count}),
            timestamp=now_dt
        )
        db.add(audit_log)
        db.commit()

        # Telemetry & WebSocket broadcast
        WorkflowTelemetryLogger.log_audit_event(
            action_name="JOB_STOPPED",
            message=f"Job #{job_id} stopped: {reason} ({cancelled_tasks_count} tasks cancelled)",
            instance_id=job_id,
            actor_id=auth_user_id
        )

        try:
            ws_manager.broadcast_event("JOB_STOPPED", {
                "job_id": job_id,
                "status": "Stopped",
                "reason": reason,
                "user_id": auth_user_id
            })
        except Exception:
            pass

        logger.info(f"Job #{job_id} stopped successfully ({cancelled_tasks_count} tasks cancelled).")
        return success_response(
            message=f"Job #{job_id} has been stopped successfully.",
            data={"job_id": job_id, "status": "Stopped", "cancelled_tasks": cancelled_tasks_count}
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error stopping job #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


# ==========================================
# 8. RESTART WORKFLOW JOB
# ==========================================

@router.post("/{job_id}/restart", summary="Restart a workflow job from the beginning")
def restart_job(
    job_id: int,
    payload: Optional[JobRestartRequest] = None,
    db: Session = Depends(get_workflow_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Resets the job back to its START node and executes the initial workflow steps.
    Accepts updated variables to override or extend previous inputs.
    """
    try:
        inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail=f"Job #{job_id} not found.")

        auth_user_id = current_user.get("id") or current_user.get("user_id") if isinstance(current_user, dict) else None
        now_dt = datetime.now()

        # 1. Retrieve and merge variables
        existing_vars = {}
        if inst.serialized_state:
            try:
                state_data = json.loads(inst.serialized_state)
                existing_vars = state_data.get("variables", {})
            except Exception:
                pass

        if payload and payload.variables:
            existing_vars.update(payload.variables)

        existing_vars["restarted_at"] = now_dt.isoformat()
        existing_vars["restarted_by"] = auth_user_id

        # 2. Reset human tasks
        db.query(SpiffHumanTask).filter(SpiffHumanTask.instance_id == job_id).delete()

        # 3. If reset_history requested, clear previous activity traces
        if payload and payload.reset_history:
            db.query(SpiffActivityHistory).filter(SpiffActivityHistory.instance_id == job_id).delete()

        # 4. Resolve workflow version definition
        version = db.query(WorkflowVersion).filter(
            WorkflowVersion.workflow_version_id == inst.bpmn_definition_id
        ).first()

        if not version:
            raise HTTPException(status_code=404, detail=f"Workflow definition #{inst.bpmn_definition_id} not found.")

        start_node = next((n for n in version.nodes if n.node_type == "START" and n.is_active), None)
        if not start_node:
            raise HTTPException(status_code=400, detail="Workflow definition has no START node.")

        # 5. Reset instance attributes
        inst.status = "Running"
        inst.started_on = now_dt
        inst.completed_on = None
        inst.current_task_code = start_node.node_key
        inst.serialized_state = json.dumps(
            {"version_id": version.workflow_version_id, "variables": existing_vars},
            default=str
        )
        db.flush()

        # 6. Advance graph from START node
        res = StudioExecutionAdapter._advance_graph(
            db=db,
            instance=inst,
            version=version,
            from_node=start_node,
            action="RESTART",
            user_id=auth_user_id,
            variables=existing_vars
        )

        # 7. Record restart activity
        restart_log = SpiffActivityHistory(
            instance_id=job_id,
            activity_id="LIFECYCLE_RESTART",
            activity_name="Job Restarted",
            activity_type="SYSTEM",
            status="RESTARTED",
            variables=json.dumps({"restarted_by": auth_user_id, "new_status": inst.status}),
            timestamp=now_dt
        )
        db.add(restart_log)
        db.commit()

        # 8. Telemetry & WebSocket broadcast
        WorkflowTelemetryLogger.log_audit_event(
            action_name="JOB_RESTARTED",
            message=f"Job #{job_id} restarted from START node",
            instance_id=job_id,
            actor_id=auth_user_id
        )

        try:
            ws_manager.broadcast_event("JOB_RESTARTED", {
                "job_id": job_id,
                "status": inst.status,
                "current_node": inst.current_task_code,
                "user_id": auth_user_id
            })
        except Exception:
            pass

        logger.info(f"Job #{job_id} restarted successfully.")
        return success_response(
            message=f"Job #{job_id} has been restarted successfully.",
            data={
                "job_id": job_id,
                "status": inst.status,
                "current_node_key": inst.current_task_code,
                "execution_result": res
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error restarting job #{job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)
