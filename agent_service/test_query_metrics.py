import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tools.query_metrics import query_metrics
import json

def test_query_metrics():
    print("=== Test 1: Error rate during incident ===")
    result = query_metrics(
        metric_name="error_rate",
        start="2024-12-29T09:20:00",
        end="2024-12-29T09:40:00",
        interval="5m"
    )
    print(f"Found {result['count']} datapoints")
    print(f"Aggregates: {json.dumps(result['aggregates'], indent=2)}")
    print()
    
    print("\n=== Test 2: Response time - last 90 minutes ===")
    result = query_metrics(
        metric_name="response_time",
        start="2024-12-29T09:00:00",
        end="2024-12-29T10:30:00",
        interval="5m"
    )
    print(f"Count: {result['count']}")
    print(f"Max response time: {result['aggregates']['max']}ms")
    
    print("=== Test 3: CPU usage during recovery ===")
    result = query_metrics(
        metric_name="cpu_usage",
        start="2024-12-29T09:30:00",
        end="2024-12-29T09:50:00",
        interval="5m"
    )
    print(f"Average CPU: {result['aggregates']['avg']:.2f}%")
    print(f"Peak CPU: {result['aggregates']['max']:.2f}%")

if __name__ == "__main__":
    test_query_metrics()