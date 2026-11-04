# Architecture & Technical Design: Personal AI Agent Studio

## 1. System Overview
Personal AI Agent Studio is a production-grade, local-first agentic workspace combining:
- **Retrieval-Augmented Generation (RAG)** with persistent FAISS vector storage and local embeddings.
- **Deterministic Intent Routing (`router.py`)** enforcing zero-token fast paths, RAG query isolation, and direct tool dispatch.
- **LangGraph Multi-Intent Orchestration** capable of planning, multi-step tool composition, and dynamic context gathering.
- **Human-in-the-Loop (HITL) Safety Engine** enforcing two-phase approval barriers on sensitive external write actions.
- **SQLite Relational Persistence** storing conversation threads, messages, tasks, memories, and pending proposals across sessions and devices.
- **Dual-Mode Authentication** supporting both standalone PBKDF2 password registration/login and Google Workspace OAuth.
- **Synchronized SSE Streaming Pipeline** guaranteeing sequential token streaming, staged component mount queues, and atomic persistence.
- **High-Performance React Single-Page Application (SPA)** utilizing Vite, dynamic code-splitting, manual chunk grouping, and an editorial burgundy-and-cream interface.

```
                      +---------------------------------------+
                      |       React 19 SPA (Vite / Tailwind)  |
                      |  - Dynamic Code Splitting (<100kB core)|
                      |  - Procedural Mascot Avatar Engine    |
                      |  - SQLite Synced Conversation History |
                      +-------------------+-------------------+
                                          |
                                          | HTTP / SSE Stream
                                          v
                      +---------------------------------------+
                      |         FastAPI Gateway Server        |
                      |  - Session Middleware & CORS          |
                      |  - Standalone & Google OAuth Auth     |
                      |  - Health & Telemetry (/health)       |
                      |  - SSE Streaming (/api/chat/stream)   |
                      +-------------------+-------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
                v                                                   v
+-------------------------------+                   +-------------------------------+
|   Zero-Latency Fast Path      |                   |  Deterministic Intent Router  |
| - Instant Greeting (<0.5ms)   |                   | - Strict Prefix Strip & Regex |
| - Direct Small Talk (<0.5ms)  |                   | - 100% Zero Substantive Hijack|
+-------------------------------+                   +---------------+---------------+
                                                                    |
                +---------------------------------------------------+
                |
                +-------------------+-------------------+-------------------+
                |                   |                   |                   |
                v                   v                   v                   v
+-----------------------+ +-------------------+ +-------------------+ +-------------------+
|  FAISS Vector Store   | |  Google Workspace | | Task & Memory DB  | |  HITL Approval    |
| - Persistent Disk Path| | - Gmail Read/Draft| | - Tasks & Reminders| | - Two-Phase Commit|
| - SHA-256 Deduplication| | - Calendar Events | | - Long-term Prefs | | - Pending Actions |
| - Single-Doc Deletion | | - Fernet Encrypted| | - SQLite Storage  | | - Explicit Cards  |
+-----------------------+ +-------------------+ +-------------------+ +-------------------+
```

---

## 2. Component Architecture

### A. Advanced Hybrid RAG Engine (`backend/services/hybrid_retriever.py`, `chunking.py`, `parsers.py`)
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (384 dimensions, local ONNX CPU execution via `FastEmbed`). Zero document text sent externally.
- **Disk Persistence**: Serialized into `data/vector_store/` using native FAISS `save_local` / `load_local` alongside `documents_registry.json` and `bm25_store.json`.
- **Lexical Matching**: `rank-bm25` (`BM25Okapi`) for exact technical alphanumeric identifiers (`DAA-4`, `BC-3`, `0/1 knapsack`, `BCNF`).
- **Score Fusion**: Reciprocal Rank Fusion (RRF, $k=60$) combining semantic and lexical rankings.
- **Local Reranker**: FlashRank `ms-marco-TinyBERT-L-2-v2` (3.2MB local ONNX model) providing cross-encoder precision without heavy GPU dependencies.
- **Structural Chunking**: Sentence-boundary preservation using `(?<=[.!?])\s+`, prepending section headings to every chunk to avoid losing hierarchical context.
- **Multi-Format Parsers**: Structure-aware parsers for PDF (PyPDF), DOCX (python-docx), CSV (header-aware record blocks), JSON (hierarchical blocks), Markdown/TXT, and YouTube transcripts.
- **Deduplication Engine**: Computes SHA-256 hash of inbound content before splitting. Duplicate documents are rejected with existing record references.
- **Document Management**: Document entries track `doc_id`, `chunk_count`, `content_hash`, and rich source metadata (`chunk_id`, `page_number`, `section_heading`, `source_location`) in `documents_registry.json`. Single-document deletion reconstructs remaining documents in both FAISS and BM25 indices simultaneously.

### B. Deterministic Intent Routing Engine (`backend/services/router.py`)
- **Normalized Prefix Stripping**: Separates polite prefixes (*"Hi"*, *"Good morning"*, *"Thanks"*) from substantive commands (*"Hi, search my uploaded PDF"*, *"Good morning, check my unread emails"*).
- **Zero-Token Fast Paths**: Resolves pure small talk, greetings, capability queries, and status checks in sub-millisecond latency (**p50: 0.407ms**) with **0 LLM API calls**.
- **RAG Query Isolation**: Document retrieval is strictly bounded to explicit document keywords and indexed coursework. General questions and live web queries are shielded from syllabus chunk pollution.
- **Live Internet Routing**: Detects live web search intents (*"for web search today top 5 news"*) and immediately dispatches DuckDuckGo with fallback timeouts.

### C. Human-in-the-Loop (HITL) Safety Engine (`backend/services/approval_service.py`)
- **Strict Boundary**: Mutating external state (e.g. `send_email`, `create_calendar_event`, `delete_calendar_event`) CANNOT execute autonomously.
- **Two-Phase Action Protocol**:
  1. **Phase 1 (Proposal)**: The agent calls `propose_action()`, creating a record in SQLite `pending_actions` in state `'pending'` with cryptographic ID `act_<uuid>`.
  2. **Phase 2 (Execution)**: The frontend displays an interactive `ActionProposalCard`. The user must click **Approve** (calling `POST /api/actions/approve/{action_id}`) or **Cancel**.
  3. Once approved, `execute_approved_action()` checks single-execution idempotency, fires the Google API call, and marks the record `'completed'`. Duplicate execution attempts are rejected.

### D. SQLite Conversation Persistence (`backend/services/database.py`)
- **Normalized Multi-User Schema**:
  - `users`: User profiles with `id`, `email`, `display_name`, `password_hash`, `google_access_token`, `google_refresh_token`, `token_expires_at`, `created_at`, `updated_at`.
  - `conversations`: Primary thread registry with `id`, `user_id`, `title`, `model`, `created_at`, `updated_at`, `last_message_at`, `archived_at`. Indexed by `user_id` and `updated_at`.
  - `messages`: Historical turns (`id`, `conversation_id`, `user_id`, `sender`, `text`, `source`, `message_type`, `metadata_json`, `created_at`). Indexed by `conversation_id` and `created_at`.
  - `tasks`: Task management items with status, priority, and due dates.
  - `memories`: Persistent user preferences incorporated into system prompts.
  - `pending_actions`: Staged actions pending user approval.
- **Cold-Start Recovery**: When thread history is absent from RAM, `get_thread_context_str` dynamically queries SQLite, restoring thread context across server restarts.

### E. Dual-Mode Authentication & Security (`backend/routes/auth.py`)
- **Standalone Email/Password Auth**:
  - `POST /api/auth/register`: Hashes passwords using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a 16-byte random salt.
  - `POST /api/auth/login`: Constant-time comparison via `secrets.compare_digest` to prevent timing attacks.
  - `GET /api/auth/me`: Sanitizes user profiles, omitting password hashes and OAuth credentials.
- **Upload Security**: Enforces 25MB maximum upload limits, extension whitelisting (`.pdf`, `.txt`, `.md`, `.csv`, `.json`), and path traversal sanitization via `os.path.basename`.
- **Zero-Secret Health Check**: `GET /health` reports database, vector store, and OAuth status without exposing keys or tokens.

### F. Synchronized SSE Streaming Pipeline (`backend/services/chat_service.py`)
- Immediate persistence of inbound user message upon request arrival.
- SSE sequence: `stage (thinking)` $\to$ `meta (source & citations)` $\to$ progressive `token` deltas $\to$ `stage (success)`.
- Assistant message, retrieved citations, and action proposal references persisted atomically upon completion.
