from typing import Dict, Any, Callable
from .search_logs import search_logs
from .query_metrics import query_metrics
from .create_ticket import create_ticket
from .generate_report import generate_report

# MCP Tool Registry
TOOLS: Dict[str, Dict[str, Any]] = {
    "search_logs": {
        "function": search_logs,
        "description": "Search through application logs for specific patterns or errors. Returns matching log entries with timestamps and context.",
        "schema": {
            "query": {
                "type": "string",
                "description": "Search term or pattern to find in logs",
                "required": True,
                "example": "error"
            },
            "time_range": {
                "type": "string",
                "description": "Time window to search (e.g., '1h', '24h', '7d')",
                "required": False,
                "default": "1h",
                "example": "24h"
            }
        },
        "requires_approval": False,
        "timeout": 30,
        "category": "observability"
    },
    
    "query_metrics": {
        "function": query_metrics,
        "description": "Query time-series metrics data (error_rate, response_time, cpu_usage, memory_usage). Returns datapoints and statistical aggregates.",
        "schema": {
            "metric_name": {
                "type": "string",
                "description": "Name of metric to query",
                "required": True,
                "enum": ["error_rate", "response_time", "cpu_usage", "memory_usage"],
                "example": "error_rate"
            },
            "start": {
                "type": "string",
                "description": "Start time (ISO format or relative like '1h', '24h')",
                "required": True,
                "example": "1h"
            },
            "end": {
                "type": "string",
                "description": "End time (ISO format or 'now')",
                "required": True,
                "example": "now"
            },
            "interval": {
                "type": "string",
                "description": "Data aggregation interval",
                "required": False,
                "default": "5m",
                "example": "5m"
            }
        },
        "requires_approval": False,
        "timeout": 30,
        "category": "observability"
    },
    
    "create_ticket": {
        "function": create_ticket,
        "description": "Create a new incident ticket. THIS IS A HIGH-RISK ACTION - creates work for humans and should only be used when evidence clearly indicates a problem requiring investigation.",
        "schema": {
            "title": {
                "type": "string",
                "description": "Brief, actionable title for the ticket",
                "required": True,
                "example": "Payment gateway timeout spike"
            },
            "description": {
                "type": "string",
                "description": "Detailed description with evidence, timeline, and impact",
                "required": True,
                "example": "15 payment timeouts detected between 09:18-09:30..."
            },
            "severity": {
                "type": "string",
                "description": "Severity level",
                "required": True,
                "enum": ["critical", "high", "medium", "low"],
                "example": "high"
            },
            "tags": {
                "type": "array",
                "description": "Optional categorization tags",
                "required": False,
                "example": ["payment", "timeout"]
            }
        },
        "requires_approval": True,  # ← KEY: This tool needs human approval
        "timeout": 10,
        "category": "action"
    },
    
    "generate_report": {
        "function": generate_report,
        "description": "Generate a markdown investigation report from findings. Use this as the final step to summarize your investigation.",
        "schema": {
            "findings": {
                "type": "array",
                "description": "List of findings, each with type, summary, and details",
                "required": True,
                "example": [
                    {
                        "type": "log",
                        "summary": "Payment errors detected",
                        "details": {"count": 15, "time_range": "1h"}
                    }
                ]
            }
        },
        "requires_approval": False,
        "timeout": 20,
        "category": "reporting"
    }
}

def get_tool(tool_name: str) -> Callable:
    if tool_name not in TOOLS:
        raise ValueError(f"Tool '{tool_name}' not found. Available: {list(TOOLS.keys())}")
    return TOOLS[tool_name]["function"]

def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    if tool_name not in TOOLS:
        raise ValueError(f"Tool '{tool_name}' not found")
    return TOOLS[tool_name]["schema"]

def requires_approval(tool_name: str) -> bool:
    if tool_name not in TOOLS:
        return False
    return TOOLS[tool_name].get("requires_approval", False)

def list_tools() -> Dict[str, Any]:
    return {
        name: {
            "description": config["description"],
            "schema": config["schema"],
            "requires_approval": config["requires_approval"],
            "category": config.get("category", "general")
        }
        for name, config in TOOLS.items()
    }

def validate_tool_inputs(tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    schema = get_tool_schema(tool_name)
    validated = {}
    
    for param_name, param_config in schema.items():
        if param_config.get("required", False):
            if param_name not in inputs:
                raise ValueError(f"Missing required parameter: {param_name}")
        
        if param_name in inputs:
            value = inputs[param_name]
        elif "default" in param_config:
            value = param_config["default"]
        else:
            continue
        
        expected_type = param_config.get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Parameter {param_name} must be a string")
        elif expected_type == "array" and not isinstance(value, list):
            raise ValueError(f"Parameter {param_name} must be an array")
        
        if "enum" in param_config:
            if value not in param_config["enum"]:
                raise ValueError(
                    f"Parameter {param_name} must be one of: {param_config['enum']}"
                )
        
        validated[param_name] = value
    
    return validated