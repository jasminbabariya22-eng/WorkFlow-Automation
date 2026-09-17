"""
logger.py
Enterprise Global Logging, Daily Date-Partitioned File Handlers, 30-Day Retention,
Frontend Ingestion, and Workflow Telemetry Observability.
"""

import logging
import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Any, List, Optional

# Base Directory for backend and frontend logs
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
FRONTEND_LOG_DIR = os.path.join(LOG_DIR, "frontend")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(FRONTEND_LOG_DIR, exist_ok=True)


class DailyDateFileHandler(logging.Handler):
    """
    High-performance, thread-safe daily rotating file handler that writes directly to
    date-stamped log files: {prefix}_{YYYY-MM-DD}.log inside target directory.
    Seamlessly switches to a new file when the date rolls over at midnight.
    """
    def __init__(self, log_dir: str, prefix: str = "app", level: int = logging.INFO):
        super().__init__(level)
        self.log_dir = log_dir
        self.prefix = prefix
        self._lock = threading.Lock()
        self._current_date: Optional[str] = None
        self._file_handle = None
        os.makedirs(self.log_dir, exist_ok=True)
        self._check_and_rotate()

    def _get_target_file(self, date_str: str) -> str:
        return os.path.join(self.log_dir, f"{self.prefix}_{date_str}.log")

    def _check_and_rotate(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        if today_str != self._current_date:
            if self._file_handle:
                try:
                    self._file_handle.flush()
                    self._file_handle.close()
                except Exception:
                    pass
            self._current_date = today_str
            file_path = self._get_target_file(today_str)
            self._file_handle = open(file_path, "a", encoding="utf-8", buffering=1)

    def emit(self, record):
        with self._lock:
            try:
                self._check_and_rotate()
                msg = self.format(record)
                if self._file_handle:
                    self._file_handle.write(msg + "\n")
            except Exception:
                self.handleError(record)

    def close(self):
        with self._lock:
            if self._file_handle:
                try:
                    self._file_handle.flush()
                    self._file_handle.close()
                except Exception:
                    pass
                self._file_handle = None
            super().close()


def cleanup_old_logs(retention_days: int = 30):
    """
    Scans LOG_DIR and its subdirectories and deletes any log files older than retention_days.
    Preserves exact 30-day historical window.
    """
    cutoff_ts = time.time() - (retention_days * 86400)
    cleaned_count = 0
    try:
        for root, _, files in os.walk(LOG_DIR):
            for f in files:
                if f.endswith(".log"):
                    fp = os.path.join(root, f)
                    try:
                        if os.path.getmtime(fp) < cutoff_ts:
                            os.remove(fp)
                            cleaned_count += 1
                    except Exception:
                        pass
    except Exception:
        pass
    return cleaned_count


# --- Standard Log Formatters ---
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# 1. Console Stream Handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

# 2. Daily Application Log Handler (app_YYYY-MM-DD.log) - All INFO, WARN, ERROR
daily_app_handler = DailyDateFileHandler(LOG_DIR, prefix="app", level=logging.INFO)
daily_app_handler.setFormatter(formatter)

# 3. Daily Error Log Handler (error_YYYY-MM-DD.log) - Strict ERROR, CRITICAL only
daily_error_handler = DailyDateFileHandler(LOG_DIR, prefix="error", level=logging.ERROR)
daily_error_handler.setFormatter(formatter)

# 4. Daily Frontend Log Handler (frontend/frontend_YYYY-MM-DD.log)
frontend_file_handler = DailyDateFileHandler(FRONTEND_LOG_DIR, prefix="frontend", level=logging.INFO)
frontend_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | [FRONTEND] %(message)s",
    "%Y-%m-%d %H:%M:%S"
)
frontend_file_handler.setFormatter(frontend_formatter)

# --- Global Logger Setup ---
logger = logging.getLogger("ers_logger")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(stream_handler)
logger.addHandler(daily_app_handler)
logger.addHandler(daily_error_handler)
logger.propagate = False

# Attach handlers to root logger and Uvicorn loggers for full application coverage
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in [stream_handler, daily_app_handler, daily_error_handler]:
    if h not in root_logger.handlers:
        root_logger.addHandler(h)

for uvicorn_log_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
    u_log = logging.getLogger(uvicorn_log_name)
    u_log.handlers = [stream_handler, daily_app_handler, daily_error_handler]
    u_log.propagate = False

# Run initial 30-day retention cleanup on module load
cleanup_old_logs(retention_days=30)


def log_frontend_event(
    level: str,
    message: str,
    timestamp: Optional[str] = None,
    url: Optional[str] = None,
    stack: Optional[str] = None,
    component: Optional[str] = None,
    user_id: Optional[Any] = None,
    details: Optional[Dict[str, Any]] = None
):
    """
    Logs an event originating from the Frontend client into backend/logs/frontend/frontend_YYYY-MM-DD.log
    and feeds it into WorkflowTelemetryLogger for live dashboard observability.
    """
    lvl = level.upper().strip() if level else "INFO"
    meta_parts = []
    if component:
        meta_parts.append(f"Component: <{component}>")
    if url:
        meta_parts.append(f"URL: {url}")
    if user_id:
        meta_parts.append(f"User: #{user_id}")

    meta_str = f" [{ ' | '.join(meta_parts) }]" if meta_parts else ""
    full_msg = f"{message}{meta_str}"
    if stack:
        full_msg += f"\n  Stack Trace:\n{stack}"

    # Log record for frontend file handler
    rec = logging.LogRecord(
        name="frontend_client",
        level=getattr(logging, lvl, logging.INFO),
        pathname="frontend",
        lineno=1,
        msg=full_msg,
        args=(),
        exc_info=None
    )
    frontend_file_handler.emit(rec)

    # Also record into Daily App / Error log if it's an error
    if lvl in ("ERROR", "CRITICAL"):
        logger.error(f"[FRONTEND] {full_msg}")
    else:
        logger.info(f"[FRONTEND] {full_msg}")

    # Telemetry registration
    try:
        WorkflowTelemetryLogger._record_event(
            level=lvl,
            event_type="FRONTEND_LOG",
            message=f"[FRONTEND] {message}",
            details={"url": url, "component": component, "user_id": user_id, "stack": stack, **(details or {})}
        )
    except Exception:
        pass


class WorkflowTelemetryLogger:
    """
    Enterprise Global Workflow Telemetry, Distributed Tracing & Observability Logger.
    Provides in-memory ring-buffer streaming for live monitoring dashboards alongside
    rotating file logs and structured console outputs.
    """
    _MAX_BUFFER_SIZE = 500
    _buffer: deque = deque(maxlen=_MAX_BUFFER_SIZE)
    _start_time = time.time()

    # Metrics counters
    _total_executions: int = 0
    _total_errors: int = 0
    _total_duration_ms: float = 0.0

    @classmethod
    def _record_event(
        cls,
        level: str,
        event_type: str,
        message: str,
        trace_id: Optional[str] = None,
        instance_id: Optional[int] = None,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        actor_id: Optional[Any] = None,
        actor_role: Optional[str] = None,
        action: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Internal helper to record a structured telemetry event into memory & file."""
        now_dt = datetime.now()
        event_id = str(uuid.uuid4())[:8]
        resolved_trace = trace_id or f"trc_{int(time.time()*1000)}"

        entry = {
            "id": event_id,
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "iso_timestamp": now_dt.isoformat(),
            "level": level.upper(),
            "event_type": event_type.upper(),
            "message": message,
            "trace_id": resolved_trace,
            "instance_id": instance_id,
            "node_id": node_id,
            "node_name": node_name,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "details": details or {},
            "error": error
        }

        # Thread-safe append to circular buffer
        cls._buffer.appendleft(entry)

        # Update metrics
        if duration_ms is not None:
            cls._total_executions += 1
            cls._total_duration_ms += duration_ms
        if level.upper() == "ERROR":
            cls._total_errors += 1

        # Format log line for file & console
        dur_str = f" ({duration_ms:.1f}ms)" if duration_ms is not None else ""
        inst_str = f" [Inst #{instance_id}]" if instance_id else ""
        node_str = f" [{node_name or node_id}]" if node_name or node_id else ""
        log_msg = f"[{resolved_trace}]{inst_str}{node_str} {message}{dur_str}"
        
        if level.upper() == "ERROR":
            logger.error(log_msg)
        elif level.upper() in ("WARN", "WARNING"):
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return entry

    @classmethod
    def log_node_execution(
        cls,
        node_id: str,
        node_name: str,
        node_type: str,
        action: str,
        duration_ms: float,
        instance_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        actor_id: Optional[Any] = None,
        actor_role: Optional[str] = None,
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS"
    ) -> Dict[str, Any]:
        """Logs the execution of a visual workflow graph node with timing and diffs."""
        level = "INFO" if status.upper() == "SUCCESS" else "ERROR"
        msg = f"Node '{node_name}' ({node_type}) executed action '{action}' - {status}"
        return cls._record_event(
            level=level,
            event_type="NODE_EXECUTION",
            message=msg,
            trace_id=trace_id,
            instance_id=instance_id,
            node_id=node_id,
            node_name=node_name,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            duration_ms=duration_ms,
            details=details
        )

    @classmethod
    def log_audit_event(
        cls,
        action_name: str,
        message: str,
        instance_id: Optional[int] = None,
        actor_id: Optional[Any] = None,
        actor_role: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        trace_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Logs a human or system compliance audit transition."""
        return cls._record_event(
            level="AUDIT",
            event_type="AUDIT_TRAIL",
            message=message,
            trace_id=trace_id,
            instance_id=instance_id,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action_name,
            details=details
        )

    @classmethod
    def log_error(
        cls,
        message: str,
        error: Any,
        trace_id: Optional[str] = None,
        instance_id: Optional[int] = None,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Logs a runtime exception or node execution failure."""
        err_str = str(error)
        return cls._record_event(
            level="ERROR",
            event_type="SYSTEM_ERROR",
            message=message,
            trace_id=trace_id,
            instance_id=instance_id,
            node_id=node_id,
            error=err_str,
            details=details
        )

    @classmethod
    def log_db_query(
        cls,
        query_type: str,
        table_name: str,
        duration_ms: float,
        rows_affected: int = 0,
        trace_id: Optional[str] = None,
        instance_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Logs a Client DB read/write/update query execution."""
        msg = f"DB {query_type.upper()} on '{table_name}' affected {rows_affected} rows"
        return cls._record_event(
            level="INFO",
            event_type="DB_QUERY",
            message=msg,
            trace_id=trace_id,
            instance_id=instance_id,
            duration_ms=duration_ms,
            details={"table": table_name, "query_type": query_type, "rows_affected": rows_affected}
        )

    @classmethod
    def get_telemetry_events(
        cls,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        instance_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Queries the in-memory telemetry buffer with filtering."""
        results = []
        search_lower = search.lower().strip() if search else None
        target_level = level.upper().strip() if level and level.upper() != "ALL" else None
        target_type = event_type.upper().strip() if event_type else None

        for item in cls._buffer:
            if target_level and item["level"] != target_level:
                continue
            if target_type and item["event_type"] != target_type:
                continue
            if instance_id is not None and item["instance_id"] != instance_id:
                continue
            if search_lower:
                msg_match = search_lower in item["message"].lower()
                node_match = search_lower in str(item.get("node_name", "")).lower()
                trace_match = search_lower in str(item.get("trace_id", "")).lower()
                if not (msg_match or node_match or trace_match):
                    continue
            results.append(item)
            if len(results) >= limit:
                break
        return results

    @classmethod
    def get_observability_metrics(cls) -> Dict[str, Any]:
        """Calculates real-time health metrics from the telemetry buffer."""
        uptime_seconds = round(time.time() - cls._start_time, 1)
        avg_latency = round(cls._total_duration_ms / max(cls._total_executions, 1), 2)
        error_rate = round((cls._total_errors / max(cls._total_executions + cls._total_errors, 1)) * 100, 2)

        return {
            "uptime_seconds": uptime_seconds,
            "total_logged_events": len(cls._buffer),
            "total_step_executions": cls._total_executions,
            "total_errors": cls._total_errors,
            "average_step_latency_ms": avg_latency,
            "error_rate_percentage": error_rate,
            "buffer_capacity": cls._MAX_BUFFER_SIZE,
            "status": "HEALTHY" if error_rate < 10 else "DEGRADED"
        }

    @classmethod
    def clear_buffer(cls):
        """Clears in-memory buffer."""
        cls._buffer.clear()