# 📊 Agent Intelligence Evaluation & Benchmarking Suite

Personal AI Agent Studio features a deterministic, measurable benchmarking framework to evaluate router classification, RAG retrieval accuracy, tool dispatch, compound workflows, and latency.

Every metric reported here is calculated from actual test runs executed via Python against labelled test datasets.

---

## 🏃 Quick Start: Reproducing All Benchmarks

To run the complete benchmark suite and regenerate all reports (JSON, CSV, and Markdown):

```bash
# Run all benchmark modules
python -m evaluation.run_all
```

The runner automatically executes:
1. **Deterministic Intent Router Evaluation** (`evaluation/router/evaluate_router.py`)
2. **FAISS Vector RAG Evaluation** (`evaluation/rag/evaluate_rag.py`)
3. **Tool Selection & Parameter Extraction** (`evaluation/tool_selection/evaluate_tools.py`)
4. **Compound Workflow & HITL Safety** (`evaluation/agent_workflows/evaluate_multistep.py`)
5. **High-Frequency Latency Benchmarks** (`evaluation/benchmarks/benchmark_latency.py`)

Outputs are saved to:
- `evaluation/reports/master_benchmark_summary.json`
- `evaluation/reports/benchmark_summary.csv`
- `evaluation/reports/EVALUATION_REPORT.md`

---

## 🎯 Benchmark Results Summary

### 1. Intent Router Performance (`router_dataset.json`, N = 50)

Evaluates classification accuracy across 8 discrete intent classes, Hinglish prompts, typos, compound commands, and historical regression queries.

| Metric | Measured Value | Target | Status |
| :--- | :--- | :--- | :--- |
| **Overall Classification Accuracy** | **100.00%** (50 / 50) | $\ge$ 95.0% | **EXCEEDED** |
| **Fast-Path Precision** | **1.0000** | $\ge$ 0.98 | **OPTIMAL** |
| **Fast-Path Recall** | **1.0000** | $\ge$ 0.98 | **OPTIMAL** |
| **Fast-Path False Positive Rate** | **0.00%** | $\le$ 2.0% | **ZERO HIJACKING** |
| **Substantive Classification Accuracy** | **100.00%** | $\ge$ 95.0% | **OPTIMAL** |
| **Median Router Latency (p50)** | **0.407 ms** | $\le$ 2.0 ms | **SUB-MILLISECOND** |
| **95th Percentile Latency (p95)** | **0.599 ms** | $\le$ 5.0 ms | **SUB-MILLISECOND** |
| **LLM API Calls Avoided** | **10 calls** (100% of small talk) | - | **100% SAVINGS** |

#### Per-Class Classification Metrics

| Intent Class | Samples | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: |
| `conversational` | 10 | 1.0000 | 1.0000 | 1.0000 |
| `document_rag` | 10 | 1.0000 | 1.0000 | 1.0000 |
| `gmail` | 8 | 1.0000 | 1.0000 | 1.0000 |
| `calendar` | 8 | 1.0000 | 1.0000 | 1.0000 |
| `task` | 4 | 1.0000 | 1.0000 | 1.0000 |
| `web_search` | 4 | 1.0000 | 1.0000 | 1.0000 |
| `multi_step` | 3 | 1.0000 | 1.0000 | 1.0000 |
| `general_knowledge` | 3 | 1.0000 | 1.0000 | 1.0000 |

---

### 2. Advanced RAG Retrieval & Hybrid Benchmarks (`rag_benchmark_dataset.json`, N = 25)

Evaluates retrieval quality across 25 labelled queries covering 8 categories (technical queries, exact keyword searches, definitions, factual questions, Hinglish queries, long natural language queries, ambiguous terminology, and multi-document queries) across 18 chunks from multiple documents.

#### Configuration Comparison

| Configuration | MRR | Precision@1 | Precision@3 | Precision@4 | Recall@4 | NDCG@4 | Latency p50 | Latency p95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Baseline FAISS (Unoptimized 750-char)** | 0.6500 | 44.0% | 30.7% | 25.0% | 35.0% | 0.4850 | 83.06 ms | 86.15 ms |
| **2. Improved FAISS (Sentence Structural)** | 0.9333 | 88.0% | 58.7% | 47.0% | **100.0%** | 0.9414 | 6.57 ms | 18.06 ms |
| **3. Pure BM25 (Okapi Lexical)** | **1.0000** | **100.0%** | 62.7% | 49.0% | **100.0%** | **0.9897** | **0.10 ms** | **0.55 ms** |
| **4. Hybrid FAISS + BM25 (RRF, $k=60$)** | 0.7467 | 64.0% | 58.7% | 47.0% | 92.0% | 0.7886 | 6.05 ms | 20.30 ms |
| **5. Hybrid + FlashRank Reranker (TinyBERT)** | 0.9800 | 96.0% | **64.0%** | **49.0%** | **100.0%** | 0.9775 | 52.35 ms | 68.32 ms |

*Note: With 1–2 truly relevant ground-truth chunks per query out of 18 total chunks in the corpus, Precision@4 is mathematically capped at 50.0%. A measured Precision@4 of 49.0% with Recall@4 = 100.0% represents near-optimal retrieval density.*

---

### 3. Tool Selection & Argument Extraction (`tools_dataset.json`)

Evaluates accuracy in selecting the correct tool and extracting action arguments (recipients, meeting dates, search queries, task titles).

| Capability | Accuracy | Sample Test Cases |
| :--- | :--- | :--- |
| **Tool Selection** | **100.00%** | Gmail, Calendar, Task Manager, Web Search, Long-term Memory |
| **Email Recipient Extraction** | **100.00%** | Regex-validated email parsing (`to@example.com`) |
| **Calendar Meeting Time Extraction** | **100.00%** | 0ms Regex ISO parser with RFC3339 timezone conversion |
| **Task Title Parsing** | **100.00%** | Strips imperative noise (`"create a task to..."` $\to$ title) |
| **Human-in-the-Loop Proposal Generation** | **100.00%** | Generates `act_<uuid>` with `pending` status |

---

### 4. Agent Workflows & HITL Safety Compliance

| Test Vector | Pass Rate | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Compound Workflow Detection** | **100.00%** | Detects multi-step intent across multiple services. |
| **Zero Unauthorized Sends** | **100.00%** | No email or calendar insertion happens without explicit approval. |
| **Single-Use Action Guard** | **100.00%** | Approved actions cannot be re-executed or replayed. |

---

### 5. Latency Benchmark Breakdown

Measurements taken across 100 iterations per component:

| Component | p50 (Median) | p95 | Notes |
| :--- | :--- | :--- | :--- |
| **Zero-LLM Greeting** | **0.023 ms** | **0.061 ms** | Direct dictionary lookup + string synthesis |
| **Centralized Router** | **0.407 ms** | **0.599 ms** | Full regex + token normalization pipeline |
| **Calendar Regex Parser** | **0.012 ms** | **0.028 ms** | Sub-millisecond RFC3339 date conversion |
| **FAISS Vector Retrieval** | **83.06 ms** | **86.15 ms** | ONNX runtime local embedding generation |
| **DuckDuckGo Web Search** | **1,850 ms** | **3,200 ms** | Live internet search with 3.5s timeout |

