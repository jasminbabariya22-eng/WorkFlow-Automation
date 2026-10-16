# Workflow Execution Sequence Diagram

This document illustrates the end-to-end request and execution path through the **WorkFlow-Automation** engine, covering initial workflow triggering, automated node execution, human approval gate pausing, decision submission, and final process termination.

---

## 1. Complete Workflow Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Employee as Requester (Employee Portal)
    actor Manager as Approver (Manager Portal)
    participant Gateway as Client Gateway (/client or /api/v1/workflow-hub)
    participant Adapter as StudioExecutionAdapter
    participant WfDB as Workflow DB (SessionLocal)
    participant Pool as DynamicEnginePool
    participant ClientDB as Client Database
    participant Email as EmailDispatcher
    participant WS as WebSocket Gateway

    %% Phase 1: Initiation
    rect rgb(240, 248, 255)
    Note over Employee, Gateway: Phase 1: Workflow Initiation & Trigger
    Employee->>Gateway: POST /client/submit/LEAVE {data: {days: 3, reason: "Vacation"}}
    Gateway->>Adapter: start_workflow(entity_type="leave_requests", data, user_id=105)
    Adapter->>WfDB: resolve_published_version(db, "leave_requests")
    WfDB-->>Adapter: wf_version (id=4, version_number=2)
    Adapter->>WfDB: Insert spiff_workflow_instance (status='Running')
    Adapter->>WfDB: Insert workflow_history (action='SUBMIT', actor=105)
    Adapter->>WS: broadcast_event("WORKFLOW_STARTED", instance_data)
    end

    %% Phase 2: Automated Steps
    rect rgb(245, 255, 245)
    Note over Adapter, ClientDB: Phase 2: Automated Node Execution (CRUD & Notifications)
    Adapter->>Pool: Get Engine for connection_id=1
    Pool->>ClientDB: INSERT INTO leave_requests (employee_id, days, status) VALUES (...) RETURNING id
    ClientDB-->>Adapter: {id: 42, status: "PENDING"}
    Adapter->>WfDB: Insert workflow_activity_history (node="CreateRecord", status="COMPLETED")
    
    Adapter->>Email: dispatch_email(template="SubmitNotification", to="manager@company.com")
    Email->>ClientDB: Query active SMTP config (email_server)
    Email-->>Adapter: Email Sent
    Adapter->>WfDB: Insert workflow_activity_history (node="NotifyManager", status="COMPLETED")
    end

    %% Phase 3: Human Task Blocking
    rect rgb(255, 250, 240)
    Note over Adapter, WS: Phase 3: Human Approval Gate (Waiting State)
    Adapter->>Adapter: Next node is APPROVAL (role_code='DEPT_MANAGER')
    Adapter->>WfDB: Insert SpiffHumanTask (task_spec_id='ManagerReview', status='READY', role='DEPT_MANAGER')
    Adapter->>WfDB: Update spiff_workflow_instance (status='WAITING')
    Adapter->>WS: broadcast_event("TASK_READY", task_data)
    Adapter-->>Gateway: Return Execution Summary {record_id: 42, instance_id: 108, status: "WAITING"}
    Gateway-->>Employee: HTTP 200 Success Response
    end

    %% Phase 4: Decision & Resumption
    rect rgb(255, 245, 255)
    Note over Manager, ClientDB: Phase 4: Human Task Decision & Graph Resumption
    Manager->>Gateway: POST /client/action/LEAVE {record_id: 42, action: "APPROVE", user_id: 3}
    Gateway->>Adapter: execute_action(instance_id=108, action="APPROVE", user_id=3)
    Adapter->>Adapter: is_user_authorized_for_task(user_id=3, task) -> TRUE
    Adapter->>WfDB: Update SpiffHumanTask (status='COMPLETED', completed_on=NOW())
    Adapter->>WfDB: Insert workflow_history (action='APPROVE', actor=3, remarks="Approved")
    Adapter->>WS: broadcast_event("TASK_COMPLETED", task_data)
    
    Adapter->>Adapter: Evaluate Outgoing Edges with ConditionEvaluator
    Note over Adapter: Branch 'APPROVE' matches! Traverse to UPDATE_RECORD
    Adapter->>Pool: Get Connection Engine
    Pool->>ClientDB: UPDATE leave_requests SET status='APPROVED' WHERE id=42
    ClientDB-->>Adapter: Updated 1 row
    Adapter->>WfDB: Insert workflow_activity_history (node="UpdateRecord", status="COMPLETED")
    end

    %% Phase 5: Termination
    rect rgb(240, 255, 255)
    Note over Adapter, WS: Phase 5: Workflow Termination
    Adapter->>Adapter: Next node is END (status='COMPLETED')
    Adapter->>WfDB: Update spiff_workflow_instance (status='COMPLETED', completed_on=NOW())
    Adapter->>WS: broadcast_event("WORKFLOW_COMPLETED", instance_data)
    Adapter-->>Gateway: Execution Complete {status: "COMPLETED"}
    Gateway-->>Manager: HTTP 200 Success Response
    end
```

---

## 2. Related Documentation Links

- Engine Architecture: [Engine Architecture](../03-workflow-engine/engine-architecture.md)
- Runtime Execution: [Runtime Execution](../03-workflow-engine/runtime-execution.md)
- Human Task Details: [Human Tasks & Approvals](../03-workflow-engine/human-tasks-and-approvals.md)
