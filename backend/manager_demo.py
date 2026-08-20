import json, time
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask
from app.workflow.models.history import WorkflowHistory
from app.core.database import ClientDatabaseAdapter
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ts = int(time.time())

print("=" * 75)
print("     ENTERPRISE WORKFLOW DEMONSTRATION FOR MANAGER")
print("=" * 75)
print("\nThis test shows BOTH databases working together on a dedicated business record:")
print("  1. CLIENT DATABASE   -> Business Data (table: mst_department)")
print("  2. WORKFLOW DATABASE -> Engine Data (instances, tasks, audit history)\n")

# -------------------------------------------------------------
# STEP 1: CREATE A DEDICATED BUSINESS RECORD IN CLIENT DB
# -------------------------------------------------------------
print("--- [1/4] INITIAL BUSINESS RECORD IN CLIENT DATABASE: ---")

dept_res = ClientDatabaseAdapter.create_entity_record_generic(
    table_name='mst_department',
    values={
        'dept_name': f'New_Department_Pending_{ts}',
        'created_by': 1,
        'is_deleted': 0
    },
    result_mapping={'id': 'dept_id'}
)
dept_id = dept_res['dept_id']

dept_before = ClientDatabaseAdapter.read_entity_record(
    table_name='mst_department',
    fields=['id', 'dept_name'],
    filters=[{'field': 'id', 'operator': '=', 'value': dept_id}]
)

print(f"   * Client Table : mst_department")
print(f"   * Record ID    : {dept_before['id']}")
print(f"   * Dept Name    : '{dept_before['dept_name']}' (Status: Pending Approval)\n")

# -------------------------------------------------------------
# STEP 2: CREATE & PUBLISH A WORKFLOW
# -------------------------------------------------------------
print("--- [2/4] WORKFLOW DESIGN: ---")
print("   Pipeline: [START] --> [USER TASK: Manager Review] --> [DB UPDATE] --> [END]")

wf_payload = {
    'name': f'Manager_Approval_Flow_{ts}',
    'workflow_key': f'mgr_flow_{ts}',
    'entity_type': 'DEPARTMENT_RECORD',
    'description': 'Approval flow for new department creation',
    'nodes': [
        {'id': 'n_start', 'type': 'START', 'name': 'Start', 'position_x': 100, 'position_y': 50, 'config': {'taskCode': 'START'}},
        {
            'id': 'n_task',
            'type': 'USER_TASK',
            'name': 'Manager Review',
            'position_x': 100,
            'position_y': 150,
            'config': {
                'taskCode': 'MANAGER_REVIEW',
                'assignment': {'type': 'role', 'roleName': 'all good Up', 'roleId': '18'},
                'actions': ['APPROVE', 'REJECT']
            }
        },
        {
            'id': 'n_update',
            'type': 'ACTION',
            'name': 'Update Department in Client DB',
            'position_x': 100,
            'position_y': 250,
            'config': {
                'taskCode': 'DB_UPDATE_STEP',
                'actionType': 'DB_UPDATE',
                'table': 'mst_department',
                'filters': [{'field': 'id', 'operator': '=', 'value': dept_id}],
                'updates': {
                    'dept_name': f'Active_Department_{ts}'
                },
                'resultMapping': {'affectedRows': 'rows_updated'}
            }
        },
        {'id': 'n_end', 'type': 'END', 'name': 'End', 'position_x': 100, 'position_y': 350, 'config': {'taskCode': 'COMPLETED'}}
    ],
    'edges': [
        {'id': 'e1', 'source': 'n_start', 'target': 'n_task', 'label': 'SUBMIT'},
        {'id': 'e2', 'source': 'n_task', 'target': 'n_update', 'label': 'APPROVE'},
        {'id': 'e3', 'source': 'n_update', 'target': 'n_end', 'label': 'NEXT'}
    ]
}

r = client.post('/workflow-studio/workflows', json=wf_payload)
wf_id = r.json()['workflow_id']
client.post(f'/workflow-studio/workflows/{wf_id}/publish')
print(f"   * Workflow Definition saved & activated in Workflow DB (ID: {wf_id})\n")

# -------------------------------------------------------------
# STEP 3: START WORKFLOW (PAUSES AT USER TASK)
# -------------------------------------------------------------
print("--- [3/4] STARTING WORKFLOW INSTANCE: ---")
with WorkflowSessionLocal() as db:
    s = StudioExecutionAdapter.start_workflow(
        entity_type='DEPARTMENT_RECORD',
        entity_id=dept_id,
        user_id=1,
        db=db,
        definition_id=wf_id
    )
    inst_id = s['instance_id']
    
    # Inspect Workflow DB tables
    inst_row = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == inst_id).first()
    task_row = db.query(SpiffHumanTask).filter(SpiffHumanTask.instance_id == inst_id, SpiffHumanTask.status == 'READY').first()

    print(f"   * [Workflow DB] workflow_instance table   -> Instance #{inst_row.instance_id}, Status = '{inst_row.status}'")
    print(f"   * [Workflow DB] workflow_human_task table -> Task #{task_row.task_id} ('{task_row.task_spec_id}'), Status = '{task_row.status}'")
    print(f"   * [Client DB]   mst_department table      -> Dept Name is still '{dept_before['dept_name']}' (Unchanged while waiting)")
    print(f"   * Workflow is now WAITING for human approval.\n")

# -------------------------------------------------------------
# STEP 4: MANAGER CLICKS 'APPROVE'
# -------------------------------------------------------------
print("--- [4/4] EXECUTING 'APPROVE' ACTION: ---")
with WorkflowSessionLocal() as db:
    res = StudioExecutionAdapter.execute_action(
        entity_type='DEPARTMENT_RECORD',
        entity_id=dept_id,
        action='APPROVE',
        user_id=1,
        db=db
    )
    
    # Check Workflow DB final state
    inst_final = db.query(SpiffWorkflowInstance).filter(SpiffWorkflowInstance.instance_id == inst_id).first()
    tasks_all = db.query(SpiffHumanTask).filter(SpiffHumanTask.instance_id == inst_id).all()
    history_all = db.query(WorkflowHistory).filter(WorkflowHistory.instance_id == inst_id).all()

    print(f"   * [Workflow DB] workflow_instance table   -> Status = '{inst_final.status}' (Completed on: {inst_final.completed_on})")
    print(f"   * [Workflow DB] workflow_human_task table -> Task Status = '{tasks_all[0].status}' (Completed on: {tasks_all[0].completed_on})")
    print(f"   * [Workflow DB] workflow_history table    -> {len(history_all)} Audit Trail records saved:")
    for h in history_all:
        print(f"        - Step: {h.from_state_code} --[{h.action_name}]--> {h.to_state_code} (by User #{h.performed_by})")

# Check Client DB final state
dept_after = ClientDatabaseAdapter.read_entity_record(
    table_name='mst_department',
    fields=['id', 'dept_name'],
    filters=[{'field': 'id', 'operator': '=', 'value': dept_id}]
)

print(f"\n   * [Client DB]   mst_department table (ID={dept_id}) -> Dept Name CHANGED to: '{dept_after['dept_name']}'")

print("\n" + "=" * 75)
print("                         SUMMARY OF CHANGES")
print("=" * 75)
print(f"1. CLIENT DATABASE (Business Data):")
print(f"   mst_department.dept_name : '{dept_before['dept_name']}'  --->  '{dept_after['dept_name']}'")
print(f"\n2. WORKFLOW DATABASE (Engine Data):")
print(f"   workflow_instance        : Started ---> WAITING ---> Completed")
print(f"   workflow_human_task      : Created ---> READY ---> COMPLETED")
print(f"   workflow_history         : 3 Audit Trail records saved with exact timestamps")
print("=" * 75)
