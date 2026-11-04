# AGENT.md — Central Project Knowledge Base & Working Reference

> **Mandatory Reference for Autonomous & Pair-Programming Agents:**
> Read this document at the start of any new session or task. Do not perform redundant full-codebase exploratory scans when context is already established here. Only inspect and modify files directly related to the specific task. Update this document whenever significant architectural changes, new endpoints, schemas, or conventions are introduced.

---

## 1. Project Overview & Purpose

**Personal AI Agent Studio (`Agentic_RAG`)** is a production-grade, local-first agentic workspace assistant. It pairs a high-performance **RAG (Retrieval-Augmented Generation)** knowledge engine with **multi-step tool orchestration**, **multi-user Google OAuth 2.0 (Gmail & Google Calendar)**, **task management**, **long-term memory**, and **Human-in-the-Loop (HITL) approval cards** for sensitive operations.

The user interface follows a modern, warm burgundy-and-cream editorial aesthetic with an interactive mascot, responsive multi-turn chat streaming via SSE, and source inspection.

---

## 2. Technology Stack & Versions

### Backend
- **Python**: 3.11.9
- **Web Framework**: FastAPI (`v0.115+`) & Uvicorn (ASGI server)
- **Agent & Orchestration**: LangChain Core, LangGraph (`StateGraph`), LangChain Google GenAI
- **LLM**: Google Gemini API via `langchain-google-genai` (`gemini-3.5-flash-lite`, `gemini-3-flash-preview`, `gemini-flash-latest`)
- **Embeddings**: `fastembed` (`BAAI/bge-small-en-v1.5`, 384-dimensional ONNX embeddings running locally on CPU)
- **Vector Store**: FAISS (`IndexFlatL2` with `InMemoryDocstore`) with disk persistence in `data/vector_store/`
- **Lexical Retrieval**: BM25 (`rank-bm25` `BM25Okapi`) with disk-persisted corpus in `data/vector_store/bm25_store.json`
- **Reranker**: FlashRank (`ms-marco-TinyBERT-L-2-v2`, 3.2MB local ONNX model)
- **Hybrid Fusion**: Reciprocal Rank Fusion (RRF, $k=60$)
- **Document Parsers**: PyPDF (`pypdf`), Word DOCX (`python-docx`), CSV/JSON, Plain Text & Markdown, YouTube Transcript API
- **Web Search**: DuckDuckGo Search (`DuckDuckGoSearchRun`)
- **Database**: SQLite3 (`data/agent_studio.db`) with RowFactory
- **Security & Token Encryption**: `cryptography.fernet.Fernet`
- **Google API Integrations**: `google-api-python-client`, `google-auth-oauthlib` (Gmail v1 & Calendar v3)

### Frontend
- **Runtime & Bundler**: Node.js, Vite (`v8.3.5`), Rolldown bundler, TypeScript (`~7.0.2`)
- **UI Framework**: React (`v19.3.1`) & React DOM (`v19.3.1`)
- **Performance**: Dynamic code-splitting with `React.lazy` / `Suspense` and manual vendor chunks (`91.6 kB` core bundle)
- **Styling**: Vanilla CSS (`index.css`) with CSS variables and custom keyframe animations
- **Icons**: `lucide-react` (`v1.63.0`)
- **Markdown Rendering**: `react-markdown` (`v10.1.0`), `remark-gfm` (`v4.0.1`)
- **Procedural Avatar**: `@bible-strong/avatar-react` (`v0.1.0`)

---

## 3. Overall Project Architecture

```
                      ┌────────────────────────────────────────┐
                      │    React 19 SPA (frontend/src)         │
                      │  - Multi-session chat & SSE streaming  │
                      │  - Human-in-the-Loop Approval Cards   │
                      │  - Document Ingestion & Task Modal     │
                      │  - Code-split dynamic chunks (<100kB)  │
                      └───────────────────▲────────────────────┘
                                          │ HTTP / SSE (/api/chat/stream)
                                          ▼
                      ┌────────────────────────────────────────┐
                      │         FastAPI App (server.py)        │
                      │  - Session & CORS Middleware           │
                      │  - Static Asset Serving (SPA catchall) │
                      └───────────────────▲────────────────────┘
                                          │
            ┌─────────────────────────────┼────────────────────────────┐
            ▼                             ▼                            ▼
┌───────────────────────┐   ┌───────────────────────────┐   ┌─────────────────────────┐
│ Ingestion & FAISS RAG │   │   Tool & Intent Router    │   │ SQLite (agent_studio.db)│
│ - PyMuPDF (PDFs)      │   │ - Priority 0: Zero-LLM    │   │ - users (OAuth tokens)  │
│ - YouTube Transcript  │   │   Greetings & Declines    │   │ - conversations (SQLite)│
│ - SHA-256 Deduplicate │   │ - Priority 1.5: Multi-    │   │ - messages (Turns)      │
│ - Disk Persistence    │   │   Intent Orchestrator     │   │ - tasks & reminders     │
│   (data/vector_store/)│   │ - Priority 1: Gmail       │   │ - memories & preferences│
└───────────────────────┘   │ - Priority 2: Calendar    │   │ - pending_actions (HITL)│
                            │ - Priority 3: Tasks/Mem   │   └─────────────────────────┘
                            │ - Priority 4: Web Search  │
                            │ - Priority 5: RAG Search  │
                            │ - Priority 6: Gemini LLM  │
                            └───────────────────────────┘
```

---

## 4. Folder Structure & Key Responsibilities

```
d:\AGENTIC AI\LangChain\Projects\
├── AGENT.md                       # Central Project Knowledge Base (this file)
├── server.py                      # FastAPI root application entry point & SPA mount
├── run_app.bat                    # One-click Windows startup batch script
├── .env                           # Local environment variables (DO NOT COMMIT)
├── .env.example                   # Template environment variables for setup
├── docs/
│   ├── ARCHITECTURE.md            # System Architecture & Technical Specification
│   └── CHANGELOG.md               # Chronological version release log
├── data/
│   ├── agent_studio.db            # SQLite persistence (users, conversations, tasks, memories)
│   └── vector_store/              # Persistent FAISS index files & documents_registry.json
├── backend/
│   ├── config.py                  # Gemini model registry, caching, and failover defaults
│   ├── embeddings.py              # Local FastEmbed BGE-small embedding wrapper & text splitters
│   ├── graph.py                   # LangGraph state machine definitions (AgentState, nodes, edges)
│   ├── memory.py                  # Short-term chat history tracking & turn recording
│   ├── prompts.py                 # System prompts for conversational & RAG generation
│   ├── tools.py                   # Intent detectors, multi-intent logic, greeting handlers, search
│   ├── vector_store.py            # Persistent FAISS store (save/load disk, hash dedup, delete)
│   ├── routes/
│   │   ├── actions.py             # Human-in-the-Loop approve / reject endpoints
│   │   ├── auth.py                # Google OAuth 2.0 login, callback, status, logout
│   │   ├── chat.py                # SSE streaming chat endpoint (/api/chat/stream)
│   │   ├── conversations.py       # SQLite conversation threads CRUD & message pagination
│   │   ├── documents.py           # Ingestion (PDF, text notes, YouTube) & single-doc deletion
│   │   ├── memory.py              # Persistent memory listing and addition
│   │   └── tasks.py               # Task management CRUD & overdue filtering
│   ├── services/
│   │   ├── approval_service.py    # Pending action proposal, execution, and cancellation
│   │   ├── chat_service.py        # Central SSE stream generator with priority routing
│   │   ├── chunking.py            # Sentence-boundary preserving structural chunker & metadata
│   │   ├── database.py            # SQLite schema initialization and CRUD helper methods
│   │   ├── document_service.py    # Multi-format ingestion, dedup, and dual FAISS+BM25 indexing
│   │   ├── google_service.py      # Gmail & Calendar API client calls with Fernet encryption
│   │   ├── hybrid_retriever.py    # Dual FAISS dense + BM25Okapi lexical with RRF & FlashRank
│   │   ├── parsers.py             # Multi-format parsers (PDF, DOCX, CSV, JSON, Markdown/TXT)
│   │   ├── query_processor.py     # Noise cleaning, follow-up expansion, and document filtering
│   │   └── router.py              # Central deterministic query intent classification
│   └── utils/
│       ├── auth.py                # Session-based user ID extraction helper
│       ├── crypto.py              # Fernet symmetric encryption / decryption helpers
│       └── retry.py               # Exponential backoff, resilient failover, friendly errors
└── frontend/
    ├── package.json               # Frontend dependencies & build scripts
    ├── vite.config.ts             # Vite config with proxying and vendor code splitting
    ├── dist/                      # Production built static assets (served by server.py)
    └── src/
        ├── App.tsx                # Main application component: session, toast, stream handlers
        ├── index.css              # Global styles, typography, animations, caret fix
        ├── avatar.avatar.json     # Configuration for procedural studio mascot
        ├── constants/
        │   └── theme.ts           # Burgundy & cream color tokens and available Gemini models
        ├── types/
        │   └── index.ts           # TypeScript interfaces: Message, TaskItem, Proposal, Document
        └── components/
            ├── avatar/
            │   └── StudioBrandLogo.tsx # StudioBrandLogo mascot component with emotion states
            ├── chat/
            │   ├── ActionProposalCard.tsx # Human-in-the-Loop approval card with Approve/Cancel
            │   ├── ChatMessage.tsx        # Message turn container with copy, feedback, citations
            │   ├── MarkdownContent.tsx    # Styled markdown renderer with remark-gfm
            │   ├── RetrievedContext.tsx   # Collapsible source citations & chunk inspection
            │   └── ThinkingIndicator.tsx  # Dynamic thinking status indicator
            ├── composer/
            │   ├── Composer.tsx           # Message textarea, model picker, attach menu, submit
            │   └── UploadChip.tsx         # File ingestion upload progress chip
            ├── layout/
            │   ├── Sidebar.tsx            # Thread history, search, rename/delete, knowledge tray
            │   └── TopBar.tsx             # OAuth status, task modal button, user badge
            ├── modals/
            │   ├── GoogleConnectModal.tsx # Google OAuth connection prompt dialog (lazy loaded)
            │   ├── TaskManagerModal.tsx   # Full-featured task and reminder manager (lazy loaded)
            │   ├── TextModal.tsx          # Raw text & notes ingestion modal
            │   └── YouTubeModal.tsx       # YouTube video transcript ingestion modal
            └── welcome/
                └── HeroWelcome.tsx        # Interactive hero section with playful mascot actions
```

---

## 5. API Endpoints Reference

### Chat & Streaming
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat/stream` | Server-Sent Events (SSE) streaming chat endpoint with multi-intent orchestration |
| `POST` | `/api/chat` | Synchronous LangGraph RAG execution |
| `GET` | `/api/models` | List available Gemini models and active default |

### Conversations (SQLite Persistence)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/conversations` | List conversation threads with pagination (`limit`, `offset`) |
| `GET` | `/api/conversations/{id}` | Retrieve single thread with persisted message turns |
| `POST` | `/api/conversations` | Batch persist/update conversation turns in SQLite |
| `PATCH` | `/api/conversations/{id}/title` | Rename conversation thread title |
| `DELETE` | `/api/conversations/{id}` | Permanently delete conversation thread and cascaded messages |

### Document Knowledge Base (FAISS RAG)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/documents` | Retrieve list of all currently indexed documents in vector store |
| `POST` | `/api/documents/upload` | Upload & index PDF documents into the FAISS vector store |
| `POST` | `/api/documents/add` | Ingest raw text notes into the FAISS vector store with SHA-256 deduplication |
| `POST` | `/api/documents/youtube` | Fetch YouTube video transcript and index into FAISS |
| `DELETE`| `/api/documents/{id}` | Remove a single document and re-serialize FAISS index |
| `DELETE`| `/api/documents/clear` | Clear the FAISS vector store and document registry |

### Google OAuth 2.0 & Workspace
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/auth/google/login` | Initiates Google OAuth 2.0 authorization redirect |
| `GET` | `/api/auth/google/callback` | Handles OAuth redirect, exchanges code for encrypted tokens |
| `GET` | `/api/auth/status` | Sub-millisecond SQLite check of current user Google connection status |
| `POST` | `/api/auth/logout` | Disconnects and removes Google OAuth tokens for the session |

### Tasks & Reminders
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/tasks` | Lists active tasks for the current user |
| `POST` | `/api/tasks` | Creates a new task |
| `PATCH` | `/api/tasks/{id}/complete`| Toggles task completion status |
| `DELETE`| `/api/tasks/{id}` | Deletes a task |
| `GET` | `/api/tasks/overdue` | Retrieves tasks whose due date has passed |

### Long-Term Memory
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/memory` | Lists all persistent long-term memories |
| `POST` | `/api/memory` | Stores a new preference or long-term memory |

### Human-in-the-Loop Actions
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/actions/{id}/approve`| Executes an approved sensitive action (e.g., sends drafted email) |
| `POST` | `/api/actions/{id}/cancel` | Cancels a proposed sensitive action |

---

## 6. Database Schema & Relationships (`agent_studio.db`)

All data is persisted in SQLite with schema migrations managed in [`backend/services/database.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/services/database.py):

### `users`
- `id` (TEXT, PK): Unique user UUID or `default`.
- `email` (TEXT, UNIQUE): Google account email.
- `google_access_token` (TEXT): Fernet-encrypted OAuth access token.
- `google_refresh_token` (TEXT): Fernet-encrypted OAuth refresh token.
- `token_expires_at` (TEXT): ISO timestamp.
- `created_at` (TEXT): ISO timestamp.

### `conversations`
- `id` (TEXT, PK): Unique thread identifier (e.g., `thread_179328...`).
- `user_id` (TEXT, Nullable, FK -> `users.id`): Associated user.
- `title` (TEXT): Thread title.
- `model` (TEXT): Model identifier (default: `gemini-3.5-flash-lite`).
- `created_at` / `updated_at` (TEXT): ISO timestamps.

### `messages`
- `id` (TEXT, PK): Message turn UUID.
- `conversation_id` (TEXT, FK -> `conversations.id` ON DELETE CASCADE).
- `sender` (TEXT): `'user' | 'assistant' | 'system'`.
- `text` (TEXT): Rendered response or query.
- `source` (TEXT, Nullable): Source attribution tag.
- `metadata_json` (TEXT): Serialized metadata (retrieved documents, action proposal, doc meta).
- `created_at` (TEXT): ISO timestamp.

### `tasks`
- `id` (TEXT, PK): UUID.
- `user_id` (TEXT, FK -> `users.id`): Associated user.
- `title` (TEXT): Task title.
- `description` (TEXT): Details / context.
- `due_date` (TEXT, Nullable): Due date (`YYYY-MM-DD`).
- `priority` (TEXT): `'low' | 'medium' | 'high'`.
- `status` (TEXT): `'pending' | 'completed'`.
- `category` (TEXT): Category tag.
- `created_at` / `updated_at` (TEXT): ISO timestamps.

### `memories`
- `id` (TEXT, PK): UUID.
- `category` (TEXT): `'preference' | 'fact' | 'work'`.
- `content` (TEXT): Memory text.
- `created_at` (TEXT): ISO timestamp.

### `pending_actions`
- `id` (TEXT, PK): UUID (e.g., `act_abc123`).
- `action_type` (TEXT): `'send_email' | 'create_calendar_event'`.
- `summary` (TEXT): User-friendly summary.
- `payload_json` (TEXT): Serialized parameters for execution.
- `status` (TEXT): `'pending' | 'approved' | 'rejected' | 'executed'`.
- `created_at` / `executed_at` (TEXT): ISO timestamps.

---

## 7. Authentication & Token Encryption Flow

1. **Initiation**: User clicks **Connect Google** in the top bar or is prompted by a Gmail/Calendar intent.
2. **OAuth Scopes**:
   - `openid`, `userinfo.email`, `userinfo.profile`
   - `gmail.readonly`, `gmail.send`, `gmail.compose`, `gmail.modify`
   - `calendar`, `calendar.events`
3. **Encryption at Rest**:
   - Both `google_access_token` and `google_refresh_token` are encrypted using `cryptography.fernet.Fernet` with the key stored in `ENCRYPTION_KEY`.
   - Raw tokens are never stored in plaintext in SQLite or exposed to the frontend.
4. **Latency Optimization**:
   - `/api/auth/status` queries the local SQLite database directly (sub-millisecond `~0.05ms`) instead of making remote Google HTTP calls.
5. **Auto-Invalidation on Refresh Failure**:
   - If Google revokes access or refresh fails, credentials in `users` are cleared, cleanly prompting the user to re-authenticate without crashing the backend.

---

## 8. Core Business Logic & Centralized Request Routing

All incoming user queries pass through the **Centralized Intent Router** ([`backend/services/router.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/services/router.py)), which classifies queries into an explicit `QueryIntent` before any routing execution occurs. Both the streaming pipeline ([`backend/services/chat_service.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/services/chat_service.py)) and the LangGraph state machine ([`backend/graph.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/graph.py)) share this centralized routing engine.

### QueryIntent Architecture
```python
class QueryIntent(str, Enum):
    CONVERSATIONAL     = "conversational"      # Pure greetings, pleasantries, small talk (Zero-LLM)
    DOCUMENT_RAG       = "document_rag"        # Ingested documents, study materials, practicals, notes
    GMAIL              = "gmail"               # Search, read, draft, send emails
    CALENDAR           = "calendar"            # Check availability, free slots, schedule/delete events
    TASK               = "task"                # Create, list, complete tasks and reminders
    MEMORY             = "memory"              # Long-term preference storage and recall
    WEB_SEARCH         = "web_search"          # Explicit live internet searches via DuckDuckGo
    MULTI_STEP         = "multi_step"          # Compound instructions (e.g. Email + Calendar/Tasks)
    GENERAL_KNOWLEDGE  = "general_knowledge"   # General LLM inquiries when no doc is relevant
    UNKNOWN            = "unknown"
```

### Strict Classification Rules (Permanent Policy)
1. **Rule A — Exact Conversational Matching**:
   - Pure conversational fast paths use exact normalized dictionaries (`EXACT_WELCOME_GREETINGS`, `EXACT_CAPABILITIES`, `EXACT_GRATITUDE`, `EXACT_FAREWELLS`, `EXACT_STATUS`, `EXACT_ACKNOWLEDGMENTS`, `EXACT_DECLINATIONS`) or regex word boundaries (`\b[a-z]+\b`).
   - **Zero Substring Traps**: Substring matching (`"no"` in `"now"`, `"hi"` in `"hinglish"`) is strictly forbidden.
2. **Rule B — Substantive Intent Always Takes Priority**:
   - If a message contains an actual request, document reference, or tool command (e.g., *"Now prepare my practicals"*, *"Hi, explain DAA"*, *"Hey, search my PDF"*, *"No, actually send the email"*, *"Thanks, now summarize this document"*), it is **NEVER** classified as pure small talk.
   - Any polite greeting prefix is stripped to expose the substantive payload before classification.
3. **Rule C — Length Is Not an Intent Signal**:
   - Short messages (*"Explain Dijkstra"*, *"Search my PDF"*, *"Find Sarah's email"*, *"Book a meeting"*) are legitimate requests and are never classified as small talk based on word count.
4. **Rule D — Welcome Card Separation**:
   - The interactive capability card (01–04 grid) is triggered ONLY when `is_welcome_card=True` on pure opening welcome greetings or capability inquiries. Gratitude, pleasantries, and substantive queries never display the card.

### Routing Cascade Order
1. **Multi-Step Orchestrator (`QueryIntent.MULTI_STEP`)**: Evaluates compound instructions via `detect_multi_intent()`.
2. **Tool Handlers (`QueryIntent.GMAIL`, `CALENDAR`, `TASK`, `MEMORY`, `WEB_SEARCH`)**: Evaluates explicit tool actions.
3. **Document RAG (`QueryIntent.DOCUMENT_RAG`)**: Evaluates queries containing document keywords (`pdf`, `practical`, `syllabus`, `notes`, `file`, etc.), study requests, or follow-up questions when documents are indexed (`doc_count > 0`).
4. **Conversational Fast Path (`QueryIntent.CONVERSATIONAL`)**: Pure small talk without tasks executes zero-LLM with a 1.05s thinking cadence.
5. **General Knowledge Fallback (`QueryIntent.GENERAL_KNOWLEDGE`)**: Routes general questions to Gemini LLM with streaming backoff.

### Structured Diagnostic Logging
Every routing decision automatically outputs telemetry:
```text
[ROUTER] Query received: "Now prepare me for my practicals"
[ROUTER] Normalized query: "now prepare me for my practicals"
[ROUTER] Detected intent: QueryIntent.DOCUMENT_RAG
[ROUTER] Classification reason: Substantive document or study request with indexed documents available
[ROUTER] Selected execution path: faiss_document_rag
[ROUTER] RAG invoked: True
[ROUTER] Tools selected: ['retriever']
[ROUTER] Fast path: False
```
*(User credentials, email bodies, and document contents are strictly redacted from router logs.)*

### Automated Regression Testing
All changes to routing must pass the regression suites before merging:
- `tests/test_router_regression.py`: Automated unit suite with 5 test categories covering false-positives, genuine greetings, multi-intent, follow-ups, and short queries.
- `tests/test_live_production_path.py`: End-to-end integration test against the live FastAPI streaming endpoint validating real FAISS retrieval with citations. Run:
  ```bash
  .\venv\Scripts\python.exe tests/test_router_regression.py
  .\venv\Scripts\python.exe tests/test_live_production_path.py
  ```

---

## 9. Model Selection, Status & Failover

Google has deprecated older Gemini models (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-1.5-flash`, `gemini-2.0-flash`) for new users.

- **Primary Supported Model**: `gemini-3.5-flash-lite` (Active & Stable)
- **Supported Alternatives**: `gemini-3-flash-preview`, `gemini-flash-latest`
- **Failover Logic**: In [`backend/utils/retry.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/utils/retry.py), if any model fails with `404 (Not Found)`, `503 (High Demand)`, or rate limits, the stream automatically fails over to `gemini-3.5-flash-lite` to ensure requests complete cleanly.

---

## 10. Environment Variables (Names Only)

Defined in `.env`:
- `GEMINI_API_KEY`: API key from Google AI Studio.
- `GOOGLE_API_KEY`: Fallback Gemini API key.
- `GOOGLE_CLIENT_ID`: Google Cloud OAuth 2.0 Web Application Client ID.
- `GOOGLE_CLIENT_SECRET`: Google Cloud OAuth 2.0 Client Secret.
- `GOOGLE_REDIRECT_URI`: OAuth callback URI (`http://localhost:8000/api/auth/google/callback`).
- `ENCRYPTION_KEY`: 32-byte Fernet secret key for token encryption.
- `SECRET_KEY`: FastAPI session middleware secret key.
- `MCP_ENABLED`: Optional boolean flag for Model Context Protocol sidecars.

---

## 11. Existing Conventions & Constraints

1. **Anti-Overthinking Policy (Execution-Focused)**:
   - **Priority:** Correctness → Simplicity → Execution Speed → Maintainability.
   - Stop excessive reasoning; implement the simplest effective solution directly.
   - Read `AGENT.md` first; avoid inspecting unrelated files or analyzing code repeatedly.
   - Never create problems that don't exist, avoid premature refactoring, and limit tool calls.
   - Once the requested issue is resolved and verified, STOP immediately.
2. **Git Commits & Pushes**:
   - **Strict Rule:** NEVER run `git commit` or `git push` unless the user explicitly commands it in their prompt.
3. **UI & Styling Conventions**:
   - Warm Burgundy (`#7a1c30`), Beige surface (`#faf7f2`), and Slate Gray (`#1e242a`).
   - Global `caret-color: transparent !important;` prevents static text selection carets on clicks.
   - Text selection is disabled on headers, sidebar items, and chips (`user-select: none`).
4. **Production Server Startup**:
   - `python server.py` serves both FastAPI endpoints and React build output (`frontend/dist`) on `http://localhost:8000`.
   - When modifying frontend code, always run `npm --prefix frontend run build` before restarting `server.py`.
5. **Safety & Privacy**:
   - Real email credentials or tokens must NEVER be logged or committed.
   - `.env` is strictly git-ignored. Keep placeholders in `.env.example`.

---

## 12. Current Project Status & Verified State

- **Zero-LLM Greetings & Declinations**: Verified working with ~450ms thinking state and smooth ~30ms typing cadence.
- **RAG & FAISS Vector Store**: Verified disk persistence (`data/vector_store/`), SHA-256 deduplication, and single-document removal.
- **Multi-Intent Orchestrator**: Verified compound query planning (e.g. read email $\rightarrow$ summarize $\rightarrow$ propose calendar event).
- **SQLite Conversations Persistence**: Verified thread management and turn history persistence across sessions.
- **Google OAuth 2.0 & Token Refresh**: Verified working with Fernet encryption and safe failure recovery.
- **Human-in-the-Loop Action Approval**: Verified working for Gmail drafts and Calendar scheduling.
- **Gmail Reading & Inbox Search**: Verified intelligent query normalization (stripping conversational requests to return real inbox contents, count extraction, sender filtering, and anti-hallucination guardrail preventing placeholder brackets).
- **Frontend Bundle**: Optimized with `React.lazy` and manual chunks, core app reduced to 91.6 kB.
- **Server**: Running and healthy on `http://localhost:8000`.
