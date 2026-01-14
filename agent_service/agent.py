from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from anthropic import Anthropic
import logging
import sys
import redis

from state_machine import StateMachine, State
from tools import get_tool, validate_tool_inputs, requires_approval, list_tools
from models import Run, Step, ToolCall, RunStatus, StepState, ToolCallStatus
from database import SessionLocal

import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from logger_config import setup_logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class Agent:
    """
    LLM-powered task orchestrator with explicit state machine.
    
    Executes tasks by:
    1. Planning with LLM (what tool to call)
    2. Executing tools
    3. Evaluating with LLM (are we done?)
    4. Repeating until goal achieved or failed
    """
    
    def __init__(self, run_id: int, api_key: str):
        self.run_id = run_id
        self.logger = setup_logging(run_id=run_id)
        self.logger.info(f"Agent initialized for run {run_id}")
        self.state_machine = StateMachine()
        self.client = Anthropic(api_key=api_key)
        self.max_steps = 10  # Safety limit: prevent infinite loops
        self.current_step_number = 0
        self.db = SessionLocal()

        self.redis_client = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True
    )
        
        self.logger = logging.getLogger(f"Agent-{run_id}")
        self.logger.setLevel(logging.INFO)
        
        log_file = logging.FileHandler(f"logs/run_{run_id}.log")
        log_file.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(log_file)
        
        self.run = self.db.query(Run).filter(Run.id == run_id).first()
        if not self.run:
            raise ValueError(f"Run {run_id} not found")
        
        self.logger.info(f"Initialized agent for run {run_id}: {self.run.goal}")
        
        existing_steps = self.db.query(Step)\
            .filter(Step.run_id == run_id)\
            .order_by(Step.step_number.desc())\
            .first()
        
        if existing_steps:
            self.current_step_number = existing_steps.step_number
            self.state_machine.current_state = existing_steps.state
            self.logger.info(f"Resuming from step {self.current_step_number}, state {existing_steps.state}")
    
    def run_agent(self):
        self.logger.info("Starting agent execution")
        
        try:
            while not self.state_machine.is_terminal():
                if self.state_machine.current_state == State.NEEDS_APPROVAL:
                    self.logger.info("Run paused - awaiting approval")
                    break
                # Safety check: max steps
                if self.current_step_number >= self.max_steps:
                    self.logger.warning(f"Max steps ({self.max_steps}) exceeded")
                    self._transition_to_failed(
                        f"Max steps ({self.max_steps}) exceeded"
                    )
                    break
                
                # Only increment step number for PLAN state
                if self.state_machine.current_state == State.PLAN:
                    self.current_step_number += 1
                
                self.logger.info(f"Executing step {self.current_step_number}, state: {self.state_machine.current_state}")
                
                self._execute_current_state()
                
                self.db.commit()
            
            if self.state_machine.current_state == State.DONE:
                self.run.status = RunStatus.DONE
                self.logger.info("Agent completed successfully")
            elif self.state_machine.current_state == State.FAILED:
                self.run.status = RunStatus.FAILED
                self.logger.error("Agent failed")
            
            self.db.commit()
            
        except Exception as e:
            self.logger.exception(f"Unexpected error: {str(e)}")
            self._transition_to_failed(f"Unexpected error: {str(e)}")
            raise
        
        finally:
            self.db.close()
            self.logger.info("Agent execution finished")
    
    def _execute_current_state(self):
        state = self.state_machine.current_state
        
        if state == State.PLAN:
            self._handle_plan_state()
        elif state == State.EXECUTE_TOOL:
            self._handle_execute_state()
        elif state == State.EVALUATE:
            self._handle_evaluate_state()
        elif state == State.NEEDS_APPROVAL:
            self._handle_needs_approval_state()
    
    def _handle_plan_state(self):
        self.logger.info("Planning next action")
        
        # Build context for LLM
        context = self._build_planning_context()
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )
        except Exception as e:
            self.logger.error(f"LLM API error during planning: {str(e)}")
            self._transition_to_failed(f"LLM API error: {str(e)}")
            return
        
        if not response.content or len(response.content) == 0:
            self.logger.error("Empty response from LLM")
            self._transition_to_failed("Empty LLM response")
            return
        
        response_text = response.content[0].text
        self.logger.debug(f"LLM response: {response_text[:200]}...")
        
        # Parse LLM response
        try:
            plan = self._parse_planning_response(response_text)
        except ValueError as e:
            self.logger.error(f"Failed to parse LLM response: {str(e)}")
            self._transition_to_failed(f"Invalid LLM response format: {str(e)}")
            return
        
        self.logger.info(f"Parsed plan from LLM: {json.dumps(plan, indent=2)}")
        
        if "action" not in plan:
            self.logger.error("Missing 'action' field in plan")
            self._transition_to_failed("Invalid plan format: missing 'action'")
            return
        
        step = Step(
            run_id=self.run_id,
            state=State.PLAN.value,
            step_number=self.current_step_number,
            reasoning=plan.get("reasoning", "")
        )
        self.db.add(step)
        self.db.flush()
        
        if plan["action"] == "done":
            self.logger.info("Agent decided goal is complete")
            self.state_machine.transition(State.DONE)
            step.state = State.DONE.value
        
        elif plan["action"] == "call_tool":
            tool_name = plan.get("tool_name")
            inputs = plan.get("inputs", {})
            
            if not tool_name:
                self.logger.error("Missing tool_name in plan")
                self._transition_to_failed("Invalid plan: missing tool_name")
                return
            
            self.logger.info(f"Planning to call tool: {tool_name}")
            
            # Validate tool inputs against schema
            try:
                validated_inputs = validate_tool_inputs(tool_name, inputs)
            except Exception as e:
                self.logger.error(f"Input validation failed for {tool_name}: {str(e)}")
                self._transition_to_failed(f"Invalid tool inputs: {str(e)}")
                return
            
            # Create pending tool call
            tool_call = ToolCall(
                step_id=step.id,
                tool_name=tool_name,
                inputs=json.dumps(validated_inputs),
                status=ToolCallStatus.PENDING
            )
            self.db.add(tool_call)
            
            self.state_machine.transition(State.EXECUTE_TOOL)
        
        else:
            self.logger.error(f"Unknown action: {plan['action']}")
            self._transition_to_failed(f"Unknown action: {plan['action']}")
    
    def _build_planning_context(self) -> str:
        tools_info = list_tools()
        tools_desc = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in tools_info.items()
        ])
        
        steps = self.db.query(Step)\
            .filter(Step.run_id == self.run_id)\
            .order_by(Step.step_number)\
            .all()
        
        steps_summary = []
        for step in steps:
            for tc in step.tool_calls:
                if tc.outputs:
                    steps_summary.append(
                        f"Step {step.step_number}: Called {tc.tool_name}, "
                        f"result summary: {self._summarize_output(tc.outputs)}"
                    )
        
        steps_text = "\n".join(steps_summary) if steps_summary else "None yet"
        
        return f"""You are an ops automation agent. Your goal is:

        {self.run.goal}

        Available tools:
        {tools_desc}

        Previous steps:
        {steps_text}

        What should you do next? Respond in JSON format:

        If you need to call a tool:
        {{
            "action": "call_tool",
            "tool_name": "tool_name_here",
            "inputs": {{"param": "value"}},
            "reasoning": "Why I'm calling this tool"
        }}

        If the goal is achieved:
        {{
            "action": "done",
            "reasoning": "Why the goal is complete"
        }}

        IMPORTANT: 
        - When calling a tool, you MUST include all required parameters in "inputs"
        - For generate_report, "findings" must be an array of objects like:
        [{{"type": "log", "summary": "No errors found", "details": {{"count": 0}}}}]
        - NOT a string

        Respond with ONLY the JSON, no other text."""
    
    def _parse_planning_response(self, response_text: str) -> Dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
    
    def _summarize_output(self, outputs_json: str) -> str:
        try:
            outputs = json.loads(outputs_json)
            
            if "count" in outputs:
                return f"{outputs.get('count', 0)} results"
            elif "aggregates" in outputs:
                agg = outputs["aggregates"]
                return f"avg={agg.get('avg', 0):.2f}, max={agg.get('max', 0):.2f}"
            elif "ticket_id" in outputs:
                return f"Created {outputs['ticket_id']}"
            elif "findings_count" in outputs:
                return f"{outputs['findings_count']} findings"
            else:
                return "Success"
        except:
            return "Completed"
    
    def _transition_to_failed(self, reason: str):
        self.logger.error(f"Transitioning to FAILED: {reason}")
        
        # Check if already in terminal state
        if self.state_machine.current_state in {State.DONE, State.FAILED}:
            self.logger.warning(f"Already in terminal state {self.state_machine.current_state}, skipping transition")
            return
        
        self.state_machine.transition(State.FAILED)
        
        step = Step(
            run_id=self.run_id,
            state=State.FAILED.value,
            step_number=self.current_step_number + 1,
            reasoning=reason
        )
        self.db.add(step)
        self.db.commit()
        
        self.run.status = RunStatus.FAILED
        self.db.commit()

    def _handle_execute_state(self):
        current_step = self.db.query(Step)\
            .filter(
                Step.run_id == self.run_id,
                Step.step_number == self.current_step_number
            )\
            .first()
        
        if not current_step:
            self.logger.error("No current step found")
            self._transition_to_failed("No current step found")
            return
        
        tool_call = self.db.query(ToolCall)\
            .filter(
                ToolCall.step_id == current_step.id,
                ToolCall.status == ToolCallStatus.PENDING
            )\
            .first()
        
        if not tool_call:
            self.logger.error("No pending tool call found")
            self._transition_to_failed("No pending tool call found")
            return
        
        self.logger.info(f"Executing tool: {tool_call.tool_name}")
        
        tool_call.status = ToolCallStatus.RUNNING
        self.db.commit()
        
        try:
            inputs = json.loads(tool_call.inputs)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid tool call inputs JSON: {str(e)}")
            tool_call.status = ToolCallStatus.FAILED
            tool_call.error_message = f"Invalid inputs JSON: {str(e)}"
            self._transition_to_failed(f"Invalid tool inputs: {str(e)}")
            return
        
        retry_key = f"retry:{self.run_id}:{tool_call.id}"
        attempts = int(self.redis_client.get(retry_key) or 0)
        
        if attempts > 0:
            # Exponential backoff: 1s, 2s, 4s
            delay = 2 ** (attempts - 1)
            self.logger.info(f"Retry attempt {attempts}, waiting {delay}s")
            time.sleep(delay)
        
        if requires_approval(tool_call.tool_name):
            self.logger.info(f"Tool {tool_call.tool_name} requires approval. Pausing before execution.")
            self.run.status = RunStatus.NEEDS_APPROVAL
            tool_call.status = ToolCallStatus.PENDING  # keep it pending
            current_step.state = State.NEEDS_APPROVAL.value
            self.state_machine.transition(State.NEEDS_APPROVAL)

            self.db.commit()
            return
        
        # Execute tool with 30s timeout
        try:
            result = self._execute_tool_with_timeout(
                tool_call.tool_name,
                inputs,
                timeout=30
            )
            
            tool_call.outputs = json.dumps(result)
            tool_call.status = ToolCallStatus.SUCCESS
            tool_call.executed_at = datetime.utcnow()
            
            self.logger.info(f"Tool {tool_call.tool_name} succeeded")
            
            self.redis_client.delete(retry_key)

            if requires_approval(tool_call.tool_name):
                self.logger.info(f"Tool {tool_call.tool_name} requires approval - pausing execution")
                self.state_machine.transition(State.NEEDS_APPROVAL)
                current_step.state = State.NEEDS_APPROVAL.value
                self.run.status = RunStatus.NEEDS_APPROVAL
                self.db.commit()
                return 
            
            self.state_machine.transition(State.EVALUATE)
            current_step.state = State.EVALUATE.value
        
        except TimeoutError:
            self.logger.error(f"Tool {tool_call.tool_name} timed out")
            
            if attempts < 3:
                attempts += 1
                self.redis_client.setex(retry_key, 3600, attempts)  # 1 hour TTL
                self.logger.info(f"Scheduling retry {attempts}/3")
                tool_call.status = ToolCallStatus.PENDING  # Reset to retry
            else:
                self.logger.error("Max retries exceeded")
                tool_call.status = ToolCallStatus.FAILED
                tool_call.error_message = f"Timeout after 30 seconds (3 retries)"
                self._transition_to_failed(f"Tool {tool_call.tool_name} timed out after retries")
        
        except Exception as e:
            self.logger.exception(f"Tool {tool_call.tool_name} failed: {str(e)}")
            
            if attempts < 3:
                attempts += 1
                self.redis_client.setex(retry_key, 3600, attempts)
                self.logger.info(f"Scheduling retry {attempts}/3 after error")
                tool_call.status = ToolCallStatus.PENDING  # Reset to retry
            else:
                self.logger.error("Max retries exceeded")
                tool_call.status = ToolCallStatus.FAILED
                tool_call.error_message = str(e)
                tool_call.outputs = json.dumps({"error": str(e)})
                
                tb = traceback.format_exc()
                self.logger.debug(f"Full traceback:\n{tb}")
                
                self._transition_to_failed(f"Tool error: {str(e)}")
    
    def _execute_tool_with_timeout(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        tool_func = get_tool(tool_name)
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool_func, **inputs)
            try:
                result = future.result(timeout=timeout)
                return result
            except Exception as e:
                future.cancel()
                raise
    
    def _handle_evaluate_state(self):
        self.logger.info("Evaluating progress")
        
        context = self._build_evaluation_context()

        self.logger.debug(f"Evaluation context:\n{context[:500]}...")
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )
        except Exception as e:
            self.logger.error(f"LLM API error during evaluation: {str(e)}")
            self._transition_to_failed(f"LLM API error: {str(e)}")
            return
        
        if not response.content or len(response.content) == 0:
            self.logger.error("Empty response from LLM during evaluation")
            self._transition_to_failed("Empty LLM response")
            return
        
        response_text = response.content[0].text
        self.logger.debug(f"Evaluation response: {response_text[:200]}...")
        
        # Parse LLM response
        try:
            evaluation = self._parse_evaluation_response(response_text)
        except ValueError as e:
            self.logger.error(f"Failed to parse evaluation response: {str(e)}")
            self._transition_to_failed(f"Invalid evaluation format: {str(e)}")
            return
        
        if "decision" not in evaluation:
            self.logger.error("Missing 'decision' field in evaluation")
            self._transition_to_failed("Invalid evaluation: missing 'decision'")
            return
        
        current_step = self.db.query(Step)\
            .filter(Step.run_id == self.run_id, Step.step_number == self.current_step_number)\
            .first()

        if current_step:
            current_step.reasoning += f"\n[Evaluation] {evaluation.get('reasoning', '')}"
            current_step.state = State.EVALUATE.value
        
        decision = evaluation["decision"]
        self.logger.info(f"Evaluation decision: {decision}")

        # Transition based on decision
        if decision == "continue":
            self.state_machine.transition(State.PLAN)
        elif decision == "done":
            self.state_machine.transition(State.DONE)
        elif decision == "needs_approval":
            self.state_machine.transition(State.NEEDS_APPROVAL)
        elif decision == "failed":
            self._transition_to_failed(evaluation.get("reasoning", "Agent decided to fail"))
        else:
            self.logger.error(f"Unknown evaluation decision: {decision}")
            self._transition_to_failed(f"Unknown decision: {decision}")
    
    def _build_evaluation_context(self) -> str:
        steps = self.db.query(Step)\
            .filter(Step.run_id == self.run_id)\
            .order_by(Step.step_number)\
            .all()
        
        steps_detail = []
        for step in steps:
            for tc in step.tool_calls:
                approval_note = " (REQUIRES APPROVAL)" if requires_approval(tc.tool_name) else ""
                steps_detail.append(
                    f"Step {step.step_number}: {tc.tool_name}{approval_note}\n"
                    f"Inputs: {tc.inputs}\n"
                    f"Outputs: {tc.outputs if tc.outputs else 'N/A'}\n"
                )
        
        steps_text = "\n".join(steps_detail) if steps_detail else "None"
        
        return f"""You are evaluating progress on this goal:

    {self.run.goal}

    Steps executed so far:
    {steps_text}

    Has the goal been achieved? Respond in JSON format:

    If goal is complete:
    {{
        "decision": "done",
        "reasoning": "Why the goal is achieved"
    }}

    If you need to continue (call more tools):
    {{
        "decision": "continue",
        "reasoning": "What still needs to be done"
    }}

    If a tool marked "(REQUIRES APPROVAL)" was just executed successfully:
    {{
        "decision": "needs_approval",
        "reasoning": "Requesting approval for [tool name]"
    }}

    If goal cannot be achieved:
    {{
        "decision": "failed",
        "reasoning": "Why we failed"
    }}

    IMPORTANT: If you just executed a tool that requires approval, you MUST respond with "needs_approval".

    Respond with ONLY the JSON, no other text."""
    
    def _parse_evaluation_response(self, response_text: str) -> Dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse evaluation response as JSON: {e}")
    
    def _handle_needs_approval_state(self):
        self.logger.info("Waiting for approval")
        
        current_step = self.db.query(Step)\
            .filter(
                Step.run_id == self.run_id,
                Step.step_number == self.current_step_number
            )\
            .first()
        
        if not current_step:
            self.logger.error("No current step found in NEEDS_APPROVAL")
            self._transition_to_failed("No current step for approval")
            return
        
        tool_call = self.db.query(ToolCall)\
            .filter(ToolCall.step_id == current_step.id)\
            .order_by(ToolCall.created_at.desc())\
            .first()
        
        if not tool_call:
            self.logger.warning("No tool call found for approval, transitioning to PLAN")
            self.state_machine.transition(State.PLAN)
            return
        
        self.logger.info(f"Pausing for approval of {tool_call.tool_name}")
        
        self.run.status = RunStatus.NEEDS_APPROVAL
        self.db.commit()