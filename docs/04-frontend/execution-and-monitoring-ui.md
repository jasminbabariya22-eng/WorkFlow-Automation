# Execution & Monitoring UI

## 1. Overview & Monitoring Screen

The **Monitoring Dashboard** (`frontend/src/components/Monitoring.jsx`) provides end-to-end operational visibility into active, completed, and failed workflow instances across the platform.

Accessed via the navigation bar (`?view=monitoring`), it combines high-level KPI cards, live-updating instance tables, granular step-by-step execution traces, and manual task interaction capabilities.

```text
+---------------------------------------------------------------------------------+
|  WORKFLOW PLATFORM OBSERVABILITY & MONITORING                   [Auto-Refresh O] |
+------------------+------------------+------------------+------------------------+
| TOTAL INSTANCES  | ACTIVE RUNNING   | PENDING TASKS    | COMPLETED / FAILED     |
|       1,280      |        14        |        8         |      1,242 / 16        |
+------------------+------------------+------------------+------------------------+
| FILTER: [All Workflows v] [Status: All v] [Search Instances...                ] |
+---------------------------------------------------------------------------------+
| ID   Workflow Name        Entity ID   Status     Started At       Actions       |
| 108  Leave Approval Flow  42          WAITING    10 mins ago      [View Trace]  |
| 107  Purchase Requisition 915         COMPLETED  25 mins ago      [View Trace]  |
| 106  Vendor Onboarding    104         FAILED     1 hour ago       [View Trace]  |
+---------------------------------------------------------------------------------+
```

---

## 2. Real-Time Telemetry & WebSocket Integration

The monitoring screen connects directly to the backend WebSocket gateway at `/ws/workflow` on mount:
- **Event Listeners**:
  - `WORKFLOW_STARTED`: Inserts the new instance into the top of the table.
  - `TASK_READY`: Increments the "Pending Tasks" counter and updates instance status to `WAITING`.
  - `TASK_COMPLETED`: Updates task state and resumes animation.
  - `WORKFLOW_COMPLETED`: Updates status pill to `COMPLETED` (green) or `REJECTED` (amber).
  - `JOB_FAILED`: Highlights the instance row in red and increments the "Failed" counter.
- **Graceful Fallback**: If WebSockets disconnect due to network interruption, the UI automatically falls back to polling `/workflow/monitoring/instances` every 5 seconds.

---

## 3. Instance Detail Inspector

Clicking **`[View Trace]`** opens a multi-tabbed drawer for the selected instance:

### A. Execution Variables Tab
- Displays runtime memory context passed through the workflow.
- Renders sanitized JSON without freezing the DOM: non-`data:` strings between 2,000 and 20,000 characters are cut to 2,000 characters and receive a `[Truncated, total X chars]` suffix, while `data:` URIs and strings exceeding 20,000 characters are represented by payload badges (e.g. `[Large Binary / Base64 Payload: 1.25 MB]`).
- Includes initial input parameters, resolved database columns, API responses, and final calculation outputs.

### B. Activity Execution Logs Tab
- Fetched from `/workflow/monitoring/instances/{id}/logs`.
- Presents a chronological table of every node executed:
  - Node Name and Type (e.g., `READ_RECORD`, `CONDITION`, `APPROVAL`).
  - Execution Status (`COMPLETED`, `FAILED`, `WAITING`).
  - Step Execution Latency (in milliseconds).
  - Error Messages and stack traces (if step failed).

### C. State History Audit Trail Tab
- Fetched from `/workflow/monitoring/instances/{id}/history`.
- Renders the immutable state transition audit log:
  - Transition Name (e.g. `SUBMIT`, `MANAGER_APPROVE`, `FINANCE_APPROVE`).
  - From State &rarr; To State.
  - Actor ID & Actor Role.
  - User remarks/comments entered during approval.
  - Exact timestamp.

---

## 4. In-App Task Actioning

When inspecting an instance currently blocked in a `WAITING` state on a human task:
1. If the logged-in user possesses the required role or administrative privileges, an **Action Bar** appears at the bottom of the inspector.
2. The user can view the pending task details, enter optional remarks, and click **`Approve`** or **`Reject`**.
3. The UI submits a POST request to `/workflow/tasks/{task_id}/complete` (or `/reject`).
4. The backend resumes execution, and the monitoring drawer updates in real time to show the next executed step.

---

## 5. Related Documentation Links

- Frontend Architecture: [Frontend Architecture](./frontend-architecture.md)
- Runtime Execution: [Runtime Execution](../03-workflow-engine/runtime-execution.md)
- Monitoring APIs: [API Reference](../02-backend/api-reference.md)
