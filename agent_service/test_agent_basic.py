import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import Agent
from models import Run, RunStatus
from database import SessionLocal, engine
from models import Base
import json

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def test_planning():
    
    db = SessionLocal()
    run = Run(
        goal="Search logs for errors in the last hour",
        status=RunStatus.RUNNING
    )
    db.add(run)
    db.commit()
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in .env")
        return
    
    agent = Agent(run_id=run.id, api_key=api_key)
    
    print("=== Running PLAN step ===")
    agent._execute_current_state()
    
    print(f"\nCurrent state: {agent.state_machine.current_state.value}")
    
    assert agent.state_machine.current_state.value == "execute_tool"
    
    steps = db.query(Step).filter(Step.run_id == run.id).all()
    print(f"Steps created: {len(steps)}")
    
    for step in steps:
        print(f"  Step {step.step_number}: {step.state.value}")
        print(f"  Reasoning: {step.reasoning}")
        
        for tc in step.tool_calls:
            print(f"    Tool call: {tc.tool_name}")
            print(f"    Inputs: {tc.inputs}")
    
    db.close()

def test_execution():
    
    db = SessionLocal()
    run = Run(
        goal="Search logs for 'error' keyword",
        status=RunStatus.RUNNING
    )
    db.add(run)
    db.commit()
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    agent = Agent(run_id=run.id, api_key=api_key)
    
    print("=== PLAN ===")
    agent._execute_current_state()
    agent.current_step_number += 1
    
    print("\n=== EXECUTE ===")
    agent._execute_current_state()
    
    steps = db.query(Step).filter(Step.run_id == run.id).all()
    
    for step in steps:
        for tc in step.tool_calls:
            print(f"Tool: {tc.tool_name}")
            print(f"Status: {tc.status.value}")
            if tc.outputs:
                outputs = json.loads(tc.outputs)
                print(f"Results: {outputs.get('count', 0)} matches")
    
    db.close()

if __name__ == "__main__":
    print("Test 1: Planning\n")
    test_planning()
    
    print("\n" + "="*50)
    print("Test 2: Execution\n")
    test_execution()