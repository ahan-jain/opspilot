from enum import Enum
from typing import Optional, Set, Dict

class State(Enum):

    PLAN = "plan"
    EXECUTE_TOOL = "execute_tool"
    EVALUATE = "evaluate"
    NEEDS_APPROVAL = "needs_approval"
    DONE = "done"
    FAILED = "failed"

class StateMachine:
    
    # valid transitions
    TRANSITIONS: Dict[State, Set[State]] = {
        State.PLAN: {
            State.EXECUTE_TOOL,  
            State.DONE,          
            State.FAILED          
        },
        State.EXECUTE_TOOL: {
            State.EVALUATE,      
            State.FAILED         
        },
        State.EVALUATE: {
            State.PLAN,          
            State.NEEDS_APPROVAL, 
            State.DONE,           
            State.FAILED          
        },
        State.NEEDS_APPROVAL: {
            State.EXECUTE_TOOL,   
            State.FAILED          
        },
        State.DONE: set(),       
        State.FAILED: set()       
    }
    
    def __init__(self, initial_state: State = State.PLAN):
        self.current_state = initial_state
        self.transition_history = [initial_state]
    
    def can_transition(self, from_state: State, to_state: State) -> bool:
        return to_state in self.TRANSITIONS.get(from_state, set())
    
    def transition(self, to_state: State, reason: str = "") -> bool:
        if not self.can_transition(self.current_state, to_state):
            raise ValueError(
                f"Invalid transition: {self.current_state.value} → {to_state.value}. "
                f"Valid transitions from {self.current_state.value}: "
                f"{[s.value for s in self.TRANSITIONS[self.current_state]]}"
            )
        
        self.transition_history.append(to_state)
        self.current_state = to_state
        
        return True
    
    def is_terminal(self, state: Optional[State] = None) -> bool:
        check_state = state if state is not None else self.current_state
        return check_state in {State.DONE, State.FAILED}
    
    def get_valid_transitions(self, state: Optional[State] = None) -> Set[State]:
        check_state = state if state is not None else self.current_state
        return self.TRANSITIONS.get(check_state, set())
    
    def reset(self):
        self.current_state = State.PLAN
        self.transition_history = [State.PLAN]
    
    def get_history(self) -> list:
        return [s.value for s in self.transition_history]