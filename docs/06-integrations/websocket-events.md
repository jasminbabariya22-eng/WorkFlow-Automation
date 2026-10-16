# WebSocket Events

## 1. Overview & Architecture

The **WebSocket Real-Time Gateway** (`backend/app/core/websocket.py`) provides full-duplex, low-latency event streaming between the backend execution engine and connected frontend clients (Studio UI, Monitoring Dashboard, and external client portals).

It eliminates the need for aggressive client-side polling, ensuring that dashboard metrics, instance state pills, and human approval queues update instantaneously upon workflow state transitions.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Frontend UI / Monitoring Dashboard
    participant WS as WebSocket Endpoint (/ws/workflow)
    participant Mgr as WorkflowConnectionManager (Singleton)
    participant Engine as StudioExecutionAdapter / Job Worker

    Client->>WS: Connect: ws://localhost:8000/ws/workflow?user_id=3
    WS->>Mgr: connect(websocket, user_id="3")
    Mgr-->>Client: WebSocket Connected (Handshake complete)

    loop Heartbeat Keepalive
        Client->>WS: Send plain text "ping"
        WS-->>Client: Reply plain text "pong"
    end

    Note over Engine: Workflow advances; state transition occurs
    Engine->>Mgr: broadcast_event("TASK_READY", task_data, target_user_id)
    Mgr->>Client: Send JSON Frame: {"type": "TASK_READY", "data": {...}, "timestamp": "..."}
    Client->>Client: UI updates pending task badge and table row
```

---

## 2. Endpoint Specification

- **URL**: `ws://<HOST>:8000/ws/workflow` (or `wss://` when TLS is enabled).
- **Query Parameters**:
  - `user_id` (string, optional): Client user identifier used to route user-specific notifications.
- **Connection Lifecycle**:
  - **Connect**: Client initiates WebSocket handshake. Server accepts and stores connection in `active_connections` and `user_connections[user_id]`.
  - **Keepalive**: Client sends string `"ping"` every 30 seconds; server replies `"pong"`.
  - **Disconnect**: On socket disconnect or send failure, server removes the connection handle to prevent memory leaks.

---

## 3. Event Taxonomy & JSON Payloads

The platform broadcasts standard event envelopes:
```json
{
  "type": "<EVENT_TYPE>",
  "data": { ... },
  "timestamp": "2026-10-16T11:20:00.123456"
}
```

### Verified Event Types:

| Event Type | Trigger Source | Data Payload Key Contents |
| :--- | :--- | :--- |
| **`WORKFLOW_STARTED`** | `StudioExecutionAdapter.start_workflow()` | `instance_id`, `spec_id`, `entity_id`, `entity_type`, `started_on` |
| **`TASK_READY`** | Human Task / Approval node reached | `task_id`, `instance_id`, `task_spec_id`, `role_code`, `entity_id` |
| **`TASK_COMPLETED`** | Approver submits decision | `task_id`, `instance_id`, `action`, `performed_by`, `completed_on` |
| **`WORKFLOW_COMPLETED`**| Flow reaches terminal `END` node | `instance_id`, `final_status` (`COMPLETED`/`REJECTED`), `completed_on` |
| **`JOB_QUEUED`** | Async job enqueued in worker pool | `job_id`, `entity_type`, `entity_id`, `status: "QUEUED"` |
| **`JOB_PROGRESS`** | Automated step completed in worker | `job_id`, `step_index`, `current_node`, `completed_steps` |
| **`JOB_FAILED`** | Unhandled exception in job worker | `job_id`, `error_message`, `failed_at` |
| **`JOB_PAUSED`** | Operator pauses execution job | `job_id`, `status: "PAUSED"` |
| **`JOB_RESUMED`** | Operator resumes execution job | `job_id`, `status: "RESUMED"` |
| **`JOB_STOPPED`** | Operator stops execution job | `job_id`, `status: "STOPPED"` |
| **`JOB_RESTARTED`** | Operator restarts job from start | `job_id`, `status: "RESTARTED"` |

---

## 4. Thread-Safe & Sync-Safe Broadcast Mechanism

Because workflow execution can occur within synchronous FastAPI endpoints, background worker threads (`WorkflowJobExecutor`), or asynchronous tasks (`DatabaseTriggerWorker`), the `WorkflowConnectionManager.broadcast_event()` method handles event loop bridging safely:

```python
def broadcast_event(self, event_type: str, data: Dict[str, Any], target_user_id: Optional[str] = None):
    # 1. Resolves active running asyncio loop or falls back to server main loop
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = self._main_loop

    # 2. If loop is running, safely schedules coroutine from thread
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(self._async_broadcast(payload, target_user_id), loop)
    else:
        # 3. Fallback for non-async worker threads: spawns temporary daemon thread
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(self._async_broadcast(payload, target_user_id))
            new_loop.close()

        threading.Thread(target=run_in_thread, daemon=True).start()
```

---

## 5. Related Documentation Links

- Frontend WebSocket Service: [Frontend API Integration](../04-frontend/frontend-api-integration.md)
- Monitoring Dashboard: [Execution & Monitoring UI](../04-frontend/execution-and-monitoring-ui.md)
- Client Gateway: [Client Application Gateway](./client-application-gateway.md)
