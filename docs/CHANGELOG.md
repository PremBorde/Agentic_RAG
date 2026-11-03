# Changelog

All notable changes to the Personal AI Agent Studio codebase are documented in this file.

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

