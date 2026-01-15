'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import { getRun, Run } from '../../../lib/api';

export default function RunDetailPage() {
  const params = useParams();
  const runId = params.id as string;
  const [run, setRun] = useState<Run | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRun();
    const interval = setInterval(loadRun, 2000);
    return () => clearInterval(interval);
  }, [runId]);

  async function loadRun() {
    try {
      const data = await getRun(runId);
      setRun(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load run:', error);
      setLoading(false);
    }
  }

  async function handleApprove(approved: boolean) {
    try {
      const pendingStep = run?.steps.find(s => 
        s.tool_calls.some(tc => tc.status === 'pending')
      );
      
      if (!pendingStep) {
        alert('No pending step found');
        return;
      }

      const response = await fetch(`http://localhost:8000/runs/${runId}/approve`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({approved})
      });

      if (!response.ok) throw new Error('Failed to approve');
      
      loadRun();
      
      alert(approved ? 'Approved! Execution will continue.' : 'Rejected. Run stopped.');
    } catch (error) {
      console.error('Approval failed:', error);
      alert('Failed to process approval');
    }
  }

  if (loading) return <div className="p-8">Loading...</div>;
  if (!run) return <div className="p-8">Run not found</div>;

  return (
    <div className="max-w-6xl mx-auto p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Run #{run.id}</h1>
        <p className="text-gray-600 mb-4">{run.goal}</p>
        <div className="flex items-center gap-4">
          <span className={`
            px-3 py-1 rounded-full text-sm font-medium
            ${run.status === 'done' ? 'bg-green-100 text-green-800' : ''}
            ${run.status === 'running' ? 'bg-blue-100 text-blue-800' : ''}
            ${run.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
            ${run.status === 'needs_approval' ? 'bg-yellow-100 text-yellow-800' : ''}
          `}>
            {run.status}
          </span>

          {/* Approval Buttons */}
          {run.status === 'needs_approval' && (
            <div className="flex gap-2">
              <button
                onClick={() => handleApprove(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                ✓ Approve
              </button>
              <button
                onClick={() => handleApprove(false)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                ✗ Reject
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-6">
        {run.steps && run.steps.length > 0 ? (
          run.steps.map((step) => (
            <div key={step.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                  Step {step.step_number}: {step.state}
                </h3>
                <span className="text-sm text-gray-500">
                  {new Date(step.created_at).toLocaleTimeString()}
                </span>
              </div>

              {step.reasoning && (
                <p className="text-gray-700 mb-4 italic">{step.reasoning}</p>
              )}

              {/* Tool Calls */}
              {step.tool_calls && step.tool_calls.length > 0 && (
                <div className="space-y-4">
                  {step.tool_calls.map((tc) => (
                    <div key={tc.id} className="border-l-4 border-blue-500 pl-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-blue-700">
                          {tc.tool_name}
                        </span>
                        <span className={`
                          text-xs px-2 py-1 rounded ml-4
                          ${tc.status === 'success' ? 'bg-green-100 text-green-800' : ''}
                          ${tc.status === 'pending' ? 'bg-gray-100 text-gray-800' : ''}
                          ${tc.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
                        `}>
                          {tc.status}
                        </span>
                      </div>

                      {/* Inputs */}
                      <div className="mb-2">
                        <span className="text-sm font-medium text-gray-600">Inputs:</span>
                        <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                          {JSON.stringify(tc.inputs, null, 2)}
                        </pre>
                      </div>

                      {/* Outputs */}
                      {tc.outputs && (
                        <div>
                          <span className="text-sm font-medium text-gray-600">Outputs:</span>
                          <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                            {JSON.stringify(tc.outputs, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Error */}
                      {tc.error_message && (
                        <div className="mt-2 text-sm text-red-600">
                          Error: {tc.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
            No steps yet
          </div>
        )}
      </div>
    </div>
  );
}