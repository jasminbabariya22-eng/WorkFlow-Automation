# Universal Workflow Hub API — Complete Guidance & Reference Manual

**Endpoint URL:** `POST http://<HOST>:8000/api/v1/workflow-hub`  
**Also available at:** `POST http://<HOST>:8000/api/v1/workflow-hub/gateway`

---

## 📌 1. Overview & Architecture

The **Universal Workflow Hub Gateway API** serves as a **single, centralized mediator** between any Client UI (React, Vue, Angular, Mobile App) or external microservice and the backend Workflow Engine.

### Why This API?
- **No Hardcoded Endpoints:** You do not need to build separate custom endpoints for every new workflow (e.g. `/api/v1/leaves`, `/api/v1/expenses`, `/api/v1/tickets`).
- **100% Generic & Dynamic:** The client simply sends the `spec_id` (the unique workflow identifier) and the `operation` to perform.
- **Dynamic Database & Schema Reflection:** The API automatically discovers target tables, columns, primary keys, schemas, human task approval roles, and permitted actions dynamically from the workflow definition and client database.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ANY Client UI / External Service                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
               Sends ONLY: spec_id + operation + payload
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              POST /api/v1/workflow-hub (Central Master Gateway)         │
├────────────────────────────────────────────────────────────────────────┤
│  1. SCHEMA            -> Dynamic metadata, fields, roles, allowed acts │
│  2. SUBMIT            -> Inserts DB record & starts workflow execution │
│  3. GET_TASKS         -> Retrieves pending approval tasks for user     │
│  4. ACTION            -> Executes APPROVE / REJECT / custom actions    │
│  5. FETCH_RECORDS     -> Queries business records from bound table     │
│  6. HISTORY           -> Real-time execution status & audit timeline   │
│  7. DISPATCH_EMAILS   -> Triggers SMTP delivery for pending email jobs │
│  8. CATALOG           -> Lists all active published workflows          │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
     ┌─────────────────────────────┐   ┌───────────────────────────────┐
     │  Workflow Engine & Runtime  │   │  Dynamic Client Database Pool │
     │  (SpiffWorkflow / Graph)    │   │  (Postgres, MySQL, SQLite)    │
     └─────────────────────────────┘   └───────────────────────────────┘
```

---

## 📑 2. Request Body Schema Overview

Every request to `POST /api/v1/workflow-hub` uses this JSON schema:

| Field | Type | Required? | Description |
|:---|:---:|:---:|:---|
| `spec_id` | `string` | **Yes** | Unique identifier/key of the workflow (e.g. `"emp_leave_request"`, `"workflow_1"`, `"wfh_request_wf"`). |
| `operation` | `string` | No (default: `"SUBMIT"`) | Operation to execute: `SCHEMA`, `SUBMIT`, `GET_TASKS`, `ACTION`, `FETCH_RECORDS`, `HISTORY`, `DISPATCH_EMAILS`, `CATALOG`. |
| `record_id` | `integer` | Conditional | Primary key ID of the business record (Required for `ACTION` and `HISTORY`). |
| `action` | `string` | No (default: `"APPROVE"`) | Action code to execute during an `ACTION` operation (`"APPROVE"`, `"REJECT"`, etc.). |
| `data` | `object` | Conditional | Key-value pairs of entity fields & workflow variables passed during `SUBMIT`. |
| `user_id` | `integer` | No | ID of the acting user/employee. |
| `user_name` | `string` | No | Name of the user submitting or approving the request. |
| `user_email` | `string` | No | Email of the user submitting the request. |
| `role` | `string` | No | Role of the user (e.g. `"MANAGER"`, `"ADMIN"`, `"FUNCTION_HEAD"`). |
| `remarks` | `string` | No | Optional comments/notes for the approval or rejection action. |
| `status_filter` | `string` | No | Filter status for `FETCH_RECORDS` (e.g. `"PENDING"`, `"APPROVED"`, `"ALL"`). |
| `limit` | `integer` | No (default: `100`) | Pagination limit for record queries. |
| `offset` | `integer` | No (default: `0`) | Pagination offset for record queries. |
| `variables` | `object` | No | Custom runtime workflow variables passed into engine execution. |

---

## 🛠️ 3. Operations Reference & Samples

---

### Operation 1: `SCHEMA` (Dynamic Schema Discovery)
Returns dynamic metadata about the workflow: bound table, existing columns, primary key, approval roles, allowed actions, and steps.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "SCHEMA"
}
```

#### Response (`200 OK`):
```json
{
  "data": {
    "spec_id": "emp_leave_request",
    "clean_key": "emp_leave_request",
    "title": "Employee Leave Request Workflow",
    "workflow_id": 112,
    "version_id": 123,
    "connection_id": 4,
    "table_name": "leave_requests",
    "table_exists": true,
    "primary_key": "leave_request_id",
    "status_column": "status",
    "default_status": "PENDING",
    "approval_roles": [
      "MANAGER",
      "ADMIN"
    ],
    "allowed_actions": [
      "APPROVE",
      "REJECT"
    ],
    "columns": [
      "leave_request_id",
      "employee_id",
      "leave_type_id",
      "start_date",
      "end_date",
      "reason",
      "status",
      "submitted_at",
      "created_at",
      "updated_at",
      "days"
    ],
    "steps": [
      {
        "step_key": "start_leave",
        "name": "Submit Leave Request",
        "type": "START"
      },
      {
        "step_key": "mgr_approval",
        "name": "Manager Approval",
        "type": "HUMAN_APPROVAL",
        "role": "MANAGER",
        "actions": [
          "APPROVE",
          "REJECT"
        ]
      },
      {
        "step_key": "record_approve",
        "name": "Update Status to APPROVED",
        "type": "RECORD"
      },
      {
        "step_key": "communication-1788324847400",
        "name": "Send Email on Approved",
        "type": "COMMUNICATION"
      },
      {
        "step_key": "end_approved",
        "name": "Approved End",
        "type": "END"
      }
    ],
    "is_active": true
  },
  "Error": {
    "Error": false,
    "Error_message": "Schema resolved successfully for 'emp_leave_request'",
    "Error_Code": 200
  }
}
```

---

### Operation 2: `SUBMIT` (Create Record & Start Workflow)
Inserts data into the client database table, launches the workflow, and pauses at the first human approval task in `WAITING` state (or executes to `Completed` if no human task exists).

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "SUBMIT",
  "data": {
    "employee_id": 5,
    "leave_type_id": 1,
    "start_date": "2026-09-25",
    "end_date": "2026-09-27",
    "days": 3,
    "reason": "Family vacation in Goa"
  },
  "user_id": 5,
  "user_name": "Jasmin Babariya",
  "user_email": "jasmin@example.com"
}
```

#### Response (`201 Created`):
```json
{
  "data": {
    "spec_id": "emp_leave_request",
    "record_id": 68,
    "primary_key": "leave_request_id",
    "instance_id": 597,
    "job_id": 597,
    "status": "PENDING",
    "workflow_status": "WAITING",
    "current_task": "MANAGER_APPROVAL",
    "workflow_error": null
  },
  "Error": {
    "Error": false,
    "Error_message": "Workflow request #68 submitted successfully.",
    "Error_Code": 201
  }
}
```

---

### Operation 3: `GET_TASKS` (Fetch Pending Approval Tasks)
Retrieves all active human tasks waiting in `READY` status for a specific user ID or role code.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "GET_TASKS",
  "user_id": 3,
  "role": "MANAGER"
}
```

#### Response (`200 OK`):
```json
{
  "data": [
    {
      "task_id": 1079,
      "instance_id": 597,
      "entity_type": "leave_requests",
      "entity_id": 68,
      "task_key": "mgr_approval",
      "task_name": "Manager Approval",
      "task_code": "MANAGER_APPROVAL",
      "role_code": "MANAGER",
      "assignment": {
        "type": "role",
        "roleId": "2",
        "roleName": "MANAGER"
      },
      "allowed_actions": [
        "APPROVE",
        "REJECT"
      ],
      "created_on": "2026-09-16T15:17:34.721936"
    }
  ],
  "Error": {
    "Error": false,
    "Error_message": "Retrieved 1 pending tasks for 'emp_leave_request'",
    "Error_Code": 200
  }
}
```

---

### Operation 4: `ACTION` (Execute Approval / Rejection)
Completes the pending human approval task on a record. The engine resumes, executes intermediate DB updates (e.g. `status = 'APPROVED'`), sends notifications over SMTP, and transitions to the next step or `Completed`.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "ACTION",
  "record_id": 68,
  "action": "APPROVE",
  "user_id": 3,
  "role": "MANAGER",
  "remarks": "Leave approved. Have a great vacation!"
}
```

#### Response (`200 OK`):
```json
{
  "data": {
    "spec_id": "emp_leave_request",
    "record_id": 68,
    "action": "APPROVE",
    "workflow_status": "Completed",
    "current_task": "APPROVED_END",
    "message": "Workflow execution completed successfully."
  },
  "Error": {
    "Error": false,
    "Error_message": "Action 'APPROVE' executed successfully on record #68.",
    "Error_Code": 200
  }
}
```

---

### Operation 5: `FETCH_RECORDS` (Query Business Records)
Queries and returns data records directly from the database table bound to this workflow.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "FETCH_RECORDS",
  "status_filter": "ALL",
  "limit": 20,
  "offset": 0
}
```

#### Response (`200 OK`):
```json
{
  "data": [
    {
      "leave_request_id": 68,
      "employee_id": 5,
      "leave_type_id": 1,
      "start_date": "2026-09-25",
      "end_date": "2026-09-27",
      "days": 3,
      "reason": "Family vacation in Goa",
      "status": "APPROVED",
      "created_at": "2026-09-16T09:47:33.705591",
      "updated_at": "2026-09-16T09:47:37.796927"
    }
  ],
  "Error": {
    "Error": false,
    "Error_message": "Retrieved 1 records for workflow 'emp_leave_request'",
    "Error_Code": 200
  }
}
```

---

### Operation 6: `HISTORY` (Live Step-by-Step Audit Timeline)
Fetches the complete execution history, timestamps, variable snapshots, and live status for a record.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "emp_leave_request",
  "operation": "HISTORY",
  "record_id": 68
}
```

#### Response (`200 OK`):
```json
{
  "data": {
    "spec_id": "emp_leave_request",
    "record_id": 68,
    "instance_id": 597,
    "workflow_status": "Completed",
    "current_task": "APPROVED_END",
    "started_on": "2026-09-16T15:17:34.044714",
    "completed_on": "2026-09-16T15:17:39.139069",
    "timeline": [
      {
        "history_id": 1906,
        "activity_id": "mgr_approval",
        "activity_name": "Manager Approval",
        "activity_type": "APPROVAL",
        "status": "READY",
        "timestamp": "2026-09-16T15:17:35.011178"
      },
      {
        "history_id": 1907,
        "activity_id": "record_approve",
        "activity_name": "Update Status to APPROVED",
        "activity_type": "RECORD",
        "status": "COMPLETED",
        "timestamp": "2026-09-16T15:17:37.796927"
      },
      {
        "history_id": 1908,
        "activity_id": "communication-1788324847400",
        "activity_name": "Send Email on Approved",
        "activity_type": "COMMUNICATION",
        "status": "COMPLETED",
        "timestamp": "2026-09-16T15:17:38.656001"
      },
      {
        "history_id": 1909,
        "activity_id": "end_approved",
        "activity_name": "Approved End",
        "activity_type": "END",
        "status": "COMPLETED",
        "timestamp": "2026-09-16T15:17:39.379918"
      }
    ]
  },
  "Error": {
    "Error": false,
    "Error_message": "Workflow execution history retrieved successfully",
    "Error_Code": 200
  }
}
```

---

### Operation 7: `DISPATCH_EMAILS` (Trigger SMTP Queue Delivery)
Processes all pending email jobs from client database tables (`mst_email_job`) and delivers them over SMTP immediately.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "workflow_1",
  "operation": "DISPATCH_EMAILS",
  "limit": 50
}
```

#### Response (`200 OK`):
```json
{
  "data": {
    "processed": 2,
    "success": 2,
    "failed": 0,
    "details": [
      {
        "job_id": 99,
        "status": "Sent",
        "to": "jasminbabariya22@gmail.com",
        "subject": "change 18"
      },
      {
        "job_id": 100,
        "status": "Sent",
        "to": "jasminbabariya22@gmail.com",
        "subject": "change 18"
      }
    ]
  },
  "Error": {
    "Error": false,
    "Error_message": "Email queue processed",
    "Error_Code": 200
  }
}
```

---

### Operation 8: `CATALOG` (List All Active Workflows)
Returns a list of all registered, active workflows available in the platform catalog.

#### Request:
```json
POST http://192.168.1.183:8000/api/v1/workflow-hub
Content-Type: application/json

{
  "spec_id": "all",
  "operation": "CATALOG"
}
```

#### Response (`200 OK`):
```json
{
  "data": [
    {
      "spec_id": "emp_leave_request",
      "title": "Employee Leave Request Workflow",
      "table_name": "leave_requests",
      "approval_roles": ["MANAGER", "ADMIN"],
      "workflow_id": 112
    },
    {
      "spec_id": "workflow_1",
      "title": "Workflow_1",
      "table_name": "test",
      "approval_roles": [],
      "workflow_id": 128
    },
    {
      "spec_id": "wfh_request_wf",
      "title": "Work From Home",
      "table_name": "wfh_requests",
      "approval_roles": ["MANAGER"],
      "workflow_id": 116
    }
  ],
  "Error": {
    "Error": false,
    "Error_message": "Retrieved catalog workflows",
    "Error_Code": 200
  }
}
```

---

## ⚡ 4. Summary of Operations Cheatsheet

| Operation Name | Description | Key Parameters Required |
|:---|:---|:---|
| **`SCHEMA`** | Discover dynamic columns, roles, actions, table name | `spec_id` |
| **`SUBMIT`** | Insert row and start workflow | `spec_id`, `data`, `user_id` |
| **`GET_TASKS`** | List pending approval tasks for user / role | `spec_id`, `user_id`, `role` |
| **`ACTION`** | Approve / reject / execute human action | `spec_id`, `record_id`, `action`, `user_id`, `role` |
| **`FETCH_RECORDS`**| Query entity records from database | `spec_id`, `status_filter` |
| **`HISTORY`** | Get step timeline & live execution state | `spec_id`, `record_id` |
| **`DISPATCH_EMAILS`**| Flush pending email queue via SMTP | `spec_id`, `limit` |
| **`CATALOG`** | List all available published workflows | `spec_id` (any string) |

---

## 💻 5. How to Use in ClientApp (JavaScript / React / Vue / Node.js)

### Option A: Reusable JavaScript API Client (`workflowHub.js`)

Save this helper in your frontend app (e.g. `src/services/workflowHub.js`):

```javascript
const API_URL = 'http://192.168.1.183:8000/api/v1/workflow-hub';

export class WorkflowHubClient {
  static async request(specId, operation, payload = {}) {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        spec_id: specId,
        operation: operation.toUpperCase(),
        ...payload
      })
    });

    const json = await response.json();
    if (!response.ok || json.Error?.Error) {
      throw new Error(json.Error?.Error_message || 'Workflow operation failed');
    }
    return json.data;
  }

  // 1. Submit Record & Start Workflow
  static submit(specId, formData, user) {
    return this.request(specId, 'SUBMIT', {
      data: formData,
      user_id: user.id,
      user_name: user.name,
      user_email: user.email
    });
  }

  // 2. Fetch Pending Tasks (Approvals Inbox)
  static getPendingTasks(specId, user) {
    return this.request(specId, 'GET_TASKS', {
      user_id: user.id,
      role: user.role
    });
  }

  // 3. Approve or Reject Task
  static executeAction(specId, recordId, action, user, remarks = '') {
    return this.request(specId, 'ACTION', {
      record_id: recordId,
      action: action.toUpperCase(), // 'APPROVE' or 'REJECT'
      user_id: user.id,
      role: user.role,
      remarks: remarks
    });
  }

  // 4. Fetch All Records for Table
  static getRecords(specId, statusFilter = 'ALL') {
    return this.request(specId, 'FETCH_RECORDS', { status_filter: statusFilter });
  }

  // 5. Fetch Execution History Timeline
  static getHistory(specId, recordId) {
    return this.request(specId, 'HISTORY', { record_id: recordId });
  }
}
```

---

### Option B: React Form Submission Example

```jsx
import React, { useState } from 'react';
import { WorkflowHubClient } from './services/workflowHub';

export function LeaveRequestForm({ currentUser }) {
  const [formData, setFormData] = useState({
    leave_type_id: 1,
    start_date: '',
    end_date: '',
    days: 1,
    reason: ''
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await WorkflowHubClient.submit('emp_leave_request', formData, currentUser);
      setResult(`Submitted successfully! Record #${res.record_id}, Status: ${res.workflow_status}`);
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '400px' }}>
      <h3>Submit Leave Request</h3>
      <input type="date" value={formData.start_date} onChange={e => setFormData({...formData, start_date: e.target.value})} required />
      <input type="date" value={formData.end_date} onChange={e => setFormData({...formData, end_date: e.target.value})} required />
      <input type="number" placeholder="Days" value={formData.days} onChange={e => setFormData({...formData, days: Number(e.target.value)})} required />
      <textarea placeholder="Reason" value={formData.reason} onChange={e => setFormData({...formData, reason: e.target.value})} required />
      <button type="submit" disabled={loading}>{loading ? 'Submitting...' : 'Submit Request'}</button>
      {result && <p style={{ color: 'green' }}>{result}</p>}
    </form>
  );
}
```

---

### Option C: React Manager Approvals Inbox Example

```jsx
import React, { useEffect, useState } from 'react';
import { WorkflowHubClient } from './services/workflowHub';

export function ManagerApprovalsInbox({ currentManager }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const list = await WorkflowHubClient.getPendingTasks('emp_leave_request', currentManager);
      setTasks(list);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTasks(); }, []);

  const handleAction = async (recordId, action) => {
    const remarks = prompt(`Enter remarks for ${action}:`);
    await WorkflowHubClient.executeAction('emp_leave_request', recordId, action, currentManager, remarks);
    alert(`Request #${recordId} ${action}D successfully!`);
    loadTasks(); // Refresh list
  };

  return (
    <div>
      <h3>Pending Approvals Inbox</h3>
      {loading && <p>Loading tasks...</p>}
      {tasks.length === 0 && !loading && <p>No pending approvals.</p>}
      <ul>
        {tasks.map(t => (
          <li key={t.task_id} style={{ marginBottom: '15px', border: '1px solid #ddd', padding: '10px' }}>
            <p><strong>Record ID:</strong> #{t.entity_id}</p>
            <p><strong>Task:</strong> {t.task_name} ({t.role_code})</p>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => handleAction(t.entity_id, 'APPROVE')} style={{ background: 'green', color: '#fff' }}>Approve</button>
              <button onClick={() => handleAction(t.entity_id, 'REJECT')} style={{ background: 'red', color: '#fff' }}>Reject</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

