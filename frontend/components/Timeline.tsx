import { Step } from '@/lib/api';
import ToolCallCard from './ToolCallCard';

interface TimelineProps {
  steps: Step[];
  runId: number;
}

export default function Timeline({ steps, runId }: TimelineProps) {
  if (steps.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
        No steps yet...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {steps.map((step, index) => (
        <div key={step.id} className="relative">
          {index < steps.length - 1 && (
            <div className="absolute left-6 top-16 w-0.5 h-full bg-gray-300 -z-10"></div>
          )}

          {/* Step card */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center">
              <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold mr-4">
                {step.step_number}
              </div>
              
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  {step.state.replace('_', ' ').toUpperCase()}
                </h3>
                {step.reasoning && (
                  <p className="text-sm text-gray-600 mt-1">
                    {step.reasoning}
                  </p>
                )}
              </div>

              <span className={`
                px-3 py-1 rounded-full text-xs font-medium
                ${step.state === 'done' ? 'bg-green-100 text-green-800' : ''}
                ${step.state === 'plan' ? 'bg-purple-100 text-purple-800' : ''}
                ${step.state === 'execute_tool' ? 'bg-blue-100 text-blue-800' : ''}
                ${step.state === 'evaluate' ? 'bg-indigo-100 text-indigo-800' : ''}
                ${step.state === 'needs_approval' ? 'bg-yellow-100 text-yellow-800' : ''}
                ${step.state === 'failed' ? 'bg-red-100 text-red-800' : ''}
              `}>
                {step.state}
              </span>
            </div>

            {/* Tool calls */}
            {step.tool_calls.length > 0 && (
              <div className="p-6 space-y-4">
                {step.tool_calls.map(tc => (
                  <ToolCallCard
                    key={tc.id}
                    toolCall={tc}
                    runId={runId}
                    stepId={step.id}
                    needsApproval={step.state === 'needs_approval'}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}