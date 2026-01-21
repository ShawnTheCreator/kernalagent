"""
Skills API Router - REST endpoints for Skills DB.

Exposes skills to frontend while keeping SQLite private to backend.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.db.skills_repo import get_all_skills, get_skill_by_id, increment_skill_usage, save_skill

router = APIRouter(prefix="/api/skills", tags=["skills"])


class CreateSkillRequest(BaseModel):
    """Request body for creating a skill from C# SkillRecorder."""
    name: str
    description: Optional[str] = ""
    steps: List[Dict[str, Any]]  # List of recorded actions
    intent_signature: Optional[str] = None  # Auto-generated if not provided


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


@router.post("")
async def create_skill(request: CreateSkillRequest):
    """
    Create a new skill from C# SkillRecorder.
    
    Called after local save to sync skill to Firebase Firestore.
    
    Args:
        request: Skill name, description, and recorded steps
        
    Returns:
        The generated skill ID and status.
    """
    # Generate intent signature from skill name if not provided
    intent_signature = request.intent_signature or f"skill:{request.name.lower().replace(' ', '_')}"
    
    try:
        skill_id = save_skill(
            name=request.name,
            intent_signature=intent_signature,
            steps=request.steps,
            description=request.description or f"Recorded skill: {request.name}",
            confidence="0.95",  # User-recorded skills are high confidence
            is_global=False  # User skills are private by default
        )
        
        print(f"[SKILLS API] Created skill: {request.name} (ID: {skill_id})")
        
        return {
            "status": "created",
            "skill_id": skill_id,
            "skill_name": request.name
        }
    except Exception as e:
        print(f"[SKILLS API] Error creating skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
