import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, Future

from app.core.logger import logger, WorkflowTelemetryLogger
from app.core.websocket import ws_manager
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow.persistence.models import (
    SpiffWorkflowInstance,
    SpiffHumanTask,
    SpiffActivityHistory
)
from app.workflow_definition.models import (
    GenericWorkflow,
    WorkflowVersion,
    WorkflowNode
)


class WorkflowJobExecutor:
    """
    Enterprise Workflow Execution Worker Engine.
    Manages an asynchronous worker thread pool to execute workflow instances,
    automated nodes, and human task transitions decoupled from HTTP request cycles.
    """

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="WfExecutorWorker")
        self._lock = threading.Lock()
        self._is_paused = False

        # Metrics counters
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._active_tasks = 0
        self._recent_jobs: List[Dict[str, Any]] = []

    def is_paused(self) -> bool:
        return self._is_paused

    def pause_executor(self) -> None:
        with self._lock:
            self._is_paused = True
        logger.info("Workflow Job Executor paused.")

    def resume_executor(self) -> None:
        with self._lock:
            self._is_paused = False
        logger.info("Workflow Job Executor resumed.")

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": "PAUSED" if self._is_paused else "HEALTHY",
                "max_workers": self.max_workers,
                "active_tasks": self._active_tasks,
                "total_submitted": self._total_submitted,
                "total_completed": self._total_completed,
                "total_failed": self._total_failed,
                "queue_depth": max(0, self._active_tasks - self.max_workers),
                "is_paused": self._is_paused
            }

    def submit_job_async(
        self,
        entity_type: str,
        entity_id: int,
        definition_id: int,
        user_id: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Immediately creates a QUEUED job record in the database and dispatches
        its execution to the background worker pool, returning in < 15ms.
        """
        if self._is_paused:
            raise RuntimeError("Workflow Executor is currently PAUSED. Cannot accept new async jobs.")

        db = WorkflowSessionLocal()
        try:
            from app.workflow_studio.runtime.adapter import StudioExecutionAdapter

            version = StudioExecutionAdapter.resolve_published_version(db, entity_type, definition_id=definition_id)
            current_time = datetime.now()
            vars_dict = dict(variables or {})
            vars_dict.setdefault("entity_id", entity_id)
            vars_dict.setdefault("entity_type", entity_type)
            if user_id:
                vars_dict.setdefault("user_id", user_id)

            if version and hasattr(version, "workflow") and version.workflow and version.workflow.connection_id:
                vars_dict.setdefault("connection_id", version.workflow.connection_id)

            start_node = next((n for n in version.nodes if n.node_type == "START" and n.is_active), None)
            if not start_node:
                raise ValueError("Workflow definition has no START node.")

            # Create or update SpiffWorkflowInstance in QUEUED state
            instance = db.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.entity_type == entity_type,
                SpiffWorkflowInstance.entity_id == entity_id
            ).first()

            if not instance:
                instance = SpiffWorkflowInstance(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    bpmn_definition_id=version.workflow_version_id,
                    status="QUEUED",
                    serialized_state=json.dumps({"version_id": version.workflow_version_id, "variables": vars_dict}, default=str),
                    current_task_code=start_node.node_key,
                    started_on=current_time
                )
                db.add(instance)
            else:
                instance.bpmn_definition_id = version.workflow_version_id
                instance.status = "QUEUED"
                instance.serialized_state = json.dumps({"version_id": version.workflow_version_id, "variables": vars_dict}, default=str)
                instance.current_task_code = start_node.node_key
                instance.started_on = current_time
                instance.completed_on = None
                db.query(SpiffHumanTask).filter(SpiffHumanTask.instance_id == instance.instance_id).delete()

            db.commit()
            instance_id = instance.instance_id

            # Update metrics
            with self._lock:
                self._total_submitted += 1
                self._active_tasks += 1

            # Dispatch execution to background worker
            self._executor.submit(
                self._execute_job_worker,
                instance_id=instance_id,
                entity_type=entity_type,
                entity_id=entity_id,
                definition_id=definition_id,
                user_id=user_id,
                variables=vars_dict
            )

            # Broadcast WebSocket QUEUED event
            try:
                ws_manager.broadcast_event("JOB_QUEUED", {
                    "job_id": instance_id,
                    "workflow_id": definition_id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "status": "QUEUED",
                    "current_node": start_node.node_key
                })
            except Exception:
                pass

            logger.info(f"Dispatched Job #{instance_id} to background worker pool.")

            return {
                "job_id": instance_id,
                "workflow_id": definition_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "QUEUED",
                "current_node_key": start_node.node_key,
                "async_dispatched": True,
                "started_on": current_time
            }

        finally:
            db.close()

    def _execute_job_worker(
        self,
        instance_id: int,
        entity_type: str,
        entity_id: int,
        definition_id: int,
        user_id: Optional[int],
        variables: Dict[str, Any]
    ) -> None:
        """Worker thread entrypoint that executes the workflow steps."""
        start_time = time.time()
        db = WorkflowSessionLocal()
        try:
            from app.workflow_studio.runtime.adapter import StudioExecutionAdapter

            instance = db.query(SpiffWorkflowInstance).filter(
                SpiffWorkflowInstance.instance_id == instance_id
            ).first()

            if not instance:
                logger.error(f"Executor worker: Instance #{instance_id} not found in database.")
                return

            version = StudioExecutionAdapter.resolve_published_version(db, entity_type, definition_id=definition_id)
            start_node = next((n for n in version.nodes if n.node_type == "START" and n.is_active), None)

            # Transition from QUEUED to Running
            instance.status = "Running"
            db.flush()

            # Advance graph from START
            res = StudioExecutionAdapter._advance_graph(
                db=db,
                instance=instance,
                version=version,
                from_node=start_node,
                action="SUBMIT",
                user_id=user_id,
                variables=variables
            )
            db.commit()

            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info(f"Executor: Job #{instance_id} completed worker step in {duration_ms}ms (final status: {instance.status})")

            # Metrics
            with self._lock:
                self._total_completed += 1

            # Broadcast WebSocket updates
            try:
                ws_manager.broadcast_event("JOB_PROGRESS", {
                    "job_id": instance_id,
                    "status": instance.status,
                    "current_node": instance.current_task_code,
                    "duration_ms": duration_ms
                })
            except Exception:
                pass

        except Exception as err:
            db.rollback()
            logger.error(f"Executor: Failed executing Job #{instance_id}: {err}", exc_info=True)
            with self._lock:
                self._total_failed += 1

            # Mark instance failed
            try:
                fail_inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == instance_id).first()
                if fail_inst:
                    fail_inst.status = "Failed"
                    db.commit()
            except Exception:
                pass

            try:
                ws_manager.broadcast_event("JOB_FAILED", {
                    "job_id": instance_id,
                    "status": "Failed",
                    "error": str(err)
                })
            except Exception:
                pass

        finally:
            with self._lock:
                self._active_tasks = max(0, self._active_tasks - 1)
            db.close()

    def dispatch_existing_job(self, job_id: int) -> Dict[str, Any]:
        """Dispatches an already existing job that is QUEUED or WAITING to the executor."""
        db = WorkflowSessionLocal()
        try:
            inst = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == job_id).first()
            if not inst:
                raise ValueError(f"Job #{job_id} not found.")

            if inst.status in ["Completed", "Stopped", "Cancelled"]:
                raise ValueError(f"Cannot dispatch job with terminal status '{inst.status}'.")

            with self._lock:
                self._total_submitted += 1
                self._active_tasks += 1

            vars_dict = {}
            if inst.serialized_state:
                try:
                    vars_dict = json.loads(inst.serialized_state).get("variables", {})
                except Exception:
                    pass

            self._executor.submit(
                self._execute_job_worker,
                instance_id=inst.instance_id,
                entity_type=inst.entity_type,
                entity_id=inst.entity_id,
                definition_id=inst.bpmn_definition_id,
                user_id=vars_dict.get("user_id"),
                variables=vars_dict
            )

            return {
                "job_id": job_id,
                "status": "DISPATCHED",
                "message": f"Job #{job_id} queued for background executor processing."
            }
        finally:
            db.close()

    def shutdown(self, wait: bool = True) -> None:
        logger.info("Shutting down Workflow Job Executor...")
        self._executor.shutdown(wait=wait)


# Global Singleton Executor instance
workflow_executor = WorkflowJobExecutor(max_workers=8)
