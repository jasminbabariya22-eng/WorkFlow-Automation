import pytest
from app.workflow.runtime.parser import SpiffBPMNParser

def test_parser_valid_xml():
    parser = SpiffBPMNParser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                      id="Definitions_1"
                      targetNamespace="http://bpmn.io/schema/bpmn">
      <bpmn:process id="TestProcess" isExecutable="true">
        <bpmn:startEvent id="StartEvent_1"/>
      </bpmn:process>
    </bpmn:definitions>
    """
    spec = parser.parse_xml(xml_content, "TestProcess")
    assert spec is not None
    assert spec.name == "TestProcess"

def test_parser_invalid_xml():
    parser = SpiffBPMNParser()
    with pytest.raises(Exception):
        parser.parse_xml("invalid xml string", "TestProcess")
