# Workflow Execution Sequence & Lifecycle Guide

This document explains the end-to-end execution path of the **WorkFlow-Automation** platform in a clear, accessible visual format. 

---

## 1. High-Level Executive Journey

The workflow lifecycle operates in four simple stages:

```mermaid
flowchart LR
    A["1. Submission\nEmployee submits form"] --> B["2. Automated Engine\nWorkflow starts & emails sent"]
    B --> C["3. Approval Gate\nManager reviews in inbox"]
    C --> D["4. Completion\nRecord updated & event broadcast"]

    classDef primary fill:#2563eb,stroke:#1d4ed8,stroke-width:2px,color:#fff;
    classDef success fill:#16a34a,stroke:#15803d,stroke-width:2px,color:#fff;
    classDef warning fill:#d97706,stroke:#b45309,stroke-width:2px,color:#fff;
    classDef info fill:#0891b2,stroke:#0e7490,stroke-width:2px,color:#fff;

    class A primary;
    class B info;
    class C warning;
    class D success;
```

---

## 2. End-to-End Execution Sequence Diagrams

To keep diagrams clean and readable across both desktop and mobile screens, the complete flow is broken into three focused, sequential phases.

### Phase 1: Request Ingestion & Workflow Initiation

When an employee submits a new business request (e.g., Leave Application, Purchase Order):

```mermaid
sequenceDiagram
    autonumber
    actor Employee as Requester (Employee)
    participant Gateway as Client Gateway (/client/submit)
    participant ClientDB as Client Database
    participant Adapter as StudioExecutionAdapter

    Employee->>Gateway: POST /client/submit/LEAVE (Token + Form Data)
    Note over Gateway: Authenticates JWT token and resolves module binding
    Gateway->>ClientDB: INSERT INTO leave_requests (...) RETURNING id
    ClientDB-->>Gateway: Created record_id = 42 (status = "PENDING")
    
    Gateway->>Adapter: start_workflow(entity_type="leave_requests", entity_id=42)
    Note over Adapter: Resolves published version and creates workflow instance
    Adapter-->>Gateway: Instance #108 started (status = "Running")
    Gateway-->>Employee: HTTP 200 OK (record_id = 42, instance_id = 108)
```

---

### Phase 2: Automated Steps & Human Approval Gate

The engine traverses automated tasks, sends notifications, and halts at the approval gate:

```mermaid
sequenceDiagram
    autonumber
    participant Adapter as StudioExecutionAdapter
    participant WfDB as Workflow Database
    participant Notify as Email & WebSocket
    actor Manager as Approver (Manager)

    Note over Adapter: Starts graph traversal from START node
    Adapter->>Notify: Send Email Notification to manager@company.com
    Adapter->>WfDB: Log activity_history (node="NotifyManager", status="COMPLETED")
    
    Note over Adapter: Next node is APPROVAL (role="DEPT_MANAGER")
    Adapter->>WfDB: INSERT INTO workflow_human_task (status="READY", role="DEPT_MANAGER")
    Adapter->>WfDB: UPDATE spiff_workflow_instance SET status="WAITING"
    Adapter->>Notify: WebSocket broadcast "TASK_READY"
    Notify-->>Manager: Real-time UI notification badge: "1 Pending Approval"
```

---

### Phase 3: Manager Decision, State Synchronization & Completion

The manager reviews the item in their inbox and submits a decision:

```mermaid
sequenceDiagram
    autonumber
    actor Manager as Approver (Manager)
    participant Gateway as Client Gateway (/client/action)
    participant Adapter as StudioExecutionAdapter
    participant ClientDB as Client Database
    participant WS as WebSocket Hub

    Manager->>Gateway: GET /client/tasks/LEAVE (View Pending Items)
    Gateway-->>Manager: List of pending items (Record #42, John Doe, 3 days)

    Manager->>Gateway: POST /client/action/LEAVE {record_id: 42, action: "APPROVE"}
    Gateway->>Adapter: execute_action(entity_id=42, action="APPROVE", user_id=3)
    
    Note over Adapter: Completes human task and routes outgoing edge "APPROVE"
    Adapter->>ClientDB: UPDATE leave_requests SET status="APPROVED" WHERE id=42
    ClientDB-->>Adapter: 1 Row Updated
    
    Note over Adapter: Hits END node and completes instance
    Adapter->>WS: Broadcast "WORKFLOW_COMPLETED"
    WS-->>Manager: UI status updated to "Completed"
    Gateway-->>Manager: HTTP 200 OK ("Action executed successfully")
```

---

## 3. Runtime State Progression Matrix

This table summarizes how state changes across databases and components at each milestone:

| Milestone / Event | Client DB Record Status | Workflow Instance Status | Human Task Status | Active Notification |
| :--- | :--- | :--- | :--- | :--- |
| **1. Form Submitted** | `PENDING` | `Running` | *(None)* | `WORKFLOW_STARTED` |
| **2. Email Dispatched** | `PENDING` | `Running` | *(None)* | Email sent to manager |
| **3. Approval Gate Hit** | `PENDING` | `WAITING` | `READY` (Role: Manager) | `TASK_READY` (WebSocket) |
| **4. Decision Submitted**| `PENDING` &rarr; `APPROVED` | `Running` &rarr; `Completed` | `COMPLETED` | `TASK_COMPLETED` (WebSocket) |
| **5. Process Terminal** | `APPROVED` | `Completed` | `COMPLETED` | `WORKFLOW_COMPLETED` |

---

## 4. Key Component Directory

| Component | Responsibility in Sequence |
| :--- | :--- |
| **Client Gateway** (`client_gateway.py`) | Authenticates JWT tokens, validates inputs, and coordinates client-side CRUD with workflow triggers. |
| **Dynamic Engine Pool** (`database.py`) | Dynamically resolves and manages database connection pools for multiple client databases. |
| **Studio Execution Adapter** (`adapter.py`) | Executes published workflow graphs node by node, evaluates conditions, and manages instance state. |
| **Condition Evaluator** (`actions.py`) | Evaluates edge rules and decisions (`APPROVE`, `REJECT`) to determine the next active branch. |
| **WebSocket Hub** (`websocket.py`) | Pushes real-time execution updates to connected browser clients without polling. |

---

## 5. Related Technical Documentation

- [Engine Architecture](../03-workflow-engine/engine-architecture.md) — Node evaluation loop and engine internals.
- [Human Tasks & Approvals](../03-workflow-engine/human-tasks-and-approvals.md) — Human task data models, inbox queries, and role authorization.
- [Client Application Gateway](../06-integrations/client-application-gateway.md) — API reference for client submissions and action triggers.
- [WebSocket Real-Time Events](../06-integrations/websocket-events.md) — WebSocket lifecycle and JSON payload taxonomy.
