import os
import json
import time
import re
from urllib.parse import urlparse, urlencode, parse_qs
from typing import Optional, Dict, Any
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
from backend.services.database import (
    get_user_by_id,
    register_user,
    authenticate_user,
    sanitize_user_dict
)
from backend.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/auth", tags=["Google OAuth & Session Auth"])

# ── Safe Redirect & Thread Sanitization Helpers ─────────────────────────────

def sanitize_thread_id(thread_id: Optional[str]) -> Optional[str]:
    """Validates and sanitizes a thread_id to prevent injection."""
    if not thread_id:
        return None
    tid = str(thread_id).strip()
    if re.match(r'^[a-zA-Z0-9_\-]{1,128}$', tid):
        return tid
    return None

def sanitize_return_to_path(return_to: Optional[str]) -> Optional[str]:
    """
    Validates that a return path is strictly a relative internal path.
    Guarantees that external or protocol-relative URLs (open redirects) cannot be triggered.
    """
    if not return_to:
        return None
    trimmed = str(return_to).strip()
    # Must start with forward slash, disallowing protocol relative (//evil.com), backslashes (/\\evil.com)
    if not trimmed.startswith("/") or trimmed.startswith("//") or trimmed.startswith("/\\"):
        return None
    # Reject dangerous protocols or schemes
    if any(s in trimmed.lower() for s in ("javascript:", "data:", "vbscript:", "\\")):
        return None
    parsed = urlparse(trimmed)
    if parsed.netloc or parsed.scheme:
        return None
    return trimmed

def build_redirect_url(
    base_return: Optional[str] = None,
    thread_id: Optional[str] = None,
    connected: bool = True,
    error: Optional[str] = None
) -> str:
    """
    Constructs a safe internal redirect URL back to the frontend.
    Preserves thread_id and sets connection or error indicators without leaking tokens or secrets.
    """
    target_base = "/"
    existing_params: Dict[str, Any] = {}

    safe_path = sanitize_return_to_path(base_return)
    if safe_path:
        parsed = urlparse(safe_path)
        target_base = parsed.path or "/"
        if parsed.query:
            for k, v in parse_qs(parsed.query).items():
                if k not in ("token", "code", "secret", "password"):
                    existing_params[k] = v[0] if len(v) == 1 else v

    # Add query flags
    if connected:
        existing_params["connected"] = "true"
    if error:
        existing_params["oauth_error"] = str(error)

    # Thread ID takes precedence if supplied
    clean_tid = sanitize_thread_id(thread_id) or sanitize_thread_id(existing_params.get("thread_id"))
    if clean_tid:
        existing_params["thread_id"] = clean_tid
    else:
        existing_params.pop("thread_id", None)

    qs = urlencode(existing_params)
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if frontend_url:
        return f"{frontend_url}{target_base}?{qs}" if qs else f"{frontend_url}{target_base}"
    return f"{target_base}?{qs}" if qs else target_base


# ── Concurrent OAuth State Storage ──────────────────────────────────────────

_oauth_state_cache: Dict[str, Dict[str, Any]] = {}
_oauth_verifier_cache: Dict[str, str] = {}  # Legacy compatibility
_STATE_TTL_SECONDS = 900  # 15 minute expiration

def _cleanup_expired_oauth_states():
    now = time.time()
    expired = [k for k, v in _oauth_state_cache.items() if now - v.get("created_at", 0) > _STATE_TTL_SECONDS]
    for k in expired:
        _oauth_state_cache.pop(k, None)

def store_oauth_state(
    state: str,
    code_verifier: Optional[str],
    thread_id: Optional[str],
    return_to: Optional[str],
    request: Optional[Request] = None
):
    """
    Stores OAuth state metadata mapped by unique state token.
    Supports concurrent browser tabs without cross-tab session contamination.
    """
    _cleanup_expired_oauth_states()
    meta = {
        "code_verifier": code_verifier,
        "thread_id": sanitize_thread_id(thread_id),
        "return_to": sanitize_return_to_path(return_to),
        "created_at": time.time()
    }
    _oauth_state_cache[state] = meta
    if code_verifier:
        _oauth_verifier_cache[state] = code_verifier

    # Mirror into Starlette session for session-level persistence
    if request and hasattr(request, "session"):
        if "oauth_states" not in request.session or not isinstance(request.session.get("oauth_states"), dict):
            request.session["oauth_states"] = {}
        request.session["oauth_states"][state] = meta
        if code_verifier:
            request.session["code_verifier"] = code_verifier
        request.session["oauth_state"] = state
        if meta["thread_id"]:
            request.session["oauth_thread_id"] = meta["thread_id"]

def pop_oauth_state(state: Optional[str], request: Optional[Request] = None) -> Dict[str, Any]:
    """Retrieves and clears preserved OAuth state metadata."""
    _cleanup_expired_oauth_states()
    meta: Dict[str, Any] = {}
    if state and state in _oauth_state_cache:
        meta = _oauth_state_cache.pop(state)
        _oauth_verifier_cache.pop(state, None)
    elif request and hasattr(request, "session"):
        session_states = request.session.get("oauth_states", {})
        if state and state in session_states:
            meta = session_states.pop(state)
        elif not state:
            meta = {
                "code_verifier": request.session.get("code_verifier"),
                "thread_id": request.session.get("oauth_thread_id"),
                "return_to": None
            }

    # Fallback to code_verifier if not populated
    if not meta.get("code_verifier"):
        if state and state in _oauth_verifier_cache:
            meta["code_verifier"] = _oauth_verifier_cache.pop(state)
        elif request and hasattr(request, "session"):
            meta["code_verifier"] = request.session.get("code_verifier")

    return meta


# ── Auth Endpoints ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register_account(req: RegisterRequest, request: Request):
    """Registers a new user with email and password."""
    try:
        user = register_user(req.email, req.password, req.display_name)
        if hasattr(request, "session"):
            request.session["user_id"] = user["id"]
            request.session["user_email"] = user["email"]
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login_account(req: LoginRequest, request: Request):
    """Authenticates user with email and password, establishing session."""
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if hasattr(request, "session"):
        request.session["user_id"] = user["id"]
        request.session["user_email"] = user["email"]
    return {"success": True, "user": user}

@router.get("/me")
def get_current_user_profile(request: Request):
    """Returns the authenticated user's profile and active session state."""
    user_id = get_current_user_id(request)
    if not user_id:
        return {"authenticated": False, "user": None}
    raw_user = get_user_by_id(user_id)
    if not raw_user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": sanitize_user_dict(raw_user)}

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
def login(
    request: Request,
    redirect_uri: Optional[str] = None,
    thread_id: Optional[str] = None,
    return_to: Optional[str] = None
):
    """
    Builds the Google OAuth login URL, preserves conversation thread and return path,
    and redirects the user directly to Google.
    """
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    result = get_oauth_url(r_uri)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    state = result.get("state")
    code_verifier = result.get("code_verifier")
    if state:
        store_oauth_state(
            state=state,
            code_verifier=code_verifier,
            thread_id=thread_id,
            return_to=return_to,
            request=request
        )

    return RedirectResponse(url=result["url"])

@router.get("/google/url")
@router.get("/url")
def get_auth_url(
    request: Request,
    redirect_uri: Optional[str] = None,
    thread_id: Optional[str] = None,
    return_to: Optional[str] = None
):
    """Returns the Google OAuth authorization URL as JSON with preserved conversation state."""
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    result = get_oauth_url(r_uri)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    state = result.get("state")
    code_verifier = result.get("code_verifier")
    if state:
        store_oauth_state(
            state=state,
            code_verifier=code_verifier,
            thread_id=thread_id,
            return_to=return_to,
            request=request
        )

    return result

@router.get("/google/callback")
@router.get("/callback")
def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    state: Optional[str] = None,
    redirect_uri: Optional[str] = None
):
    """
    Exchanges authorization code for per-user tokens, encrypts tokens, 
    persists the user in the database, and creates a secure session.
    Restores the originating conversation thread and return route upon return.
    """
    r_uri = redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    
    # Retrieve preserved state metadata (per-state token to isolate concurrent tabs)
    meta = pop_oauth_state(state, request=request)
    thread_id = meta.get("thread_id")
    return_to = meta.get("return_to")

    # Handle OAuth cancellation or errors from Google
    if error or not code:
        err_msg = error_description or error or "Google authentication cancelled or failed."
        target_url = build_redirect_url(
            base_return=return_to,
            thread_id=thread_id,
            connected=False,
            error=err_msg
        )
        return RedirectResponse(url=target_url)

    code_verifier = meta.get("code_verifier")
    res = exchange_code_for_user(code, r_uri, code_verifier=code_verifier)
    if not res.get("success"):
        err_msg = res.get("error", "OAuth code exchange failed")
        target_url = build_redirect_url(
            base_return=return_to,
            thread_id=thread_id,
            connected=False,
            error=err_msg
        )
        return RedirectResponse(url=target_url)

    # Establish session for logged-in user
    if hasattr(request, "session"):
        request.session["user_id"] = res["user_id"]
        request.session["user_email"] = res["email"]

    target_url = build_redirect_url(
        base_return=return_to,
        thread_id=thread_id,
        connected=True
    )
    return RedirectResponse(url=target_url)

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
@router.post("/google/disconnect")
@router.post("/disconnect")
def logout_or_disconnect(request: Request):
    """Clears the session, clears DB tokens, and returns JSON or redirect."""
    user_id = get_current_user_id(request)
    disconnect_google(user_id)
    if hasattr(request, "session"):
        request.session.clear()
    if request.method == "POST":
        return {"success": True, "connected": False, "message": "Successfully signed out."}
    return RedirectResponse(url="/?disconnected=true")
