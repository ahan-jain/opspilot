import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tools.generate_report import generate_report

def test_generate_report():
    findings = [
        {
            "type": "log",
            "summary": "Payment gateway timeout errors",
            "details": {
                "count": 15,
                "time_range": "09:18-09:30",
                "sample_messages": [
                    "Failed to process payment: timeout connecting to payment gateway",
                    "Payment retry successful for order_id=98765"
                ]
            }
        },
        {
            "type": "metric",
            "summary": "Error rate spike detected",
            "details": {
                "metric": "error_rate",
                "aggregates": {
                    "avg": 13.76,
                    "max": 18.7,
                    "p95": 18.7
                }
            }
        },
        {
            "type": "metric",
            "summary": "Response time degradation",
            "details": {
                "metric": "response_time",
                "aggregates": {
                    "avg": 485.3,
                    "max": 720.8,
                    "p95": 680.5
                }
            }
        },
        {
            "type": "ticket",
            "summary": "Investigate payment gateway connectivity",
            "details": {
                "ticket_id": "TICKET-A3F2B9C1",
                "severity": "high"
            }
        }
    ]
    
    result = generate_report(findings)
    
    print("=== REPORT ===")
    print(result["report"])
    print("\n=== SUMMARY ===")
    print(result["summary"])
    print(f"\n=== FINDINGS COUNT: {result['findings_count']} ===")

if __name__ == "__main__":
    test_generate_report()