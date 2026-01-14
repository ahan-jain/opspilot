import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agent import Agent
from models import Run, RunStatus, Step
from database import SessionLocal, engine
from models import Base
import json

# Reset database before tests
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def run_scenario(goal: str, scenario_name: str):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*60}\n")
    print(f"Goal: {goal}\n")
    
    db = SessionLocal()

    run = Run(goal=goal, status=RunStatus.RUNNING)
    db.add(run)
    db.commit()
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    agent = Agent(run_id=run.id, api_key=api_key)
    
    try:
        agent.run_agent()
    except Exception as e:
        print(f"ERROR: {e}")
    
    db.refresh(run)
    steps = db.query(Step).filter(Step.run_id == run.id).order_by(Step.step_number).all()
    
    print(f"\n--- RESULTS ---")
    print(f"Status: {run.status.value}")
    print(f"Steps taken: {len(steps)}\n")
    
    for step in steps:
        print(f"Step {step.step_number}: {step.state.value}")
        for tc in step.tool_calls:
            if tc.outputs:
                outputs = json.loads(tc.outputs)
                if "count" in outputs:
                    print(f"  → {tc.tool_name}: {outputs['count']} results")
                elif "ticket_id" in outputs:
                    print(f"  → {tc.tool_name}: {outputs['ticket_id']}")
                elif "findings_count" in outputs:
                    print(f"  → {tc.tool_name}: {outputs['findings_count']} findings")
                else:
                    print(f"  → {tc.tool_name}: Success")
    
    db.close()
    return run.id

# === SCENARIO 1: Simple Investigation ===
def scenario_1():
    run_scenario(
        goal="Investigate error spike in last hour",
        scenario_name="Simple Investigation"
    )

# === SCENARIO 2: Multi-Step with Ticket ===
def scenario_2():
    run_scenario(
        goal="Find slow endpoints and create ticket if needed",
        scenario_name="Multi-Step with Ticket Creation"
    )

# === SCENARIO 3: System Health Summary ===
def scenario_3():
    run_scenario(
        goal="Summarize system health from metrics and logs",
        scenario_name="System Health Summary"
    )

# === SCENARIO 4: Targeted Investigation ===
def scenario_4():
    run_scenario(
        goal="Investigate payment gateway timeout errors",
        scenario_name="Targeted Error Investigation"
    )

if __name__ == "__main__":
    print("Running OpsPilot Test Scenarios")
    print("This will take ~5-10 minutes...\n")
    
    scenario_1()
    scenario_2()
    scenario_3()
    scenario_4()
    
    print(f"\n{'='*60}")
    print("ALL SCENARIOS COMPLETE")
    print(f"{'='*60}")