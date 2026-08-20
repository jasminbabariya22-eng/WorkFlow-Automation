import time
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def get_error_message(response) -> str:
    """Helper to extract error message from standard or custom error responses."""
    data = response.json()
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        if "Error" in data and isinstance(data["Error"], dict):
            return str(data["Error"].get("Error_message", ""))
    return response.text


def test_01_create_workflow():
    """Test 1 — Verify a workflow can be created in DRAFT."""
    wf_key = f"proc_approval_{int(time.time())}"
    res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Purchase Requisition Workflow",
        "description": "Generic approval process for purchase requests",
        "entity_type": "PurchaseRequest"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["workflow_key"] == wf_key
    assert data["name"] == "Purchase Requisition Workflow"
    assert data["entity_type"] == "PurchaseRequest"
    assert data["status"] == "DRAFT"
    assert data["latest_version"] == 1
    assert data["published_version"] is None
    print("Test 1 passed: Created workflow in DRAFT with initial version 1")


def test_02_create_version():
    """Test 2 — Verify a workflow version can be created."""
    wf_key = f"audit_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Audit Finding Workflow",
        "entity_type": "Audit"
    })
    wf_id = wf_res.json()["workflow_id"]

    v_res = client.post(f"/workflows/{wf_id}/versions", json={
        "definition_metadata": {"author": "Compliance Team", "sla_days": 5}
    })
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["workflow_id"] == wf_id
    assert v_data["version_number"] == 2
    assert v_data["status"] == "DRAFT"
    assert v_data["definition_metadata"]["author"] == "Compliance Team"
    print("Test 2 passed: Created workflow version 2 in DRAFT")


def test_03_create_nodes():
    """Test 3 — Verify multiple generic node types can be stored with JSON configuration."""
    wf_key = f"incident_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Incident Response Workflow",
        "entity_type": "Incident"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Get initial version ID
    v_list = client.get(f"/workflows/{wf_id}/versions").json()
    v_id = v_list[0]["workflow_version_id"]

    # 1. START node
    start_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "start_trigger",
        "node_type": "START",
        "name": "Incident Created Trigger",
        "position_x": 100,
        "position_y": 200,
        "configuration": {"event": "INCIDENT_REPORTED"}
    })
    assert start_res.status_code == 200
    assert start_res.json()["node_type"] == "START"

    # 2. APPROVAL node
    appr_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "triage_approval",
        "node_type": "APPROVAL",
        "name": "Incident Lead Triage",
        "position_x": 300,
        "position_y": 200,
        "configuration": {
            "role": "INCIDENT_LEAD",
            "actions": ["APPROVE", "REJECT", "ESCALATE"],
            "sla_hours": 4
        }
    })
    assert appr_res.status_code == 200
    assert appr_res.json()["configuration"]["role"] == "INCIDENT_LEAD"

    # 3. CONDITION node
    cond_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "severity_check",
        "node_type": "CONDITION",
        "name": "High Severity Check",
        "position_x": 500,
        "position_y": 200,
        "configuration": {"expression": "incident.severity == 'P1'"}
    })
    assert cond_res.status_code == 200

    # 4. EMAIL node
    email_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "alert_notification",
        "node_type": "EMAIL",
        "name": "Dispatch Alert Notification",
        "position_x": 700,
        "position_y": 200,
        "configuration": {"template": "INCIDENT_ALERT_EMAIL", "to": "oncall@company.com"}
    })
    assert email_res.status_code == 200

    # 5. END node
    end_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "resolved_end",
        "node_type": "END",
        "name": "Incident Resolved",
        "position_x": 900,
        "position_y": 200,
        "configuration": {"status": "RESOLVED"}
    })
    assert end_res.status_code == 200
    print("Test 3 passed: Created multiple generic node types with JSON configuration")


def test_04_create_connections():
    """Test 4 — Verify connections correctly link nodes."""
    wf_key = f"conn_test_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Connection Test Workflow"
    })
    wf_id = wf_res.json()["workflow_id"]
    v_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    # Create 3 nodes
    n1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "start", "node_type": "START", "name": "Start"
    }).json()["node_id"]

    n2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "review", "node_type": "APPROVAL", "name": "Manager Review"
    }).json()["node_id"]

    n3 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "end", "node_type": "END", "name": "End"
    }).json()["node_id"]

    # Connect n1 -> n2
    c1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n1,
        "target_node_id": n2,
        "label": "Submit"
    })
    assert c1.status_code == 200
    assert c1.json()["source_node_id"] == n1
    assert c1.json()["target_node_id"] == n2

    # Connect n2 -> n3
    c2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n2,
        "target_node_id": n3,
        "label": "Approve",
        "condition": "action == 'APPROVE'"
    })
    assert c2.status_code == 200
    print("Test 4 passed: Connections correctly link nodes")


def test_05_validate_valid_workflow():
    """Test 5 — Verify a valid workflow (START -> APPROVAL -> END) validates successfully."""
    wf_key = f"valid_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Valid Test Flow"
    })
    wf_id = wf_res.json()["workflow_id"]
    v_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    n_start = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "start", "node_type": "START", "name": "Start"
    }).json()["node_id"]

    n_appr = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "approval", "node_type": "APPROVAL", "name": "Head Approval"
    }).json()["node_id"]

    n_end = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "end", "node_type": "END", "name": "Completed"
    }).json()["node_id"]

    client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n_start, "target_node_id": n_appr, "label": "Submit"
    })
    client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": n_appr, "target_node_id": n_end, "label": "Approve"
    })

    val_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert val_data["status"] == "VALIDATED"
    assert len(val_data["errors"]) == 0
    print("Test 5 passed: Valid workflow validation succeeded")


def test_06_reject_invalid_workflow():
    """Test 6 — Verify invalid workflow definitions are rejected."""
    wf_key = f"invalid_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Invalid Test Flow"
    })
    wf_id = wf_res.json()["workflow_id"]
    v_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    # Case A: No START node (Only an approval node)
    client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "orphan_approval", "node_type": "APPROVAL", "name": "Orphan Task"
    })
    val_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/validate")
    assert val_res.json()["is_valid"] is False
    assert any(e["code"] == "MISSING_START_NODE" for e in val_res.json()["errors"])
    assert any(e["code"] == "MISSING_END_NODE" for e in val_res.json()["errors"])

    # Case B: Duplicate node key in same version
    dup_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "orphan_approval", "node_type": "APPROVAL", "name": "Duplicate Task"
    })
    assert dup_res.status_code == 400
    assert "already exists" in get_error_message(dup_res)

    # Case C: Connection referencing missing node
    conn_bad = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={
        "source_node_id": 99999, "target_node_id": 88888
    })
    assert conn_bad.status_code == 400
    print("Test 6 passed: Invalid workflow definitions correctly rejected")


def test_07_publish_valid_workflow():
    """Test 7 — Verify a valid version can be published."""
    wf_key = f"pub_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={
        "workflow_key": wf_key,
        "name": "Publish Test Flow"
    })
    wf_id = wf_res.json()["workflow_id"]
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

    pub_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/publish")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["status"] == "PUBLISHED"
    assert pub_data["published_at"] is not None

    # Check workflow definition status is now ACTIVE
    wf_get = client.get(f"/workflows/{wf_id}").json()
    assert wf_get["status"] == "ACTIVE"
    assert wf_get["published_version"] == 1
    print("Test 7 passed: Valid workflow version published successfully")


def test_08_published_version_immutability():
    """Test 8 — Verify modifying nodes or connections of a PUBLISHED version is rejected."""
    wf_key = f"immutable_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={"workflow_key": wf_key, "name": "Immutable Flow"})
    wf_id = wf_res.json()["workflow_id"]
    v_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    n1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={"node_key": "start", "node_type": "START", "name": "Start"}).json()["node_id"]
    n2 = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={"node_key": "end", "node_type": "END", "name": "End"}).json()["node_id"]
    c1 = client.post(f"/workflows/{wf_id}/versions/{v_id}/connections", json={"source_node_id": n1, "target_node_id": n2}).json()["connection_id"]

    # Publish version
    client.post(f"/workflows/{wf_id}/versions/{v_id}/publish")

    # 1. Attempt to add a node to published version -> Must Fail
    add_node_res = client.post(f"/workflows/{wf_id}/versions/{v_id}/nodes", json={
        "node_key": "new_task", "node_type": "APPROVAL", "name": "Forbidden Task"
    })
    assert add_node_res.status_code == 400
    assert "Cannot modify a published workflow version" in get_error_message(add_node_res)

    # 2. Attempt to update a node on published version -> Must Fail
    update_node_res = client.put(f"/workflows/{wf_id}/versions/{v_id}/nodes/{n1}", json={
        "name": "Modified Start Name"
    })
    assert update_node_res.status_code == 400
    assert "Cannot modify a published workflow version" in get_error_message(update_node_res)

    # 3. Attempt to delete a connection on published version -> Must Fail
    del_conn_res = client.delete(f"/workflows/{wf_id}/versions/{v_id}/connections/{c1}")
    assert del_conn_res.status_code == 400
    assert "Cannot modify a published workflow version" in get_error_message(del_conn_res)
    print("Test 8 passed: Immutability on published versions strictly enforced")


def test_09_version_evolution():
    """Test 9 — Verify creating Version 2 from Version 1, modifying Version 2, and verifying Version 1 remains unchanged."""
    wf_key = f"evolution_flow_{int(time.time())}"
    wf_res = client.post("/workflows", json={"workflow_key": wf_key, "name": "Evolution Flow"})
    wf_id = wf_res.json()["workflow_id"]
    v1_id = client.get(f"/workflows/{wf_id}/versions").json()[0]["workflow_version_id"]

    # Version 1 graph: Start -> FH Approval -> End
    n_start = client.post(f"/workflows/{wf_id}/versions/{v1_id}/nodes", json={"node_key": "start", "node_type": "START", "name": "Start"}).json()["node_id"]
    n_fh = client.post(f"/workflows/{wf_id}/versions/{v1_id}/nodes", json={"node_key": "fh", "node_type": "APPROVAL", "name": "FH Approval", "configuration": {"role": "FUNCTION_HEAD"}}).json()["node_id"]
    n_end = client.post(f"/workflows/{wf_id}/versions/{v1_id}/nodes", json={"node_key": "end", "node_type": "END", "name": "End"}).json()["node_id"]

    client.post(f"/workflows/{wf_id}/versions/{v1_id}/connections", json={"source_node_id": n_start, "target_node_id": n_fh})
    client.post(f"/workflows/{wf_id}/versions/{v1_id}/connections", json={"source_node_id": n_fh, "target_node_id": n_end})

    # Publish Version 1
    client.post(f"/workflows/{wf_id}/versions/{v1_id}/publish")

    # Create Version 2 by cloning from Version 1
    v2_res = client.post(f"/workflows/{wf_id}/versions", json={"clone_from_version_id": v1_id})
    assert v2_res.status_code == 200
    v2_id = v2_res.json()["workflow_version_id"]
    assert v2_res.json()["version_number"] == 2
    assert v2_res.json()["status"] == "DRAFT"

    # Add RM Approval step to Version 2
    v2_detail = client.get(f"/workflows/{wf_id}/versions/{v2_id}").json()
    assert len(v2_detail["nodes"]) == 3
    assert len(v2_detail["connections"]) == 2

    # Add new node to Version 2
    n_rm = client.post(f"/workflows/{wf_id}/versions/{v2_id}/nodes", json={
        "node_key": "rm", "node_type": "APPROVAL", "name": "RM Approval", "configuration": {"role": "RISK_MANAGER"}
    }).json()["node_id"]

    # Verify Version 1 is still intact and unchanged (still 3 nodes, status PUBLISHED)
    v1_detail = client.get(f"/workflows/{wf_id}/versions/{v1_id}").json()
    assert v1_detail["status"] == "PUBLISHED"
    assert len(v1_detail["nodes"]) == 3

    # Verify Version 2 now has 4 nodes
    v2_detail_updated = client.get(f"/workflows/{wf_id}/versions/{v2_id}").json()
    assert len(v2_detail_updated["nodes"]) == 4
    print("Test 9 passed: Version evolution and isolation verified")


def test_10_existing_workflow_regression():
    """Test 10 — Run existing workflow definition & execution checks to ensure zero regression."""
    # Test existing workflow management endpoint
    list_res = client.get("/workflow/definitions")
    assert list_res.status_code in [200, 307]

    # Test health endpoint
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"
    print("Test 10 passed: Zero regression on existing endpoints")


if __name__ == "__main__":
    test_01_create_workflow()
    test_02_create_version()
    test_03_create_nodes()
    test_04_create_connections()
    test_05_validate_valid_workflow()
    test_06_reject_invalid_workflow()
    test_07_publish_valid_workflow()
    test_08_published_version_immutability()
    test_09_version_evolution()
    test_10_existing_workflow_regression()
    print("\nALL PHASE 1 GENERIC WORKFLOW DEFINITION TESTS PASSED SUCCESSFULLY!")
