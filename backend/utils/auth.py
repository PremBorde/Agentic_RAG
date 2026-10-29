import os
from typing import Optional
from fastapi import Request
from backend.services.database import get_user_by_id

def get_current_user_id(request: Request) -> Optional[str]:
    """Retrieves logged-in user_id from the session."""
    if hasattr(request, "session"):
        return request.session.get("user_id")
    return None

def get_current_user_email(request: Request) -> Optional[str]:
    """Retrieves logged-in user_email from the session."""
    if hasattr(request, "session"):
        return request.session.get("user_email")
    return None

def get_current_user(request: Request):
    """Retrieves full user record from database for currently logged-in user."""
    uid = get_current_user_id(request)
    if uid:
        return get_user_by_id(uid)
    return None

