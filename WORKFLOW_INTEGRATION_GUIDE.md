# ⚡ Workflow Integration Guide

This guide explains how to connect and run any workflow (such as **`emp_leave_request`**) between your local frontend UI (**ClientApp**) and the backend **Workflow Engine** running at `http://192.168.1.183:8000`.

---

## 1. The 3 Core API Endpoints

To run the complete workflow from start to finish, you only need these **3 URLs**:

| # | Action | HTTP Method | Exact Endpoint URL |
|:---:|:---|:---:|:---|
| **1** | **Start Leave Request** | `POST` | `http://192.168.1.183:8000/workflow/jobs/create` |
| **2** | **Get Pending Approvals** | `GET` | `http://192.168.1.183:8000/workflow/tasks?role_code=MANAGER&status=READY` |
| **3** | **Approve Task** | `POST` | `http://192.168.1.183:8000/workflow/tasks/{task_id}/complete` |
| *-* | *Reject Task (Optional)* | `POST` | `http://192.168.1.183:8000/workflow/tasks/{task_id}/reject` |

---

## 2. The Single Syntax Needed in ClientApp

In [`ClientApp/src/services/workflowClient.js`](file:///d:/WorkFlow/ClientApp/src/services/workflowClient.js), set your server URL:

```javascript
class WorkflowClient {
  constructor() {
    // Your Server Workflow Engine URL
    this.serverUrl = 'http://192.168.1.183:8000'
  }
}
```

---

## 3. Detailed Request & Response Formats

### Step 1: Employee Applies for Leave (Trigger Workflow)

* **HTTP Method**: `POST`
* **URL**: `http://192.168.1.183:8000/workflow/jobs/create`
* **Headers**: `Content-Type: application/json`
* **Payload**:
```json
{
  "workflow_key": "emp_leave_request",
  "variables": {
    "employee_id": 5,
    "employee_name": "Jasmin",
    "leave_type": "Annual Leave",
    "start_date": "2026-09-10",
    "end_date": "2026-09-12",
    "days": 3,
    "reason": "Personal Vacation"
  }
}
```
* **Response**:
```json
{
  "job_id": 1024,
  "instance_id": "INST-5501",
  "workflow_key": "emp_leave_request",
  "status": "RUNNING"
}
```

---

### Step 2: Manager Fetches Pending Tasks

* **HTTP Method**: `GET`
* **URL**: `http://192.168.1.183:8000/workflow/tasks?role_code=MANAGER&status=READY`
* **Response**:
```json
{
  "success": true,
  "data": [
    {
      "task_id": 8801,
      "instance_id": "INST-5501",
      "task_spec_id": "manager_review_task",
      "role_code": "MANAGER",
      "status": "READY",
      "created_on": "2026-09-16T11:00:00"
    }
  ]
}
```

---

### Step 3: Manager Approves the Task

* **HTTP Method**: `POST`
* **URL**: `http://192.168.1.183:8000/workflow/tasks/8801/complete`
* **Headers**: `Content-Type: application/json`
* **Payload**:
```json
{
  "remark": "Approved. Have a great vacation!",
  "variables": {
    "action": "APPROVE"
  }
}
```
* **Response**:
```json
{
  "success": true,
  "task_id": 8801,
  "status": "COMPLETED",
  "workflow_status": "COMPLETED"
}
```

---

## 4. How to Connect Any Future Workflow

The exact **same 3 endpoints** work for **any other workflow** (Expense, Purchase Order, IT Ticket, etc.).

You only change the **`workflow_key`**:
* **Leave**: `"workflow_key": "emp_leave_request"`
* **Expense**: `"workflow_key": "expense_claim"`
* **Purchase Order**: `"workflow_key": "purchase_order"`

---

## 5. Live Backend Observability & Monitoring

Once your UI triggers the endpoints, the backend engine executes the BPMN logic and records telemetry:
* **Workflow Monitoring API**: `GET http://192.168.1.183:8000/workflow/monitoring/instances`
* **Real-Time WebSocket**: `ws://192.168.1.183:8000/ws/workflow`
