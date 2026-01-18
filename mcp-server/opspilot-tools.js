import { spawn } from "child_process";

export const opsPilotTools = [
  {
    name: "search_logs",
    description:
      "Search application logs for patterns within a time range. Returns matching log entries with timestamps.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "Search term or pattern to find in logs (e.g., 'timeout', 'error', 'database')",
        },
        time_range: {
          type: "string",
          description:
            "Time window to search. Examples: '1h' (1 hour), '24h' (24 hours), '7d' (7 days)",
          default: "1h",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "query_metrics",
    description:
      "Query time-series metrics data for performance analysis. Returns datapoints and aggregates (min, max, avg, p95).",
    inputSchema: {
      type: "object",
      properties: {
        metric: {
          type: "string",
          description: "Metric to query",
          enum: ["error_rate", "response_time", "cpu_usage", "memory_usage"],
        },
        start: {
          type: "string",
          description: "Start time (e.g., '1h', '24h', '7d')",
          default: "1h",
        },
        end: {
          type: "string",
          description: "End time (default: 'now')",
          default: "now",
        },
      },
      required: ["metric"],
    },
  },
  {
    name: "create_ticket",
    description:
      "Create an incident ticket. HIGH-RISK operation that requires approval. Use when investigation reveals issues requiring human action.",
    inputSchema: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Short summary of the issue",
        },
        description: {
          type: "string",
          description: "Detailed description with evidence and findings",
        },
        severity: {
          type: "string",
          enum: ["critical", "high", "medium", "low"],
          description: "Severity level based on impact",
          default: "medium",
        },
        tags: {
          type: "array",
          items: { type: "string" },
          description:
            "Tags for categorization (e.g., ['database', 'performance'])",
        },
      },
      required: ["title", "description"],
    },
  },
  {
    name: "generate_report",
    description:
      "Generate an investigation report with findings and recommendations",
    inputSchema: {
      type: "object",
      properties: {
        title: {
          type: "string",
          description: "Report title",
        },
        findings: {
          type: "array",
          items: { type: "string" },
          description: "List of findings from investigation",
        },
        recommendations: {
          type: "array",
          items: { type: "string" },
          description: "Recommended actions",
        },
      },
      required: ["title", "findings"],
    },
  },
];

export async function executeOpsPilotTool(toolName, args) {
  return new Promise((resolve, reject) => {
    const pythonScript = `
import sys
import json
sys.path.insert(0, '/app')
from tools.${toolName} import ${toolName}

args = json.loads('${JSON.stringify(args).replace(/'/g, "\\'")}')
result = ${toolName}(**args)
print(json.dumps(result))
`;

    const python = spawn("python3", ["-c", pythonScript], {
      cwd: "/app",
      env: process.env,
    });

    let stdout = "";
    let stderr = "";

    python.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    python.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    python.on("close", (code) => {
      if (code !== 0) {
        resolve({
          content: [
            {
              type: "text",
              text: `Error executing ${toolName}: ${
                stderr || `Exit code ${code}`
              }`,
            },
          ],
          isError: true,
        });
      } else {
        try {
          const result = JSON.parse(stdout);
          resolve({
            content: [
              {
                type: "text",
                text: JSON.stringify(result, null, 2),
              },
            ],
          });
        } catch (e) {
          resolve({
            content: [
              {
                type: "text",
                text: `Failed to parse JSON: ${stdout}`,
              },
            ],
            isError: true,
          });
        }
      }
    });
  });
}