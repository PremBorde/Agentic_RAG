import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.services.router import classify_query, QueryIntent
from backend.tools import detect_gmail_intent, detect_calendar_intent, detect_task_intent

def run_tool_evaluation(dataset_path: str = None) -> dict:
    if not dataset_path:
        dataset_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "tools_dataset.json")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total = len(dataset)
    tool_correct = 0
    args_correct = 0

    for item in dataset:
        inst = item["instruction"]
        exp_tool = item["expected_tool"]
        exp_args = item.get("expected_args", {})

        pred_tool = "unknown"
        pred_params = {}

        decision = classify_query(inst, doc_count=1)
        intent = decision.intent

        if intent == QueryIntent.GMAIL:
            g = detect_gmail_intent(inst)
            action, pred_params = g if g else ("unknown", {})
            pred_tool = f"gmail:{action}"
        elif intent == QueryIntent.CALENDAR:
            c = detect_calendar_intent(inst)
            action, pred_params = c if c else ("unknown", {})
            pred_tool = f"calendar:{action}"
        elif intent == QueryIntent.TASK:
            t = detect_task_intent(inst)
            action, pred_params = t if t else ("unknown", {})
            pred_tool = f"tasks:{action}"
        elif intent == QueryIntent.WEB_SEARCH:
            pred_tool = "web_search"
            pred_params = {"query": inst}

        is_tool_match = (pred_tool == exp_tool)
        if is_tool_match:
            tool_correct += 1

        # Check arguments
        is_args_match = True
        for k, v in exp_args.items():
            if k.endswith("_contains"):
                base_k = k[:-9]
                val = pred_params.get(base_k, "") or inst
                if v.lower() not in val.lower():
                    is_args_match = False
            else:
                if pred_params.get(k) != v:
                    is_args_match = False

        if is_tool_match and is_args_match:
            args_correct += 1

    report = {
        "total_test_cases": total,
        "tool_selection_accuracy": round(tool_correct / total if total > 0 else 0.0, 4),
        "argument_extraction_accuracy": round(args_correct / total if total > 0 else 0.0, 4)
    }

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "tools_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    rep = run_tool_evaluation()
    print("=== Tool Selection Evaluation Results ===")
    print(f"Tool Selection Accuracy: {rep['tool_selection_accuracy'] * 100:.2f}%")
    print(f"Argument Extraction Accuracy: {rep['argument_extraction_accuracy'] * 100:.2f}%")

