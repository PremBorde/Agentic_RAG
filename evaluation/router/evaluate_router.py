import os
import sys
import json
import csv
import time
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.services.router import classify_query, QueryIntent

def run_router_evaluation(dataset_path: str = None) -> dict:
    if not dataset_path:
        dataset_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "router_dataset.json")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total_samples = len(dataset)
    correct_count = 0
    confusion_matrix = defaultdict(lambda: defaultdict(int))
    class_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    fast_path_count = 0
    fast_path_false_positives = 0
    latencies = []

    for item in dataset:
        query = item["query"]
        expected = item["expected_intent"]
        doc_count = item.get("doc_count", 1)

        t0 = time.perf_counter()
        decision = classify_query(query, doc_count=doc_count)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        predicted = decision.intent.value if hasattr(decision.intent, "value") else str(decision.intent)
        confusion_matrix[expected][predicted] += 1

        if decision.is_fast_path:
            fast_path_count += 1
            if predicted != expected:
                fast_path_false_positives += 1

        if predicted == expected:
            correct_count += 1
            class_stats[expected]["tp"] += 1
        else:
            class_stats[predicted]["fp"] += 1
            class_stats[expected]["fn"] += 1

    accuracy = correct_count / total_samples if total_samples > 0 else 0.0
    sorted_latencies = sorted(latencies)
    p50_latency = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0.0
    p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0.0

    # Compute Precision, Recall, F1 for each class
    metrics_per_class = {}
    for cls, s in class_stats.items():
        tp, fp, fn = s["tp"], s["fp"], s["fn"]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        metrics_per_class[cls] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn
        }

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_samples": total_samples,
        "correct_samples": correct_count,
        "accuracy": round(accuracy, 4),
        "fast_path_count": fast_path_count,
        "fast_path_false_positives": fast_path_false_positives,
        "fast_path_fp_rate": round(fast_path_false_positives / fast_path_count if fast_path_count > 0 else 0.0, 4),
        "api_calls_avoided": fast_path_count - fast_path_false_positives,
        "latency_ms": {
            "p50": round(p50_latency, 3),
            "p95": round(p95_latency, 3),
            "mean": round(sum(latencies) / len(latencies) if latencies else 0.0, 3)
        },
        "per_class_metrics": metrics_per_class,
        "confusion_matrix": {k: dict(v) for k, v in confusion_matrix.items()}
    }

    # Save reports
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    with open(os.path.join(reports_dir, "router_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save confusion matrix as CSV
    all_classes = sorted(list(set(list(confusion_matrix.keys()) + [c for row in confusion_matrix.values() for c in row.keys()])))
    with open(os.path.join(reports_dir, "router_confusion_matrix.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Expected \\ Predicted"] + all_classes)
        for expected_cls in all_classes:
            row = [expected_cls] + [confusion_matrix[expected_cls].get(pred_cls, 0) for pred_cls in all_classes]
            writer.writerow(row)

    return report

if __name__ == "__main__":
    rep = run_router_evaluation()
    print(f"=== Router Evaluation Results ===")
    print(f"Accuracy: {rep['accuracy'] * 100:.2f}% ({rep['correct_samples']}/{rep['total_samples']})")
    print(f"Latency p50: {rep['latency_ms']['p50']}ms | p95: {rep['latency_ms']['p95']}ms")
    print(f"Fast-path FP Rate: {rep['fast_path_fp_rate'] * 100:.2f}% | API Calls Avoided: {rep['api_calls_avoided']}")

