# API Reference

This document provides a comprehensive reference for all registered FastAPI REST and WebSocket endpoints in the **WorkFlow-Automation** platform. Every endpoint listed below reflects actual registered routes in `backend/app/main.py`.

---

## 1. Global & Core Infrastructure APIs

### Health Check
- **`GET /health`**
  - **Tag**: `Health`
  - **Purpose**: Liveness and readiness verification for Docker, Kubernetes, and load balancers.
  - **Auth**: None.
  - **Success Response (200)**:
    ```json
    {
      "status": "healthy",
      "service": "Workflow Engine & Studio Platform API",
      "version": "2.0.0"
    }
    ```

### WebSocket Real-Time Gateway
- **`WS /ws/workflow`**
  - **Query Parameters**: `user_id` (optional string for user-targeted event routing).
  - **Purpose**: Full-duplex connection for receiving real-time workflow lifecycle events (`WORKFLOW_STARTED`, `TASK_READY`, `TASK_COMPLETED`, `WORKFLOW_COMPLETED`, `JOB_*`).
  - **Ping/Pong Protocol**: Client may send plain string `"ping"`, server immediately replies with `"pong"`.

---

## 2. Client Application Gateway (`/client`)
*Source: `backend/app/workflow/api/client_gateway.py`*

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/client/query` | Generic parameterized query (SELECT, INSERT, UPDATE, DELETE) against client DB. | Yes |
| `POST` | `/client/submit/{module_code}` | Submits a new entity record and triggers its bound workflow. | Yes |
| `POST` | `/client/action/{module_code}` | Submits a workflow action decision (`APPROVE`, `REJECT`) for a record. | Yes |
| `GET` | `/client/tasks/{module_code}` | Fetches pending workflow tasks for the logged-in user or role. | Yes |
| `GET` | `/client/history/{module_code}/{record_id}` | Retrieves chronological workflow state history for a business record. | Yes |
| `GET` | `/client/modules` | Lists all configured client module bindings. | Yes |

#### Request Example: `POST /client/query`
```json
{
  "table_name": "leave_requests",
  "connection_id": 1,
  "operation": "SELECT",
  "columns": ["id", "employee_id", "leave_type", "status", "created_at"],
  "filters": [
    { "field": "status", "operator": "=", "value": "PENDING" }
  ],
  "order_by": "created_at",
  "order_direction": "DESC",
  "limit": 50,
  "offset": 0
}
```

#### Request Example: `POST /client/action/LEAVE`
```json
{
  "record_id": 42,
  "action": "APPROVE",
  "user_id": 3,
  "role": "MANAGER",
  "remarks": "Leave request verified and approved.",
  "variables": { "approval_level": 1 }
}
```

---

## 3. Universal Workflow Hub Gateway (`/api/v1/workflow-hub`)
*Source: `backend/app/workflow/api/workflow_hub_api.py`*

The Universal Hub allows external frontends to interact with ANY workflow definition using only its `spec_id` without needing specialized endpoints.

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/workflow-hub` | Universal mediator executing `SUBMIT`, `ACTION`, `FETCH_RECORDS`, `GET_TASKS`, `SCHEMA`, `HISTORY`. | Yes |
| `POST` | `/api/v1/workflow-hub/submit` | Dedicated submit endpoint for starting workflow instances with form data. | Yes |
| `POST` | `/api/v1/workflow-hub/action` | Dedicated endpoint to submit human task transitions (`APPROVE`, `REJECT`). | Yes |
| `GET` | `/api/v1/workflow-hub/tasks` | Retrieves pending tasks filtered by `spec_id`, `user_id`, or `role`. | Yes |
| `GET` | `/api/v1/workflow-hub/history/{spec_id}/{record_id}` | Retrieves execution history for a specific specification and record. | Yes |
| `GET` | `/api/v1/workflow-hub/schema/{spec_id}` | Returns input fields, target table schema, and form layout. | Yes |
| `GET` | `/api/v1/workflow-hub/records/{spec_id}` | Fetches underlying business records managed by the workflow. | Yes |
| `GET` | `/api/v1/workflow-hub/catalog` | Lists all published active workflows with schemas and module metadata. | Yes |
| `POST` | `/api/v1/workflow-hub/catalog/refresh` | Evicts cached workflow bindings and introspects live tables. | Yes |

#### Request Example: `POST /api/v1/workflow-hub` (Submit)
```json
{
  "spec_id": "purchase_requisition_flow",
  "operation": "SUBMIT",
  "parameter": {
    "item_description": "Server Hardware Upgrade",
    "total_amount": 75000,
    "department": "IT Operations"
  },
  "user_id": 12,
  "user_name": "John Doe",
  "user_email": "john.doe@company.com"
}
```

---

## 4. Workflow Definitions & Management (`/workflow/definitions`)
*Source: `backend/app/workflow/api/definitions.py` & `backend/app/workflow_management/api.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow/definitions` | Lists all BPMN definitions with pagination and status filters. | Yes |
| `POST` | `/workflow/definitions` | Creates a new draft BPMN workflow specification. | Yes |
| `GET` | `/workflow/definitions/{id}` | Retrieves a specific definition by ID including XML and JSON graphs. | Yes |
| `PUT` | `/workflow/definitions/{id}` | Updates an existing draft workflow specification. | Yes |
| `DELETE`| `/workflow/definitions/{id}` | Soft-deletes a workflow specification (`is_deleted=1`). | Yes |
| `POST` | `/workflow/definitions/{id}/validate` | Validates graph connectivity, node properties, and BPMN compliance. | Yes |
| `POST` | `/workflow/definitions/{id}/publish` | Publishes a definition, generating a new immutable version. | Yes |
| `POST` | `/workflow/definitions/{id}/deactivate`| Deactivates an active workflow definition. | Yes |
| `POST` | `/workflow/definitions/{id}/duplicate` | Clones a definition with a new unique `spec_id`. | Yes |
| `GET` | `/workflow/definitions/{id}/export` | Exports the compiled BPMN 2.0 XML file for Camunda / external tools. | Yes |
| `POST` | `/workflow/definitions/{id}/execute` | Manually triggers execution of a specific definition. | Yes |
| `GET` | `/workflow/definitions/{spec_id}/latest`| Resolves the highest published active version for a `spec_id`. | Yes |
| `GET` | `/workflow/definitions/{spec_id}/versions`| Lists all historic versions of a specific workflow specification. | Yes |

---

## 5. Generic Workflow Graph APIs (`/workflows`)
*Source: `backend/app/workflow_definition/api.py` & `backend/app/workflow/api/workflows_api.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflows` | Lists generic workflow definitions. | Yes |
| `POST` | `/workflows` | Creates a generic workflow entity. | Yes |
| `GET` | `/workflows/{workflow_id}` | Retrieves a workflow header with version summaries. | Yes |
| `PUT` | `/workflows/{workflow_id}` | Updates workflow metadata (name, description, entity_type). | Yes |
| `DELETE`| `/workflows/{workflow_id}` | Deletes a workflow and all associated versions/nodes. | Yes |
| `GET` | `/workflows/{workflow_id}/versions` | Lists all versions (`WorkflowVersion`) for a workflow. | Yes |
| `POST` | `/workflows/{workflow_id}/versions` | Creates a new draft version for a workflow. | Yes |
| `GET` | `/workflows/{workflow_id}/versions/{version_id}` | Gets complete version graph including nodes and connections. | Yes |
| `POST` | `/workflows/{workflow_id}/versions/{version_id}/publish` | Validates and marks version as `PUBLISHED`. | Yes |
| `POST` | `/workflows/{workflow_id}/versions/{version_id}/validate`| Runs graph validation on nodes and edge bindings. | Yes |
| `POST` | `/workflows/{workflow_id}/versions/{version_id}/archive` | Archives a published or draft version. | Yes |
| `POST` | `/workflows/{workflow_id}/versions/{version_id}/nodes` | Adds an individual node step to a version graph. | Yes |
| `PUT` | `/workflows/{workflow_id}/versions/{version_id}/nodes/{node_id}` | Updates node position, configuration, or label. | Yes |
| `DELETE`| `/workflows/{workflow_id}/versions/{version_id}/nodes/{node_id}` | Removes a node step from a version graph. | Yes |
| `POST` | `/workflows/{workflow_id}/versions/{version_id}/connections` | Adds a directed edge between two nodes. | Yes |
| `DELETE`| `/workflows/{workflow_id}/versions/{version_id}/connections/{connection_id}` | Deletes a connection edge. | Yes |

### Inspection Endpoints (`/workflows/*`)
- `GET /workflows/catalog` — Returns client app catalog of workflows.
- `GET /workflows/by-table/{table_name}` — Finds workflow bound to a specific client database table.
- `GET /workflows/by-client-db/{connection_id_or_name}` — Lists workflows bound to a client DB connection.
- `GET /workflows/by-status/{status_val}` — Filters workflows by status (`DRAFT`, `ACTIVE`, `ARCHIVED`).
- `GET /workflows/inspect/{id_or_code}` — Full graph inspection payload for external clients.

---

## 6. Visual Workflow Studio APIs (`/workflow-studio`)
*Source: `backend/app/workflow_studio/api.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow-studio/canvas/workflows` | Lists workflows formatted for the Studio dashboard. | Yes |
| `POST` | `/workflow-studio/canvas/workflows` | Creates a new visual workflow canvas definition. | Yes |
| `GET` | `/workflow-studio/canvas/workflows/{id}` | Loads canvas graph (`nodes`, `edges`, `config`) for Designer. | Yes |
| `PUT` | `/workflow-studio/canvas/workflows/{id}` | Saves canvas graph layout and node configurations. | Yes |
| `POST` | `/workflow-studio/canvas/workflows/{id}/publish` | Compiles and publishes current canvas graph. | Yes |
| `POST` | `/workflow-studio/canvas/workflows/{id}/validate`| Runs full canvas validation check (orphans, end states). | Yes |
| `GET` | `/workflow-studio/catalog/nodes` | Returns catalog of available node types with schemas and icons. | Yes |
| `POST` | `/workflow-studio/test/simulate-step` | Executes a single node step in isolation for testing. | Yes |
| `POST` | `/workflow-studio/test/execute-generic-node`| Executes test queries or API calls live during simulation. | Yes |

---

## 7. Database Connections API (`/workflow-studio/connections`)
*Source: `backend/app/workflow_studio/connections_api.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow-studio/connections` | Lists all configured database connections. | Yes |
| `POST` | `/workflow-studio/connections` | Creates a new database connection profile (encrypts password). | Yes |
| `GET` | `/workflow-studio/connections/{id}` | Retrieves connection profile details (password masked). | Yes |
| `PUT` | `/workflow-studio/connections/{id}` | Updates database connection host, port, credentials. | Yes |
| `DELETE`| `/workflow-studio/connections/{id}` | Deactivates or removes a database connection. | Yes |
| `POST` | `/workflow-studio/connections/test` | Tests live database connectivity before saving. | Yes |
| `GET` | `/workflow-studio/connections/{id}/tables` | Introspects and lists all available tables/views in DB. | Yes |
| `GET` | `/workflow-studio/connections/{id}/tables/{table_name}/columns` | Introspects column names, data types, primary keys, and nullability. | Yes |
| `GET` | `/workflow-studio/connections/{id}/roles` | Introspects master user roles from the client database. | Yes |
| `GET` | `/workflow-studio/connections/{id}/users` | Introspects master user list from the client database. | Yes |
| `GET` | `/workflow-studio/connections/{id}/departments` | Introspects department master list from the client database. | Yes |

---

## 8. Workflow Monitoring & Telemetry (`/workflow/monitoring`)
*Source: `backend/app/workflow/api/monitoring.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow/monitoring/instances` | Lists running and completed workflow execution instances. | Yes |
| `GET` | `/workflow/monitoring/instances/{id}` | Retrieves detailed status and execution metrics for an instance. | Yes |
| `GET` | `/workflow/monitoring/instances/{id}/variables` | Returns sanitized runtime context variables (large payloads truncated). | Yes |
| `GET` | `/workflow/monitoring/instances/{id}/logs` | Returns step-by-step activity execution logs for an instance. | Yes |
| `GET` | `/workflow/monitoring/instances/{id}/history` | Retrieves state transition audit trail from `workflow_history`. | Yes |
| `GET` | `/workflow/monitoring/tasks/pending` | Lists all human approval tasks waiting across all instances. | Yes |
| `GET` | `/workflow/monitoring/metrics` | Prometheus-compatible metrics output for scrapers. | Yes |
| `GET` | `/workflow/monitoring/telemetry` | Returns real-time in-memory telemetry entries from ring buffer. | Yes |
| `POST` | `/workflow/monitoring/telemetry/clear` | Clears the in-memory telemetry buffer. | Yes |

---

## 9. Workflow Jobs & Executor (`/workflow/jobs`, `/workflow/executor`)
*Source: `backend/app/workflow/api/jobs.py` & `backend/app/workflow/api/executor.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow/jobs` | Lists queued and active background execution jobs. | Yes |
| `POST` | `/workflow/jobs` | Submits a new background execution job. | Yes |
| `GET` | `/workflow/jobs/{job_id}/status` | Checks current status of a background job. | Yes |
| `POST` | `/workflow/jobs/{job_id}/pause` | Pauses an active job. | Yes |
| `POST` | `/workflow/jobs/{job_id}/resume` | Resumes a paused job. | Yes |
| `POST` | `/workflow/jobs/{job_id}/stop` | Terminates and stops a running job. | Yes |
| `POST` | `/workflow/jobs/{job_id}/restart` | Restarts a failed or completed job from the beginning. | Yes |
| `GET` | `/workflow/jobs/{job_id}/history` | Retrieves execution trace history for a job. | Yes |
| `GET` | `/workflow/executor/status` | Returns worker thread pool status, queue depth, and metrics. | Yes |
| `POST` | `/workflow/executor/pause` | Pauses the global background worker thread pool. | Yes |
| `POST` | `/workflow/executor/resume` | Resumes the global background worker thread pool. | Yes |
| `POST` | `/workflow/executor/dispatch` | Dispatches an asynchronous job execution directly. | Yes |

---

## 10. Human Tasks (`/workflow/tasks`)
*Source: `backend/app/workflow/api/human_tasks.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/workflow/tasks` | Retrieves active human tasks filtered by `role_code` or `user_id`. | Yes |
| `POST` | `/workflow/tasks/{id}/complete` | Completes an approval task with action `APPROVE` and optional variables. | Yes |
| `POST` | `/workflow/tasks/{id}/reject` | Rejects an approval task with action `REJECT` and comments. | Yes |

---

## 11. System Logs API (`/logs`)
*Source: `backend/app/core/logs_api.py`*

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/logs` | Queries recent log entries filtered by level (`INFO`, `WARNING`, `ERROR`). | Yes |
| `GET` | `/logs/files` | Lists available daily partitioned log files with size and date. | Yes |
| `POST` | `/logs/frontend/ingest` | Ingests frontend browser console errors into the backend daily log. | Yes |

---

## 12. Standard Response Schemas

### Standard Success Response
All responses wrapped via `app.core.response.success_response`:
```json
{
  "data": { ... },
  "Error": {
    "Error": false,
    "Error_message": "Success",
    "Error_Code": 200
  }
}
```

### Standard Error Response
All errors handled via `app.core.response.error_response` or `app.core.exception_handler.build_error_response`:
```json
{
  "data": null,
  "Error": {
    "Error": true,
    "Error_message": "Validation Error: spec_id is required",
    "Error_Code": 400
  }
}
```
