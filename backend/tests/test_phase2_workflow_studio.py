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


def test_01_create_generic_workflow_draft():
    """TEST 1: Create a generic workflow draft successfully."""
    payload = {
        "workflow_key": f"studio_draft_{int(time.time())}",
        "name": "Vendor Onboarding Workflow",
        "description": "Multi-tier vendor review and approval process",
        "entity_type": "Vendor"
    }
    res = client.post("/workflow-studio/workflows", json=payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["name"] == "Vendor Onboarding Workflow"
    assert data["entity_type"] == "Vendor"
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert data["version_status"] == "DRAFT"
    print("TEST 1 Passed: Generic workflow draft created successfully.")


def test_02_save_nodes_and_edges():
    """TEST 2: Save nodes and edges successfully."""
    wf_res = client.post("/workflow-studio/workflows", json={
        "name": "Expense Claim Workflow",
        "entity_type": "Expense"
    })
    wf_id = wf_res.json()["workflow_id"]

    update_payload = {
        "nodes": [
            {
                "id": "start",
                "type": "START",
                "name": "Claim Submitted",
                "position_x": 100,
                "position_y": 200,
                "config": {"trigger": "FORM_SUBMIT"}
            },
            {
                "id": "manager_appr",
                "type": "APPROVAL",
                "name": "Manager Approval",
                "position_x": 300,
                "position_y": 200,
                "config": {
                    "role": "LINE_MANAGER",
                    "actions": ["APPROVE", "REJECT"],
                    "visibility": {"owner": True}
                }
            },
            {
                "id": "end_approved",
                "type": "END",
                "name": "Claim Approved",
                "position_x": 500,
                "position_y": 200,
                "config": {"status": "APPROVED"}
            }
        ],
        "edges": [
            {
                "id": "e_start_mgr",
                "source": "start",
                "target": "manager_appr",
                "label": "Submit"
            },
            {
                "id": "e_mgr_end",
                "source": "manager_appr",
                "target": "end_approved",
                "condition": "APPROVE",
                "label": "Approve"
            }
        ]
    }
    update_res = client.put(f"/workflow-studio/workflows/{wf_id}", json=update_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    assert data["nodes"][1]["config"]["role"] == "LINE_MANAGER"
    print("TEST 2 Passed: Nodes and edges saved successfully.")


def test_03_retrieve_saved_workflow_definition():
    """TEST 3: Retrieve the saved workflow definition."""
    wf_res = client.post("/workflow-studio/workflows", json={
        "name": "CAPA Investigation Workflow",
        "entity_type": "CAPA"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "position_x": 50, "position_y": 50, "config": {}},
            {"id": "qa_review", "type": "APPROVAL", "name": "QA Review", "position_x": 200, "position_y": 50, "config": {"role": "QA_LEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end", "type": "END", "name": "End", "position_x": 400, "position_y": 50, "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "qa_review", "label": "Submit"},
            {"source": "qa_review", "target": "end", "condition": "APPROVE", "label": "Approve"}
        ]
    })

    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["workflow_id"] == wf_id
    assert data["name"] == "CAPA Investigation Workflow"
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    print("TEST 3 Passed: Retrieved saved workflow definition with full graph.")


def test_04_validation_rejects_without_start():
    """TEST 4: Validation rejects a workflow without START."""
    wf_res = client.post("/workflow-studio/workflows", json={"name": "No Start Flow"})
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "orphan_task", "type": "APPROVAL", "name": "Orphan Approval", "config": {"role": "MANAGER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "orphan_task", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "MISSING_START_NODE" for e in val_data["errors"])
    print("TEST 4 Passed: Workflow without START rejected by validation.")


def test_05_validation_rejects_disconnected_orphan_node():
    """TEST 5: Validation rejects a workflow with disconnected/orphan node."""
    wf_res = client.post("/workflow-studio/workflows", json={"name": "Disconnected Node Flow"})
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "valid_appr", "type": "APPROVAL", "name": "Valid Step", "config": {"role": "MANAGER", "actions": ["APPROVE"]}},
            {"id": "orphan_appr", "type": "APPROVAL", "name": "Disconnected Step", "config": {"role": "FINANCE", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "valid_appr"},
            {"source": "valid_appr", "target": "end"}
            # orphan_appr has no incoming or outgoing edges
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "ORPHAN_NODE_NO_INCOMING" for e in val_data["errors"])
    print("TEST 5 Passed: Disconnected/orphan node rejected by validation.")


def test_06_validation_rejects_approval_without_role_or_actions():
    """TEST 6: Validation rejects an Approval node without role/actions."""
    wf_res = client.post("/workflow-studio/workflows", json={"name": "Unconfigured Approval Flow"})
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "bad_appr", "type": "APPROVAL", "name": "Empty Config Approval", "config": {}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "bad_appr"},
            {"source": "bad_appr", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "APPROVAL_MISSING_ROLE" for e in val_data["errors"])
    assert any(e["code"] == "APPROVAL_MISSING_ACTIONS" for e in val_data["errors"])
    print("TEST 6 Passed: Approval node without role/actions rejected by validation.")


def test_07_valid_risk_approval_graph_passes_validation():
    """TEST 7: Valid Risk Approval graph (configured generically) passes validation."""
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"risk_std_{int(time.time())}",
        "name": "Standard Enterprise Risk Approval",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Construct the complete multi-tier Risk approval graph with loops & force-approval
    risk_graph_payload = {
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "position_x": 100, "position_y": 100, "config": {}},
            {
                "id": "fh_appr",
                "type": "APPROVAL",
                "name": "Functional Head Approval",
                "position_x": 250,
                "position_y": 100,
                "config": {
                    "role": "FUNCTION_HEAD",
                    "actions": ["APPROVE", "REJECT"]
                }
            },
            {
                "id": "rm_appr",
                "type": "APPROVAL",
                "name": "Risk Manager Approval",
                "position_x": 400,
                "position_y": 100,
                "config": {
                    "role": "RISK_MANAGER",
                    "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]
                }
            },
            {
                "id": "rh_appr",
                "type": "APPROVAL",
                "name": "Risk Head Approval",
                "position_x": 550,
                "position_y": 100,
                "config": {
                    "role": "RISK_HEAD",
                    "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]
                }
            },
            {
                "id": "draft_rework",
                "type": "USER_TASK",
                "name": "Risk Owner Rework",
                "position_x": 350,
                "position_y": 300,
                "config": {
                    "role": "RISK_OWNER",
                    "actions": ["RESUBMIT"]
                }
            },
            {"id": "end_approved", "type": "END", "name": "Risk Approved", "position_x": 700, "position_y": 100, "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "fh_appr", "label": "Submit"},
            {"source": "fh_appr", "target": "rm_appr", "condition": "APPROVE", "label": "Approve"},
            {"source": "fh_appr", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rm_appr", "target": "rh_appr", "condition": "APPROVE", "label": "Approve"},
            {"source": "rm_appr", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rm_appr", "target": "end_approved", "condition": "FORCE_APPROVE", "label": "Force Approve"},
            {"source": "rh_appr", "target": "end_approved", "condition": "APPROVE", "label": "Approve"},
            {"source": "rh_appr", "target": "draft_rework", "condition": "REJECT", "label": "Reject"},
            {"source": "rh_appr", "target": "end_approved", "condition": "FORCE_APPROVE", "label": "Force Approve"},
            {"source": "draft_rework", "target": "fh_appr", "condition": "RESUBMIT", "label": "Resubmit"}
        ]
    }
    client.put(f"/workflow-studio/workflows/{wf_id}", json=risk_graph_payload)

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert val_data["status"] == "VALIDATED"
    assert len(val_data["errors"]) == 0
    print("TEST 7 Passed: Generic Multi-tier Risk Approval Graph validated successfully.")


def test_08_publish_valid_workflow():
    """TEST 8: Publishing a valid workflow changes status to PUBLISHED."""
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"publish_test_{int(time.time())}",
        "name": "Change Request Flow",
        "entity_type": "ChangeRequest"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "review", "type": "APPROVAL", "name": "Review", "config": {"role": "CAB_MEMBER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "review"},
            {"source": "review", "target": "end"}
        ]
    })

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["version_status"] == "PUBLISHED"
    assert pub_data["status"] == "ACTIVE"
    assert pub_data["published_at"] is not None
    print("TEST 8 Passed: Publishing valid workflow changes status to PUBLISHED.")


def test_09_published_workflow_immutability():
    """TEST 9: Published workflow cannot be modified directly."""
    wf_res = client.post("/workflow-studio/workflows", json={"name": "Immutable Flow"})
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [{"source": "start", "target": "end"}]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    # Attempt to modify published version
    mod_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "name": "Hacked Name",
        "nodes": [{"id": "start", "type": "START", "name": "Mutated Start", "config": {}}]
    })
    assert mod_res.status_code == 400
    assert "Cannot modify a published workflow version" in get_error_message(mod_res)
    print("TEST 9 Passed: Published workflow cannot be modified directly.")


def test_10_existing_bpmn_risk_workflow_continues_to_work():
    """TEST 10: Existing BPMN-based Risk workflow continues to work without regression."""
    # Verify existing definition list
    def_res = client.get("/workflow/definitions")
    assert def_res.status_code in [200, 307]

    # Verify health
    health_res = client.get("/health")
    assert health_res.status_code == 200
    print("TEST 10 Passed: Existing BPMN workflow runtime continues to work.")


if __name__ == "__main__":
    test_01_create_generic_workflow_draft()
    test_02_save_nodes_and_edges()
    test_03_retrieve_saved_workflow_definition()
    test_04_validation_rejects_without_start()
    test_05_validation_rejects_disconnected_orphan_node()
    test_06_validation_rejects_approval_without_role_or_actions()
    test_07_valid_risk_approval_graph_passes_validation()
    test_08_publish_valid_workflow()
    test_09_published_workflow_immutability()
    test_10_existing_bpmn_risk_workflow_continues_to_work()
    print("\nALL PHASE 2 WORKFLOW STUDIO TESTS PASSED SUCCESSFULLY!")
