from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.workflow.database import get_workflow_db
from app.core.dependencies import get_current_user
from app.core.response import success_response, error_response
from app.core.logger import logger
from app.workflow.runtime.executor_service import workflow_executor

router = APIRouter(prefix="/workflow/executor", tags=["Workflow Executor"])


class DispatchJobRequest(BaseModel):
    job_id: int = Field(..., description="Workflow Job (Instance) ID to dispatch to background executor")


@router.get("/status", summary="Get executor worker pool status and health metrics")
def get_executor_status(
    current_user: dict = Depends(get_current_user)
):
    """
    Returns real-time worker thread pool telemetry: active workers, queue depth,
    total jobs completed, failed, and global pause status.
    """
    try:
        metrics = workflow_executor.get_metrics()
        return success_response(data=metrics)
    except Exception as e:
        logger.error(f"Error fetching executor status: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


@router.post("/pause", summary="Globally pause the background job executor")
def pause_executor(
    current_user: dict = Depends(get_current_user)
):
    """
    Pauses new task pickups across all background executor worker threads.
    """
    try:
        workflow_executor.pause_executor()
        return success_response(
            message="Workflow Job Executor paused successfully.",
            data={"status": "PAUSED"}
        )
    except Exception as e:
        logger.error(f"Error pausing executor: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


@router.post("/resume", summary="Globally resume the background job executor")
def resume_executor(
    current_user: dict = Depends(get_current_user)
):
    """
    Resumes worker thread pickup for queued workflow tasks.
    """
    try:
        workflow_executor.resume_executor()
        return success_response(
            message="Workflow Job Executor resumed successfully.",
            data={"status": "HEALTHY"}
        )
    except Exception as e:
        logger.error(f"Error resuming executor: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)


@router.post("/dispatch", summary="Manually dispatch an existing job to the executor")
def dispatch_job(
    payload: DispatchJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Pushes an existing pending or queued job to the background worker pool for immediate processing.
    """
    try:
        res = workflow_executor.dispatch_existing_job(payload.job_id)
        return success_response(
            message=res.get("message", "Job dispatched successfully."),
            data=res
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error dispatching job #{payload.job_id}: {e}", exc_info=True)
        return error_response(message=str(e), status_code=500)
