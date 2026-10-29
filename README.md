# Agentic RAG Studio (LangGraph + React UI)

An agentic Retrieval-Augmented Generation application powered by **LangGraph**, **Gemini 2.5 Flash**, **FAISS Vector Store**, **DuckDuckGo Web Search**, and a modern **React + Vite** frontend.

---

## Architecture Overview

```
                      [START]
                         │
                         ▼
                   [1. retrieve] ◄──── (FAISS Vector Store)
                         │
                         ▼
               [2. Router: Evaluator]
                      /     \
           (Relevant)/       \(Insufficient / Out-of-Corpus)
                    /         \
                   ▼           ▼
        [4. generate]     [3. web_search] ◄──── (DuckDuckGo Tool)
                   ▲           │
                    \──────────/
                         │
                         ▼
                       [END]
```

---

## Features

1. **Interactive RAG Chat**:
   - Chat with your indexed knowledge base.
   - Dynamic source indicator: Displays whether an answer was derived from **Local FAISS Vector Store** or **DuckDuckGo Web Search**.
   - **"Inspect Retrieved Actual Documents"**: Expandable card on every message displaying the exact document chunks, scores, and sources used.

2. **Actual Documents & Knowledge Base Inspector**:
   - Live view of all indexed documents in the FAISS vector database.
   - Shows chunk counts, creation timestamps, previews, and full document modal viewers.

3. **Multi-Source Knowledge Ingestion**:
   - **Custom Text / Articles**: Paste any notes or documentation into FAISS.
   - **YouTube Transcripts**: Paste a YouTube URL or video ID to automatically extract transcripts (integrating `YouTubeTranscriptApi`), split into chunks, embed, and index into FAISS.

---

## How to Run

### Option 1: Unified Full-Stack (One-Click)
Run the server (FastAPI serves both API and the built React frontend on port `8000`):
```bash
.\run_app.bat
```
or
```powershell
.\venv\Scripts\python.exe server.py
```
Open your browser at:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

### Option 2: Frontend Development Mode (Hot-Reloading)
To make UI changes with Vite hot-reloading:
```bash
# Terminal 1: Start Backend
.\venv\Scripts\python.exe server.py

# Terminal 2: Start Vite Dev Server
cd frontend
npm run dev
```
Open your browser at:
**[http://localhost:3000](http://localhost:3000)** (proxies `/api` to port 8000).

---

## API Endpoints

- `GET  /api/health`: Health status and active models.
- `GET  /api/documents`: List all indexed documents in FAISS.
- `POST /api/chat`: Send a query through the LangGraph pipeline with retrieved chunks.
- `POST /api/documents/add`: Ingest custom text into FAISS.
- `POST /api/documents/youtube`: Ingest YouTube video transcript into FAISS.

