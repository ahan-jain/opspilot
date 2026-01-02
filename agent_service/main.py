from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json

from database import get_db, engine
from models import Base, Run, Step, ToolCall, RunStatus
from schemas import (
    RunCreate, RunResponse, StepResponse, ToolCallResponse,
    ToolsListResponse, ToolInfo, ExecutionResponse, ErrorResponse
)
from tools import list_tools, get_tool, validate_tool_inputs, requires_approval

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OpsPilot Agent API",
    description="LLM-powered task orchestration with explicit state machine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/tools", response_model=ToolsListResponse)
def get_tools():
    tools_dict = list_tools()
    tools_list = [
        ToolInfo(
            name=name,
            description=config["description"],
            schema=config["schema"],
            requires_approval=config["requires_approval"],
            category=config["category"]
        )
        for name, config in tools_dict.items()
    ]
    
    return ToolsListResponse(tools=tools_list, count=len(tools_list))


@app.post("/runs", response_model=RunResponse, status_code=201)
def create_run(run_data: RunCreate, db: Session = Depends(get_db)):

    run = Run(
        goal=run_data.goal,
        status=RunStatus.RUNNING
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    return run

@app.get("/runs", response_model=List[RunResponse])
def list_runs(
    limit: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):

    query = db.query(Run).order_by(Run.created_at.desc())
    
    if status:
        try:
            status_enum = RunStatus(status)
            query = query.filter(Run.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    
    runs = query.limit(limit).all()
    return runs

@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):

    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    
    return run

@app.post("/runs/{run_id}/execute", response_model=ExecutionResponse)
def execute_run(run_id: int, db: Session = Depends(get_db)):

    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    
    if run.status != RunStatus.RUNNING:
        raise HTTPException(
            400,
            f"Cannot execute run in status: {run.status.value}"
        )
    
    # TODO: Agent orchestration will go here (Day 5-6)
    return ExecutionResponse(
        run_id=run_id,
        status="started",
        message="Execution queued (agent not yet implemented)",
        current_step=None
    )

@app.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db)):

    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    
    db.delete(run)
    db.commit()
    
    return None


@app.get("/runs/{run_id}/steps", response_model=List[StepResponse])

def get_run_steps(run_id: int, db: Session = Depends(get_db)):
    steps = db.query(Step)\
        .filter(Step.run_id == run_id)\
        .order_by(Step.step_number)\
        .all()
    
    return steps

@app.post("/runs/{run_id}/steps/{step_id}/approve")

def approve_step(
    run_id: int,
    step_id: int,
    db: Session = Depends(get_db)
):
    step = db.query(Step).filter(
        Step.id == step_id,
        Step.run_id == run_id
    ).first()
    
    if not step:
        raise HTTPException(404, "Step not found")
    
    if step.state != StepState.NEEDS_APPROVAL:
        raise HTTPException(
            400,
            f"Step is not awaiting approval (current state: {step.state.value})"
        )
    
    # TODO: Resume execution (Day 6)
    return {
        "run_id": run_id,
        "step_id": step_id,
        "status": "approved",
        "message": "Approval recorded (execution resumption not yet implemented)"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "opspilot-agent"}

@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    return ErrorResponse(
        error="Validation Error",
        detail=str(exc),
        status_code=400
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)