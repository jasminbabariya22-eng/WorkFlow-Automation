import logging
import os
import json
import time
import uuid
from datetime import datetime
from collections import deque
from typing import Dict, Any, List, Optional
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "workflow_telemetry.log")

# Standard base logger
logger = logging.getLogger("ers_logger")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# StreamHandler for stdout logging
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# File handler with midnight rotation
try:
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
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
        elif level.upper() == "WARN" or level.upper() == "WARNING":
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