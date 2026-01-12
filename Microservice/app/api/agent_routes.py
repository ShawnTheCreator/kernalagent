"""
Agent Routes - REST APIs for Frontend Integration

Exposes stable, clean APIs for frontend consumption:
- POST /agent/preview - Preview agent decision for an intent
- GET /skills - List all learned skills
- GET /agent/session/{session_id} - Get session timeline

These APIs are safe (no real execution) and demo-friendly.

BUG FIXES APPLIED:
- FIX 1: Complete response schema with action in all steps
- FIX 2: Vision bypass (always UI_STABLE, no frame dependency)
- FIX 3: Safe DONE handling
- FIX 4: Filter malformed skill entries
- FIX 5: Clean JSON with logging module
"""
import logging
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

# Configure logging (FIX 5: Use logging instead of print)
logger = logging.getLogger(__name__)


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
    action: str  # Required: SCROLL, CLICK, TYPE, FIND, DONE, ANALYZE
    explanation: str


class PreviewResponse(BaseModel):
    """Response from agent preview endpoint."""
    session_id: str
    intent: str
    strategy: str  # REUSE_SKILL, ADAPT_SKILL, FRESH_REASONING
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
    - Does NOT depend on vision/frames (FIX 2)
    
    Args:
        request: Contains the user's intent
        
    Returns:
        Preview response with decision details
    """
    intent = request.intent.strip()
    if not intent:
        raise HTTPException(status_code=400, detail="Intent cannot be empty")
    
    logger.info(f"Preview request for intent: '{intent}'")
    
    # Create a new session
    session = create_session(intent)
    
    # Create fresh memory for this session
    memory = AgentMemory()
    
    # FIX 2: Always use UI_STABLE - preview mode does NOT depend on vision
    # This prevents red-screen failures and Gemini refusals
    decision = decide_next_action(
        vision_signal="UI_STABLE",  # Always stable for preview
        user_intent=intent,
        memory=memory
    )
    
    # Extract decision details with safe defaults
    strategy = decision.get("strategy", "FRESH_REASONING")
    skill_name = decision.get("skill_name")
    confidence = decision.get("confidence", 0.5)
    reason = decision.get("reason", "Decision made by agent")
    
    # FIX 1 & FIX 3: Build steps with guaranteed action field
    steps = []
    skill_steps = decision.get("steps", [])
    
    if skill_steps:
        for step in skill_steps:
            # Ensure action_type exists (FIX 1)
            action_type = step.get("action_type") or step.get("action") or "ANALYZE"
            explanation = step.get("context") or step.get("explanation") or ""
            steps.append(StepResponse(
                action=action_type.upper(),
                explanation=explanation
            ))
    
    # FIX 3: Handle DONE or empty steps safely
    if not steps:
        # Default step based on strategy
        if strategy == "FRESH_REASONING":
            steps.append(StepResponse(
                action="ANALYZE",
                explanation=reason
            ))
        else:
            steps.append(StepResponse(
                action="DONE",
                explanation="No specific steps available - requires live execution"
            ))
    
    # Determine action type for timeline
    action_type = steps[0].action if steps else "ANALYZE"
    
    # Add to session timeline
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
    
    logger.info(f"Preview complete: {strategy} | {skill_name} | {confidence:.0%}")
    
    # FIX 1: Return complete response with all required fields
    return PreviewResponse(
        session_id=session.session_id,
        intent=intent,
        strategy=strategy,
        skill=skill_name,
        confidence=round(confidence, 2),  # Clean float
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
    
    FIX 4: Filters out malformed skill entries missing required fields.
    
    Returns:
        List of all valid skills with metadata
    """
    logger.info("Fetching all skills")
    
    skills = get_all_skills()
    
    # FIX 4: Filter and transform to response model
    result = []
    for skill in skills:
        # FIX 4: Skip malformed entries missing required fields
        if not skill.get("id") or not skill.get("name") or not skill.get("intent_signature"):
            logger.warning(f"Skipping malformed skill: {skill}")
            continue
        
        result.append(SkillResponse(
            id=skill["id"],
            name=skill["name"],
            intent_signature=skill["intent_signature"],
            success_count=skill.get("success_count", 0),
            last_used_at=skill.get("last_used_at")
        ))
    
    logger.info(f"Returning {len(result)} valid skills")
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
    logger.info(f"Fetching session: {session_id}")
    
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
