from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    workflow_id: Optional[int] = Field(None, description="Workflow Definition ID (BPMN definition ID or GenericWorkflow workflow_id)")
    workflow_key: Optional[str] = Field(None, description="Specification ID or Workflow Key")
    entity_type: Optional[str] = Field("generic_job", description="Associated entity type")
    entity_id: Optional[int] = Field(None, description="Associated business entity record ID (auto-generated if omitted)")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Initial payload and variables for the job")
    title: Optional[str] = Field(None, description="Optional title or label for this execution job")
    async_execution: bool = Field(False, description="Whether to dispatch execution asynchronously to the background worker pool")


class JobActionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for the lifecycle action (pause, stop, resume)")


class JobRestartRequest(BaseModel):
    variables: Optional[Dict[str, Any]] = Field(None, description="Optional updated variables (merges with original if provided)")
    reset_history: bool = Field(False, description="Whether to purge previous step history")


class JobSummaryResponse(BaseModel):
    job_id: int
    entity_type: str
    entity_id: int
    workflow_id: Optional[int]
    workflow_name: str
    workflow_key: str
    status: str
    current_node_key: Optional[str]
    progress_percent: float
    started_on: datetime
    completed_on: Optional[datetime]


class JobStatusResponse(BaseModel):
    job_id: int
    entity_type: str
    entity_id: int
    workflow_id: Optional[int]
    workflow_name: str
    workflow_key: str
    status: str
    current_node_key: Optional[str]
    current_node: Optional[Dict[str, Any]]
    progress_percent: float
    pending_tasks: List[Dict[str, Any]]
    variables: Dict[str, Any]
    started_on: datetime
    completed_on: Optional[datetime]
    duration_seconds: Optional[float]


class JobHistoryResponse(BaseModel):
    job_id: int
    status: str
    activities: List[Dict[str, Any]]
    transitions: List[Dict[str, Any]]
