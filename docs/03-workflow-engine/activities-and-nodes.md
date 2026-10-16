# Activities & Node Inventory

This document provides a comprehensive technical inventory of all workflow node types implemented in the **WorkFlow-Automation** platform. Every node specification below is verified against the backend execution handlers (`backend/app/workflow_studio/runtime/actions.py`, `adapter.py`), compiler mappings (`compiler.py`), and frontend property drawers (`frontend/src/components/properties/`).

---

## 1. Summary of Supported Node Types

| Node Type Identifier | Category | Execution Mode | Side Effect |
| :--- | :--- | :--- | :--- |
| **`START`** | Trigger / Boundary | Instantaneous | Initializes context and records start time. |
| **`USER_TASK`** | Human Interaction | Blocking / Pauses | Creates `workflow_human_task` with status `READY`. |
| **`APPROVAL`** | Human Interaction | Blocking / Pauses | Creates hierarchical approval gate with action buttons. |
| **`CREATE_RECORD`** | Database Action | Automated | Executes parameterized `INSERT INTO ...` on client DB. |
| **`READ_RECORD`** | Database Action | Automated | Executes parameterized `SELECT ...` and injects variables. |
| **`UPDATE_RECORD`** | Database Action | Automated | Executes targeted `UPDATE ... SET ...` on client DB. |
| **`DELETE_RECORD`** | Database Action | Automated | Executes parameterized `DELETE FROM ...` on client DB. |
| **`API_CALL`** | Integration | Automated | Executes outbound HTTP call (`GET`, `POST`, `PUT`, etc.). |
| **`CONDITION`** | Control Flow | Automated / Routing | Evaluates expression and activates `TRUE` or `FALSE` branch. |
| **`SWITCH`** | Control Flow | Automated / Routing | Evaluates discrete field and routes to matching branch. |
| **`COMMUNICATION`** | Notification | Automated | Dispatches templated MIME email via client SMTP. |
| **`TIMER` / `WAIT`** | Control Flow | Automated / Catch | Enforces delay or waiting interval. |
| **`END`** | Terminal Boundary | Completes Flow | Sets instance to `COMPLETED` or `REJECTED`. |

---

## 2. Detailed Node Specifications

### 1. START (`START`)
- **Purpose**: Defines the entry point of the workflow graph.
- **Runtime Implementation**: Handled directly in `StudioExecutionAdapter.start_workflow()`.
- **Validation Rules**: Exactly one active `START` node must exist in the published graph.
- **Configuration Schema**:
  ```json
  {
    "label": "Start Workflow",
    "triggerType": "API",
    "description": "Triggered via Client Portal or Webhook"
  }
  ```
- **Side Effects**: Generates `spiff_workflow_instance` record; logs initial record in `workflow_history`.

---

### 2. USER_TASK (`USER_TASK`) & APPROVAL (`APPROVAL`)
- **Purpose**: Pauses execution and waits for human input, form submission, or managerial sign-off.
- **Runtime Implementation**: `StudioExecutionAdapter.start_workflow()` (detects human node and pauses) and `execute_action()`.
- **Configuration Fields**:
  - `role_code` (string, required): Assigned role identifier (e.g., `MANAGER`, `FUNCTION_HEAD`, `FINANCE_APPROVER`).
  - `assignee_id` (integer, optional): Specific user ID assigned to the task.
  - `actions` (array of strings): Available decision outcomes, defaults to `["APPROVE", "REJECT"]`.
  - `form_schema` (object, optional): Dynamic field configuration presented to the user.
- **Configuration Example**:
  ```json
  {
    "label": "Manager Approval",
    "role_code": "DEPT_MANAGER",
    "actions": ["APPROVE", "REJECT", "REQUEST_CHANGES"],
    "sla_hours": 24,
    "require_remarks_on_reject": true
  }
  ```
- **Side Effects**: Inserts a row in `workflow_human_task`; updates `spiff_workflow_instance.status = 'WAITING'`.

---

### 3. CREATE_RECORD (`CREATE_RECORD`)
- **Purpose**: Inserts a new record into a client database table.
- **Runtime Implementation**: `_db_create_handler()` in `backend/app/workflow_studio/runtime/actions.py`.
- **Configuration Fields**:
  - `table_name` (string, required): Target client database table name.
  - `connection_id` (integer, optional): Connection profile ID (defaults to active workflow connection).
  - `field_mappings` (object, required): Key-value map of column names to static values or template variables (`{{variable}}`).
  - `conflict_rule` (string, optional): `DO_NOTHING` or `DO_UPDATE`.
- **Configuration Example**:
  ```json
  {
    "table_name": "leave_audit_log",
    "connection_id": 1,
    "field_mappings": {
      "leave_id": "{{entity_id}}",
      "action_by": "{{user_id}}",
      "action_name": "SUBMIT",
      "created_at": "NOW()"
    },
    "conflict_rule": "DO_NOTHING"
  }
  ```
- **Side Effects**: Executes parameterized `INSERT INTO ...` on client database.

---

### 4. READ_RECORD (`READ_RECORD`)
- **Purpose**: Queries a client database table and binds resulting columns into runtime context variables.
- **Runtime Implementation**: `_db_read_handler()` in `backend/app/workflow_studio/runtime/actions.py`.
- **Configuration Fields**:
  - `table_name` (string, required): Target table name.
  - `connection_id` (integer, optional): Connection profile ID.
  - `filter_field` (string): Column to filter on (e.g. `id`).
  - `filter_value` (string): Value expression (e.g. `{{entity_id}}`).
  - `output_variable` (string): Variable prefix to store loaded fields (defaults to row keys).
- **Configuration Example**:
  ```json
  {
    "table_name": "mst_users",
    "filter_field": "user_id",
    "filter_value": "{{user_id}}",
    "columns": ["user_name", "email", "department_id", "salary"]
  }
  ```
- **Side Effects**: Reads client database; injects variables into workflow memory context.

---

### 5. UPDATE_RECORD (`UPDATE_RECORD`)
- **Purpose**: Modifies existing records in the client database upon transitions or approvals.
- **Runtime Implementation**: `_db_update_handler()` in `backend/app/workflow_studio/runtime/actions.py`.
- **Configuration Fields**:
  - `table_name` (string, required): Target table name.
  - `key_field` (string): Primary key column (defaults to `id`).
  - `key_value` (string): Value expression (defaults to `{{entity_id}}`).
  - `updates` (object, required): Field-value pairs to update.
- **Configuration Example**:
  ```json
  {
    "table_name": "leave_requests",
    "key_field": "id",
    "key_value": "{{entity_id}}",
    "updates": {
      "status": "APPROVED",
      "approved_by": "{{user_id}}",
      "approved_at": "NOW()"
    }
  }
  ```
- **Side Effects**: Executes parameterized `UPDATE ... SET ... WHERE id = :id` on client database.

---

### 6. DELETE_RECORD (`DELETE_RECORD`)
- **Purpose**: Deletes targeted records from the client database.
- **Runtime Implementation**: Parameterized SQL execution via `ClientDatabaseAdapter`.
- **Configuration Fields**:
  - `table_name` (string, required): Target table name.
  - `filter_field` (string, required): Column condition.
  - `filter_value` (string, required): Value condition.
- **Side Effects**: Executes parameterized `DELETE FROM ... WHERE ...` on client database.

---

### 7. API_CALL (`API_CALL`)
- **Purpose**: Orchestrates outbound HTTP requests to external microservices or webhooks.
- **Runtime Implementation**: Executed via HTTP client with response variable capture.
- **Configuration Fields**:
  - `url` (string, required): Target endpoint URL (supports `{{variable}}` interpolation).
  - `method` (string): `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
  - `headers` (object): Request headers (e.g. `Authorization`, `Content-Type`).
  - `body_template` (string / JSON): Request payload template.
  - `response_variable` (string): Variable name to store parsed JSON response (defaults to `api_response`).
- **Configuration Example**:
  ```json
  {
    "url": "https://api.erp.internal/v1/notifications",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer {{env_erp_token}}"
    },
    "body_template": "{\"event\": \"LEAVE_APPROVED\", \"record_id\": {{entity_id}}}",
    "response_variable": "erp_sync_result"
  }
  ```
- **Side Effects**: Outbound HTTP traffic; captures response status and data into context.

---

### 8. CONDITION (`CONDITION`) & SWITCH (`SWITCH`)
- **Purpose**: Control-flow branching nodes evaluating runtime variables.
- **Runtime Implementation**: `ConditionEvaluator.evaluate_node_condition()` in `actions.py`.
- **Supported Operators**: `equals` (`==`), `not_equals` (`!=`), `greater_than` (`>`), `less_than` (`<`), `greater_than_or_equals` (`>=`), `less_than_or_equals` (`<=`).
- **Configuration Example**:
  ```json
  {
    "field": "total_amount",
    "operator": "greater_than",
    "value": 50000
  }
  ```
- **Side Effects**: Pure control flow; determines which outgoing sequence connection to follow.

---

### 9. COMMUNICATION (`COMMUNICATION`)
- **Purpose**: Dispatches dynamic HTML or text emails via client database-configured SMTP servers.
- **Runtime Implementation**: `_email_notification_handler()` calling `EmailDispatcher`.
- **Configuration Fields**:
  - `to` (string / array): Recipient email address or variable (e.g. `{{user_email}}`).
  - `cc` / `bcc` (optional): Additional carbon-copy recipients.
  - `subject` (string): Email subject with variable interpolation.
  - `template_body` (string): HTML or plain text template supporting `{{variable}}` chips.
- **Configuration Example**:
  ```json
  {
    "to": "{{employee_email}}",
    "cc": ["manager@company.com"],
    "subject": "Leave Request #{{entity_id}} Approved",
    "template_body": "<p>Dear {{employee_name}},</p><p>Your leave request has been approved.</p>"
  }
  ```
- **Side Effects**: Delivers SMTP message; logs delivery status in `workflow_activity_history`.

---

### 10. END (`END`, `END_APPROVED`, `END_REJECTED`)
- **Purpose**: Terminates workflow execution.
- **Runtime Implementation**: `StudioExecutionAdapter` terminates traversal loop.
- **Configuration Example**:
  ```json
  {
    "label": "Process Completed",
    "final_status": "COMPLETED"
  }
  ```
- **Side Effects**: Updates `spiff_workflow_instance.status = 'COMPLETED'` (or `'REJECTED'`); stamps `completed_on`; emits `WORKFLOW_COMPLETED` WebSocket event.

---

## 3. Related Documentation Links

- Engine Architecture: [Engine Architecture](./engine-architecture.md)
- Lifecycle Transitions: [Workflow Lifecycle](./workflow-lifecycle.md)
- Node Configuration UI: [Node Configuration Panels](../04-frontend/node-configuration.md)
