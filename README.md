# 🧠 Agentic RAG Studio

<div align="center">

![Agentic Studio Companion Logo](./Futuristic%20AI%20Knowledge%20Assistant%20Logo.png)

### Intelligent Autonomous Retrieval-Augmented Generation with LangGraph, FAISS & Gemini

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangGraph-Agentic_Workflow-FF9900?style=for-the-badge&logo=chainlink&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FAISS](https://img.shields.io/badge/Vector_Store-FAISS-00599C?style=for-the-badge&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![Gemini](https://img.shields.io/badge/LLM-Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

</div>

---

## 📌 Overview

**Agentic RAG Studio** is a full-stack, enterprise-grade **Agentic Retrieval-Augmented Generation (RAG)** platform designed to feel as fluid, capable, and responsive as modern AI interfaces like ChatGPT and Claude.

Unlike traditional static RAG pipelines that blindly retrieve documents for every prompt, Agentic Studio utilizes a **LangGraph state machine** to dynamically classify query intent. It routes greetings and capability questions directly to conversational synthesis, extracts semantic answers from indexed private documents using **FAISS**, and autonomously falls back to **DuckDuckGo Web Search** when external real-world knowledge is required.

---

## 🚀 Key Highlights & Capabilities

### 1. 🤖 Agentic Multi-Stage Orchestration (LangGraph)
* **Intelligent Query Classification**: Differentiates between conversational greetings, document questions, coding tasks, and explicit web queries without polluting answers with irrelevant search snippets.
* **Grounded Synthesis**: Eliminates robotic boilerplate phrases like *"Based on the retrieved context..."* in favor of clear, direct, and authoritative markdown explanations.
* **Autonomous Fallback**: Queries DuckDuckGo for live internet search when requested or when internal knowledge is absent.

### 2. 📂 Multi-Source Document Ingestion
* **File Ingestion**: Upload `.pdf`, `.txt`, `.docx`, `.csv`, `.md`, or `.json` files with real-time animated indexing progress chips.
* **YouTube Transcript Pipeline**: Provide any YouTube video URL or ID to automatically download, clean, chunk, and embed video transcripts via `youtube-transcript-api`.
* **Raw Text / Custom Notes**: Direct markdown and text note ingestion with instant chunk previewing.
* **Local Fast Embeddings**: High-throughput on-device embeddings (`fastembed`) coupled with FAISS vector similarity retrieval.

### 3. 🎨 ChatGPT & Claude-Grade UI / UX
* **True SSE Streaming**: Progressive real-time token rendering with a subtle streaming cursor and animated thinking states.
* **Interactive Citations `[1]`**: Clickable inline source citations that smoothly scroll and flash-highlight the exact source chunk in the collapsible context viewer.
* **Procedural Companion Avatar**: Integrated `@bible-strong/avatar-react` displaying expressive animations for *idle*, *thinking*, *searching*, *generating*, and *sleeping* states.
* **Rich Markdown Rendering**: Full GitHub Flavored Markdown (GFM) with syntax-highlighted code blocks, copy-to-clipboard buttons, formatted tables, and math formatting.
* **Dynamic Follow-Up Prompts**: Contextually relevant follow-up question chips generated beneath completed answers.
* **Conversation Management**: Multi-thread history sidebar, auto-generated titles from the first prompt, inline thread renaming, search filtering, and deletion.

---

## 🏗️ Architecture & Workflow

```
                                  [USER QUERY]
                                        │
                                        ▼
                         [LangGraph Intent Router]
                               /        │        \
         (Conversational / QA)/         │         \(Explicit Web Search)
                             /    (Has Documents)  \
                            /           │           \
                           ▼            ▼            ▼
             [Assistant LLM]   [FAISS Retriever]   [DuckDuckGo Search]
                    │                   │                    │
                    │                   ▼                    │
                    │         [Relevance Grader]             │
                    │          /               \             │
                    │ (Relevant)     (Out-of-Corpus Fallback)│
                    │        │                   │           │
                    │        ▼                   └───────────┤
                    │  [RAG Generation]                      │
                    │        ▲                               │
                    │        └───────────────────────────────┘
                    ▼
          [Server-Sent Events (SSE) Stream Engine]
                    │
                    ▼
          [Interactive React Studio UI]
```

---

## 📂 Project Structure

```
Agentic_RAG/
├── server.py                                 # FastAPI application entrypoint (~50 lines)
│
├── backend/                                  # Modular Python backend package
│   ├── __init__.py
│   ├── config.py                             # Model registry, environment loader & cached LLMs
│   ├── embeddings.py                         # Text normalizers, LocalFastEmbeddings & recursive splitter
│   ├── vector_store.py                       # FAISS vector store registry & document retriever
│   ├── memory.py                             # Session thread turn history & conversation memory
│   ├── tools.py                              # DuckDuckGo search tool & query intent classifiers
│   ├── prompts.py                            # Context-grounded generation & assistant prompts
│   ├── graph.py                              # LangGraph StateGraph nodes, router & compiled workflow
│   ├── services/
│   │   ├── document_service.py               # File (PDF/DOCX/TXT), text & YouTube ingestion pipelines
│   │   └── chat_service.py                   # SSE streaming chat generator with dynamic stage signals
│   └── routes/
│       ├── documents.py                      # REST endpoints for uploading, listing, and clearing docs
│       └── chat.py                           # REST endpoints for chat streams and available models
│
└── frontend/                                 # Modern React + Vite + TypeScript Single Page App
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── package.json
    ├── public/                               # Favicons, vector crests, and mascot assets
    └── src/
        ├── App.tsx                           # Main chat application coordinator
        ├── avatar.avatar.json                # Procedural avatar geometry, colors & animation keys
        ├── index.css                         # Tailored styles, focus rings & animations
        ├── types/                            # Shared TypeScript interfaces
        ├── constants/                        # Burgundy/Beige color palette tokens & model catalogs
        └── components/
            ├── avatar/                       # Procedural animated avatar components
            ├── chat/                         # ChatMessage, MarkdownContent, RetrievedContext, ThinkingIndicator
            ├── composer/                     # Rounded composer dock, model selector, upload chip
            ├── layout/                       # Collapsible Sidebar with search, TopBar header
            ├── modals/                       # Custom text and YouTube transcript ingestion modals
            └── welcome/                      # Hero welcome screen with starter prompt cards
```

---

## ⚡ Getting Started

### Prerequisites

* **Python 3.10+** (Python 3.11 recommended)
* **Node.js 18+** & **npm**
* A free **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/)

---

### Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/PremBorde/Agentic_RAG.git
   cd Agentic_RAG
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```
   Add your Gemini API key:
   ```env
   GEMINI_API_KEY="your_actual_gemini_api_key_here"
   GOOGLE_API_KEY="your_actual_gemini_api_key_here"
   ```

3. **Install Backend Dependencies**:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   
   # Linux/macOS:
   source venv/bin/activate

   # Install requirements
   pip install fastapi uvicorn langchain langchain-google-genai langchain-community langgraph faiss-cpu fastembed pypdf youtube-transcript-api python-dotenv
   ```

4. **Install Frontend Dependencies & Build**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

---

## 💻 Running the Application

### Option A: Unified Production Mode (FastAPI serves both API & React UI)

Run the single unified server:
```powershell
.\venv\Scripts\python.exe server.py
```
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

### Option B: Frontend Development Mode (Hot-Reloading)

For frontend UI development with instant hot module replacement:

```bash
# Terminal 1: Start Backend API
.\venv\Scripts\python.exe server.py

# Terminal 2: Start Vite Dev Server
cd frontend
npm run dev
```
Open your browser at:
👉 **[http://localhost:3000](http://localhost:3000)** *(Vite proxies `/api` calls directly to port 8000)*.

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/models` | List all available Gemini models and active default. |
| `POST` | `/api/chat/stream` | Stream real-time SSE events (`stage`, `meta`, `token`, `done`, `error`). |
| `GET` | `/api/documents` | Retrieve list of all indexed documents and total chunk count. |
| `POST` | `/api/documents/upload` | Upload `.pdf`, `.txt`, `.docx`, `.csv`, `.md` for FAISS indexing. |
| `POST` | `/api/documents/add` | Ingest raw text or private notes into the vector store. |
| `POST` | `/api/documents/youtube` | Extract and index transcript from a YouTube video URL or ID. |
| `POST` | `/api/documents/clear` | Clear the FAISS vector database and indexed document registry. |
| `DELETE`| `/api/threads/{thread_id}` | Delete a conversation thread and its history from memory. |

---

## 🛠️ Tech Stack

* **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain Core](https://github.com/langchain-ai/langchain)
* **LLM Engine**: Google Gemini (`gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-3.1-pro`)
* **Vector Store**: Meta [FAISS](https://github.com/facebookresearch/faiss) (Facebook AI Similarity Search)
* **Embeddings**: [FastEmbed](https://github.com/qdrant/fastembed) (On-device lightweight embedding generation)
* **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/)
* **Frontend Framework**: [React 18](https://react.dev/), [Vite](https://vitejs.dev/), [TypeScript](https://www.typescriptlang.org/)
* **UI Components & Icons**: [Lucide React](https://lucide.dev/), `@bible-strong/avatar-react`, `react-markdown`, `remark-gfm`

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

<div align="center">
Developed with ❤️ by <a href="https://github.com/PremBorde">Prem Borde</a>
</div>
