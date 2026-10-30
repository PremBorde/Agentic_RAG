# AGENT.md — Central Project Knowledge Base & Reference

> **Mandatory Reference for Autonomous & Pair-Programming Agents:**
> Read this document at the start of any new session or task. Do not perform redundant full-codebase exploratory scans when context is already established here. Only inspect and modify files directly related to the specific task. Update this document whenever significant architectural changes, new endpoints, schemas, or conventions are introduced.

---

## 1. Project Overview & Purpose

**Personal AI Agent Studio (`Agentic_RAG`)** is a production-grade, local-first agentic workspace assistant. It pairs a high-performance **RAG (Retrieval-Augmented Generation)** knowledge engine with **tool orchestration**, **multi-user Google OAuth 2.0 (Gmail & Google Calendar)**, **task management**, **long-term memory**, and **Human-in-the-Loop (HITL) approval cards** for sensitive operations.

The user interface follows a modern, warm burgundy-and-cream editorial aesthetic with an interactive mascot, responsive multi-turn chat streaming via SSE, and source inspection.

---

## 2. Technology Stack & Versions

### Backend
- **Python**: 3.11.9
- **Web Framework**: FastAPI (v0.115+) & Uvicorn (ASGI server)
- **Agent & Orchestration**: LangChain Core / LangGraph (`StateGraph`), LangChain Google GenAI
- **LLM**: Google Gemini API via `langchain-google-genai` (`gemini-3.5-flash-lite`, `gemini-3-flash-preview`, `gemini-flash-latest`)
- **Embeddings**: `fastembed` (`BAAI/bge-small-en-v1.5`, 384-dimensional ONNX embeddings running locally on CPU)
- **Vector Store**: FAISS (`IndexFlatL2` with `InMemoryDocstore`)
- **Web Search**: DuckDuckGo Search (`DuckDuckGoSearchRun`)
- **Database**: SQLite3 (`data/agent_studio.db`) with RowFactory
- **Security & Token Encryption**: `cryptography.fernet.Fernet`
- **Google API Integrations**: `google-api-python-client`, `google-auth-oauthlib` (Gmail v1 & Calendar v3)

### Frontend
- **Runtime & Bundler**: Node.js, Vite (`v8.3.5`), TypeScript (`~7.0.2`)
- **UI Framework**: React (`v19.3.1`) & React DOM (`v19.3.1`)
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
│ - YouTube Transcript  │   │   Greetings & Declines    │   │ - tasks & reminders     │
│ - FastEmbed (ONNX)    │   │ - Priority 1: Gmail       │   │ - memories & preferences│
│ - In-memory FAISS L2  │   │ - Priority 2: Calendar    │   │ - pending_actions (HITL)│
└───────────────────────┘   │ - Priority 3: Tasks/Mem   │   └─────────────────────────┘
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
├── rag.py                         # Standalone / legacy RAG prototyping script
├── .env                           # Local environment variables (DO NOT COMMIT)
├── .env.example                   # Template environment variables for setup
├── data/
│   └── agent_studio.db            # SQLite persistence for OAuth, tasks, memories, actions
├── backend/
│   ├── config.py                  # Gemini model registry, caching, and failover defaults
│   ├── embeddings.py              # Local FastEmbed BGE-small embedding wrapper & text splitters
│   ├── graph.py                   # LangGraph state machine definitions (AgentState, nodes, edges)
│   ├── memory.py                  # Short-term chat history tracking & turn recording
│   ├── prompts.py                 # System prompts for conversational & RAG generation
│   ├── tools.py                   # Intent detection regex, greeting handlers, DuckDuckGo search
│   ├── vector_store.py            # FAISS vector store initialization, retrieval, and resetting
│   ├── routes/
│   │   ├── actions.py             # Human-in-the-Loop approve / reject endpoints
│   │   ├── auth.py                # Google OAuth 2.0 login, callback, status, logout
│   │   ├── chat.py                # SSE streaming chat endpoint (/api/chat/stream)
│   │   ├── documents.py           # Ingestion for PDF, raw text notes, and YouTube transcripts
│   │   ├── memory.py              # Persistent memory listing and addition
│   │   └── tasks.py               # Task management CRUD & overdue filtering
│   ├── services/
│   │   ├── approval_service.py    # Pending action proposal, execution, and cancellation
│   │   ├── chat_service.py        # Central SSE stream generator with priority routing
│   │   ├── database.py            # SQLite schema initialization and CRUD helper methods
│   │   ├── document_service.py    # Text chunking, extraction, and vector indexing logic
│   │   └── google_service.py      # Gmail & Calendar API client calls with Fernet encryption
│   └── utils/
│       └── retry.py               # Exponential backoff, resilient failover, friendly errors
└── frontend/
    ├── package.json               # Frontend dependencies & build scripts
    ├── vite.config.ts             # Vite dev server proxying /api to http://localhost:8000
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
            ├── avatar/            # StudioBrandLogo component with emotion states
            ├── chat/              # ChatMessage, MarkdownContent, RetrievedContext, ThinkingIndicator
            ├── composer/          # Message input textarea, model dropdown, attach menu
            ├── layout/            # TopBar, Sidebar (session management & KB tray)
            ├── modals/            # GoogleConnectModal, TaskManagerModal, ActionProposalCard
            └── welcome/           # HeroWelcome with interactive playful mascot & speech bubble
```

---

## 5. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat/stream` | Server-Sent Events (SSE) streaming chat endpoint with multi-intent orchestration |
| `GET` | `/api/conversations` | List conversation threads with pagination |
| `GET` | `/api/conversations/{id}` | Retrieve single thread with persisted message turns |
| `POST` | `/api/conversations` | Batch persist/update conversation turns in SQLite |
| `PATCH` | `/api/conversations/{id}/title` | Rename conversation thread title |
| `DELETE` | `/api/conversations/{id}` | Permanently delete conversation thread and cascaded messages |
| `POST` | `/api/documents/upload` | Upload & index PDF documents into the FAISS vector store |
| `POST` | `/api/documents/add` | Ingest raw text notes into the FAISS vector store with SHA-256 deduplication |
| `POST` | `/api/documents/youtube` | Fetch YouTube video transcript and index into FAISS |
| `GET` | `/api/documents` | Retrieve list of all currently indexed documents |
| `DELETE`| `/api/documents/{id}` | Remove a single document and re-serialize FAISS index |
| `DELETE`| `/api/documents/clear` | Clear the FAISS vector store and document registry |
| `GET` | `/api/auth/google/login` | Initiates Google OAuth 2.0 authorization redirect |
| `GET` | `/api/auth/google/callback` | Handles OAuth redirect, exchanges code for encrypted tokens |
| `GET` | `/api/auth/status` | Sub-millisecond SQLite check of current user Google connection status |
| `POST` | `/api/auth/logout` | Disconnects and removes Google OAuth tokens for the session |
| `GET` | `/api/tasks` | Lists active tasks for the current user |
| `POST` | `/api/tasks` | Creates a new task |
| `PATCH` | `/api/tasks/{id}/complete`| Toggles task completion status |
| `DELETE`| `/api/tasks/{id}` | Deletes a task |
| `GET` | `/api/tasks/overdue` | Retrieves tasks whose due date has passed |
| `GET` | `/api/memory` | Lists all persistent long-term memories |
| `POST` | `/api/memory` | Stores a new preference or long-term memory |
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
   - Raw tokens are never stored in plaintext in SQLite.
4. **Latency Optimization**:
   - `/api/auth/status` and `get_connection_status(user_id)` query the local SQLite database directly (sub-millisecond ~0.05ms) instead of executing remote Google HTTP calls.

---

## 8. Core Business Logic & Request Routing

When a message is received at `/api/chat/stream`, [`backend/services/chat_service.py`](file:///d:/AGENTIC%20AI/LangChain/Projects/backend/services/chat_service.py) executes the following routing cascade:

1. **Priority 0 — Zero-LLM Conversational & Declinations**:
   - Checked via `is_conversational_query(question)`.
   - Handles greetings (*"Hi"*, *"Good morning"*), bot capability questions (*"What can you do?"*), pleasantries (*"How are you?"*, *"Thank you"*), and polite declinations (*"No"*, *"Nope"*, *"Nothing right now"*).
   - Generates instant direct responses streamed at 12ms per word with **0ms LLM latency and zero API calls**.
2. **Priority 1 — Gmail Intent**:
   - Evaluated via `detect_gmail_intent(question)`.
   - Read/search actions execute via Google Service.
   - Sending an email proposes an **ActionProposalCard** (Human-in-the-Loop) and requires approval.
3. **Priority 2 — Google Calendar Intent**:
   - Evaluated via `detect_calendar_intent(question)`.
   - Free slot / availability inquiries return calendar schedules.
   - Creating an event generates an ActionProposalCard for user approval.
4. **Priority 3 — Tasks & Reminders**:
   - Evaluated via `detect_task_intent(question)`.
   - Creates, lists, or filters overdue tasks directly via SQLite.
5. **Priority 4 — Long-Term Memory**:
   - Evaluated via `detect_memory_intent(question)` (e.g., *"Remember that I prefer morning meetings"*).
6. **Priority 5 — Explicit Web Search**:
   - Evaluated via `is_explicit_web_search(question)`.
   - Executes live DuckDuckGo search queries and feeds results into the prompt context.
7. **Priority 6 — Document Retrieval (FAISS RAG)**:
   - If indexed documents exist (`doc_count > 0`), retrieves relevant chunks (`k=4`) using `LocalFastEmbeddings` (BGE-small ONNX) and formats with source attribution.
8. **Priority 7 — General Assistant Generation**:
   - Falls back to `conv_prompt` using `get_active_llm()`.
   - Wrapped with `astream_with_backoff()` with automatic failover to `gemini-3.5-flash-lite`.

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

- **Zero-LLM Greetings & Declinations**: Verified working with ~2ms latency.
- **RAG & FAISS Vector Store**: Verified working with local BGE-small embeddings.
- **Google OAuth 2.0 & Token Refresh**: Verified working with Fernet encryption.
- **Human-in-the-Loop Action Approval**: Verified working for Gmail drafts and Calendar scheduling.
- **Mascot Interaction**: Interactive animations (bounce, wiggle, spin, boing) and speech bubble popups on click.
- **Git State**: Clean working tree on branch `main`.

