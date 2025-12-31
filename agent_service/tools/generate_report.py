from typing import Dict, List
from datetime import datetime

def generate_report(findings: List[Dict]) -> Dict:
    """
    Generate a markdown report from investigation findings.
    
    Args:
        findings: List of findings, each containing:
            {
                "type": "log" | "metric" | "ticket" | "observation",
                "summary": str,
                "details": dict,
                "timestamp": str (optional)
            }
    
    Returns:
        {
            "report": str (markdown),
            "summary": str (2-3 sentence overview),
            "findings_count": int
        }
    """
    if not findings:
        return {
            "report": "# Investigation Report\n\nNo findings to report.",
            "summary": "No significant findings.",
            "findings_count": 0
        }
    
    report_lines = []
    report_lines.append("# OpsPilot Investigation Report")
    report_lines.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report_lines.append(f"\n**Findings:** {len(findings)}")
    report_lines.append("\n---\n")
    
    report_lines.append("## Executive Summary\n")
    summary = _generate_summary(findings)
    report_lines.append(summary)
    report_lines.append("\n---\n")
    
    report_lines.append("## Detailed Findings\n")
    
    for i, finding in enumerate(findings, 1):
        finding_type = finding.get("type", "observation")
        finding_summary = finding.get("summary", "No summary provided")
        details = finding.get("details", {})
        
        report_lines.append(f"### {i}. {finding_type.upper()}: {finding_summary}\n")
        
        # Add type-specific formatting
        if finding_type == "log":
            count = details.get("count", 0)
            time_range = details.get("time_range", "unknown")
            report_lines.append(f"- **Occurrences:** {count}")
            report_lines.append(f"- **Time Range:** {time_range}")
            
            if "sample_messages" in details:
                report_lines.append(f"- **Sample Messages:**")
                for msg in details["sample_messages"][:3]:
                    report_lines.append(f"  - `{msg}`")
        
        elif finding_type == "metric":
            metric_name = details.get("metric", "unknown")
            aggregates = details.get("aggregates", {})
            report_lines.append(f"- **Metric:** {metric_name}")
            report_lines.append(f"- **Average:** {aggregates.get('avg', 0):.2f}")
            report_lines.append(f"- **Peak:** {aggregates.get('max', 0):.2f}")
            report_lines.append(f"- **P95:** {aggregates.get('p95', 0):.2f}")
        
        elif finding_type == "ticket":
            ticket_id = details.get("ticket_id", "unknown")
            severity = details.get("severity", "unknown")
            report_lines.append(f"- **Ticket ID:** {ticket_id}")
            report_lines.append(f"- **Severity:** {severity}")
        
        report_lines.append("") 
    

    if any(f.get("type") == "ticket" for f in findings):
        report_lines.append("---\n")
        report_lines.append("## Actions Taken\n")
        tickets = [f for f in findings if f.get("type") == "ticket"]
        for ticket in tickets:
            details = ticket.get("details", {})
            ticket_id = details.get("ticket_id", "unknown")
            report_lines.append(f"- Created {ticket_id} for investigation")
    
    report_markdown = "\n".join(report_lines)
    
    return {
        "report": report_markdown,
        "summary": summary,
        "findings_count": len(findings)
    }

def _generate_summary(findings: List[Dict]) -> str:
    finding_types = {}
    for finding in findings:
        ftype = finding.get("type", "observation")
        finding_types[ftype] = finding_types.get(ftype, 0) + 1
    
    summary_parts = []
    
    if "log" in finding_types:
        summary_parts.append(f"{finding_types['log']} log-related findings")
    
    if "metric" in finding_types:
        summary_parts.append(f"{finding_types['metric']} metric anomalies")
    
    if "ticket" in finding_types:
        summary_parts.append(f"{finding_types['ticket']} ticket(s) created")
    
    if summary_parts:
        summary = f"Investigation identified {', '.join(summary_parts)}. "
    else:
        summary = "Investigation completed. "
    
    # Add severity if any tickets were created
    tickets = [f for f in findings if f.get("type") == "ticket"]
    if tickets:
        severities = [t.get("details", {}).get("severity") for t in tickets]
        if "critical" in severities or "high" in severities:
            summary += "Immediate action recommended."
        else:
            summary += "Follow-up investigation recommended."
    
    return summary