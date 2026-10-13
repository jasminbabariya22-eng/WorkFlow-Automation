import time
import pytest


def test_create_and_inspect_workflow(client):
    """Test creating a workflow definition and inspecting its metadata."""
    wf_key = f"def_test_{int(time.time() * 1000)}"
    res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Definition Test Flow",
        "description": "Integration test for workflow definition",
        "entity_type": "Invoice"
    })
    assert res.status_code == 200
    data = res.json()
    assert "workflow_id" in data
    wf_id = data["workflow_id"]

    # Inspect workflow
    get_res = client.get(f"/workflows/{wf_id}")
    assert get_res.status_code == 200
    wf_data = get_res.json()
    assert wf_data["workflow_key"] == wf_key
    assert wf_data["status"] == "DRAFT"


def test_add_nodes_connections_and_validate(client):
    """Test building a workflow version with nodes and connections, then validating."""
    wf_key = f"valid_flow_{int(time.time() * 1000)}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Validation Test Flow"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Fetch initial version ID
    v_res = client.get(f"/workflows/{wf_id}/versions")
    assert v_res.status_code == 200
    v_id = v_res.json()[0]["workflow_version_id"]

    # Add START, APPROVAL, and END nodes
    n1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "start", "node_type": "START", "name": "Start"
    }).json()["node_id"]

    n2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "manager_review", "node_type": "APPROVAL", "name": "Manager Review",
        "configuration": {"role": "MANAGER"}
    }).json()["node_id"]

    n3 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "end", "node_type": "END", "name": "End"
    }).json()["node_id"]

    # Connect: start -> manager_review -> end
    c1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n1, "target_node_id": n2, "label": "Submit"
    })
    assert c1.status_code == 200

    c2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n2, "target_node_id": n3, "label": "Approve", "condition": "APPROVE"
    })
    assert c2.status_code == 200

    # Validate version
    val_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert val_data["status"] == "VALIDATED"


def test_publish_workflow_and_immutability(client):
    """Test publishing a validated workflow and verifying published version immutability."""
    wf_key = f"pub_flow_{int(time.time() * 1000)}"
    wf_id = client.post("/workflows", json={
        "workflow_key": wf_key, "name": "Publish Flow"
    }).json()["workflow_id"]

    v_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    n1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "start", "node_type": "START", "name": "Start"
    }).json()["node_id"]

    n2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "end", "node_type": "END", "name": "End"
    }).json()["node_id"]

    client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n1, "target_node_id": n2
    })

    # Publish
    pub_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/publish")
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "PUBLISHED"

    # Verify workflow definition is ACTIVE
    wf_data = client.get(f"/workflows/{wf_id}").json()
    assert wf_data["status"] == "ACTIVE"
    assert wf_data["published_version"] == 1

    # Verify immutability: adding a node to a published version must fail
    fail_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "extra", "node_type": "APPROVAL", "name": "Extra Task"
    })
    assert fail_res.status_code == 400


def test_version_evolution(client):
    """Test creating a new draft version from a published version."""
    wf_key = f"evolve_flow_{int(time.time() * 1000)}"
    wf_id = client.post("/workflows", json={
        "workflow_key": wf_key, "name": "Evolve Flow"
    }).json()["workflow_id"]

    v1_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    n1 = client.post(f"/workflows/{wf_id}/versions/{v1_id}/nodes", json={
        "node_key": "start", "node_type": "START", "name": "Start"
    }).json()["node_id"]
    n2 = client.post(f"/workflows/{wf_id}/versions/{v1_id}/nodes", json={
        "node_key": "end", "node_type": "END", "name": "End"
    }).json()["node_id"]
    client.post(f"/workflows/{wf_id}/versions/{v1_id}/connections", json={
        "source_node_id": n1, "target_node_id": n2
    })
    client.post(f"/workflows/{wf_id}/versions/{v1_id}/publish")

    # Create Version 2 cloned from Version 1
    v2_res = client.post(f"/workflows/{wf_id}/versions", json={"clone_from_version_id": v1_id})
    assert v2_res.status_code == 200
    v2_data = v2_res.json()
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "DRAFT"
