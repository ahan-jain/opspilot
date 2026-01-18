#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFile, writeFile, readdir } from "fs/promises";
import { join } from "path";

import { opsPilotTools, executeOpsPilotTool } from "./opspilot-tools.js";

const server = new Server(
  {
    name: "opspilot-aggregator",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

const filesystemTools = [
  {
    name: "read_file",
    description: "Read contents of a file from /app/data directory",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Relative path to file within /app/data (e.g., 'logs/app.log')",
        },
        file_path: {  
            type: "string",
            description: "Alias for 'path' - relative path to file within /app/data",
          },
      },
      required: [],
    },
  },
  {
    name: "write_file",
    description: "Write contents to a file in /app/data directory",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Relative path to file within /app/data",
        },
        filename: {  
            type: "string",
            description: "Alias for 'path' - relative path to file within /app/data",
          },
        content: {
          type: "string",
          description: "Content to write to the file",
        },
      },
      required: ["path", "content"],
    },
  },
  {
    name: "list_directory",
    description: "List contents of a directory in /app/data",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Relative path to directory within /app/data (default: '.')",
          default: ".",
        },
      },
    },
  },
];

const allTools = [...opsPilotTools, ...filesystemTools];

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: allTools };
});
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  const isOpsPilotTool = opsPilotTools.some((t) => t.name === name);

  if (isOpsPilotTool) {
    return await executeOpsPilotTool(name, args);
  }

  try {
    if (name === "read_file") {
      const filePath = join("/app/data", args.path || args.file_path);
      const content = await readFile(filePath, "utf-8");
      return {
        content: [
          {
            type: "text",
            text: content,
          },
        ],
      };
    }

    if (name === "write_file") {
      const filePath = join("/app/data", args.path || args.filename);
      await writeFile(filePath, args.content, "utf-8");
      return {
        content: [
          {
            type: "text",
            text: `Successfully wrote to ${args.path}`,
          },
        ],
      };
    }

    if (name === "list_directory") {
      const dirPath = join("/app/data", args.path || ".");
      const files = await readdir(dirPath, { withFileTypes: true });
      const fileList = files.map((f) => ({
        name: f.name,
        type: f.isDirectory() ? "directory" : "file",
      }));
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(fileList, null, 2),
          },
        ],
      };
    }

    return {
      content: [
        {
          type: "text",
          text: `Unknown tool: ${name}`,
        },
      ],
      isError: true,
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Filesystem error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});


async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("OpsPilot MCP Aggregator running on stdio");
}

main().catch(console.error);