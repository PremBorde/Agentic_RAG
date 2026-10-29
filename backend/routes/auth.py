from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from backend.services.google_service import (
    get_oauth_url,
    handle_oauth_callback,
    get_connection_status,
    disconnect_google
)

router = APIRouter(prefix="/api/auth/google", tags=["Google Auth"])

@router.get("/status")
def status():
    """Returns the current connection status of Google integration."""
    return get_connection_status()

@router.get("/url")
def get_auth_url(redirect_uri: Optional[str] = None):
    """Generates the Google OAuth authorization URL."""
    result = get_oauth_url(redirect_uri)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/callback")
def oauth_callback(code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None):
    """Callback endpoint for Google OAuth authorization code exchange."""
    res = handle_oauth_callback(code, redirect_uri)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "OAuth failed"))
    # Redirect back to frontend root with success query
    return RedirectResponse(url="/?google_connected=true")

@router.post("/disconnect")
def disconnect():
    """Disconnects Google account and deletes stored tokens."""
    success = disconnect_google()
    return {"success": success, "message": "Google account disconnected."}
