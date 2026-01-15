const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Run {
  id: number;
  goal: string;
  status: 'running' | 'done' | 'failed' | 'needs_approval';
  created_at: string;
  updated_at: string;
  steps: Step[];
}

export interface Step {
  id: number;
  run_id: number;
  state: string;
  step_number: number;
  reasoning?: string;
  created_at: string;
  tool_calls: ToolCall[];
}

export interface ToolCall {
  id: number;
  step_id: number;
  tool_name: string;
  inputs: any;
  outputs?: any;
  status: string;
  error_message?: string;
  created_at: string;
  executed_at?: string;
}

export async function getRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error('Failed to fetch run');
  return res.json();
}

export async function listRuns(): Promise<Run[]> {
    const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) throw new Error('Failed to fetch runs');
  return res.json();
}

export async function createRun(goal: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({goal})
  });
  if (!res.ok) throw new Error('Failed to create run');
  return res.json();
}

export async function executeRun(runId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/execute`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to execute run');
}

export async function approveStep(runId: number, stepId: number, approved: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}/steps/${stepId}/approve`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({approved})
  });
  if (!res.ok) throw new Error('Failed to approve step');
}