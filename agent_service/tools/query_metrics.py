import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics

def query_metrics(
    metric: str = None,
    metric_type: str = None,
    metric_name: str = None,
    metric_names: str = None,
    start: str = "1h",
    end: str = "now",
    time_range: str = None,
    interval: str = "5m"
) -> Dict:
    """
    Query time-series metrics data.
    
    Args:
        metric: Metric to query (error_rate, response_time, cpu_usage, memory_usage)
        start: Start time (ISO format or relative like "1h", "24h")
        end: End time (ISO format or "now")
        interval: Data point interval (5m, 15m, 1h)
    
    Returns:
        {
            "metric": str,
            "datapoints": [{"timestamp": str, "value": float}, ...],
            "aggregates": {"min": float, "max": float, "avg": float, "p95": float},
            "interval": str,
            "time_range": {"start": str, "end": str}
        }
    """
    if time_range:
        start = time_range

    metric_to_query = metric or metric_type or metric_name or metric_names
    
    if not metric_to_query:
        return {
            "error": "Must provide metric, metric_type, or metric_name(s) parameter",
            "datapoints": [],
            "aggregates": {}
        }
    
    start_time = _parse_time(start)
    end_time = _parse_time(end)
    
    # Load metrics data
    metrics_file = "/app/data/metrics/metrics.json"
    
    with open(metrics_file, 'r') as f:
        all_metrics = json.load(f)
    
    if metric_to_query not in all_metrics:
        return {
            "error": f"Metric '{metric_to_query}' not found",
            "available_metrics": list(all_metrics.keys())
        }
    
    # Filter datapoints by time range
    raw_datapoints = all_metrics[metric_to_query]
    filtered_datapoints = []
    
    for point in raw_datapoints:
        point_time = datetime.fromisoformat(point["timestamp"])
        if start_time <= point_time <= end_time:
            filtered_datapoints.append(point)
    
    # Calculate aggregates
    if filtered_datapoints:
        values = [p["value"] for p in filtered_datapoints]
        aggregates = {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p95": _percentile(values, 95)
        }
    else:
        aggregates = {"min": 0, "max": 0, "avg": 0, "p95": 0}
    
    return {
        "metric": metric_to_query,
        "datapoints": filtered_datapoints,
        "aggregates": aggregates,
        "interval": interval,
        "time_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "count": len(filtered_datapoints)
    }

def _parse_time(time_str: str) -> datetime:
    if time_str == "now":
        return datetime.utcnow()
    
    # Try relative time (e.g., "1h", "24h")
    if time_str.endswith('h'):
        hours = int(time_str[:-1])
        return datetime.utcnow() - timedelta(hours=hours)
    elif time_str.endswith('d'):
        days = int(time_str[:-1])
        return datetime.utcnow() - timedelta(days=days)
    
    # Try ISO format
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        # Default to now
        return datetime.utcnow()

def _percentile(values: List[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * (percentile / 100))
    return sorted_values[min(index, len(sorted_values) - 1)]