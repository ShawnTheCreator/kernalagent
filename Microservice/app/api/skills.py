"""
Skills API Router - REST endpoints for Skills DB.

Exposes skills to frontend while keeping SQLite private to backend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.skills_repo import get_all_skills, get_skill_by_id, increment_skill_usage

router = APIRouter(prefix="/api/skills", tags=["skills"])


class RunSkillRequest(BaseModel):
    """Request body for running a skill."""
    skill_id: str


class RunSkillResponse(BaseModel):
    """Response after queueing a skill."""
    status: str
    skill_id: str
    skill_name: str | None = None


@router.get("")
async def list_skills():
    """
    Get all learned skills.
    
    Returns:
        List of all skills with their steps and metadata.
    """
    skills = get_all_skills()
    return {"skills": skills}


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """
    Get a single skill by ID.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        Skill details or 404 if not found.
    """
    skill = get_skill_by_id(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"skill": skill}


@router.post("/run")
async def run_skill(request: RunSkillRequest):
    """
    Queue a skill for execution on the desktop agent.
    
    For hackathon: This immediately returns "queued" status.
    The actual execution is handled by the WebSocket layer.
    
    Args:
        request: Contains skill_id to run
        
    Returns:
        Status indicating the skill was queued.
    """
    skill = get_skill_by_id(request.skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Increment usage count
    increment_skill_usage(request.skill_id)
    
    # TODO: Send to desktop agent via WebSocket
    # For hackathon, we just mark it as queued
    # In production, this would push to a queue or broadcast via WS
    
    print(f"[SKILLS API] Queued skill for execution: {skill['name']}")
    
    return RunSkillResponse(
        status="queued",
        skill_id=request.skill_id,
        skill_name=skill["name"]
    )
