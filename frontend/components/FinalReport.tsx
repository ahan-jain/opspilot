'use client';

import { useState, useEffect } from 'react';
import { Step } from '@/lib/api';

interface FinalReportProps {
  steps: Step[];
}

export default function FinalReport({ steps }: FinalReportProps) {
  const [report, setReport] = useState<string | null>(null);

  useEffect(() => {
    for (const step of steps) {
      for (const tc of step.tool_calls) {
        if (tc.tool_name === 'generate_report' && tc.outputs) {
          setReport(tc.outputs.report);
          return;
        }
      }
    }
  }, [steps]);

  if (!report) return null;

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          Final Report
        </h2>
        <button
          onClick={() => {
            const blob = new Blob([report], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'opspilot-report.md';
            a.click();
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Download Report
        </button>
      </div>
      
      <div className="prose prose-sm max-w-none">
        <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded">
          {report}
        </pre>
      </div>
    </div>
  );
}