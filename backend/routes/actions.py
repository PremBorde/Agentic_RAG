from fastapi import APIRouter, HTTPException, Request
from backend.services.approval_service import execute_approved_action, reject_action
from backend.services.database import get_pending_action
from backend.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/actions", tags=["Human Approvals"])

@router.get("/{action_id}")
def get_action_details(action_id: str):
    """Retrieves status and details of a proposed action."""
    action = get_pending_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action

@router.post("/{action_id}/approve")
def approve_action(action_id: str, request: Request):
    """Executes a proposed action upon explicit user confirmation."""
    action = get_pending_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    user_id = get_current_user_id(request)
    action_user_id = action.get("payload", {}).get("user_id")
    if user_id and action_user_id and action_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied: action belongs to another user")

    result = execute_approved_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result

@router.post("/{action_id}/reject")
def cancel_action(action_id: str, request: Request):
    """Cancels a proposed action."""
    action = get_pending_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    user_id = get_current_user_id(request)
    action_user_id = action.get("payload", {}).get("user_id")
    if user_id and action_user_id and action_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied: action belongs to another user")

    result = reject_action(action_id)
    return result

