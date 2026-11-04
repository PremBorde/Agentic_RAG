import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.vector_store import vector_store, retriever

def run_rag_evaluation(dataset_path: str = None, k: int = 4) -> dict:
    if not dataset_path:
        dataset_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "rag_dataset.json")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    doc_count = len(vector_store.index_to_docstore_id)
    if doc_count == 0:
        return {
            "status": "warning",
            "message": "Vector store is empty. Ingest at least one document to benchmark retrieval.",
            "doc_count": 0
        }

    total_queries = len(dataset)
    reciprocal_ranks = []
    precision_scores = []
    latencies = []

    for item in dataset:
        q = item["question"]
        expected_kw = [w.lower() for w in item.get("expected_keywords", [])]

        t0 = time.perf_counter()
        docs = retriever.invoke(q)
        lat_ms = (time.perf_counter() - t0) * 1000
        latencies.append(lat_ms)

        # Check relevance
        first_rel_rank = 0
        relevant_chunks_found = 0

        for rank, doc in enumerate(docs[:k], start=1):
            content_lower = doc.page_content.lower()
            matches = [kw for kw in expected_kw if kw in content_lower]
            if len(matches) >= 1:
                relevant_chunks_found += 1
                if first_rel_rank == 0:
                    first_rel_rank = rank

        rr = 1.0 / first_rel_rank if first_rel_rank > 0 else 0.0
        reciprocal_ranks.append(rr)
        prec = relevant_chunks_found / len(docs[:k]) if docs else 0.0
        precision_scores.append(prec)

    mrr = sum(reciprocal_ranks) / total_queries if total_queries > 0 else 0.0
    avg_precision = sum(precision_scores) / total_queries if total_queries > 0 else 0.0
    sorted_latencies = sorted(latencies)
    p50_latency = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0.0
    p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_queries": total_queries,
        "indexed_chunks": doc_count,
        "k": k,
        "mrr": round(mrr, 4),
        "precision_at_k": round(avg_precision, 4),
        "latency_ms": {
            "p50": round(p50_latency, 3),
            "p95": round(p95_latency, 3),
            "mean": round(sum(latencies) / len(latencies) if latencies else 0.0, 3)
        }
    }

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "rag_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report

if __name__ == "__main__":
    rep = run_rag_evaluation()
    print("=== RAG Retrieval Evaluation Results ===")
    print(f"Indexed Chunks: {rep.get('indexed_chunks', 0)}")
    print(f"Mean Reciprocal Rank (MRR): {rep.get('mrr', 0.0):.4f}")
    print(f"Precision@{rep.get('k', 4)}: {rep.get('precision_at_k', 0.0) * 100:.2f}%")
    print(f"Retrieval Latency p50: {rep.get('latency_ms', {}).get('p50', 0)}ms | p95: {rep.get('latency_ms', {}).get('p95', 0)}ms")

