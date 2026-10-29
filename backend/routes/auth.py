import os
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from backend.services.google_service import (
    get_oauth_url,
    handle_oauth_callback,
    exchange_code_for_user,
    get_connection_status,
    disconnect_google,
    get_client_config,
    DATA_DIR
)
from backend.services.database import get_user_by_id
from backend.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["Google OAuth & Session Auth"])

class GoogleConfigRequest(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: Optional[str] = "http://localhost:8000/api/auth/google/callback"

@router.get("/google/config-status")
@router.get("/config-status")
def config_status():
    """Checks if Google OAuth credentials (Client ID & Secret) are configured."""
    cfg = get_client_config()
    return {"configured": cfg is not None}

@router.post("/google/config")
@router.post("/config")
def save_config(req: GoogleConfigRequest):
    """Saves Google OAuth Client ID and Secret with validation."""
    cid = req.client_id.strip()
    csec = req.client_secret.strip()
    
    if not cid:
        raise HTTPException(status_code=400, detail="Client ID cannot be empty.")
    if "@" in cid:
        raise HTTPException(status_code=400, detail="This looks like an email address, not a Client ID. Client ID must end with '.apps.googleusercontent.com'.")
    if not cid.endswith(".apps.googleusercontent.com"):
        raise HTTPException(status_code=400, detail="Invalid Google Client ID. It must end with '.apps.googleusercontent.com'.")
    if not csec:
        raise HTTPException(status_code=400, detail="Client Secret cannot be empty.")
        
    os.makedirs(DATA_DIR, exist_ok=True)
    secret_path = os.path.join(DATA_DIR, "client_secret.json")
    data = {
        "web": {
            "client_id": cid,
            "client_secret": csec,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [req.redirect_uri or "http://localhost:8000/api/auth/google/callback"]
        }
    }
    with open(secret_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    return {"success": True, "message": "Google OAuth credentials saved securely."}

@router.get("/google/login")
@router.get("/login")
def login(redirect_uri: Optional[str] = None):
    """Builds the Google OAuth login URL and redirects the user directly to Google."""
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    result = get_oauth_url(r_uri)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return RedirectResponse(url=result["url"])

@router.get("/google/url")
@router.get("/url")
def get_auth_url(redirect_uri: Optional[str] = None):
    """Returns the Google OAuth authorization URL as JSON."""
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    result = get_oauth_url(r_uri)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/google/callback")
@router.get("/callback")
def oauth_callback(request: Request, code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None):
    """
    Exchanges authorization code for per-user tokens, encrypts tokens, 
    persists the user in the database, and creates a secure session.
    """
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    res = exchange_code_for_user(code, r_uri)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "OAuth code exchange failed"))

    # Establish session for logged-in user
    if hasattr(request, "session"):
        request.session["user_id"] = res["user_id"]
        request.session["user_email"] = res["email"]

    return RedirectResponse(url="/?connected=true")

@router.get("/status")
@router.get("/google/status")
def status(request: Request):
    """Returns the connection status and email for the active session user."""
    user_id = get_current_user_id(request)
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            return {
                "connected": True,
                "email": user["email"],
                "expires_at": user.get("token_expires_at")
            }
            
    # Fallback to connection status
    return get_connection_status(user_id)

@router.get("/logout")
@router.get("/google/logout")
@router.post("/logout")
def logout(request: Request):
    """Clears the session and redirects back home."""
    if hasattr(request, "session"):
        request.session.clear()
    return RedirectResponse(url="/?disconnected=true")

@router.post("/google/disconnect")
@router.post("/disconnect")
def disconnect(request: Request):
    """Disconnects Google account and clears session."""
    if hasattr(request, "session"):
        request.session.clear()
    disconnect_google()
    return {"success": True, "message": "Logged out and disconnected."}
