# 🧠 Personal AI Agent Studio
<img width="1902" height="872" alt="Personal AI Agent Studio Preview" src="https://github.com/user-attachments/assets/798843dc-759d-4401-b29d-5d063cf500ff" />

<div align="center">

### Agentic AI Assistant with Private Document RAG, Google Workspace & Human-in-the-Loop Governance

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-FF9900?style=for-the-badge&logo=chainlink&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FAISS](https://img.shields.io/badge/Vector_Store-FAISS-00599C?style=for-the-badge&logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![Gemini](https://img.shields.io/badge/LLM-Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Gmail & Calendar](https://img.shields.io/badge/Integrations-Gmail_%26_Calendar-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](https://developers.google.com/workspace)

</div>

---

## 📌 Overview

**Personal AI Agent Studio** is a full-stack, enterprise-grade personal AI assistant built with **React**, **FastAPI**, **LangGraph**, **FAISS**, and **Google Gemini**.

It goes far beyond basic retrieval chatbots by combining:
1. **Deterministic Intent Router (`router.py`)**: Zero-token fast-paths for conversational greetings, small talk, and direct tool dispatch without wasteful agentic loops.
2. **Synchronized SSE Streaming**: Coordinated progressive text streaming (~18ms) paired with staged UI rendering — `ActionProposalCard`s and citation badges appear strictly after the assistant's introductory text finishes streaming.
3. **Private Document RAG**: Local FAISS vector embeddings and semantic search across PDFs, DOCX, CSV, TXT, MD, JSON, and YouTube video transcripts with inline clickable citations.
4. **Official Gmail Integration**: Search inbox, read emails, summarize long conversation threads, compose drafts, and securely send emails.
5. **Google Calendar Integration**: Check schedule, find free 30/60-minute meeting slots, detect agenda conflicts, and schedule calendar events with RFC3339 timezone compliance.
6. **Human-in-the-Loop Action Governance**: Strict security guardrails where any write action (sending an email, creating/deleting a calendar event) produces an interactive proposal card with explicit **Approve & Execute** and **Cancel** controls.
7. **Task & Reminder Manager**: Persistent SQLite to-do tracking with priorities (`low`, `medium`, `high`), due dates, and overdue alerts.
8. **Live Web Research**: Non-blocking internet research via DuckDuckGo with built-in query cleaning and fallback timeouts.

---

## 🚀 Key Capabilities & Modules

### 1. ✉️ Gmail Integration
- `search_emails`: Search messages using sender, subject, keywords, date, or unread filters.
- `read_email`: Safely inspect message body, sender, and recipient metadata.
- `summarize_email_thread`: Condense long multi-message conversations and extract key action items.
- `create_email_draft`: Prepare draft messages directly in your Gmail drafts folder.
- `send_email`: **Zero unauthorized sends**. The assistant prepares a structured action card previewing recipient, subject, and body; the email is transmitted only after you click **Approve & Execute**.

### 2. 📅 Google Calendar Integration
- `list_events`: Retrieve upcoming schedule and meeting times.
- `check_availability`: Detect conflicts on your primary calendar for any target timeframe.
- `find_free_meeting_slots`: Automatically scan business hours over the next 3–5 days to locate open slots.
- `create_event`: Zero-latency (0ms) regex date/time parsing with LLM fallback; scheduled into your Google Calendar with strict RFC3339 timezone formatting (`+05:30` / `Z`) upon approval.

### 3. ⏱️ Synchronized Streaming & Rendering Queue
- **Sequential Pacing**: Assistant explanations stream progressively (~18ms cadence) before any structured components appear.
- **Ordered Cards**: `ActionProposalCard`s and retrieved document context are held in a staged queue until the explanation text finishes streaming, preventing layout jumps or components rendering ahead of the text.
- **Non-Blocking I/O**: Heavy operations (DuckDuckGo search, FAISS retrieval, Google APIs) execute on background worker threads (`asyncio.to_thread`) with strict timeouts, keeping the UI responsive and broadcasting SSE stage updates (`searching_web`, `checking_calendar`) in real-time.

### 4. 🎯 Deterministic Intent Router (Zero Token Waste)
Instead of burning prompt tokens on wasteful LLM tool-calling loops:
- Small talk and capability questions (*"Hello"*, *"What can you do?"*) resolve in **0 LLM tokens** via zero-LLM fast paths.
- General questions (*"Write a python script..."*, *"What is TCP?"*) route directly to Gemini without irrelevant document chunks polluting the prompt.
- Document RAG **only** activates when you explicitly ask about uploaded documents or coursework, preventing college PDFs from hijacking general queries.

### 5. 📋 Persistent Task & Reminder Manager
- Lightweight persistent SQLite store (`data/agent_studio.db`).
- Create, filter, prioritize, and complete tasks directly via chat commands (e.g., *"Create a task to finish the presentation by Friday"*) or via the dedicated **Tasks** modal.
- Automatic overdue task detection and status tracking.

### 6. 🛡️ Security & Human-in-the-Loop Governance
- **Backend-Only OAuth Tokens**: Google access & refresh tokens are encrypted and isolated on the server; never exposed to the client browser.
- **Single-Use Action Bindings**: Every proposed action receives a cryptographic ID bound to exact parameters. Stale requests cannot trigger duplicate actions.
- **Untrusted Input Protection**: Content retrieved from emails, web pages, or documents is treated as untrusted data; embedded prompt injections are ignored.

---

## 🏛️ System Architecture

```
                                  [USER REQUEST]
                                         │
                                         ▼
                            [Deterministic Intent Router]
              ┌──────────────────────────┴──────────────────────────┐
              ▼                                                     ▼
      [Conversational Fast-Path]                            [Substantive Action]
         (0 LLM Tokens Spent)                                       │
              │                             ┌───────────────────────┼───────────────────────┐
              │                             ▼                       ▼                       ▼
              │                        [Gmail API]             [Calendar API]         [Web Search]
              │                             │                       │                       │
              │                 (Sensitive Write Action?) (Sensitive Write Action?)         │
              │                             │                       │                       │
              │                             ▼                       ▼                       ▼
              │                   [ActionProposalCard]    [ActionProposalCard]       [Live Results]
              │                             │                       │                       │
              │                      (User Approves)         (User Approves)                │
              │                             │                       │                       │
              │                             ▼                       ▼                       │
              │                     [Execute Send]          [Insert Event]                  │
              │                             └───────────────────────┼───────────────────────┘
              │                                                     │
              └─────────────────────────────┬───────────────────────┘
                                            ▼
                                [SSE Event Streaming]
                          (message_start -> stage -> tokens -> proposal -> done)
                                            │
                                            ▼
                          [Controlled Frontend Rendering Queue]
                      (Text Streams First ──► Action Cards Mounted)
```

---

## 🔑 Google OAuth 2.0 Setup Guide

To enable Gmail and Google Calendar features:

### Step 1: Create a Google Cloud Project
1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** > **New Project** and name it `Personal AI Agent Studio`.

### Step 2: Enable APIs
1. Navigate to **APIs & Services** > **Library**.
2. Search and click **Enable** for:
   - **Gmail API**
   - **Google Calendar API**

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** and click **Create**.
3. Fill in App Name (`Personal AI Agent Studio`) and your developer email.
4. Under **Scopes**, add:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/userinfo.email`
5. Under **Test Users**, add your personal Gmail address.

### Step 4: Create Credentials
1. Go to **APIs & Services** > **Credentials** > **Create Credentials** > **OAuth client ID**.
2. Select Application type: **Web application**.
3. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:8000/api/auth/google/callback
   ```
4. Click **Create** and copy your **Client ID** and **Client Secret**.

### Step 5: Configure `.env`
Create a `.env` file from the example:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
ENCRYPTION_KEY=your_fernet_encryption_key_here
```

---

## ⚡ Quickstart & Local Setup

### 1. Clone & Set Up Backend
```bash
# Clone the repository
git clone https://github.com/PremBorde/Agentic_RAG.git
cd Agentic_RAG

# Create & activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

### 2. Configure Environment
```bash
cp .env.example .env
# Fill in GEMINI_API_KEY and GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET
```

### 3. Build Frontend
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Run the Studio Server
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser!

---

## 💬 Example Queries

| Intent Category | Example Natural Language Query |
| :--- | :--- |
| **Gmail Search** | *"Search my unread emails about internships"* |
| **Gmail Summary** | *"Find the latest email from my manager and summarize it"* |
| **Gmail Draft & Send** | *"Send an email to prembordesn4@gmail.com regarding Diwali Wishes"* |
| **Calendar Schedule** | *"What is on my calendar for today?"* |
| **Calendar Availability**| *"Find a free 30-minute slot tomorrow afternoon"* |
| **Calendar Create** | *"Add a note on my calendar that today I am focusing on RAG project"* |
| **Web Research** | *"For web search today top 5 news"* |
| **Document RAG** | *"According to the uploaded syllabus, what are the practical assignments?"* |
| **Task Management** | *"Add a task to submit the AI project by Friday with high priority"* |
| **Long-Term Memory** | *"Remember that my preferred programming language is Python"* |

---

## 🔒 Security Principles

- **Explicit Approval for Write Actions**: No emails are sent or calendar events scheduled automatically. All sensitive actions present an interactive proposal card for human verification.
- **PKCE OAuth & Fernet Encryption**: Google OAuth tokens are encrypted at rest using Fernet symmetric encryption and never transmitted to the browser.
- **Prompt Injection Defense**: Content extracted from untrusted third-party emails or external documents is isolated from agent execution controls.
- **Deterministic Token Efficiency**: Direct conversational greetings and status checks consume zero LLM API quota.

---

## 📄 License
MIT License. Built with passion using LangChain, LangGraph, FastAPI, and React.
