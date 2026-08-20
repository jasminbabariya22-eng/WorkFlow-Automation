import json, time
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.workflow_studio.runtime.adapter import StudioExecutionAdapter
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow.persistence.models import SpiffWorkflowInstance, SpiffHumanTask
from app.core.database import ClientDatabaseAdapter

client = TestClient(app)
print("=== RUNNING USER TASK CLIENT DATABASE INTEGRATION TEST SUITE ===")

ts = int(time.time())

# ----------------------------------------------------
# 1. Fetch Master Data from Client DB
# ----------------------------------------------------
roles = ClientDatabaseAdapter.get_roles()
users = ClientDatabaseAdapter.get_users()
depts = ClientDatabaseAdapter.get_departments()

assert len(roles) > 0, "Client DB roles must not be empty"
assert len(users) > 0, "Client DB users must not be empty"
assert len(depts) > 0, "Client DB departments must not be empty"

test_role = roles[0]
test_user = users[0]
test_dept = next((d for d in depts if any(u.get("dept_id") == d["id"] for u in users)), depts[0])

# Find a user belonging to test_dept
dept_user = next((u for u in users if u.get("dept_id") == test_dept["id"]), test_user)

print(f"Master Data loaded: Roles={len(roles)}, Users={len(users)}, Depts={len(depts)}")
print(f"Target Role: {test_role['name']} (ID {test_role['id']})")
print(f"Target User: {test_user['name']} (ID {test_user['id']})")
print(f"Target Dept: {test_dept['name']} (ID {test_dept['id']}) -> User {dept_user['name']} (ID {dept_user['id']})")

# ----------------------------------------------------
# TEST 1: Role Assignment from Client DB
# ----------------------------------------------------
wf_role_payload = {
    'name': f'UT_Role_{ts}',
    'workflow_key': f'ut_role_{ts}',
    'entity_type': f'UT_Role_E_{ts}',
    'description': 'USER_TASK assigned to Client DB Role',
    'nodes': [
        {'id': 'n_start', 'type': 'START', 'name': 'Start', 'position_x': 100, 'position_y': 50, 'config': {'taskCode': 'START'}},
        {
            'id': 'n_task',
            'type': 'USER_TASK',
            'name': f"Review by {test_role['name']}",
            'position_x': 100,
            'position_y': 150,
            'config': {
                'taskCode': 'ROLE_TASK',
                'assignment': {
                    'type': 'role',
                    'roleId': str(test_role['id']),
                    'roleName': test_role['name']
                },
                'actions': ['APPROVE', 'REJECT']
            }
        },
        {'id': 'n_end', 'type': 'END', 'name': 'End', 'position_x': 100, 'position_y': 250, 'config': {'taskCode': 'END'}}
    ],
    'edges': [
        {'id': 'e1', 'source': 'n_start', 'target': 'n_task', 'label': 'SUBMIT'},
        {'id': 'e2', 'source': 'n_task', 'target': 'n_end', 'label': 'APPROVE'}
    ]
}

r1 = client.post('/workflow-studio/workflows', json=wf_role_payload)
wf1_id = r1.json()['workflow_id']
client.post(f'/workflow-studio/workflows/{wf1_id}/publish')

with WorkflowSessionLocal() as db:
    s1 = StudioExecutionAdapter.start_workflow(
        entity_type=f'UT_Role_E_{ts}',
        entity_id=1,
        user_id=int(test_user['id']),
        db=db,
        definition_id=wf1_id
    )
    assert s1['status'] == 'WAITING'
    inst1_id = s1['instance_id']

    # Verify authorization check
    user_with_role = next((u for u in users if u.get("role_id") == test_role["id"]), None)
    if user_with_role:
        pending_role_tasks = StudioExecutionAdapter.get_pending_tasks_for_user(db, int(user_with_role['id']))
        task_ids = [t['instance_id'] for t in pending_role_tasks]
        assert inst1_id in task_ids
        print(f"TEST 1 PASSED: Role assignment verified. User {user_with_role['id']} sees task in inbox.")

        # Approve and resume
        res1 = StudioExecutionAdapter.execute_action(
            entity_type=f'UT_Role_E_{ts}',
            entity_id=1,
            action='APPROVE',
            user_id=int(user_with_role['id']),
            db=db
        )
        assert res1['status'] == 'Completed'
        print("TEST 1 PASSED: Role user approved task and workflow reached Completed.")

# ----------------------------------------------------
# TEST 2: Specific User Assignment from Client DB
# ----------------------------------------------------
wf_user_payload = {
    'name': f'UT_User_{ts}',
    'workflow_key': f'ut_user_{ts}',
    'entity_type': f'UT_User_E_{ts}',
    'description': 'USER_TASK assigned to Specific Client DB User',
    'nodes': [
        {'id': 'n_start', 'type': 'START', 'name': 'Start', 'position_x': 100, 'position_y': 50, 'config': {'taskCode': 'START'}},
        {
            'id': 'n_task',
            'type': 'USER_TASK',
            'name': f"Review by {test_user['name']}",
            'position_x': 100,
            'position_y': 150,
            'config': {
                'taskCode': 'USER_TASK_SPECIFIC',
                'assignment': {
                    'type': 'user',
                    'userId': str(test_user['id']),
                    'userName': test_user['name']
                },
                'actions': ['APPROVE']
            }
        },
        {'id': 'n_end', 'type': 'END', 'name': 'End', 'position_x': 100, 'position_y': 250, 'config': {'taskCode': 'END'}}
    ],
    'edges': [
        {'id': 'e1', 'source': 'n_start', 'target': 'n_task', 'label': 'SUBMIT'},
        {'id': 'e2', 'source': 'n_task', 'target': 'n_end', 'label': 'APPROVE'}
    ]
}

r2 = client.post('/workflow-studio/workflows', json=wf_user_payload)
wf2_id = r2.json()['workflow_id']
client.post(f'/workflow-studio/workflows/{wf2_id}/publish')

with WorkflowSessionLocal() as db:
    s2 = StudioExecutionAdapter.start_workflow(
        entity_type=f'UT_User_E_{ts}',
        entity_id=2,
        user_id=int(test_user['id']),
        db=db,
        definition_id=wf2_id
    )
    assert s2['status'] == 'WAITING'
    inst2_id = s2['instance_id']

    # Specific assigned user can execute
    pending_user_tasks = StudioExecutionAdapter.get_pending_tasks_for_user(db, int(test_user['id']))
    task2_ids = [t['instance_id'] for t in pending_user_tasks]
    assert inst2_id in task2_ids

    # Unassigned user cannot execute
    diff_user = next((u for u in users if u['id'] != test_user['id']), None)
    if diff_user:
        unauth_threw = False
        try:
            StudioExecutionAdapter.execute_action(
                entity_type=f'UT_User_E_{ts}',
                entity_id=2,
                action='APPROVE',
                user_id=int(diff_user['id']),
                db=db
            )
        except HTTPException as ex:
            unauth_threw = True
            assert ex.status_code == 403
        assert unauth_threw
        print(f"TEST 2 PASSED: Unauthorized user {diff_user['id']} was strictly blocked with 403.")

    # Authorized user executes
    res2 = StudioExecutionAdapter.execute_action(
        entity_type=f'UT_User_E_{ts}',
        entity_id=2,
        action='APPROVE',
        user_id=int(test_user['id']),
        db=db
    )
    assert res2['status'] == 'Completed'
    print("TEST 2 PASSED: Specific User assignment verified end-to-end.")

# ----------------------------------------------------
# TEST 3: Department Assignment from Client DB
# ----------------------------------------------------
wf_dept_payload = {
    'name': f'UT_Dept_{ts}',
    'workflow_key': f'ut_dept_{ts}',
    'entity_type': f'UT_Dept_E_{ts}',
    'description': 'USER_TASK assigned to Client DB Department',
    'nodes': [
        {'id': 'n_start', 'type': 'START', 'name': 'Start', 'position_x': 100, 'position_y': 50, 'config': {'taskCode': 'START'}},
        {
            'id': 'n_task',
            'type': 'USER_TASK',
            'name': f"Review by {test_dept['name']}",
            'position_x': 100,
            'position_y': 150,
            'config': {
                'taskCode': 'DEPT_TASK_SPECIFIC',
                'assignment': {
                    'type': 'department',
                    'departmentId': str(test_dept['id']),
                    'departmentName': test_dept['name']
                },
                'actions': ['APPROVE']
            }
        },
        {'id': 'n_end', 'type': 'END', 'name': 'End', 'position_x': 100, 'position_y': 250, 'config': {'taskCode': 'END'}}
    ],
    'edges': [
        {'id': 'e1', 'source': 'n_start', 'target': 'n_task', 'label': 'SUBMIT'},
        {'id': 'e2', 'source': 'n_task', 'target': 'n_end', 'label': 'APPROVE'}
    ]
}

r3 = client.post('/workflow-studio/workflows', json=wf_dept_payload)
wf3_id = r3.json()['workflow_id']
client.post(f'/workflow-studio/workflows/{wf3_id}/publish')

with WorkflowSessionLocal() as db:
    s3 = StudioExecutionAdapter.start_workflow(
        entity_type=f'UT_Dept_E_{ts}',
        entity_id=3,
        user_id=int(dept_user['id']),
        db=db,
        definition_id=wf3_id
    )
    assert s3['status'] == 'WAITING'
    inst3_id = s3['instance_id']

    # Department user can view task
    pending_dept_tasks = StudioExecutionAdapter.get_pending_tasks_for_user(db, int(dept_user['id']))
    task3_ids = [t['instance_id'] for t in pending_dept_tasks]
    assert inst3_id in task3_ids

    # Execute approval
    res3 = StudioExecutionAdapter.execute_action(
        entity_type=f'UT_Dept_E_{ts}',
        entity_id=3,
        action='APPROVE',
        user_id=int(dept_user['id']),
        db=db
    )
    assert res3['status'] == 'Completed'
    print("TEST 3 PASSED: Department assignment verified end-to-end.")

print("=== ALL USER TASK CLIENT DB INTEGRATION TESTS PASSED (100%) ===")
