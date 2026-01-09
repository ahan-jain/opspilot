import os
import json
from datetime import datetime
from typing import Dict
import uuid

def create_ticket(
    title: str,
    description: str,
    severity: str = None,
    priority: str = None,
    tags: list = None
) -> Dict:
    """
    Create a new ticket (writes to JSON file).
    
    This is a HIGH-RISK tool - it creates work for humans.
    Should require approval before execution.
    
    Args:
        title: Short summary of issue
        description: Detailed description with evidence
        severity: critical | high | medium | low
        tags: Optional list of tags (e.g., ["database", "performance"])
    
    Returns:
        {
            "ticket_id": str,
            "title": str,
            "created_at": str,
            "severity": str,
            "status": "open"
        }
    """

    severity_level = severity or priority or "medium"
    
    valid_severities = ["critical", "high", "medium", "low"]
    if severity_level not in valid_severities:
        severity_level = "medium"
    
    # Generate ticket
    ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.utcnow().isoformat()
    
    ticket = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "severity": severity_level,
        "tags": tags or [],
        "status": "open",
        "created_at": created_at,
        "created_by": "opspilot-agent"
    }
    
    ticket_dir = os.path.join(
    os.path.dirname(__file__),
    "../../data/tickets"
)

    os.makedirs(ticket_dir, exist_ok=True)

    ticket_file = os.path.join(ticket_dir, f"{ticket_id}.json")

    with open(ticket_file, 'w') as f:
        json.dump(ticket, f, indent=2)
    
    return {
        "ticket_id": ticket_id,
        "title": title,
        "created_at": created_at,
        "severity": severity_level,
        "status": "open",
        "file_path": ticket_file
    }