import time
import pytest
from app.workflow.persistence.models import SpiffHumanTask, SpiffWorkflowInstance


def test_execute_studio_workflow_human_approval_lifecycle(client, db_session):
    """
    Test end-to-end execution of a Workflow Studio definition:
    1. Define START -> APPROVAL -> END workflow
    2. Validate and Publish
    3. Start instance -> reaches APPROVAL, pauses in WAITING state, creates SpiffHumanTask in READY state
    4. Approve task -> transitions to END, completes instance with Completed status
    """
    ts = int(time.time() * 1000)
    wf_key = f"runtime_approval_flow_{ts}"
    entity_id = 88000 + (ts % 1000)

    # 1. Create Workflow Draft
    create_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": wf_key,
        "name": "Runtime Approval Test Flow",
        "entity_type": "RuntimeApprovalEntity"
    })
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    # 2. Add Nodes and Edges
    graph_payload = {
        "nodes": [
            {"id": "node_start", "type": "START", "name": "Start", "config": {}},
            {
                "id": "node_approval",
                "type": "APPROVAL",
                "name": "Manager Approval",
                "config": {
                    "role": "admin",
                    "role_code": "admin",
                    "actions": ["APPROVE", "REJECT"]
                }
            },
            {"id": "node_end", "type": "END", "name": "Finished", "config": {}}
        ],
        "edges": [
            {"id": "e_start", "source": "node_start", "target": "node_approval", "label": "Submit"},
            {"id": "e_approve", "source": "node_approval", "target": "node_end", "label": "Approve", "condition": "APPROVE"}
        ]
    }
    update_res = client.put(f"/workflow-studio/workflows/{wf_id}", json=graph_payload)
    assert update_res.status_code == 200

    # 3. Validate & Publish
    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "ACTIVE"

    # 4. Start Workflow Instance
    start_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "RuntimeApprovalEntity",
        "entity_id": entity_id,
        "variables": {"test_run": True}
    })
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == "WAITING"
    assert start_data["current_task_code"] == "node_approval"
    inst_id = start_data["instance_id"]

    # 5. Verify SpiffHumanTask created in database
    task_rec = db_session.query(SpiffHumanTask).filter(
        SpiffHumanTask.instance_id == inst_id,
        SpiffHumanTask.status == "READY"
    ).first()
    assert task_rec is not None

    # 6. Advance task with APPROVE action
    action_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "RuntimeApprovalEntity",
        "entity_id": entity_id,
        "action": "APPROVE",
        "remarks": "Approved by automated unit test"
    })
    assert action_res.status_code == 200
    action_data = action_res.json()
    assert action_data["status"] in ("Completed", "COMPLETED")

    # Verify instance is completed in database
    db_inst = db_session.query(SpiffWorkflowInstance).filter(
        SpiffWorkflowInstance.instance_id == inst_id
    ).first()
    assert db_inst.status in ("Completed", "COMPLETED")


def test_execute_studio_workflow_disallowed_action(client):
    """Test that submitting an unauthorized action on a human approval task is rejected with HTTP 400."""
    ts = int(time.time() * 1000)
    wf_key = f"runtime_disallowed_{ts}"
    entity_id = 89000 + (ts % 1000)

    # Create, update, publish
    create_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": wf_key,
        "name": "Disallowed Action Flow",
        "entity_type": "DisallowedEntity"
    })
    assert create_res.status_code == 200
    wf_id = create_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "n_start", "type": "START", "name": "Start", "config": {}},
            {
                "id": "n_approval",
                "type": "APPROVAL",
                "name": "Signoff",
                "config": {"actions": ["APPROVE"]}
            },
            {"id": "n_end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "n_start", "target": "n_approval"},
            {"source": "n_approval", "target": "n_end", "condition": "APPROVE"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    # Start instance
    start_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "DisallowedEntity",
        "entity_id": entity_id
    })
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "WAITING"

    # Attempt illegal action
    bad_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "DisallowedEntity",
        "entity_id": entity_id,
        "action": "INVALID_UNKNOWN_ACTION"
    })
    assert bad_res.status_code == 400
    body = bad_res.json()
    err_msg = body.get("detail") or body.get("Error", {}).get("Error_message", "")
    assert "not permitted" in str(err_msg).lower()


def test_execute_studio_direct_automated_flow(client):
    """Test a direct automated flow without human gates completes immediately."""
    ts = int(time.time() * 1000)
    wf_key = f"runtime_auto_flow_{ts}"
    entity_id = 90000 + (ts % 1000)

    create_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": wf_key,
        "name": "Auto Direct Flow",
        "entity_type": "AutoDirectEntity"
    })
    wf_id = create_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start_node", "type": "START", "name": "Start", "config": {}},
            {"id": "end_node", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start_node", "target": "end_node"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    exec_res = client.post(f"/workflow-studio/workflows/{wf_id}/execute", json={
        "entity_type": "AutoDirectEntity",
        "entity_id": entity_id
    })
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] in ("Completed", "COMPLETED")
