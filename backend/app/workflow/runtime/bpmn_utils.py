import xml.etree.ElementTree as ET
from typing import Optional, Dict

def get_candidate_role_from_xml(bpmn_xml: str, task_spec_id: str) -> Optional[str]:
    """
    Parses a BPMN 2.0 XML string and extracts the candidateGroups configuration
    for a given User Task specification ID dynamically.
    """
    if not bpmn_xml or not task_spec_id:
        return None
    try:
        root = ET.fromstring(bpmn_xml)
        # Scan for userTask nodes using the standard BPMN namespace
        for user_task in root.findall('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}userTask'):
            if user_task.attrib.get('id') == task_spec_id:
                # Find the candidateGroups attribute (handles prefixed camunda namespaces)
                for key, val in user_task.attrib.items():
                    if 'candidateGroups' in key:
                        return val
    except Exception:
        pass
    return None


def get_extension_properties_from_xml(bpmn_xml: str, task_spec_id: str) -> Dict[str, str]:
    """
    Parses a BPMN 2.0 XML string and extracts all camunda:property name-value mappings
    defined inside extensionElements for a specific node ID dynamically.
    """
    properties = {}
    if not bpmn_xml or not task_spec_id:
        return properties
    try:
        root = ET.fromstring(bpmn_xml)
        element = root.find(f".//*[@id='{task_spec_id}']")
        if element is not None:
            extensions = element.find('.//{http://www.omg.org/spec/BPMN/20100524/MODEL}extensionElements')
            if extensions is not None:
                # Standard properties container
                camunda_props = extensions.find('.//{http://camunda.org/schema/1.0/bpmn}properties')
                if camunda_props is not None:
                    prop_list = camunda_props.findall('.//{http://camunda.org/schema/1.0/bpmn}property')
                    for p in prop_list:
                        name = p.attrib.get('name')
                        value = p.attrib.get('value')
                        if name:
                            properties[name] = value
                else:
                    # Fallback scan for child attributes with name/value keys
                    for prop in extensions.findall('.//*[@name]'):
                        name = prop.attrib.get('name')
                        value = prop.attrib.get('value')
                        if name:
                            properties[name] = value
    except Exception:
        pass
    return properties

