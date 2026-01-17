'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createRun, listRuns, executeRun, Run } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';

export default function Home() {
  const router = useRouter();
  const [goal, setGoal] = useState('');
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRecentRuns();
  }, []);

  async function loadRecentRuns() {
    try {
      const runs = await listRuns();
      setRecentRuns(runs);
    } catch (error) {
      console.error('Failed to load runs:', error);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!goal.trim() || loading) return;

    setLoading(true);
    try {
      const run = await createRun(goal);
      
      // Start execution here
      executeRun(run.id).catch(console.error);
      
      router.push(`/runs/${run.id}`);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to create run');
      setLoading(false);
    }

    
  }

  

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            OpsPilot
          </h1>
          <p className="text-gray-600">
            LLM-powered task orchestration for ops automation
          </p>
        </div>
        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Input Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <form onSubmit={handleSubmit}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              What would you like to investigate?
            </label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              placeholder="e.g., Investigate error spike in last hour and create ticket if needed"
              disabled={loading}
            />
            <div className="mt-4 flex justify-end">
              <button
                type="submit"
                disabled={!goal.trim() || loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Starting...' : 'Start Run'}
              </button>
            </div>
          </form>
        </div>

        {/* Recent Runs */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Recent Runs
          </h2>
          
          {recentRuns.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              No runs yet. Start one above!
            </div>
          ) : (
            <div className="space-y-3">
              {recentRuns.map((run) => (
                <div
                  key={run.id}
                  onClick={() => router.push(`/runs/${run.id}`)}
                  className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-gray-900 font-medium">
                        {run.goal}
                      </p>
                      <p className="text-sm text-gray-500 mt-1">
                        {formatDistanceToNow(new Date(run.created_at + 'Z'), {addSuffix: true})}
                      </p>
                    </div>
                    <span className={`
                      px-3 py-1 rounded-full text-sm font-medium
                      ${run.status === 'done' ? 'bg-green-100 text-green-800' : ''}
                      ${run.status === 'running' ? 'bg-blue-100 text-blue-800' : ''}
                      ${run.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
                      ${run.status === 'needs_approval' ? 'bg-yellow-100 text-yellow-800' : ''}
                    `}>
                      {run.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}