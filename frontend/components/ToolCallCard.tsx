'use client';

import { useState } from 'react';
import { ToolCall, approveStep } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

interface ToolCallCardProps {
  toolCall: ToolCall;
  runId: number;
  stepId: number;
  needsApproval: boolean;
}

export default function ToolCallCard({
  toolCall,
  runId,
  stepId,
  needsApproval
}: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [approving, setApproving] = useState(false);

  async function handleApproval(approved: boolean) {
    setApproving(true);
    try {
      await approveStep(runId, stepId, approved);
    } catch (error) {
      alert('Failed to submit approval');
      setApproving(false);
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="px-4 py-3 bg-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <div className={`
            w-2 h-2 rounded-full
            ${toolCall.status === 'success' ? 'bg-green-500' : ''}
            ${toolCall.status === 'running' ? 'bg-blue-500 animate-pulse' : ''}
            ${toolCall.status === 'failed' ? 'bg-red-500' : ''}
            ${toolCall.status === 'pending' ? 'bg-gray-400' : ''}
          `}></div>
          
          <span className="font-medium text-gray-900">
            {toolCall.tool_name}
          </span>
          
          <span className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(toolCall.created_at), {addSuffix: true})}
          </span>
        </div>

        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {expanded && (
        <div className="px-4 py-3 space-y-3">
          {/* Inputs */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Inputs:</h4>
            <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto">
              {JSON.stringify(toolCall.inputs, null, 2)}
            </pre>
          </div>

          {/* Outputs */}
          {toolCall.outputs && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-1">Outputs:</h4>
              <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto">
                {JSON.stringify(toolCall.outputs, null, 2)}
              </pre>
            </div>
          )}

          {/* Error */}
          {toolCall.error_message && (
            <div className="bg-red-50 border border-red-200 rounded p-2">
              <p className="text-sm text-red-800">
                <strong>Error:</strong> {toolCall.error_message}
              </p>
            </div>
          )}

          {/* Approval buttons */}
          {needsApproval && toolCall.status === 'pending' && (
            <div className="pt-2 border-t border-gray-200">
              <p className="text-sm text-gray-700 mb-3">
                This action requires your approval:
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => handleApproval(true)}
                  disabled={approving}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-400 transition-colors"
                >
                  {approving ? 'Approving...' : 'Approve'}
                </button>
                <button
                  onClick={() => handleApproval(false)}
                  disabled={approving}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:bg-gray-400 transition-colors"
                >
                  {approving ? 'Rejecting...' : 'Reject'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}