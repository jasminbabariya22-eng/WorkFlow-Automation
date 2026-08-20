import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflow.workflow_session import WorkflowSessionLocal

client = TestClient(app)


def test_01_create_workflow_draft():
    """
    Test 1 — Create workflow: Verify a new workflow can be created as DRAFT.
    """
    res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p7_flow_{int(time.time())}",
        "name": "Phase 7 Visual Workflow",
        "description": "Visual drag-and-drop workflow draft",
        "entity_type": "Risk"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["workflow_id"] is not None
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert data["version_status"] == "DRAFT"
    print("Test 1 Passed: New workflow created as DRAFT successfully.")
    return data["workflow_id"]


def test_02_add_nodes():
    """
    Test 2 — Add nodes: Verify nodes are persisted in the workflow definition.
    """
    wf_id = test_01_create_workflow_draft()

    nodes = [
        {"id": "start_1", "type": "START", "name": "Risk Submitted", "position_x": 100, "position_y": 200, "config": {"trigger": "SUBMIT", "entity_type": "Risk"}},
        {"id": "fh_approval", "type": "APPROVAL", "name": "Functional Head Approval", "position_x": 300, "position_y": 200, "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
        {"id": "end_1", "type": "END", "name": "Risk Processed", "position_x": 500, "position_y": 200, "config": {}}
    ]

    put_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": nodes,
        "edges": []
    })
    assert put_res.status_code == 200
    saved_nodes = put_res.json()["nodes"]
    assert len(saved_nodes) == 3
    assert any(n["id"] == "fh_approval" and n["type"] == "APPROVAL" for n in saved_nodes)
    print("Test 2 Passed: Nodes successfully persisted into workflow definition.")
    return wf_id


def test_03_connect_nodes():
    """
    Test 3 — Connect nodes: Verify edges are persisted correctly.
    """
    wf_id = test_02_add_nodes()

    edges = [
        {"id": "edge_submit", "source": "start_1", "target": "fh_approval", "label": "Submit"},
        {"id": "edge_appr", "source": "fh_approval", "target": "end_1", "condition": "APPROVE", "label": "Approve"}
    ]

    put_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start_1", "type": "START", "name": "Risk Submitted", "config": {}},
            {"id": "fh_approval", "type": "APPROVAL", "name": "FH Approval", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end_1", "type": "END", "name": "Risk Processed", "config": {}}
        ],
        "edges": edges
    })
    assert put_res.status_code == 200
    saved_edges = put_res.json()["edges"]
    assert len(saved_edges) == 2
    assert any(e["source"] == "start_1" and e["target"] == "fh_approval" for e in saved_edges)
    assert any(e["source"] == "fh_approval" and e["target"] == "end_1" and e["condition"] == "APPROVE" for e in saved_edges)
    print("Test 3 Passed: Edges successfully connected and persisted in workflow definition.")


def test_04_configure_approval():
    """
    Test 4 — Configure approval: Verify Role = FUNCTION_HEAD and APPROVE, REJECT are stored correctly.
    """
    wf_id = test_01_create_workflow_draft()

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "fh_appr", "type": "APPROVAL", "name": "FH Approval", "config": {
                "role": "FUNCTION_HEAD",
                "actions": ["APPROVE", "REJECT"],
                "visibility": {"owner": True, "current_role": True}
            }},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh_appr"},
            {"source": "fh_appr", "target": "end", "condition": "APPROVE"}
        ]
    })

    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    fh_node = next(n for n in get_res.json()["nodes"] if n["id"] == "fh_appr")
    assert fh_node["config"]["role"] == "FUNCTION_HEAD"
    assert "APPROVE" in fh_node["config"]["actions"]
    assert "REJECT" in fh_node["config"]["actions"]
    print("Test 4 Passed: Approval node with FUNCTION_HEAD and [APPROVE, REJECT] verified.")


def test_05_configure_force_approval():
    """
    Test 5 — Configure force approval: Verify RM/RH can be configured with FORCE_APPROVE without frontend hardcoding.
    """
    wf_id = test_01_create_workflow_draft()

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "rm_appr", "type": "APPROVAL", "name": "Risk Manager Approval", "config": {
                "role": "RISK_MANAGER",
                "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]
            }},
            {"id": "rh_appr", "type": "APPROVAL", "name": "Risk Head Approval", "config": {
                "role": "RISK_HEAD",
                "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]
            }},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "rm_appr"},
            {"source": "rm_appr", "target": "rh_appr", "condition": "APPROVE"},
            {"source": "rm_appr", "target": "end", "condition": "FORCE_APPROVE"},
            {"source": "rh_appr", "target": "end", "condition": "APPROVE"}
        ]
    })

    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    rm_node = next(n for n in get_res.json()["nodes"] if n["id"] == "rm_appr")
    rh_node = next(n for n in get_res.json()["nodes"] if n["id"] == "rh_appr")
    assert "FORCE_APPROVE" in rm_node["config"]["actions"]
    assert "FORCE_APPROVE" in rh_node["config"]["actions"]
    print("Test 5 Passed: Dynamic FORCE_APPROVE action configuration verified.")


def test_06_validation_blocks_invalid_workflows():
    """
    Test 6 — Validation: Verify invalid workflows cannot be published (e.g. Approval node without role).
    """
    wf_id = test_01_create_workflow_draft()

    # Invalid: approval node with no role
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "bad_appr", "type": "APPROVAL", "name": "Invalid Approval", "config": {"actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "bad_appr"},
            {"source": "bad_appr", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is False

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 400
    assert "validation errors" in pub_res.text.lower()
    print("Test 6 Passed: Validation correctly identified error and blocked publication.")


def test_07_valid_risk_workflow_passes_validation():
    """
    Test 7 — Valid workflow: Verify the complete multi-tier Risk workflow example passes validation.
    """
    wf_id = test_01_create_workflow_draft()

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Risk Submitted", "config": {"trigger": "SUBMIT"}},
            {"id": "fh", "type": "APPROVAL", "name": "FH Approval", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "rm", "type": "APPROVAL", "name": "RM Approval", "config": {"role": "RISK_MANAGER", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "rh", "type": "APPROVAL", "name": "RH Approval", "config": {"role": "RISK_HEAD", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "draft_rework", "type": "USER_TASK", "name": "Draft Rework", "config": {"role": "RISK_OWNER", "actions": ["RESUBMIT"]}},
            {"id": "approved_end", "type": "END", "name": "Approved", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh", "label": "Submit"},
            {"source": "fh", "target": "rm", "condition": "APPROVE", "label": "Approve"},
            {"source": "fh", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rm", "target": "rh", "condition": "APPROVE", "label": "Approve"},
            {"source": "rm", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rm", "target": "approved_end", "condition": "FORCE_APPROVE", "label": "Force Approve"},
            {"source": "rh", "target": "approved_end", "condition": "APPROVE", "label": "Approve"},
            {"source": "rh", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rh", "target": "approved_end", "condition": "FORCE_APPROVE", "label": "Force Approve"},
            {"source": "draft_rework", "target": "fh", "condition": "RESUBMIT", "label": "Resubmit"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True
    assert len(val_res.json()["errors"]) == 0
    print("Test 7 Passed: Multi-tier Risk Approval Workflow passed all validation checks cleanly.")
    return wf_id


def test_08_save_and_reload():
    """
    Test 8 — Save and reload: Create workflow -> save -> reload -> verify graph is identical.
    """
    wf_id = test_07_valid_risk_workflow_passes_validation()

    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["workflow_id"] == wf_id
    assert len(data["nodes"]) == 6
    assert len(data["edges"]) == 10
    node_ids = {n["id"] for n in data["nodes"]}
    assert node_ids == {"start", "fh", "rm", "rh", "draft_rework", "approved_end"}
    print("Test 8 Passed: Workflow successfully saved and reloaded with identical graph structure.")


def test_09_publish_valid_workflow():
    """
    Test 9 — Publish: Verify valid workflow can be published.
    """
    wf_id = test_07_valid_risk_workflow_passes_validation()

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    data = pub_res.json()
    assert data["version_status"] == "PUBLISHED"
    assert data["status"] == "ACTIVE"
    assert data["published_at"] is not None
    print("Test 9 Passed: Valid workflow successfully published.")


def test_10_existing_workflow_regression():
    """
    Test 10 — Existing workflow regression: Verify an existing workflow instance/API still works after Studio changes.
    """
    defs_res = client.get("/workflow/definitions")
    assert defs_res.status_code in [200, 307]

    tasks_res = client.get("/workflow/tasks")
    assert tasks_res.status_code == 200

    roles_res = client.get("/workflow-studio/roles")
    assert roles_res.status_code == 200
    assert len(roles_res.json()) > 0

    actions_res = client.get("/workflow-studio/actions")
    assert actions_res.status_code == 200
    assert len(actions_res.json()) > 0
    print("Test 10 Passed: Zero regression on existing workflow and runtime endpoints.")


if __name__ == "__main__":
    test_01_create_workflow_draft()
    test_02_add_nodes()
    test_03_connect_nodes()
    test_04_configure_approval()
    test_05_configure_force_approval()
    test_06_validation_blocks_invalid_workflows()
    test_07_valid_risk_workflow_passes_validation()
    test_08_save_and_reload()
    test_09_publish_valid_workflow()
    test_10_existing_workflow_regression()
    print("\nALL 10 PHASE 7 WORKFLOW STUDIO FRONTEND TESTS PASSED SUCCESSFULLY!")
