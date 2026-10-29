from fastapi import APIRouter, HTTPException
from backend.services.approval_service import execute_approved_action, reject_action
from backend.services.database import get_pending_action

router = APIRouter(prefix="/api/actions", tags=["Human Approvals"])

@router.get("/{action_id}")
def get_action_details(action_id: str):
    """Retrieves status and details of a proposed action."""
    action = get_pending_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action

@router.post("/{action_id}/approve")
def approve_action(action_id: str):
    """Executes a proposed action upon explicit user confirmation."""
    result = execute_approved_action(action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Execution failed"))
    return result

@router.post("/{action_id}/reject")
def cancel_action(action_id: str):
    """Cancels a proposed action."""
    result = reject_action(action_id)
    return result

