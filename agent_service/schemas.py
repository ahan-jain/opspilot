from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import RunStatus, StepState, ToolCallStatus

class RunCreate(BaseModel):
    goal: str = Field(
        ...,
        description="User's goal or task description",
        min_length=10,
        max_length=500,
        example="Investigate error spike in the last hour and create ticket if needed"
    )

class StepCreate(BaseModel):
    run_id: int
    state: StepState
    step_number: int
    reasoning: Optional[str] = None

class ToolCallCreate(BaseModel):
    step_id: int
    tool_name: str = Field(..., description="Name of tool to execute")
    inputs: Dict[str, Any] = Field(..., description="Tool input parameters")

class ApprovalRequest(BaseModel):
    approved: bool = Field(..., description="Whether to approve the action")
    reason: Optional[str] = Field(None, description="Optional reason for approval/rejection")


class ToolCallResponse(BaseModel):
    id: int
    step_id: int
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]]
    status: ToolCallStatus
    error_message: Optional[str]
    created_at: datetime
    executed_at: Optional[datetime]
    
    class Config:
        from_attributes = True  # For SQLAlchemy models

class StepResponse(BaseModel):
    id: int
    run_id: int
    state: StepState
    step_number: int
    reasoning: Optional[str]
    created_at: datetime
    tool_calls: List[ToolCallResponse] = []
    
    class Config:
        from_attributes = True

class RunResponse(BaseModel):
    id: int
    goal: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    steps: List[StepResponse] = []
    
    class Config:
        from_attributes = True

class ToolInfo(BaseModel):
    name: str
    description: str
    schema: Dict[str, Any]
    requires_approval: bool
    category: str

class ToolsListResponse(BaseModel):
    tools: List[ToolInfo]
    count: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int

class ExecutionResponse(BaseModel):
    run_id: int
    status: str
    message: str
    current_step: Optional[int] = None