import os
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

app = FastAPI(
    title="Personal AI Agent Studio",
    description="Agentic Assistant with RAG, Gmail, Google Calendar, Task Management, and Human-in-the-Loop Approvals",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_secret = os.getenv("SECRET_KEY", "agentic-rag-studio-secure-session-key-random")
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    max_age=14 * 24 * 3600,
    same_site="lax",
    https_only=False
)

# Register API Routers
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(memory_router)
app.include_router(actions_router)

# Mount Frontend Single Page Application (SPA)
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api"):
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
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
