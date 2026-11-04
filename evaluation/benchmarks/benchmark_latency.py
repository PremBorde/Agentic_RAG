import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.services.router import classify_query
from backend.tools import get_direct_greeting_response

def run_latency_benchmarks(iterations: int = 50) -> dict:
    router_latencies = []
    greeting_latencies = []

    test_query = "Add an note on my calender that today i am focusing in RAG project"
    greeting_query = "Good morning"

    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = classify_query(test_query, doc_count=1)
        router_latencies.append((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        _ = get_direct_greeting_response(greeting_query)
        greeting_latencies.append((time.perf_counter() - t1) * 1000)

    router_sorted = sorted(router_latencies)
    greeting_sorted = sorted(greeting_latencies)

    report = {
        "iterations": iterations,
        "router_latency_ms": {
            "p50": round(router_sorted[len(router_sorted) // 2], 3),
            "p95": round(router_sorted[int(len(router_sorted) * 0.95)], 3),
            "mean": round(sum(router_latencies) / len(router_latencies), 3)
        },
        "zero_llm_greeting_latency_ms": {
            "p50": round(greeting_sorted[len(greeting_sorted) // 2], 3),
            "p95": round(greeting_sorted[int(len(greeting_sorted) * 0.95)], 3),
            "mean": round(sum(greeting_latencies) / len(greeting_latencies), 3)
        }
    }

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "latency_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    rep = run_latency_benchmarks()
    print("=== Latency Benchmark Results ===")
    print(f"Router Latency: p50={rep['router_latency_ms']['p50']}ms, p95={rep['router_latency_ms']['p95']}ms")
    print(f"Zero-LLM Greeting: p50={rep['zero_llm_greeting_latency_ms']['p50']}ms, p95={rep['zero_llm_greeting_latency_ms']['p95']}ms")

