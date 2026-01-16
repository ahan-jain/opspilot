'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import { getRun, Run } from '../../../lib/api';
import FinalReport from '../../../components/FinalReport';
import Timeline from '../../../components/Timeline';

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

      <Timeline steps={run.steps || []} runId={parseInt(runId)} />
  
      {/* Final Report */}
      {run.status === 'done' && (
        <FinalReport steps={run.steps} />
      )}
    </div>
  );
}