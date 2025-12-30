import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tools.search_logs import search_logs
import json

def test_search_logs():
    print("=== Test 1: Search for 'error' ===")
    result = search_logs(query="error", time_range="24h")
    print(f"Found {result['count']} matches")
    print(json.dumps(result['matches'][:3], indent=2))
    print()
    
    print("=== Test 2: Search for 'payment' ===")
    result = search_logs(query="payment", time_range="1h")
    print(f"Found {result['count']} matches")
    print(json.dumps(result['matches'], indent=2))
    print()
    
    print("=== Test 3: Search for 'database' ===")
    result = search_logs(query="database", time_range="1h")
    print(f"Found {result['count']} matches")
    print(json.dumps(result['matches'], indent=2))

if __name__ == "__main__":
    test_search_logs()