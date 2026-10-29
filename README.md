# 🧠 Personal AI Agent Studio

<div align="center">

![Personal AI Agent Studio Logo](./Futuristic%20AI%20Knowledge%20Assistant%20Logo.png)

### Production-Grade Personal AI Assistant with LangGraph, Gmail, Google Calendar, FAISS RAG, and Human-in-the-Loop Approvals

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

It goes far beyond basic retrieval-augmented chatbots by combining:
1. **Private Document RAG**: On-device vector embeddings and semantic search across PDFs, DOCX, CSV, TXT, MD, JSON, and YouTube video transcripts.
2. **Official Gmail Integration**: Search inbox, read emails, summarize long conversation threads, compose drafts, and securely send emails.
3. **Google Calendar Integration**: Check schedule, find free 30/60-minute meeting slots, detect agenda conflicts, and schedule calendar events.
4. **Task & Reminder Manager**: Persistent to-do tracking with priorities (`low`, `medium`, `high`), due dates, and overdue alerts.
5. **Human-in-the-Loop Action Approvals**: Strict security guardrails where any sensitive write action (sending an email, creating/deleting a calendar event) produces an interactive proposal card with explicit **Approve** and **Cancel** controls.
6. **Long-Term Memory**: Persistent store for personal preferences and project context.
7. **Autonomous Web Search**: Fallback to DuckDuckGo when live web knowledge is required.

---

## 🚀 Key Capabilities

### 1. ✉️ Gmail Integration
- `search_emails`: Search messages using sender, subject, keywords, date, or unread filters.
- `read_email`: Safely inspect message body, sender, and recipient metadata.
- `summarize_email_thread`: Condense long multi-message conversations and extract key action items.
- `create_email_draft`: Prepare draft messages directly in your Gmail drafts folder.
- `send_email`: **Zero unauthorized sends**. The assistant prepares a structured action card previewing recipient, subject, and body; the email is transmitted only after you click **Approve & Execute**.

### 2. 📅 Google Calendar Integration
- `list_events`: Retrieve upcoming schedule and meeting times.
- `check_availability`: Detect conflicts on your primary calendar for any target timeframe.
- `find_meeting_slots`: Automatically scan business hours over the next 3–5 days to locate open slots.
- `create_event`: Propose meeting invitations with title, agenda, and times; scheduled only upon explicit user approval.
- `delete_event`: Safely cancel or delete events with human confirmation.

### 3. 📋 Persistent Task & Reminder Manager
- Lightweight persistent SQLite store (`data/agent_studio.db`).
- Create, filter, prioritize, and complete tasks directly via chat commands (e.g., *"Create a task to finish the RAG report by Friday"*) or via the dedicated **Tasks** modal in the top bar.
- Automatic overdue task detection and status tracking.

### 4. 🛡️ Security & Human-in-the-Loop Governance
- **Backend-Only OAuth Tokens**: Google tokens (`data/google_tokens.json`) are stored strictly on the server and never sent to the browser.
- **Single-Use Action Bindings**: Every proposed action receives a cryptographic ID bound to exact parameters. Retries or stale tokens cannot trigger duplicate actions.
- **Untrusted Input Protection**: Content retrieved from emails, web pages, or documents is treated as untrusted data; embedded prompt injections are ignored.

### 5. 📂 Document Ingestion & Local FAISS RAG
- Supports `.pdf`, `.docx`, `.txt`, `.csv`, `.md`, `.json`, and YouTube URLs.
- Local vector retrieval via `FAISS` and `fastembed` (high-throughput on-device embeddings).
- Interactive inline citations `[1]` that highlight the exact source chunk in an expandable retrieved context accordion.

---

## 🏗️ Architecture & Workflow

```
                                      [USER REQUEST]
                                             │
                                             ▼
                             [LangGraph Tool-Aware Router]
                   ┌──────────┬──────────┬──────────┬──────────┐
                   ▼          ▼          ▼          ▼          ▼
             [Conversation] [RAG FAISS] [Gmail]  [Calendar] [Tasks/Memory]
                                         │          │
                              (Sensitive Action Required?)
                                      ├── Yes ──► [Action Proposal Card]
                                      │                  │
                                      │             (User Clicks)
                                      │            ┌─────┴─────┐
                                      │            ▼           ▼
                                      │       [Approve]     [Cancel]
                                      │            │           │
                                      │            ▼           ▼
                                      │       [Execute API] [Abort]
                                      │
                                      └── No ──► [Tool Query & Output]
                                                        │
                                                        ▼
                                            [Final Grounded Answer]
```

---

## 🔑 Google OAuth 2.0 Setup Guide

To enable Gmail and Google Calendar features:

### Step 1: Create a Google Cloud Project
1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** > **New Project** and name it `Personal AI Agent`.

### Step 2: Enable APIs
1. Navigate to **APIs & Services** > **Library**.
2. Search and click **Enable** for:
   - **Gmail API**
   - **Google Calendar API**

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. Select **External** and click **Create**.
3. Fill in App Name (`Personal AI Agent`) and your email address.
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
Add your keys to your local `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

---

## ⚡ Quickstart & Local Setup

### 1. Clone & Set Up Backend
```bash
# Clone the repository
git clone https://github.com/PremBorde/Agentic_RAG.git
cd Agentic_RAG

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
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

## 💬 Example Queries to Try

| Category | Example Query |
| :--- | :--- |
| **Gmail** | *"Search my unread emails about internships"* |
| **Gmail** | *"Find the latest email from my professor and summarize it"* |
| **Gmail (Approval)** | *"Send an email to team@example.com with subject 'Sprint Update' explaining today's progress"* |
| **Calendar** | *"What meetings do I have tomorrow?"* |
| **Calendar** | *"Find a free 30-minute slot this Friday afternoon"* |
| **Calendar (Approval)**| *"Schedule a Project Planning meeting tomorrow at 2 PM"* |
| **Tasks** | *"Create a task to finish my RAG project by Friday with high priority"* |
| **Tasks** | *"Show my overdue tasks"* |
| **Memory** | *"Remember that I prefer meeting agendas sent 24 hours in advance"* |
| **Document RAG** | *"Upload your PDF / video transcript and query specific details"* |
| **Web Research** | *"Search the web for the latest Python 3.13 release notes"* |

---

## 🔒 Security Summary

- **Human-in-the-Loop Approvals**: Sensitive write actions require clicking "Approve" on UI cards.
- **Backend Token Storage**: OAuth access and refresh tokens are isolated in `data/google_tokens.json` (gitignored).
- **Prompt Injection Defense**: Text extracted from third-party emails or uploaded PDFs cannot hijack tool routing.
- **Zero API Quota Leaks**: Direct conversational and small talk requests bypass external tool calls.

---

## 📜 License
MIT License. Built with passion using LangChain, LangGraph, FastAPI, and React.
