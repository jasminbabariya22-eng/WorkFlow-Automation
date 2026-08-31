from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class WorkflowCreateRequest(BaseModel):
    spec_id: str
    name: str
    description: Optional[str] = None
    xml_content: Optional[str] = None
    json_content: Optional[str] = None
    tags: Optional[str] = None
    connection_id: Optional[int] = None

class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    xml_content: Optional[str] = None
    json_content: Optional[str] = None
    tags: Optional[str] = None
    connection_id: Optional[int] = None

class ValidationErrorDetail(BaseModel):
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    severity: str  # "Error" or "Warning"
    message: str

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: List[ValidationErrorDetail]

class WorkflowDefinitionResponse(BaseModel):
    id: int
    spec_id: str
    name: Optional[str]
    version: int
    description: Optional[str]
    xml_content: Optional[str]
    json_content: Optional[str]
    is_active: bool
    status: str
    tags: Optional[str]
    connection_id: Optional[int] = None
    created_by: Optional[int]
    created_on: datetime
    updated_on: datetime
    published_on: Optional[datetime]

    class Config:
        orm_mode = True
        from_attributes = True

class WorkflowExecuteRequest(BaseModel):
    initial_variables: Optional[Dict[str, Any]] = {}
    entity_type: Optional[str] = "TestExecution"
    entity_id: Optional[int] = None

