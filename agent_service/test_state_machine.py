import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pytest
from state_machine import StateMachine, State

def test_initial_state():
    sm = StateMachine()
    assert sm.current_state == State.PLAN

def test_valid_transition_plan_to_execute():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL, reason="Calling search_logs")
    assert sm.current_state == State.EXECUTE_TOOL

def test_valid_transition_execute_to_evaluate():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    assert sm.current_state == State.EVALUATE

def test_valid_transition_evaluate_to_plan():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    sm.transition(State.PLAN)
    assert sm.current_state == State.PLAN

def test_valid_transition_evaluate_to_needs_approval():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    sm.transition(State.NEEDS_APPROVAL)
    assert sm.current_state == State.NEEDS_APPROVAL

def test_valid_transition_needs_approval_to_execute():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    sm.transition(State.NEEDS_APPROVAL)
    sm.transition(State.EXECUTE_TOOL, reason="Approval granted")
    assert sm.current_state == State.EXECUTE_TOOL

def test_transition_to_done():
    sm1 = StateMachine()
    sm1.transition(State.DONE)
    assert sm1.current_state == State.DONE
    
    sm2 = StateMachine()
    sm2.transition(State.EXECUTE_TOOL)
    sm2.transition(State.EVALUATE)
    sm2.transition(State.DONE)
    assert sm2.current_state == State.DONE

def test_transition_to_failed():
    sm = StateMachine()
    sm.transition(State.FAILED, reason="Agent error")
    assert sm.current_state == State.FAILED

def test_invalid_transition_plan_to_evaluate():
    sm = StateMachine()
    
    with pytest.raises(ValueError) as exc_info:
        sm.transition(State.EVALUATE)
    
    assert "Invalid transition" in str(exc_info.value)
    assert sm.current_state == State.PLAN 

def test_invalid_transition_execute_to_plan():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    
    with pytest.raises(ValueError):
        sm.transition(State.PLAN)
    
    assert sm.current_state == State.EXECUTE_TOOL 

def test_invalid_transition_from_done():
    sm = StateMachine()
    sm.transition(State.DONE)
    
    with pytest.raises(ValueError):
        sm.transition(State.PLAN)
    
    assert sm.current_state == State.DONE

def test_invalid_transition_from_failed():
    sm = StateMachine()
    sm.transition(State.FAILED)
    
    with pytest.raises(ValueError):
        sm.transition(State.PLAN)
    
    assert sm.current_state == State.FAILED

def test_is_terminal():
    sm = StateMachine()
    assert not sm.is_terminal()  
    
    sm.transition(State.EXECUTE_TOOL)
    assert not sm.is_terminal()  
    
    sm.transition(State.EVALUATE)
    assert not sm.is_terminal()  
    sm.transition(State.DONE)
    assert sm.is_terminal()  

def test_transition_history():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    sm.transition(State.PLAN)
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    sm.transition(State.DONE)
    
    history = sm.get_history()
    assert history == [
        "plan",
        "execute_tool",
        "evaluate",
        "plan",
        "execute_tool",
        "evaluate",
        "done"
    ]

def test_get_valid_transitions():
    sm = StateMachine()
    
    valid = sm.get_valid_transitions()
    assert State.EXECUTE_TOOL in valid
    assert State.DONE in valid
    assert State.FAILED in valid
    assert State.EVALUATE not in valid
    
    sm.transition(State.DONE)
    valid = sm.get_valid_transitions()
    assert len(valid) == 0  

def test_reset():
    sm = StateMachine()
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    
    sm.reset()
    assert sm.current_state == State.PLAN
    assert sm.get_history() == ["plan"]

def test_typical_success_flow():
    sm = StateMachine()
    
    assert sm.current_state == State.PLAN
    
    sm.transition(State.EXECUTE_TOOL, reason="search_logs")
    assert sm.current_state == State.EXECUTE_TOOL
    
    sm.transition(State.EVALUATE)
    assert sm.current_state == State.EVALUATE
    
    sm.transition(State.PLAN)
    assert sm.current_state == State.PLAN
    
    sm.transition(State.EXECUTE_TOOL, reason="query_metrics")
    sm.transition(State.EVALUATE)

    sm.transition(State.DONE)
    assert sm.current_state == State.DONE
    assert sm.is_terminal()

def test_approval_workflow():
    sm = StateMachine()
    
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.EVALUATE)
    
    sm.transition(State.NEEDS_APPROVAL)
    assert sm.current_state == State.NEEDS_APPROVAL
    
    sm.transition(State.EXECUTE_TOOL, reason="create_ticket approved")
    sm.transition(State.EVALUATE)
    sm.transition(State.DONE)
    
    assert sm.current_state == State.DONE

def test_failure_recovery():
    sm = StateMachine()
    
    sm.transition(State.EXECUTE_TOOL)
    sm.transition(State.FAILED, reason="Tool timeout")
    
    assert sm.is_terminal()
    
    with pytest.raises(ValueError):
        sm.transition(State.PLAN)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])