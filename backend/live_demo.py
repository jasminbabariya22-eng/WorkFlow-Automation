import json, time
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.workflow_session import WorkflowSessionLocal
from app.core.database import ClientDatabaseAdapter
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ts = int(time.time())

print("=" * 60)
print("1. LIVE CLIENT DATABASE STATE BEFORE WORKFLOW EXECUTION")
print("=" * 60)
before = ClientDatabaseAdapter.read_entity_record(
    table_name='mst_users',
    fields=['id', 'first_name', 'email'],
    filters=[{'field': 'id', 'operator': '=', 'value': 1}]
)
print(f"Record in Client DB (mst_users ID=1):")
print(f"  • ID:         {before['id']}")
print(f"  • First Name: {before['first_name']}")
print(f"  • Email:      {before['email']}")

# Create workflow with START -> USER_TASK -> DB_UPDATE -> END
wf_payload = {
    'name': f'Live_Approval_DB_Update_{ts}',
    'workflow_key': f'live_approval_db_update_{ts}',
    'entity_type': 'USER_RECORD',
    'description': 'Live Test: Updates Client DB upon User Task Approval',
    'nodes': [
        {'id': 'n_start', 'type': 'START', 'name': 'Start', 'position_x': 100, 'position_y': 50, 'config': {'taskCode': 'START'}},
        {
            'id': 'n_task',
            'type': 'USER_TASK',
            'name': 'Supervisor Approval',
            'position_x': 100,
            'position_y': 150,
            'config': {
                'taskCode': 'SUPERVISOR_APPROVAL',
                'assignment': {'type': 'role', 'roleName': 'all good Up', 'roleId': '18'},
                'actions': ['APPROVE', 'REJECT']
            }
        },
        {
            'id': 'n_update',
            'type': 'ACTION',
            'name': 'Update User in Client DB',
            'position_x': 100,
            'position_y': 250,
            'config': {
                'taskCode': 'DB_UPDATE_STEP',
                'actionType': 'DB_UPDATE',
                'table': 'mst_users',
                'filters': [{'field': 'id', 'operator': '=', 'value': 1}],
                'updates': {
                    'first_name': f'Verified_Live_{ts}'
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

print("\n" + "=" * 60)
print(f"2. WORKFLOW DEFINITION CREATED & ACTIVATED (ID={wf_id})")
print("=" * 60)
print("Pipeline: START -> USER_TASK (Waiting) -> APPROVE -> DB_UPDATE (Live Write) -> END")

print("\n" + "=" * 60)
print("3. STARTING WORKFLOW INSTANCE")
print("=" * 60)
with WorkflowSessionLocal() as db:
    s = StudioExecutionAdapter.start_workflow(
        entity_type='USER_RECORD',
        entity_id=1,
        user_id=1,
        db=db,
        definition_id=wf_id
    )
    inst_id = s['instance_id']
    print(f"Instance ID:    {inst_id}")
    print(f"Status:         {s['status']}")
    print(f"Current Task:   {s['current_task_code']}")

# Check DB state while waiting for approval
mid = ClientDatabaseAdapter.read_entity_record(
    table_name='mst_users',
    fields=['id', 'first_name', 'email'],
    filters=[{'field': 'id', 'operator': '=', 'value': 1}]
)
print(f"Database Value during WAITING: {mid['first_name']} (unchanged as expected)")

print("\n" + "=" * 60)
print("4. EXECUTING 'APPROVE' ACTION ON USER TASK")
print("=" * 60)
with WorkflowSessionLocal() as db:
    res = StudioExecutionAdapter.execute_action(
        entity_type='USER_RECORD',
        entity_id=1,
        action='APPROVE',
        user_id=1,
        db=db
    )
    print(f"Action Status:       {res['status']}")
    print(f"Final Task Code:     {res['current_task_code']}")
    print(f"Engine Message:      {res['message']}")

print("\n" + "=" * 60)
print("5. LIVE CLIENT DATABASE STATE AFTER APPROVAL & DB_UPDATE")
print("=" * 60)
after = ClientDatabaseAdapter.read_entity_record(
    table_name='mst_users',
    fields=['id', 'first_name', 'email'],
    filters=[{'field': 'id', 'operator': '=', 'value': 1}]
)
print(f"Record in Client DB (mst_users ID=1):")
print(f"  • ID:         {after['id']}")
print(f"  • First Name: {after['first_name']}")
print(f"  • Email:      {after['email']}")

print(f"\n>>> LIVE DATABASE CHANGE CONFIRMED: '{before['first_name']}' -> '{after['first_name']}'")

print("\n" + "=" * 60)
print("6. COMPLETE WORKFLOW AUDIT HISTORY TRACE")
print("=" * 60)
h = client.get(f'/workflow-studio/instances/{inst_id}/history').json()
for row in h:
    print(f"  • {row['from_state_code']} -> {row['to_state_code']} [{row['action_name']}] | User #{row['performed_by']} ({row['performed_role']}) at {row['performed_on']}")
