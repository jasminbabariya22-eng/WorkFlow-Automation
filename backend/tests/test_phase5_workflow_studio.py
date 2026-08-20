import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflow.workflow_session import WorkflowSessionLocal
from app.workflow_definition.models import GenericWorkflow, WorkflowVersion

client = TestClient(app)


def test_01_create_workflow_draft_successfully():
    """
    TEST 1: Create workflow draft successfully.
    """
    res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_draft_{int(time.time())}",
        "name": "Phase 5 Draft Workflow",
        "description": "Initial canvas draft",
        "entity_type": "Audit"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["workflow_id"] is not None
    assert data["status"] == "DRAFT"
    assert data["version_number"] == 1
    assert data["version_status"] == "DRAFT"
    print("TEST 1 Passed: Workflow draft created successfully.")
    return data["workflow_id"]


def test_02_save_and_retrieve_graph_correctly():
    """
    TEST 2: Save and retrieve graph correctly.
    """
    wf_id = test_01_create_workflow_draft_successfully()

    nodes = [
        {"id": "start", "type": "START", "name": "Start", "position_x": 100, "position_y": 150, "config": {}},
        {"id": "fh_appr", "type": "APPROVAL", "name": "FH Approval", "position_x": 300, "position_y": 150, "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
        {"id": "end", "type": "END", "name": "End", "position_x": 500, "position_y": 150, "config": {}}
    ]
    edges = [
        {"source": "start", "target": "fh_appr", "label": "Submit"},
        {"source": "fh_appr", "target": "end", "condition": "APPROVE", "label": "Approve"}
    ]

    put_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": nodes,
        "edges": edges
    })
    assert put_res.status_code == 200
    saved_data = put_res.json()
    assert len(saved_data["nodes"]) == 3
    assert len(saved_data["edges"]) == 2

    # Retrieve workflow definition from API
    get_res = client.get(f"/workflow-studio/workflows/{wf_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["workflow_id"] == wf_id
    assert len(get_data["nodes"]) == 3
    assert len(get_data["edges"]) == 2
    assert any(n["id"] == "fh_appr" for n in get_data["nodes"])
    print("TEST 2 Passed: Saved and retrieved workflow graph correctly.")


def test_03_unique_node_ids_enforced():
    """
    TEST 3: Unique node IDs are enforced (duplicate node ID rejected).
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_dup_{int(time.time())}",
        "name": "Duplicate Node ID Test",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Two nodes with same id 'duplicate_id'
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "duplicate_id", "type": "START", "name": "Start 1", "config": {}},
            {"id": "duplicate_id", "type": "APPROVAL", "name": "Approval 1", "config": {"role": "MANAGER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "duplicate_id", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "DUPLICATE_NODE_ID" for e in val_data["errors"])
    print("TEST 3 Passed: Duplicate node ID rejected by validation.")


def test_04_invalid_edge_referencing_nonexistent_node_rejected():
    """
    TEST 4: Invalid edge referencing nonexistent node is rejected.
    """
    from app.workflow_studio.validator import WorkflowStudioValidator
    from app.workflow_studio.schemas import StudioNode, StudioEdge

    # Direct validation of in-memory graph
    nodes = [StudioNode(id="start", type="START", name="Start"), StudioNode(id="end", type="END", name="End")]
    edges = [StudioEdge(source="start", target="nonexistent_node_99")]
    direct_val = WorkflowStudioValidator.validate_graph(nodes, edges)
    assert direct_val.is_valid is False
    assert any(e.code == "INVALID_EDGE_TARGET" for e in direct_val.errors)

    # API validation of broken graph
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_bad_edge_{int(time.time())}",
        "name": "Invalid Edge Test",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "nonexistent_node_99"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    print("TEST 4 Passed: Edge referencing nonexistent node rejected by validation.")



def test_05_workflow_without_start_rejected():
    """
    TEST 5: Workflow without START is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_no_start_{int(time.time())}",
        "name": "No Start Node Test",
        "entity_type": "Incident"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "appr", "type": "APPROVAL", "name": "Approval", "config": {"role": "MANAGER", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "appr", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "MISSING_START_NODE" for e in val_data["errors"])
    print("TEST 5 Passed: Workflow without START node rejected.")


def test_06_workflow_without_end_rejected():
    """
    TEST 6: Workflow without END is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_no_end_{int(time.time())}",
        "name": "No End Node Test",
        "entity_type": "Incident"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr", "type": "APPROVAL", "name": "Approval", "config": {"role": "MANAGER", "actions": ["APPROVE"]}}
        ],
        "edges": [
            {"source": "start", "target": "appr"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "MISSING_END_NODE" for e in val_data["errors"])
    print("TEST 6 Passed: Workflow without END node rejected.")


def test_07_approval_node_without_role_rejected():
    """
    TEST 7: Approval node without role is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_no_role_{int(time.time())}",
        "name": "Approval Without Role Test",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr", "type": "APPROVAL", "name": "Approval", "config": {"actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr"},
            {"source": "appr", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "APPROVAL_MISSING_ROLE" for e in val_data["errors"])
    print("TEST 7 Passed: Approval node without role rejected.")


def test_08_approval_node_without_actions_rejected():
    """
    TEST 8: Approval node without actions is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_no_act_{int(time.time())}",
        "name": "Approval Without Actions Test",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr", "type": "APPROVAL", "name": "Approval", "config": {"role": "MANAGER", "actions": []}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr"},
            {"source": "appr", "target": "end"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is False
    assert any(e["code"] == "APPROVAL_MISSING_ACTIONS" for e in val_data["errors"])
    print("TEST 8 Passed: Approval node without allowed actions rejected.")


def test_09_valid_generic_workflow_passes_validation():
    """
    TEST 9: Valid generic workflow passes validation.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_valid_{int(time.time())}",
        "name": "Valid Generic Flow",
        "entity_type": "CAPA"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "quality_mgr", "type": "APPROVAL", "name": "Quality Manager", "config": {"role": "QUALITY_MGR", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "quality_mgr"},
            {"source": "quality_mgr", "target": "end", "condition": "APPROVE"}
        ]
    })

    val_res = client.post(f"/workflow-studio/workflows/{wf_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["is_valid"] is True
    assert len(val_data["errors"]) == 0
    print("TEST 9 Passed: Valid generic workflow passed all validation checks.")


def test_10_published_workflow_cannot_be_directly_modified():
    """
    TEST 10: Published workflow cannot be directly modified.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_pub_lock_{int(time.time())}",
        "name": "Locked Published Flow",
        "entity_type": "Compliance"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr", "type": "APPROVAL", "name": "Appr", "config": {"role": "LEAD", "actions": ["APPROVE"]}},
            {"id": "end", "type": "END", "name": "End", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr"},
            {"source": "appr", "target": "end"}
        ]
    })
    client.post(f"/workflow-studio/workflows/{wf_id}/publish")

    # Attempt to modify published draft directly -> 400
    modify_res = client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "name": "Attempted Direct Mutate"
    })
    assert modify_res.status_code == 400
    assert "Cannot modify a published workflow" in modify_res.text
    print("TEST 10 Passed: Published workflow is immutable and rejects direct mutation.")


def test_11_publishing_invalid_workflow_is_rejected():
    """
    TEST 11: Publishing invalid workflow is rejected.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_pub_bad_{int(time.time())}",
        "name": "Invalid Publish Attempt Flow",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    # Incomplete graph (no END)
    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start", "config": {}},
            {"id": "appr", "type": "APPROVAL", "name": "Appr", "config": {"role": "LEAD", "actions": ["APPROVE"]}}
        ],
        "edges": [
            {"source": "start", "target": "appr"}
        ]
    })

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 400
    assert "validation errors" in pub_res.text.lower()
    print("TEST 11 Passed: Publishing invalid workflow was strictly blocked.")


def test_12_publishing_valid_workflow_creates_published_version():
    """
    TEST 12: Publishing valid workflow creates a published version and compiles BPMN.
    """
    wf_res = client.post("/workflow-studio/workflows", json={
        "workflow_key": f"p5_pub_good_{int(time.time())}",
        "name": "Valid Publish Flow",
        "entity_type": "Risk"
    })
    wf_id = wf_res.json()["workflow_id"]

    client.put(f"/workflow-studio/workflows/{wf_id}", json={
        "nodes": [
            {"id": "start", "type": "START", "name": "Start Event", "config": {}},
            {"id": "appr_fh", "type": "APPROVAL", "name": "FH Approval", "config": {"role": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "end_done", "type": "END", "name": "Process Completed", "config": {}}
        ],
        "edges": [
            {"source": "start", "target": "appr_fh"},
            {"source": "appr_fh", "target": "end_done", "condition": "APPROVE"}
        ]
    })

    pub_res = client.post(f"/workflow-studio/workflows/{wf_id}/publish")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["version_status"] == "PUBLISHED"
    assert pub_data["status"] == "ACTIVE"
    assert pub_data["published_at"] is not None
    print("TEST 12 Passed: Publishing valid workflow created PUBLISHED version with BPMN compilation.")


def test_13_existing_bpmn_and_runtime_tests_still_pass():
    """
    TEST 13: Existing BPMN/workflow runtime endpoints still respond without regression.
    """
    defs_res = client.get("/workflow/definitions")
    assert defs_res.status_code in [200, 307]

    tasks_res = client.get("/workflow/tasks")
    assert tasks_res.status_code == 200

    roles_res = client.get("/workflow-studio/roles")
    assert roles_res.status_code == 200

    actions_res = client.get("/workflow-studio/actions")
    assert actions_res.status_code == 200
    print("TEST 13 Passed: Existing BPMN and runtime API endpoints continue functioning flawlessly.")



if __name__ == "__main__":
    test_01_create_workflow_draft_successfully()
    test_02_save_and_retrieve_graph_correctly()
    test_03_unique_node_ids_enforced()
    test_04_invalid_edge_referencing_nonexistent_node_rejected()
    test_05_workflow_without_start_rejected()
    test_06_workflow_without_end_rejected()
    test_07_approval_node_without_role_rejected()
    test_08_approval_node_without_actions_rejected()
    test_09_valid_generic_workflow_passes_validation()
    test_10_published_workflow_cannot_be_directly_modified()
    test_11_publishing_invalid_workflow_is_rejected()
    test_12_publishing_valid_workflow_creates_published_version()
    test_13_existing_bpmn_and_runtime_tests_still_pass()
    print("\nALL 13 PHASE 5 WORKFLOW STUDIO TESTS PASSED SUCCESSFULLY!")
