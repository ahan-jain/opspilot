from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import json
import os
from agent import Agent
import uvicorn

from database import get_db, engine, SessionLocal
from models import Base, Run, Step, ToolCall, RunStatus, ToolCallStatus
from schemas import (
    RunCreate, RunResponse, StepResponse, ToolCallResponse,
    ToolsListResponse, ToolInfo, ExecutionResponse, ErrorResponse, ApprovalRequest
)
from tools import list_tools, get_tool, validate_tool_inputs, requires_approval
from state_machine import State
from datetime import datetime

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

@app.post("/runs/{run_id}/execute")
def execute_run(run_id: int):
    """Execute a run with the agent."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(404, "Run not found")
        
        if run.status == RunStatus.DONE:
            raise HTTPException(400, "Run already completed")
        
        if run.status == RunStatus.FAILED:
            raise HTTPException(400, "Run already failed")
        
        # Update status to running
        run.status = RunStatus.RUNNING
        db.commit()
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(500, "ANTHROPIC_API_KEY not set in environment")
        
        # Create and run agent
        agent = Agent(run_id=run_id, api_key=api_key)
        agent.run_agent()
        
        # Return final status
        db.refresh(run)
        return {
            "run_id": run_id,
            "status": run.status.value,
            "message": "Execution completed"
        }
    
    except Exception as e:
        # Handle errors
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.status = RunStatus.FAILED
            db.commit()
        raise HTTPException(500, f"Execution failed: {str(e)}")
    
    finally:
        db.close()

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

@app.get("/runs/{run_id}")  
def get_run(run_id: int):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        
        if not run:
            raise HTTPException(404, f"Run {run_id} not found")
        
        return {
            "id": run.id,
            "goal": run.goal,
            "status": run.status.value,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat() if run.updated_at else None
        }
    finally:
        db.close()

@app.get("/runs/{run_id}/steps")
def get_run_steps(run_id: int):
    db = SessionLocal()
    try:
        steps = db.query(Step).filter(Step.run_id == run_id).order_by(Step.step_number).all()
        
        result = []
        for step in steps:
            step_data = {
                "step_id": step.id,
                "run_id": step.run_id,
                "state": step.state,
                "step_number": step.step_number,
                "reasoning": step.reasoning,
                "created_at": step.created_at,
                "tool_calls": []
            }
            
            for tc in step.tool_calls:
                tool_call_data = {
                    "tool_call_id": tc.id,
                    "tool_name": tc.tool_name,
                    "inputs": json.loads(tc.inputs) if tc.inputs else {},  
                    "outputs": json.loads(tc.outputs) if tc.outputs else {},  
                    "status": tc.status.value if hasattr(tc.status, 'value') else tc.status,
                    "executed_at": tc.executed_at,
                    "error_message": tc.error_message
                }
                step_data["tool_calls"].append(tool_call_data)
            
            result.append(step_data)
        
        return result
    
    finally:
        db.close()

@app.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    
    db.delete(run)
    db.commit()
    
    return None

@app.post("/runs/{run_id}/approve")
def approve_run(run_id: int, approval: ApprovalRequest):
    """Approve or reject a run requiring approval."""
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(404, "Run not found")

        if run.status != RunStatus.NEEDS_APPROVAL:
            raise HTTPException(400, "Run is not awaiting approval")

        latest_step = db.query(Step)\
            .filter(Step.run_id == run_id)\
            .order_by(Step.step_number.desc(), Step.created_at.desc())\
            .first()

        if approval.approved:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(500, "ANTHROPIC_API_KEY not set")

            # Find the pending tool call that is awaiting approval
            pending_tool_call = db.query(ToolCall)\
                .join(Step, ToolCall.step_id == Step.id)\
                .filter(Step.run_id == run_id)\
                .filter(ToolCall.status == ToolCallStatus.PENDING)\
                .order_by(ToolCall.created_at.desc())\
                .first()

            if not pending_tool_call:
                raise HTTPException(400, "No pending tool call awaiting approval")

            if not requires_approval(pending_tool_call.tool_name):
                raise HTTPException(
                    400,
                    f"Pending tool call {pending_tool_call.tool_name} does not require approval"
                )

            try:
                tool_func = get_tool(pending_tool_call.tool_name)
                inputs = json.loads(pending_tool_call.inputs) if pending_tool_call.inputs else {}
                result = tool_func(**inputs)

                pending_tool_call.outputs = json.dumps(result)
                pending_tool_call.status = ToolCallStatus.SUCCESS
                pending_tool_call.executed_at = datetime.utcnow()

                run.status = RunStatus.RUNNING
                db.commit()

            except Exception as e:
                run.status = RunStatus.FAILED
                db.commit()
                raise HTTPException(500, f"Approved tool execution failed: {str(e)}")

            # Resume agent from evaluation
            agent = Agent(run_id=run_id, api_key=api_key)
            agent.state_machine.current_state = State.EVALUATE
            agent.run_agent()

            return {"status": "approved", "run_id": run_id}

        run.status = RunStatus.FAILED
        db.commit()

        step = Step(
            run_id=run_id,
            state=State.FAILED.value,
            step_number=(latest_step.step_number if latest_step else 0) + 1,
        )
        db.add(step)
        db.commit()

        return {"status": "rejected", "run_id": run_id, "reason": approval.reason}

    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "opspilot-agent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)