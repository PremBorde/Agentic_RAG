from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List

from backend.utils.auth import get_current_user_id
from backend.services.database import (
    create_task,
    list_tasks,
    get_task,
    update_task,
    complete_task,
    delete_task,
    get_overdue_tasks
)

router = APIRouter(prefix="/api/tasks", tags=["Task Management"])

class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = None
    priority: Optional[str] = "medium"
    category: Optional[str] = "general"

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None

@router.get("")
def get_all_tasks(request: Request, status: Optional[str] = None, category: Optional[str] = None):
    """Lists all tasks with optional status, category, and user isolation filters."""
    user_id = get_current_user_id(request)
    return list_tasks(status=status, category=category, user_id=user_id)

@router.get("/overdue")
def get_overdue():
    """Lists overdue tasks."""
    return get_overdue_tasks()

@router.get("/{task_id}")
def get_single_task(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("")
def add_new_task(req: TaskCreateRequest, request: Request):
    user_id = get_current_user_id(request)
    return create_task(
        title=req.title,
        description=req.description or "",
        due_date=req.due_date,
        priority=req.priority or "medium",
        category=req.category or "general",
        user_id=user_id
    )

@router.put("/{task_id}")
def modify_task(task_id: str, req: TaskUpdateRequest):
    task = update_task(
        task_id=task_id,
        title=req.title,
        description=req.description,
        due_date=req.due_date,
        priority=req.priority,
        status=req.status,
        category=req.category
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/complete")
def finish_task(task_id: str):
    task = complete_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_id}")
def remove_task(task_id: str):
    success = delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": "Task deleted"}

