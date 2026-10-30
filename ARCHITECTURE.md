# Architecture & Technical Design: Personal AI Agent Studio

## 1. System Overview
Personal AI Agent Studio is a production-grade, local-first agentic workspace combining:
- **Retrieval-Augmented Generation (RAG)** with persistent FAISS vector storage and local embeddings.
- **LangGraph Multi-Intent Orchestration** capable of planning, multi-step tool composition, and dynamic context gathering.
- **Human-in-the-Loop (HITL) Safety Engine** enforcing two-phase approval barriers on sensitive external actions.
- **SQLite Relational Persistence** storing conversation threads, messages, tasks, memories, and pending proposals across sessions and devices.
- **Google Workspace Direct Integration** (Gmail search/reading/drafting and Calendar scheduling/availability checks) with Fernet-encrypted credentials.
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
                      |  - REST Endpoints (/api/conversations)|
                      |  - SSE Streaming (/api/chat/stream)   |
                      +-------------------+-------------------+
                                          |
                +-------------------------+-------------------------+
                |                                                   |
                v                                                   v
+-------------------------------+                   +-------------------------------+
|   Zero-Latency Fast Path      |                   |  LangGraph Agent Orchestrator |
| - Instant Greeting (<5ms)     |                   | - LLM Multi-Intent Decomposer |
| - Direct Declinations (<5ms)  |                   | - Tool Routing & Execution    |
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

### A. Persistent Vector Store Pipeline (`backend/vector_store.py`)
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (local CPU/GPU execution via HuggingFaceEmbeddings).
- **Disk Persistence**: Serialized into `data/vector_store/` using LangChain's native FAISS `save_local` and `load_local`.
- **Deduplication Engine**: Computes SHA-256 hash of inbound content before splitting. Duplicate documents are rejected with existing record references.
- **Document Management**: Document entries track `doc_id`, `chunk_count`, `content_hash`, and source metadata in `documents_registry.json`. Deletions trigger an in-memory document ID filter and index re-serialization.

### B. Multi-Intent Agent Architecture (`backend/graph.py` & `backend/services/chat_service.py`)
- **Fast-Path Intent Bypass**: Common conversational greetings and negative declinations bypass LLM inference completely, returning snappy token streams in under 5ms to save quota and latency.
- **Decomposition**: Complex compound queries (e.g. *"Find email from Sarah about project and schedule a meeting tomorrow at 2 PM"*) are mapped into a multi-phase execution graph:
  1. Retrieve information from source A (Gmail search & extraction).
  2. Compute secondary dependencies (Time parsing, meeting details).
  3. Formulate Action Proposal requiring Human Confirmation.
  4. Stream synthesized summary and mount `ActionProposalCard`.

### C. Human-in-the-Loop (HITL) Safety Engine (`backend/services/approval_service.py`)
- **Strict Boundary**: Mutating external state (e.g. `send_email`, `create_calendar_event`, `delete_calendar_event`) CANNOT execute autonomously.
- **Two-Phase Action Protocol**:
  1. **Phase 1 (Proposal)**: The agent calls `propose_action()`, creating a record in SQLite `pending_actions` in state `'pending'`.
  2. **Phase 2 (Execution)**: The frontend displays an interactive card. The user must click **Approve** (calling `POST /api/actions/approve/{action_id}`) or **Cancel**.
  3. Once approved, `execute_approved_action()` checks single-execution idempotency, fires the Google API call, and marks the record `'completed'`.

### D. SQLite Conversation Persistence (`backend/services/database.py`)
- Tables:
  - `conversations`: Primary thread registry (`id`, `user_id`, `title`, `model`, `created_at`, `updated_at`).
  - `messages`: Historical turns (`id`, `conversation_id`, `sender`, `text`, `source`, `metadata_json`, `created_at`).
  - `tasks`: Task management items with status, priority, and due dates.
  - `memories`: Persistent user preferences incorporated into system prompts.
  - `pending_actions`: Staged actions pending user approval.

### E. Frontend Performance Optimization
- **Dynamic Imports**: Modals (`TaskManagerModal`, `GoogleConnectModal`) are loaded on-demand via `React.lazy` and `React.Suspense`.
- **Vendor Chunk Splitting**: Configured in Vite/Rolldown to isolate `react-vendor` (323 kB), `avatar-vendor` (178 kB), and `markdown-vendor` (49 kB).
- **Core App Footprint**: Main application chunk reduced from ~654 kB to 91 kB (<100 kB bundle size).

