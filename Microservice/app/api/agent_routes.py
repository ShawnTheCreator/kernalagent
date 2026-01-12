"""
Agent Routes - REST APIs for Frontend Integration

Exposes stable, clean APIs for frontend consumption:
- POST /agent/preview - Preview agent decision for an intent
- GET /skills - List all learned skills
- GET /agent/session/{session_id} - Get session timeline

These APIs are safe (no real execution) and demo-friendly.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.agent.decision_engine import decide_next_action
from app.agent.memory import AgentMemory
from app.agent.sessions import (
    create_session,
    get_session,
    add_timeline_entry,
    complete_session,
    session_to_dict
)
from app.db.skills_repo import get_all_skills


# =============================================================================
# API Router
# =============================================================================
router = APIRouter(tags=["agent"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PreviewRequest(BaseModel):
    """Request body for agent preview."""
    intent: str


class StepResponse(BaseModel):
    """A single step in the action plan."""
    action: str
    explanation: str


class PreviewResponse(BaseModel):
    """Response from agent preview endpoint."""
    session_id: str
    intent: str
    strategy: str
    skill: Optional[str]
    confidence: float
    steps: List[StepResponse]


class SkillResponse(BaseModel):
    """A single skill in the skills list."""
    id: str
    name: str
    intent_signature: str
    success_count: int
    last_used_at: Optional[str]


class TimelineEntryResponse(BaseModel):
    """A single timeline entry."""
    strategy: str
    skill: Optional[str]
    action: str
    confidence: float
    reason: str


class SessionResponse(BaseModel):
    """Response from session endpoint."""
    session_id: str
    intent: str
    timeline: List[TimelineEntryResponse]
    status: str


# =============================================================================
# POST /agent/preview
# Runs the agent decision engine for a given intent (safe, no execution)
# =============================================================================

@router.post("/agent/preview", response_model=PreviewResponse)
async def preview_agent_decision(request: PreviewRequest):
    """
    Preview an agent decision for the given intent.
    
    This endpoint:
    - Creates a new session
    - Runs the real decision engine
    - Returns the strategy, skill match, and steps
    - Does NOT execute any real actions (safe by default)
    
    Args:
        request: Contains the user's intent
        
    Returns:
        Preview response with decision details
    """
    intent = request.intent.strip()
    if not intent:
        raise HTTPException(status_code=400, detail="Intent cannot be empty")
    
    print(f"[API] Preview request for intent: '{intent}'")
    
    # Create a new session
    session = create_session(intent)
    
    # Create fresh memory for this session
    memory = AgentMemory()
    
    # Run the real decision engine
    # We use UI_STABLE as the vision signal since this is a preview
    decision = decide_next_action(
        vision_signal="UI_STABLE",
        user_intent=intent,
        memory=memory
    )
    
    # Extract decision details
    strategy = decision.get("strategy", "FRESH_REASONING")
    skill_name = decision.get("skill_name")
    confidence = decision.get("confidence", 0.5)
    reason = decision.get("reason", "Decision made by agent")
    
    # Build steps from skill if available
    steps = []
    skill_steps = decision.get("steps", [])
    if skill_steps:
        for step in skill_steps:
            steps.append(StepResponse(
                action=step.get("action_type", "UNKNOWN"),
                explanation=step.get("context", step.get("explanation", ""))
            ))
    else:
        # For fresh reasoning, show what action would be taken
        steps.append(StepResponse(
            action="ANALYZE",
            explanation=reason
        ))
    
    # Add to session timeline
    action_type = steps[0].action if steps else "ANALYZE"
    add_timeline_entry(
        session_id=session.session_id,
        strategy=strategy,
        skill=skill_name,
        action=action_type,
        confidence=confidence,
        reason=reason
    )
    
    # Mark session as completed (preview is single-shot)
    complete_session(session.session_id)
    
    print(f"[API] Preview complete: {strategy} | {skill_name} | {confidence:.0%}")
    
    return PreviewResponse(
        session_id=session.session_id,
        intent=intent,
        strategy=strategy,
        skill=skill_name,
        confidence=confidence,
        steps=steps
    )


# =============================================================================
# GET /skills
# Returns all learned skills from Firebase (read-only)
# =============================================================================

@router.get("/skills", response_model=List[SkillResponse])
async def list_all_skills():
    """
    Get all learned skills from Firebase.
    
    This is a read-only endpoint that returns skill metadata.
    No mutations allowed.
    
    Returns:
        List of all skills with metadata
    """
    print("[API] Fetching all skills")
    
    skills = get_all_skills()
    
    # Transform to response model
    result = []
    for skill in skills:
        result.append(SkillResponse(
            id=skill.get("id", "unknown"),
            name=skill.get("name", "Unnamed Skill"),
            intent_signature=skill.get("intent_signature", ""),
            success_count=skill.get("success_count", 0),
            last_used_at=skill.get("last_used_at")
        ))
    
    print(f"[API] Returning {len(result)} skills")
    return result


# =============================================================================
# GET /agent/session/{session_id}
# Returns the full timeline of a session (for explainability)
# =============================================================================

@router.get("/agent/session/{session_id}", response_model=SessionResponse)
async def get_agent_session(session_id: str):
    """
    Get the full reasoning timeline of a session.
    
    Used by frontend for explainability and debugging.
    
    Args:
        session_id: The session's unique ID
        
    Returns:
        Session details with full timeline
    """
    print(f"[API] Fetching session: {session_id}")
    
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Convert to response format
    session_dict = session_to_dict(session)
    
    return SessionResponse(
        session_id=session_dict["session_id"],
        intent=session_dict["intent"],
        timeline=[
            TimelineEntryResponse(**entry) 
            for entry in session_dict["timeline"]
        ],
        status=session_dict["status"]
    )
