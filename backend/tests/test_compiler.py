import pytest
import json
from app.workflow.runtime.compiler import WorkflowGraphCompiler
from app.workflow.runtime.parser import SpiffBPMNParser

def test_workflow_graph_compiler_basic():
    graph_data = {
        "nodes": [
            {"id": "Start_1", "type": "start", "name": "Start", "position": {"x": 100, "y": 200}, "config": {}},
            {"id": "FH_Task", "type": "approval", "name": "FH Approval", "position": {"x": 300, "y": 200}, "config": {"role_code": "FUNCTION_HEAD", "actions": ["APPROVE", "REJECT"]}},
            {"id": "RM_Task", "type": "approval", "name": "RM Approval", "position": {"x": 550, "y": 200}, "config": {"role_code": "RISK_MANAGER", "actions": ["APPROVE", "REJECT", "FORCE_APPROVE"]}},
            {"id": "End_1", "type": "end_approved", "name": "Approved", "position": {"x": 800, "y": 200}, "config": {}}
        ],
        "edges": [
            {"id": "e1", "source": "Start_1", "target": "FH_Task", "label": ""},
            {"id": "e2", "source": "FH_Task", "target": "RM_Task", "label": "Approve"},
            {"id": "e3", "source": "RM_Task", "target": "End_1", "label": "Approve"}
        ]
    }

    xml = WorkflowGraphCompiler.compile_graph_to_bpmn("TestGraphSpec", graph_data)
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
    assert 'userTask id="FH_Task"' in xml
    assert 'camunda:candidateGroups="FUNCTION_HEAD"' in xml
    assert 'userTask id="RM_Task"' in xml
    assert 'camunda:candidateGroups="RISK_MANAGER"' in xml

    # Verify SpiffBPMNParser compiles the generated XML cleanly
    parser = SpiffBPMNParser()
    spec = parser.parse_xml(xml, "TestGraphSpec")
    assert spec is not None
