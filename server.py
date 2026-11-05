import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routes.documents import router as documents_router
from backend.routes.chat import router as chat_router
from backend.routes.auth import router as auth_router
from backend.routes.tasks import router as tasks_router
from backend.routes.memory import router as memory_router
from backend.routes.actions import router as actions_router
from backend.routes.conversations import router as conversations_router, threads_router
from backend.routes.okf import router as okf_router

app = FastAPI(
    title="Personal AI Agent Studio",
    description="Agentic Assistant with RAG, Gmail, Google Calendar, Task Management, and Human-in-the-Loop Approvals",
    version="3.0.0"
)

# ── Production-Grade CORS Configuration ─────────────────────────────────────
raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_origins and raw_origins.strip() != "*":
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
elif raw_origins.strip() == "*":
    origins = ["*"]
else:
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session Security ────────────────────────────────────────────────────────
env = os.getenv("ENVIRONMENT", "development").lower()
session_secret = os.getenv("SECRET_KEY")
if not session_secret:
    if env == "production":
        raise RuntimeError("CRITICAL: SECRET_KEY environment variable MUST be set in production mode.")
    session_secret = "agentic-rag-studio-secure-session-key-dev-fallback"

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=(env == "production")
)

# ── Register API Routers ────────────────────────────────────────────────────
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(memory_router)
app.include_router(actions_router)
app.include_router(conversations_router)
app.include_router(threads_router)
app.include_router(okf_router)

# ── Health Check Endpoint ───────────────────────────────────────────────────
@app.get("/health", tags=["system"])
def health_check():
    """Production health check verifying database, vector store, and configuration."""
    from backend.services.database import get_db_connection
    from backend.vector_store import indexed_documents
    from backend.services.google_service import get_client_config

    db_status = "ok"
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        conn.close()
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "service": "Personal AI Agent Studio",
        "version": "3.0.0",
        "environment": env,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {
            "database": db_status,
            "vector_store": {
                "status": "ok",
                "indexed_documents_count": len(indexed_documents)
            },
            "google_oauth_configured": bool(get_client_config()),
            "llm_configured": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        }
    }

# ── Mount Frontend Single Page Application (SPA) ────────────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path == "health":
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend build not found. Run 'npm run build' in frontend directory."}

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host=host, port=port, reload=False)
