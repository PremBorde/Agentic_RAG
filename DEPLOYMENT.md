# 🚢 Production Deployment & Authentication Guide

Personal AI Agent Studio is fully containerized with a production multi-stage `Dockerfile` and `docker-compose.yml` supporting persistent SQLite database storage and FAISS vector indices.

---

## 🏗️ Architecture & Deployment Overview

The application is deployed as a single self-contained production container running FastAPI and serving pre-built React Single Page Application (SPA) static assets:

```
[User Browser]
      │
      ▼
[Reverse Proxy / Host :8000]
      │
      ▼
[FastAPI Application (Uvicorn)]
 ├── GET /health (Health & Telemetry)
 ├── /api/auth (Session & Standalone Auth)
 ├── /api/chat/stream (Synchronized SSE Pipeline)
 ├── /api/documents (FAISS RAG & Upload Security)
 ├── /api/conversations (Multi-User Persistence)
 └── Static Files (React 19 SPA)
      │
      ├── Volume: /app/data/agent_studio.db (SQLite)
      └── Volume: /app/data/faiss_index/ (FAISS Vector Store)
```

---

## 📋 Prerequisites

1. **Docker Engine $\ge$ 24.0** and **Docker Compose $\ge$ 2.20**.
2. **Google Gemini API Key**: [Get API Key](https://aistudio.google.com/app/apikey).
3. (Optional) **Google Workspace OAuth Credentials**: If integrating with Gmail and Google Calendar.

---

## 🚀 Deployment Instructions

### Step 1: Clone the Repository & Configure Environment

```bash
git clone https://github.com/your-org/personal-ai-agent-studio.git
cd personal-ai-agent-studio

# Copy template configuration
cp .env.example .env
```

### Step 2: Set Environment Variables in `.env`

Edit `.env` to configure your API keys and production secrets:

```ini
# Environment Mode
ENVIRONMENT=production
PORT=8000

# Cryptographically Secure Session Secret (Generate via: openssl rand -hex 32)
SECRET_KEY=9a48d8c2b74051fe44458d6e32d56d78791234567890abcdef1234567890abcd

# Allowed Origins for CORS (comma-separated, or specific domain)
ALLOWED_ORIGINS=https://agent.yourcompany.com,http://localhost:8000

# LLM Reasoning Engine (Required)
GEMINI_API_KEY=AIzaSy...your_gemini_api_key...
GOOGLE_API_KEY=AIzaSy...your_gemini_api_key...

# Google Workspace Integration (Optional - can also be configured via Settings UI)
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_client_secret
GOOGLE_REDIRECT_URI=https://agent.yourcompany.com/api/auth/google/callback

# Data Encryption Key for SQLite OAuth Tokens (Fernet 32-byte key)
ENCRYPTION_KEY=your_fernet_encryption_key
```

### Step 3: Launch with Docker Compose

```bash
# Build frontend, package python runner, and start in detached mode
docker compose up -d --build
```

### Step 4: Verify Deployment & Health Check

Query the production health check endpoint:

```bash
curl http://localhost:8000/health
```

Expected JSON response:
```json
{
  "status": "healthy",
  "service": "Personal AI Agent Studio",
  "version": "3.0.0",
  "environment": "production",
  "timestamp": "2026-11-03T11:45:00.000000Z",
  "checks": {
    "database": "ok",
    "vector_store": {
      "status": "ok",
      "indexed_documents_count": 0
    },
    "google_oauth_configured": true,
    "llm_configured": true
  }
}
```

---

## 🔐 Authentication Modes

Personal AI Agent Studio provides dual authentication:

### 1. Standalone Email & Password Authentication
Ideal for multi-user deployment where users do not immediately connect Google Workspace:
- **Registration**: `POST /api/auth/register`
  - Passwords hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a unique 16-byte random cryptographic salt.
- **Login**: `POST /api/auth/login`
  - Validates credentials using constant-time comparison (`secrets.compare_digest`) and establishes a secure session cookie.
- **User Profile**: `GET /api/auth/me`
  - Returns authenticated user details with sensitive passwords, access tokens, and refresh tokens automatically stripped.

### 2. Google OAuth 2.0 Integration
- Users can connect Google Workspace from the Settings modal.
- Tokens are encrypted server-side using Fernet encryption (`ENCRYPTION_KEY`) before saving into SQLite.
- Refresh tokens are never sent to the browser.

---

## 💾 Data Persistence & Backups

All state is persisted in Docker volume `personal_ai_agent_studio_data` mapped to `/app/data`:
- **SQLite Database** (`/app/data/agent_studio.db`):
  - Users, password hashes, and profiles
  - Conversation threads and message history
  - Tasks, to-dos, and priorities
  - Long-term memory and preferences
  - Human-in-the-Loop action proposals
- **FAISS Vector Store** (`/app/data/faiss_index/`):
  - Document chunk embeddings and document metadata

### Backup Script
```bash
# Backup database and vector store from running container
docker compose exec agent-studio tar -czf - /app/data > agent_studio_backup_$(date +%F).tar.gz
```

---

## 🛡️ Security Hardening Checklist

- [x] **File Upload Validation**: Enforces a strict 25MB maximum file size limit.
- [x] **File Extension Whitelist**: Only `.pdf`, `.txt`, `.md`, `.csv`, `.json` files accepted.
- [x] **Path Traversal Protection**: Filenames sanitized via `os.path.basename` and regex alphanumeric filtering.
- [x] **Zero-Leak Health Check**: `/health` displays operational status without exposing environment keys, API tokens, or session secrets.
- [x] **Non-Root Execution**: Container executes under unprivileged `appuser:appgroup`.
- [x] **CORS Origin Whitelisting**: Dynamic origin validation configured via `ALLOWED_ORIGINS`.

