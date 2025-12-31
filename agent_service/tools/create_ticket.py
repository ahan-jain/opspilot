import os
import json
from datetime import datetime
from typing import Dict
import uuid

def create_ticket(
    title: str,
    description: str,
    severity: str,
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

    valid_severities = ["critical", "high", "medium", "low"]
    if severity not in valid_severities:
        return {
            "error": f"Invalid severity. Must be one of: {valid_severities}"
        }
    
    # Generate ticket
    ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.utcnow().isoformat()
    
    ticket = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "severity": severity,
        "tags": tags or [],
        "status": "open",
        "created_at": created_at,
        "created_by": "opspilot-agent"
    }
    
    # Write to file
    ticket_file = os.path.join(
        os.path.dirname(__file__),
        f"../../data/tickets/{ticket_id}.json"
    )
    
    with open(ticket_file, 'w') as f:
        json.dump(ticket, f, indent=2)
    
    return {
        "ticket_id": ticket_id,
        "title": title,
        "created_at": created_at,
        "severity": severity,
        "status": "open",
        "file_path": ticket_file
    }