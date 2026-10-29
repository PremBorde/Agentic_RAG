import os
from typing import Dict, Any, Optional
from backend.services.database import create_pending_action, get_pending_action, update_action_status
from backend.services.google_service import (
    send_email_direct,
    create_calendar_event_direct,
    update_calendar_event_direct,
    delete_calendar_event_direct
)

def propose_action(action_type: str, summary: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generates an action proposal requiring explicit user approval before execution."""
    action_id = create_pending_action(action_type, summary, payload)
    return {
        "action_id": action_id,
        "action_type": action_type,
        "summary": summary,
        "payload": payload,
        "status": "pending"
    }

def execute_approved_action(action_id: str) -> Dict[str, Any]:
    """Executes a previously proposed action after user clicks 'Approve'."""
    action = get_pending_action(action_id)
    if not action:
        return {"success": False, "error": f"Action ID '{action_id}' not found."}
        
    if action["status"] != "pending":
        return {
            "success": False,
            "error": f"Action has already been {action['status']}. Duplicate execution blocked."
        }
        
    action_type = action["action_type"]
    payload = action["payload"]
    result: Dict[str, Any] = {}
    
    try:
        if action_type == "send_email":
            result = send_email_direct(
                to=payload.get("to", ""),
                subject=payload.get("subject", ""),
                body=payload.get("body", "")
            )
        elif action_type == "create_calendar_event":
            result = create_calendar_event_direct(
                summary=payload.get("summary", ""),
                start_time=payload.get("start_time", ""),
                end_time=payload.get("end_time", ""),
                description=payload.get("description", ""),
                attendees=payload.get("attendees")
            )
        elif action_type == "update_calendar_event":
            result = update_calendar_event_direct(
                event_id=payload.get("event_id", ""),
                summary=payload.get("summary"),
                start_time=payload.get("start_time"),
                end_time=payload.get("end_time")
            )
        elif action_type == "delete_calendar_event":
            result = delete_calendar_event_direct(
                event_id=payload.get("event_id", "")
            )
        else:
            return {"success": False, "error": f"Unknown action type: {action_type}"}
            
        if result.get("status") == "success":
            update_action_status(action_id, "completed")
            return {"success": True, "action_type": action_type, "result": result}
        else:
            update_action_status(action_id, "failed")
            return {"success": False, "action_type": action_type, "result": result}
            
    except Exception as e:
        update_action_status(action_id, "failed")
        return {"success": False, "error": str(e)}

def reject_action(action_id: str) -> Dict[str, Any]:
    """Rejects/cancels a proposed action."""
    action = get_pending_action(action_id)
    if not action:
        return {"success": False, "error": "Action not found."}
        
    update_action_status(action_id, "cancelled")
    return {"success": True, "message": "Action cancelled by user."}

