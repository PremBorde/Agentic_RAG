# Changelog

All notable changes to the Personal AI Agent Studio codebase are documented in this file.

## [3.1.0] - Production Readiness & Master Evaluation Upgrade - 2026-11-03

### Added
- **Complete Multi-User Conversation Persistence (Phase 1)**:
  - Upgraded SQLite database schema with `display_name`, `password_hash`, `updated_at` on `users`.
  - Added `last_message_at`, `archived_at` on `conversations` with composite indexes (`idx_conversations_user`, `idx_conversations_updated`).
  - Added `user_id` and `message_type` on `messages` with composite index (`idx_messages_conv_created`).
  - Implemented cold-start context recovery in `backend/memory.py`: dynamic SQLite context retrieval when thread history is absent from RAM.
  - Implemented immediate turn streaming persistence in `backend/services/chat_service.py`: user turns recorded immediately; assistant responses, citations, and proposals committed atomically upon stream completion.
  - Added session-enforced thread ownership authorization: `403 Forbidden` raised if a user requests a conversation belonging to another user.
- **Agent Intelligence Evaluation & Benchmarking Suite (Phase 2)**:
  - Created standardized evaluation datasets: `router_dataset.json` (50 queries), `rag_dataset.json`, `tools_dataset.json`.
  - Developed automated evaluators:
    - `evaluation/router/evaluate_router.py`: Measures classification accuracy, precision, recall, F1, and fast-path FP rate.
    - `evaluation/rag/evaluate_rag.py`: Evaluates vector retrieval MRR and Precision@K.
    - `evaluation/tool_selection/evaluate_tools.py`: Tests tool dispatch and argument extraction.
    - `evaluation/agent_workflows/evaluate_multistep.py`: Asserts compound workflow detection and HITL safety compliance.
    - `evaluation/benchmarks/benchmark_latency.py`: Measures p50 and p95 latencies across components.
  - Created master benchmark runner `python -m evaluation.run_all` generating JSON, CSV, and Markdown reports.
- **Standalone Authentication & Security Hardening (Phase 3)**:
  - Implemented standalone registration and login endpoints: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.
  - Cryptographically secure password hashing using **PBKDF2-HMAC-SHA256** (100,000 iterations, 16-byte random salt, constant-time `secrets.compare_digest`).
  - Hardened document upload endpoint: 25MB maximum upload limit, extension whitelisting (`.pdf`, `.txt`, `.md`, `.csv`, `.json`), and path traversal sanitization.
  - Added production health check endpoint: `GET /health` verifying database, vector store, and OAuth configuration without exposing secrets.
- **Production Containerization**:
  - Authored multi-stage `Dockerfile` with Node 20 frontend builder and Python 3.11 slim runtime.
  - Authored `docker-compose.yml` with persistent volume mount for `data/` and healthcheck instruction.
  - Added `.dockerignore` and production `.env.example`.
- **Full Regression Test Suite (Phase 4)**:
  - Implemented `tests/test_full_regression.py` covering all 17 capabilities with 100% pass rate.

### Fixed
- **Router Web Search Recognition Bug**:
  - Fixed query classification where queries starting with `"For web search..."` fell through to document RAG.
  - Overhauled regex matching to strictly isolate RAG from general and live web searches.
- **Continuation Pattern Over-matching**:
  - Removed over-broad token checks that falsely intercepted calendar queries into Gmail rechecks.

---

## [3.0.0] - Production Readiness Upgrade - 2026-10-30

### Added
- **Persistent FAISS Vector Storage**:
  - Saved FAISS index and metadata to disk under `data/vector_store/`.
  - Automatic index recovery on backend startup.
  - SHA-256 content deduplication preventing redundant chunk indexing.
  - Single-document deletion endpoint: `DELETE /api/documents/{doc_id}`.
- **SQLite Database-Backed Conversation History**:
  - Added `conversations` and `messages` tables to `data/agent_studio.db`.
  - Introduced endpoints:
    - `GET /api/conversations` (list threads with pagination)
    - `GET /api/conversations/{thread_id}` (fetch persisted turns)
    - `POST /api/conversations` (batch sync turns from frontend)
    - `PATCH /api/conversations/{thread_id}/title` (rename thread)
    - `DELETE /api/conversations/{thread_id}` (delete thread and cascade messages)
  - Synchronized frontend state on startup with fallback to `localStorage`.
- **LangGraph Multi-Intent Orchestrator**:
  - Multi-intent compound planning supporting workflows such as *search email -> summarize -> propose calendar event*.
  - Strict preservation of Human-in-the-Loop (HITL) safety: sensitive actions (sending email, booking meetings) generate approval cards before committing.
- **Fast-Path Zero-LLM Direct Streaming**:
  - Direct handling for greetings and negative declinations (`"No"`, `"Nope"`, `"Nothing"`, `"I'm good"`) delivering responsive turns in <5ms without consuming API quota.
- **Documentation**:
  - Created `AGENT.md` as the root knowledge base.
  - Created `ARCHITECTURE.md` documenting technical structure, RAG pipeline, and security flow.

### Changed
- **Gemini Model Optimization**:
  - Migrated primary model to active `gemini-3.5-flash-lite`.
  - Added automatic model failover and exponential retry logic for rate limits and deprecated model errors.
- **Frontend Code Splitting**:
  - Converted `TaskManagerModal` and `GoogleConnectModal` to `React.lazy()` dynamic imports.
  - Configured Vite/Rolldown manual chunks: `react-vendor`, `avatar-vendor`, and `markdown-vendor`.
  - Reduced main entry bundle from ~654 kB to 91 kB.
- **Google OAuth Hardening**:
  - Verified Fernet symmetric token encryption for stored access and refresh tokens.
  - Added auto-invalidation on refresh failures so frontend triggers re-authentication prompts cleanly.
