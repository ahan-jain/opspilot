import os
import json
from datetime import datetime, timedelta
from typing import Dict, List

def search_logs(query: str = None, pattern: str = None, time_range: str = "1h") -> Dict:
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

    search_term = query or pattern
    if not search_term:
        return {
            "matches": [],
            "count": 0,
            "error": "Must provide either 'query' or 'pattern' parameter"
        }
    cutoff_time = _parse_time_range(time_range)
    
    log_dir = "/app/data/logs"

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
                
                # Check if matches search_term
                if ' OR ' in search_term or '|' in search_term:
                    terms = [t.strip().lower() for t in search_term.replace('|', ' OR ').split(' OR ')]
                else:
                    terms = [search_term.lower()]

                if any(term in log_entry["message"].lower() for term in terms):
                    matches.append(log_entry)
    
    matches.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "matches": matches[:100],  # Limit to 100 results
        "count": len(matches),
        "time_range": time_range,
        "search_term": search_term,
        "searched_at": datetime.now().isoformat()
    }

def _parse_time_range(time_range: str) -> datetime:
    now = datetime.now()

    if time_range.startswith("last_"):
        time_range = time_range[5:]
    
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
    try:
        date, time, level, message = line.strip().split(" ", 3)

        timestamp = f"{date}T{time}"
        level = level.strip("[]")

        return {
            "timestamp": timestamp,
            "level": level,
            "message": message
        }
    except Exception:
        return None