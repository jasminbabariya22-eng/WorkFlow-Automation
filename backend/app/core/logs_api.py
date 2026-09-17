"""
logs_api.py
API Endpoints for Frontend Log Ingestion, Log File Management & 30-Day Retention Inspection.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.logger import logger, LOG_DIR, WorkflowTelemetryLogger, log_frontend_event, cleanup_old_logs
from app.core.response import success_response, error_response
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/logs", tags=["Global System Logs"])


class FrontendLogItem(BaseModel):
    level: str = "INFO"
    message: str
    timestamp: Optional[str] = None
    url: Optional[str] = None
    stack: Optional[str] = None
    component: Optional[str] = None
    user_id: Optional[Any] = None
    details: Optional[Dict[str, Any]] = None


class FrontendLogBatch(BaseModel):
    logs: List[FrontendLogItem]


@router.post("/frontend")
def ingest_frontend_logs(
    payload: FrontendLogBatch = Body(...),
):
    """
    Ingests client-side frontend logs and persists them into backend/logs/frontend/frontend_YYYY-MM-DD.log.
    """
    try:
        count = 0
        for item in payload.logs:
            log_frontend_event(
                level=item.level,
                message=item.message,
                timestamp=item.timestamp,
                url=item.url,
                stack=item.stack,
                component=item.component,
                user_id=item.user_id,
                details=item.details
            )
            count += 1
        return success_response(message=f"Ingested {count} frontend log entries", data={"count": count})
    except Exception as e:
        logger.error(f"LogsAPI: Failed to ingest frontend logs: {e}")
        return error_response(message=str(e), status_code=500)


@router.get("/files")
def list_log_files(
    category: Optional[str] = Query(None, description="'app', 'error', 'frontend', or None for all"),
    current_user: dict = Depends(get_current_user)
):
    """
    Lists all available daily log files from the last 30 days across backend and frontend.
    """
    try:
        cleanup_old_logs(retention_days=30)
        file_list = []

        for root, _, files in os.walk(LOG_DIR):
            for f in files:
                if not f.endswith(".log"):
                    continue
                fp = os.path.join(root, f)
                rel_path = os.path.relpath(fp, LOG_DIR).replace("\\", "/")
                file_type = "frontend" if "frontend" in rel_path else ("error" if "error" in f else "app")

                if category and category.lower() not in file_type.lower():
                    continue

                stat = os.stat(fp)
                mod_dt = datetime.fromtimestamp(stat.st_mtime)

                file_list.append({
                    "filename": f,
                    "relative_path": rel_path,
                    "type": file_type,
                    "size_bytes": stat.st_size,
                    "size_formatted": f"{round(stat.st_size / 1024, 1)} KB" if stat.st_size > 1024 else f"{stat.st_size} B",
                    "modified_at": mod_dt.strftime("%Y-%m-%d %H:%M:%S")
                })

        # Sort newest first
        file_list.sort(key=lambda x: x["modified_at"], reverse=True)
        return success_response(data=file_list)
    except Exception as e:
        return error_response(message=str(e), status_code=500)


@router.get("/download")
def download_log_file(
    file_path: str = Query(..., description="Relative log path (e.g. 'app_2026-09-17.log' or 'frontend/frontend_2026-09-17.log')"),
    current_user: dict = Depends(get_current_user)
):
    """
    Downloads a specific daily log file.
    """
    # Sanitize path to prevent directory traversal
    clean_path = os.path.normpath(file_path).lstrip("/\\")
    full_path = os.path.join(LOG_DIR, clean_path)

    if not os.path.abspath(full_path).startswith(os.path.abspath(LOG_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        path=full_path,
        filename=os.path.basename(full_path),
        media_type="text/plain"
    )
