# Personal AI Agent Studio — Comprehensive Intelligence Benchmark Report

**Execution Timestamp**: 2026-11-03T17:31:29Z  
**Python Runtime**: 3.11.9 (win32)

---

## 1. Intent Classification & Routing Performance
- **Accuracy**: **100.00%** (50/50)
- **Fast-Path False Positive Rate**: **0.00%**
- **LLM API Calls Avoided**: **10**
- **Classification Latency**: p50 = **0.316ms** | p95 = **1.055ms**

---

## 2. Advanced RAG Retrieval Engine Comparison
| Configuration | MRR | Precision@1 | Precision@4 | Recall@4 | NDCG@4 | p50 Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Existing FAISS Baseline | 0.6500 | 44.0% | 25.0% | 35.0% | 0.4850 | 83.06ms |
| Improved FAISS Dense | 0.9333 | 88.0% | 47.0% | 100.0% | 0.9414 | 6.57ms |
| Pure BM25 Lexical | 1.0000 | 100.0% | 49.0% | 100.0% | 0.9897 | 0.1ms |
| Hybrid FAISS + BM25 (RRF) | 0.7467 | 64.0% | 47.0% | 92.0% | 0.7886 | 6.05ms |
| Hybrid + FlashRank Reranker | 0.9800 | 96.0% | 49.0% | 100.0% | 0.9775 | 52.35ms |

---

## 3. Tool Selection & Argument Extraction
- **Tool Dispatch Accuracy**: **100.00%**
- **Argument Extraction Accuracy**: **100.00%**

---

## 4. Multi-Step Workflows & HITL Safety
- **Workflow Detection Rate**: **100.00%**
- **HITL Two-Phase Safety Compliance**: **100.00%** (0 unauthorized writes)

---

## 5. Latency Telemetry Breakdown
- **Zero-LLM Fast Path (p50)**: **0.018ms**
- **Deterministic Intent Router (p50)**: **0.411ms**
- **Hybrid Retrieval + Reranking (p50)**: **52.35ms**
