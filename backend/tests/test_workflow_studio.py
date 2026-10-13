import time
import pytest


def test_create_and_update_studio_graph(client):
    """Test creating a visual graph workflow in Workflow Studio and saving nodes/edges."""
    wf_key = f"studio_flow_{int(time.time() * 1000)}"
    create_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": wf_key,
        "name": "Studio Visual Workflow",
        "entity_type": "RiskItem"
    })
    assert create_res.status_code == 200
    wf_data = create_res.json()
    wf_id = wf_data["workflow_id"]
    assert wf_data["status"] == "DRAFT"

    # Save visual graph with nodes and edges
    graph_payload = {
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "position_x": 0.0, "position_y": 0.0, "config": {}},
            {"id": "approval_gate", "type": "APPROVAL", "name": "Manager Review", "position_x": 100.0, "position_y": 100.0, "config": {"role": "MANAGER", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end", "type": "END", "name": "Completed", "position_x": 200.0, "position_y": 200.0, "config": {}}
        ],
        "edges": [
            {"id": "e1", "source": "start", "target": "approval_gate", "label": "Submit"},
            {"id": "e2", "source": "approval_gate", "target": "end", "label": "Approve", "condition": "APPROVE"}
        ]
    }
    update_res = client.put(f"/workflow-studio/workflows/{wf_id}", json=graph_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert len(updated_data["nodes"]) == 3
    assert len(updated_data["edges"]) == 2


def test_validate_and_publish_studio_workflow(client):
    """Test validating and publishing a Studio workflow."""
    wf_key = f"studio_pub_{int(time.time() * 1000)}"
    wf_id = client.post("/workflow-studio/workflows", json={
        "workflow_key": wf_key,
        "name": "Publish Studio Test"
    }).json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "end"}
        ]
    })

    # Validate
    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # Publish
    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["version_status"] == "PUBLISHED"
    assert pub_res.json()["status"] == "ACTIVE"


def test_studio_catalogs_discovery(client):
    """Test retrieving dynamic role and action catalogs for workflow designer."""
    roles_res = client.get("/workflow-studio/roles")
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) >= 1
    assert any("role_code" in r for r in roles)

    actions_res = client.get("/workflow-studio/actions")
    assert actions_res.status_code == 200
    actions = actions_res.json()
    assert len(actions) >= 4
    action_codes = [a["action_code"] for a in actions]
    assert "APPROVE" in action_codes
    assert "REJECT" in action_codes
    assert "SUBMIT" in action_codes
