import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.services.router import classify_query, QueryIntent
from backend.tools import detect_multi_intent
from backend.services.approval_service import propose_action, get_pending_action, execute_approved_action

def run_multistep_evaluation() -> dict:
    scenarios = [
        {
            "query": "Find the email from Rahul, summarize it, and schedule a meeting for tomorrow at 3 PM",
            "expected_workflow": "email_and_calendar",
            "expected_tools": ["gmail", "calendar"],
            "requires_hitl": True
        },
        {
            "query": "Search emails for client feedback and create high priority tasks",
            "expected_workflow": "email_and_task",
            "expected_tools": ["gmail", "tasks"],
            "requires_hitl": False
        }
    ]

    total = len(scenarios)
    workflow_detection_success = 0
    hitl_enforcement_success = 0

    for sc in scenarios:
        decision = classify_query(sc["query"], doc_count=1)
        if decision.intent == QueryIntent.MULTI_STEP and decision.sub_action == sc["expected_workflow"]:
            workflow_detection_success += 1

        # Test HITL enforcement on sensitive multi-step actions
        if sc["requires_hitl"]:
            proposal = propose_action(
                action_type="create_calendar_event",
                summary="Meeting with Rahul",
                payload={"summary": "Meeting with Rahul", "start_time": "2026-11-04T15:00:00+05:30"}
            )
            act_id = proposal["action_id"]
            action_record = get_pending_action(act_id)
            if action_record and action_record["status"] == "pending":
                hitl_enforcement_success += 1
        else:
            hitl_enforcement_success += 1

    report = {
        "total_scenarios": total,
        "workflow_detection_rate": round(workflow_detection_success / total, 4),
        "hitl_safety_compliance": round(hitl_enforcement_success / total, 4)
    }

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "multistep_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    rep = run_multistep_evaluation()
    print("=== Multi-Step Agent Evaluation Results ===")
    print(f"Workflow Detection Rate: {rep['workflow_detection_rate'] * 100:.2f}%")
    print(f"HITL Safety Compliance: {rep['hitl_safety_compliance'] * 100:.2f}%")

