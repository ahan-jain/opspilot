import os
import json
from datetime import datetime, timedelta
from typing import Dict, List

def search_logs(query: str, time_range: str = "1h") -> Dict:
    """
    Search through log files for matching entries.
    
    Args:
        query: Search term (e.g., "error", "timeout", "user_id:12345")
        time_range: Time window to search (e.g., "1h", "24h", "7d")
    
    Returns:
        {
            "matches": [{"timestamp": str, "level": str, "message": str}, ...],
            "count": int,
            "time_range": str,
            "query": str
        }
    """
    # Parse time range
    cutoff_time = _parse_time_range(time_range)
    
    # Read log files
    log_dir = os.path.join(os.path.dirname(__file__), "../../data/logs")
    matches = []
    
    for log_file in os.listdir(log_dir):
        if not log_file.endswith(".log"):
            continue
            
        file_path = os.path.join(log_dir, log_file)
        with open(file_path, 'r') as f:
            for line in f:
                # Parse log line
                log_entry = _parse_log_line(line)
                if not log_entry:
                    continue
                
                # Check if within time range
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                if log_time < cutoff_time:
                    continue
                
                # Check if matches query
                if query.lower() in log_entry["message"].lower():
                    matches.append(log_entry)
    
    # Sort by timestamp (newest first)
    matches.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "matches": matches[:100],  # Limit to 100 results
        "count": len(matches),
        "time_range": time_range,
        "query": query,
        "searched_at": datetime.utcnow().isoformat()
    }

def _parse_time_range(time_range: str) -> datetime:
    """Convert time_range string to cutoff datetime"""
    now = datetime.utcnow()
    
    if time_range.endswith('h'):
        hours = int(time_range[:-1])
        return now - timedelta(hours=hours)
    elif time_range.endswith('d'):
        days = int(time_range[:-1])
        return now - timedelta(days=days)
    else:
        # Default to 1 hour
        return now - timedelta(hours=1)

def _parse_log_line(line: str) -> Dict:
    """Parse a log line into structured format"""
    try:
        # Expected format: 2024-12-29T10:30:45 [ERROR] Message here
        parts = line.strip().split(' ', 2)
        if len(parts) < 3:
            return None
        
        timestamp = parts[0]
        level = parts[1].strip('[]')
        message = parts[2]
        
        return {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
    except Exception:
        return None