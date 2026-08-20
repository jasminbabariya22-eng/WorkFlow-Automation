from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# 1. NODE SCHEMAS
# ==========================================

class WorkflowNodeBase(BaseModel):
    node_key: str = Field(..., description="Unique key for node within the workflow version, e.g. 'start', 'fh_approval', 'end'")
    node_type: str = Field(..., description="Type of node: START, END, APPROVAL, CONDITION, ACTION, EMAIL, FORM, WAIT, WEBHOOK")
    name: str = Field(..., description="Display label for the node")
    description: Optional[str] = None
    position_x: float = Field(default=0.0, description="X coordinate on visual canvas")
    position_y: float = Field(default=0.0, description="Y coordinate on visual canvas")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Flexible JSON configuration object")
    is_active: bool = True


class WorkflowNodeCreate(WorkflowNodeBase):
    pass


class WorkflowNodeUpdate(BaseModel):
    node_key: Optional[str] = None
    node_type: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkflowNodeResponse(WorkflowNodeBase):
    model_config = ConfigDict(from_attributes=True)

    node_id: int
    workflow_version_id: int
    created_at: datetime
    updated_at: datetime


# ==========================================
# 2. CONNECTION SCHEMAS
# ==========================================

class WorkflowConnectionBase(BaseModel):
    source_node_id: int = Field(..., description="ID of source node")
    target_node_id: int = Field(..., description="ID of target node")
    connection_key: Optional[str] = Field(None, description="Optional connection identifier")
    condition: Optional[str] = Field(None, description="Optional condition expression or action code, e.g. 'APPROVE', 'REJECT', 'amount > 10000'")
    label: Optional[str] = Field(None, description="Display label on connection wire, e.g. 'Approve', 'Reject', 'Submit'")
    metadata_json: Dict[str, Any] = Field(default_factory=dict, description="Optional connection metadata")


class WorkflowConnectionCreate(WorkflowConnectionBase):
    pass


class WorkflowConnectionResponse(WorkflowConnectionBase):
    model_config = ConfigDict(from_attributes=True)

    connection_id: int
    workflow_version_id: int
    created_at: datetime


# ==========================================
# 3. VERSION SCHEMAS
# ==========================================

class WorkflowVersionCreate(BaseModel):
    version_number: Optional[int] = Field(None, description="Optional explicit version number. If omitted, increments automatically.")
    definition_metadata: Dict[str, Any] = Field(default_factory=dict, description="Version metadata")
    clone_from_version_id: Optional[int] = Field(None, description="Optional version ID to clone nodes and connections from")


class WorkflowVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_version_id: int
    workflow_id: int
    version_number: int
    status: str  # DRAFT, VALIDATED, PUBLISHED, ARCHIVED
    definition_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by: Optional[int] = None
    created_at: datetime
    published_at: Optional[datetime] = None


class WorkflowVersionDetailResponse(WorkflowVersionResponse):
    nodes: List[WorkflowNodeResponse] = Field(default_factory=list)
    connections: List[WorkflowConnectionResponse] = Field(default_factory=list)


# ==========================================
# 4. WORKFLOW DEFINITION SCHEMAS
# ==========================================

class WorkflowCreate(BaseModel):
    workflow_key: str = Field(..., description="Unique slug for the workflow, e.g. 'risk_approval', 'purchase_order_flow'")
    name: str = Field(..., description="Human-friendly name of the workflow")
    description: Optional[str] = None
    entity_type: Optional[str] = Field(None, description="Generic entity metadata, e.g. 'Risk', 'Audit', 'Incident', 'Purchase'")


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    status: Optional[str] = None  # DRAFT, ACTIVE, ARCHIVED


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_id: int
    workflow_key: str
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime
    latest_version: Optional[int] = None
    published_version: Optional[int] = None


class WorkflowDetailResponse(WorkflowResponse):
    versions: List[WorkflowVersionResponse] = Field(default_factory=list)


# ==========================================
# 5. VALIDATION SCHEMAS
# ==========================================

class ValidationErrorItem(BaseModel):
    code: str
    message: str
    node_id: Optional[int] = None
    connection_id: Optional[int] = None
    severity: str = "ERROR"  # ERROR, WARNING


class WorkflowValidationResponse(BaseModel):
    is_valid: bool
    status: str  # VALIDATED, INVALID
    errors: List[ValidationErrorItem] = Field(default_factory=list)
    warnings: List[ValidationErrorItem] = Field(default_factory=list)
