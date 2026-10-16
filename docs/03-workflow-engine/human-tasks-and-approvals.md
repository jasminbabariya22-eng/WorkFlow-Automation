# Human Tasks & Approvals

## 1. Overview & Human Gate Concept

In enterprise business processes, automated execution frequently requires human intervention—such as managerial approval, risk assessment, or manual data review. 

When the workflow engine encounters a `USER_TASK` or `APPROVAL` node:
1. It halts automated graph traversal.
2. It indexes a new human task in the `workflow_human_task` table with status `READY`.
3. It marks the workflow instance status as `WAITING`.
4. It broadcasts a `TASK_READY` event over `/ws/workflow`.
5. The execution thread yields until an authorized user submits an approval or rejection.

```mermaid
sequenceDiagram
    autonumber
    actor Approver as User / Approver
    participant Portal as Client App / Studio Inbox
    participant Gateway as Client Gateway (/client/action)
    participant Adapter as StudioExecutionAdapter
    participant DB as Workflow Database
    participant WS as WebSocket Gateway

    Note over Adapter: Automated steps complete; engine hits APPROVAL node
    Adapter->>DB: Insert SpiffHumanTask (status='READY', role_code='MANAGER')
    Adapter->>DB: Update SpiffWorkflowInstance (status='WAITING')
    Adapter->>WS: Broadcast TASK_READY event
    
    Approver->>Portal: Opens Approval Inbox
    Portal->>Gateway: GET /client/tasks/LEAVE?user_id=5&role_id=2
    Gateway-->>Portal: List of Pending Tasks (task_id, record_id, metadata)
    
    Approver->>Portal: Clicks "Approve" (remarks="Looks good")
    Portal->>Gateway: POST /client/action/LEAVE {record_id, action:'APPROVE', user_id:5}
    Gateway->>Adapter: execute_action(instance_id, action='APPROVE', user_id=5)
    Adapter->>Adapter: is_user_authorized_for_task(user_id, task)
    Adapter->>DB: Update SpiffHumanTask (status='COMPLETED', completed_on=NOW())
    Adapter->>DB: Log workflow_history (action='APPROVE', performed_by=5)
    Adapter->>WS: Broadcast TASK_COMPLETED event
    Adapter->>Adapter: Advance Graph along 'APPROVE' outgoing edge
```

---

## 2. Data Model: `SpiffHumanTask`

Located in `backend/app/workflow/persistence/models.py`:

```python
class SpiffHumanTask(WorkflowBase):
    __tablename__ = "workflow_human_task"
    __table_args__ = {"schema": settings.WORKFLOW_DB_SCHEMA}

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=False)
    task_spec_id = Column(String(100), nullable=False)
    role_code = Column(String(50), nullable=False)
    assignee_id = Column(Integer)
    status = Column(String(20), default="READY", nullable=False)  # 'READY', 'COMPLETED', 'REJECTED'
    created_on = Column(DateTime, default=datetime.now, nullable=False)
    completed_on = Column(DateTime)
```

---

## 3. Authorization & Assignment Logic

Task access control is evaluated in `StudioExecutionAdapter.is_user_authorized_for_task()` (`backend/app/workflow_studio/runtime/adapter.py`):

1. **Direct Assignee Matching**:
   If `assignee_id` is set on the task, only a user with matching `user_id` can complete the task.
2. **Role-Based Assignment**:
   If `role_code` is defined (e.g. `FUNCTION_HEAD`, `FINANCE_APPROVER`, `MANAGER`), the engine queries the client database's user-role mapping table (`mst_users`, `mst_user_role`) or inspects the JWT payload's `role_code` to verify that the actor possesses the required role.
3. **Admin Override**:
   Users with `role_code == "admin"` or `user_type_name == "ADMIN"` can claim and complete any pending task.

---

## 4. Submitting Decisions & Resuming Execution

### Available Action APIs

#### A. Client Application Gateway
- **Endpoint**: `POST /client/action/{module_code}`
- **Payload**:
  ```json
  {
    "record_id": 104,
    "action": "APPROVE",
    "user_id": 5,
    "role": "DEPT_MANAGER",
    "remarks": "Approved after reviewing budget.",
    "variables": { "approved_budget": 50000 }
  }
  ```

#### B. Pure Workflow Tasks API
- **Approve**: `POST /workflow/tasks/{id}/complete`
- **Reject**: `POST /workflow/tasks/{id}/reject`

#### C. Universal Workflow Hub
- **Endpoint**: `POST /api/v1/workflow-hub/action`

### Resumption Mechanics
Upon receiving the decision:
1. The engine marks the active `SpiffHumanTask` status as `COMPLETED` (or `REJECTED`) and records `completed_on = datetime.now()`.
2. A permanent audit record is inserted into `workflow_history`:
   - `instance_id`: Active execution ID.
   - `action_name`: Action code (e.g., `APPROVE`, `REJECT`).
   - `performed_by`: Actor user ID.
   - `performed_role`: Role used.
   - `remarks`: Comments submitted with the decision.
3. The instance state is set back to `RUNNING`.
4. Outgoing edges from the human task node are evaluated using `ConditionEvaluator`. The edge matching the submitted action is followed, and automated graph traversal resumes.

---

## 5. Related Documentation Links

- Engine Mechanics: [Engine Architecture](./engine-architecture.md)
- Lifecycle States: [Workflow Lifecycle](./workflow-lifecycle.md)
- Client Gateway: [Client Application Gateway](../06-integrations/client-application-gateway.md)
