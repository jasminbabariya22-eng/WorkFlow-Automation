from SpiffWorkflow.bpmn.parser import BpmnParser, BpmnValidator
from SpiffWorkflow.specs.WorkflowSpec import WorkflowSpec as BpmnWorkflowSpec
from SpiffWorkflow.exceptions import WorkflowException

class SpiffBPMNParser:
    """
    Responsible for parsing BPMN 2.0 XML specifications and compiling them 
    into executable WorkflowSpec models.
    """
    def __init__(self):
        # Initialize standard parser with validator
        self.parser = BpmnParser(validator=BpmnValidator())

    def parse_xml(self, xml_content: str, spec_id: str) -> BpmnWorkflowSpec:
        """
        Parses a BPMN XML string and registers it with the given spec_id.
        """
        try:
            import re
            clean_xml = re.sub(r'^<\?xml.*?\?>', '', xml_content).strip()
            if spec_id not in self.parser.get_process_ids():
                self.parser.add_bpmn_str(clean_xml, filename=f"{spec_id}.bpmn")
            return self.parser.get_spec(spec_id)
        except Exception as e:
            raise WorkflowException(f"Failed to parse BPMN XML for spec_id '{spec_id}': {str(e)}")

    def parse_file(self, file_path: str, spec_id: str) -> BpmnWorkflowSpec:
        """
        Parses a BPMN XML file from the filesystem.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                xml_content = f.read()
            return self.parse_xml(xml_content, spec_id)
        except Exception as e:
            raise WorkflowException(f"Failed to load BPMN file at '{file_path}': {str(e)}")
