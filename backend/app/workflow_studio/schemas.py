from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# 1. STUDIO NODE SCHEMA
# ==========================================

class StudioNode(BaseModel):
    id: str = Field(..., description="Unique node identifier on canvas, e.g. 'start', 'fh_approval', 'end'")
    type: str = Field(..., description="Generic node type: START, END, APPROVAL, CONDITION, ACTION, EMAIL, USER_TASK, WAIT, WEBHOOK")
    name: str = Field(..., description="Display label on canvas")
    position_x: float = Field(default=0.0, description="X canvas coordinate")
    position_y: float = Field(default=0.0, description="Y canvas coordinate")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters (role, actions, expression, etc.)")


# ==========================================
# 2. STUDIO EDGE SCHEMA
# ==========================================

class StudioEdge(BaseModel):
    id: Optional[str] = Field(None, description="Optional unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Action code or condition expression, e.g. 'APPROVE', 'REJECT', 'amount > 10000'")
    label: Optional[str] = Field(None, description="Display label on connection wire, e.g. 'Approve', 'Reject', 'Submit'")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional edge metadata")


# ==========================================
# 3. WORKFLOW STUDIO PAYLOADS
# ==========================================

class StudioWorkflowCreate(BaseModel):
    workflow_key: Optional[str] = Field(None, description="Unique slug for workflow. Auto-generated if omitted.")
    name: str = Field(..., description="Human-friendly name of the workflow")
    description: Optional[str] = None
    entity_type: Optional[str] = Field(None, description="Generic entity type metadata, e.g. 'Risk', 'Audit', 'Incident'")
    nodes: List[StudioNode] = Field(default_factory=list, description="List of nodes on canvas")
    edges: List[StudioEdge] = Field(default_factory=list, description="List of connections on canvas")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional workflow metadata")


class StudioWorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    nodes: Optional[List[StudioNode]] = None
    edges: Optional[List[StudioEdge]] = None
    metadata: Optional[Dict[str, Any]] = None


class StudioWorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_id: int
    workflow_key: str
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    status: str  # DRAFT, ACTIVE, ARCHIVED
    version_id: int
    version_number: int
    version_status: str  # DRAFT, VALIDATED, PUBLISHED, ARCHIVED
    nodes: List[StudioNode] = Field(default_factory=list)
    edges: List[StudioEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None


class StudioWorkflowListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_id: int
    workflow_key: str
    name: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    status: str
    latest_version: int
    published_version: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# ==========================================
# 4. STUDIO VALIDATION SCHEMA
# ==========================================

class StudioValidationError(BaseModel):
    code: str
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    severity: str = "ERROR"  # ERROR, WARNING


class StudioValidationResponse(BaseModel):
    is_valid: bool
    status: str  # VALIDATED, INVALID
    errors: List[StudioValidationError] = Field(default_factory=list)
    warnings: List[StudioValidationError] = Field(default_factory=list)
