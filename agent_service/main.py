from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
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
import asyncio

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

def run_agent_with_mcp(run_id: int, api_key: str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        agent = Agent(run_id=run_id, api_key=api_key)
        loop.run_until_complete(agent.initialize_mcp())
        agent.run_agent()
        
        loop.close()
        
    except Exception as e:
        print(f"Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = RunStatus.FAILED
                db.commit()
        finally:
            db.close()

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
def execute_run(run_id: int, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise HTTPException(404, "Run not found")
        
        if run.status == RunStatus.DONE:
            raise HTTPException(400, "Run already completed")
        
        if run.status == RunStatus.FAILED:
            raise HTTPException(400, "Run already failed")
        
        run.status = RunStatus.RUNNING
        db.commit()
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(500, "ANTHROPIC_API_KEY not set in environment")
        
        background_tasks.add_task(run_agent_with_mcp, run_id, api_key)
        
        return {
            "run_id": run_id,
            "status": "started",
            "message": "Execution started in background"
        }
    
    finally:
        db.close()

@app.get("/runs")  
def list_runs(limit: int = 20, db: Session = Depends(get_db)):

    runs = db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()
    
    for run in runs:
        for step in run.steps:
            for tc in step.tool_calls:
                if tc.inputs and isinstance(tc.inputs, str):
                    tc.inputs = json.loads(tc.inputs)
                if tc.outputs and isinstance(tc.outputs, str):
                    tc.outputs = json.loads(tc.outputs)
    
    return runs

@app.get("/runs/{run_id}")  
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    for step in run.steps:
        for tc in step.tool_calls:
            if tc.inputs and isinstance(tc.inputs, str):
                tc.inputs = json.loads(tc.inputs)
            if tc.outputs and isinstance(tc.outputs, str):
                tc.outputs = json.loads(tc.outputs)
    
    return run

@app.get("/runs/{run_id}/steps")  
def get_run_steps(run_id: int, db: Session = Depends(get_db)):
    steps = db.query(Step).filter(Step.run_id == run_id).order_by(Step.step_number).all()
    
    for step in steps:
        for tc in step.tool_calls:
            if tc.inputs and isinstance(tc.inputs, str):
                tc.inputs = json.loads(tc.inputs)
            if tc.outputs and isinstance(tc.outputs, str):
                tc.outputs = json.loads(tc.outputs)
    
    return steps

@app.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    
    db.delete(run)
    db.commit()
    
    return None

@app.post("/runs/{run_id}/approve")
def approve_run(run_id: int, approval: ApprovalRequest, background_tasks: BackgroundTasks):
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

            def resume_agent():
                agent = Agent(run_id=run_id, api_key=api_key)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(agent.initialize_mcp())
                agent.state_machine.current_state = State.EVALUATE
                agent.run_agent()
                loop.close()
            
            background_tasks.add_task(resume_agent)

            return {"status": "approved", "run_id": run_id}

        run.status = RunStatus.FAILED
        db.commit()

        step = Step(
            run_id=run_id,
            state=State.FAILED.value,
            step_number=(latest_step.step_number if latest_step else 0) + 1,
            reasoning=approval.reason or "Approval rejected by user"
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