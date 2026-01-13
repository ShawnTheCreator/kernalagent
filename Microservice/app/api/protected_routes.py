"""
Protected Routes - Authenticated API Endpoints

All endpoints in this module require valid Firebase authentication.
User data is isolated - each user can only access their own resources.

Endpoints:
- GET/PATCH /me - User profile
- GET/PATCH /me/settings - User settings
- GET/POST/DELETE /me/skills - User skills
- GET /me/sessions - User sessions
- GET /me/memory - User memory
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.auth_middleware import verify_firebase_token
from app.db.users_repo import get_user, update_user
from app.db.settings_repo import get_settings, update_settings
from app.db.skills_repo import (
    get_user_skills,
    get_user_skill_by_id,
    save_user_skill,
    delete_user_skill,
    update_user_skill,
    increment_user_skill_usage
)
from app.db.sessions_repo import (
    get_recent_sessions,
    get_session,
    get_session_steps
)
from app.db.memory_repo import get_memory, update_memory

logger = logging.getLogger(__name__)

# =============================================================================
# API Router
# =============================================================================
router = APIRouter(prefix="/me", tags=["user"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UserProfileResponse(BaseModel):
    """User profile data."""
    id: str
    email: Optional[str]
    name: Optional[str]
    photoURL: Optional[str]
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    plan: str
    createdAt: str
    lastLogin: str


class UpdateProfileRequest(BaseModel):
    """Request to update user profile."""
    name: Optional[str] = None
    photoURL: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class SettingsResponse(BaseModel):
    """User settings data."""
    theme: str = "dark"
    executionMode: str = "MOCK"
    confirmActions: bool = True
    language: str = "en"
    notificationsEnabled: bool = True
    autoSaveSkills: bool = True


class UpdateSettingsRequest(BaseModel):
    """Request to update user settings."""
    theme: Optional[str] = None
    executionMode: Optional[str] = None
    confirmActions: Optional[bool] = None
    language: Optional[str] = None
    notificationsEnabled: Optional[bool] = None
    autoSaveSkills: Optional[bool] = None


class SkillStep(BaseModel):
    """A step within a skill."""
    action_type: str
    context: Optional[str] = None
    target: Optional[str] = None


class SkillResponse(BaseModel):
    """User skill data."""
    id: str
    name: str
    intent_signature: str
    description: Optional[str]
    confidence: float
    success_count: int
    last_used_at: Optional[str]
    created_at: Optional[str]


class CreateSkillRequest(BaseModel):
    """Request to create a new skill."""
    name: str
    intent_signature: str
    description: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.5


class UpdateSkillRequest(BaseModel):
    """Request to update a skill."""
    name: Optional[str] = None
    intent_signature: Optional[str] = None
    description: Optional[str] = None
    confidence: Optional[float] = None


class SessionResponse(BaseModel):
    """Session summary data."""
    session_id: str
    intent: str
    started_at: str
    ended_at: Optional[str]
    status: str
    confidence: float
    step_count: int


class SessionDetailResponse(BaseModel):
    """Session with steps."""
    session_id: str
    intent: str
    started_at: str
    ended_at: Optional[str]
    status: str
    confidence: float
    steps: List[Dict[str, Any]]


class MemoryResponse(BaseModel):
    """User memory data."""
    frequent_skills: List[str]
    failure_patterns: List[str]
    success_patterns: List[str]
    updated_at: Optional[str]


# =============================================================================
# Profile Endpoints
# =============================================================================

@router.get("", response_model=UserProfileResponse)
async def get_my_profile(user_id: str = Depends(verify_firebase_token)):
    """
    Get current user's profile.
    
    Requires: Authorization: Bearer <token>
    """
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    return UserProfileResponse(
        id=user_id,
        email=user.get("email"),
        name=user.get("name"),
        photoURL=user.get("photoURL"),
        bio=user.get("bio"),
        location=user.get("location"),
        website=user.get("website"),
        plan=user.get("plan", "free"),
        createdAt=user.get("createdAt", ""),
        lastLogin=user.get("lastLogin", "")
    )


@router.patch("", response_model=UserProfileResponse)
async def update_my_profile(
    request: UpdateProfileRequest,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Update current user's profile.
    
    Requires: Authorization: Bearer <token>
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = update_user(user_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Return updated profile
    return await get_my_profile(user_id)


# =============================================================================
# Settings Endpoints
# =============================================================================

@router.get("/settings", response_model=SettingsResponse)
async def get_my_settings(user_id: str = Depends(verify_firebase_token)):
    """
    Get current user's settings.
    
    Requires: Authorization: Bearer <token>
    Creates default settings if none exist.
    """
    settings = get_settings(user_id)
    return SettingsResponse(**settings)


@router.patch("/settings", response_model=SettingsResponse)
async def update_my_settings(
    request: UpdateSettingsRequest,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Update current user's settings.
    
    Requires: Authorization: Bearer <token>
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    updated = update_settings(user_id, updates)
    return SettingsResponse(**updated)


# =============================================================================
# Skills Endpoints
# =============================================================================

@router.get("/skills", response_model=List[SkillResponse])
async def get_my_skills(user_id: str = Depends(verify_firebase_token)):
    """
    Get all skills for current user.
    
    Requires: Authorization: Bearer <token>
    """
    skills = get_user_skills(user_id)
    
    return [
        SkillResponse(
            id=s.get("id", ""),
            name=s.get("name", ""),
            intent_signature=s.get("intent_signature", ""),
            description=s.get("description"),
            confidence=s.get("confidence", 0.5),
            success_count=s.get("success_count", 0),
            last_used_at=s.get("last_used_at"),
            created_at=s.get("created_at")
        )
        for s in skills
        if s.get("id") and s.get("name")  # Filter malformed entries
    ]


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_my_skill(
    request: CreateSkillRequest,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Create a new skill for current user.
    
    Requires: Authorization: Bearer <token>
    """
    skill_id = save_user_skill(
        user_id=user_id,
        name=request.name,
        intent_signature=request.intent_signature,
        steps=request.steps,
        description=request.description,
        confidence=request.confidence
    )
    
    # Return created skill
    skill = get_user_skill_by_id(user_id, skill_id)
    if not skill:
        raise HTTPException(status_code=500, detail="Failed to create skill")
    
    return SkillResponse(
        id=skill["id"],
        name=skill["name"],
        intent_signature=skill["intent_signature"],
        description=skill.get("description"),
        confidence=skill.get("confidence", 0.5),
        success_count=skill.get("success_count", 0),
        last_used_at=skill.get("last_used_at"),
        created_at=skill.get("created_at")
    )


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_my_skill(
    skill_id: str,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Get a specific skill by ID.
    
    Requires: Authorization: Bearer <token>
    """
    skill = get_user_skill_by_id(user_id, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return SkillResponse(
        id=skill["id"],
        name=skill["name"],
        intent_signature=skill["intent_signature"],
        description=skill.get("description"),
        confidence=skill.get("confidence", 0.5),
        success_count=skill.get("success_count", 0),
        last_used_at=skill.get("last_used_at"),
        created_at=skill.get("created_at")
    )


@router.patch("/skills/{skill_id}", response_model=SkillResponse)
async def update_my_skill(
    skill_id: str,
    request: UpdateSkillRequest,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Update a specific skill.
    
    Requires: Authorization: Bearer <token>
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = update_user_skill(user_id, skill_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return await get_my_skill(skill_id, user_id)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_skill(
    skill_id: str,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Delete a specific skill.
    
    Requires: Authorization: Bearer <token>
    """
    success = delete_user_skill(user_id, skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/skills/{skill_id}/use", response_model=SkillResponse)
async def use_my_skill(
    skill_id: str,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Mark a skill as used (increments success_count).
    
    Requires: Authorization: Bearer <token>
    """
    success = increment_user_skill_usage(user_id, skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return await get_my_skill(skill_id, user_id)


# =============================================================================
# Sessions Endpoints
# =============================================================================

@router.get("/sessions", response_model=List[SessionResponse])
async def get_my_sessions(
    limit: int = 20,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Get recent sessions for current user.
    
    Requires: Authorization: Bearer <token>
    """
    sessions = get_recent_sessions(user_id, limit=limit)
    
    return [
        SessionResponse(
            session_id=s.get("session_id", ""),
            intent=s.get("intent", ""),
            started_at=s.get("started_at", ""),
            ended_at=s.get("ended_at"),
            status=s.get("status", "UNKNOWN"),
            confidence=s.get("confidence", 0.0),
            step_count=s.get("step_count", 0)
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_my_session(
    session_id: str,
    user_id: str = Depends(verify_firebase_token)
):
    """
    Get a specific session with all steps.
    
    Requires: Authorization: Bearer <token>
    """
    session = get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    steps = get_session_steps(user_id, session_id)
    
    return SessionDetailResponse(
        session_id=session.get("session_id", ""),
        intent=session.get("intent", ""),
        started_at=session.get("started_at", ""),
        ended_at=session.get("ended_at"),
        status=session.get("status", "UNKNOWN"),
        confidence=session.get("confidence", 0.0),
        steps=steps
    )


# =============================================================================
# Memory Endpoints
# =============================================================================

@router.get("/memory", response_model=MemoryResponse)
async def get_my_memory(user_id: str = Depends(verify_firebase_token)):
    """
    Get agent memory for current user.
    
    Requires: Authorization: Bearer <token>
    """
    memory = get_memory(user_id, "long_term")
    
    return MemoryResponse(
        frequent_skills=memory.get("frequent_skills", []),
        failure_patterns=memory.get("failure_patterns", []),
        success_patterns=memory.get("success_patterns", []),
        updated_at=memory.get("updated_at")
    )


@router.patch("/memory", response_model=MemoryResponse)
async def update_my_memory(
    data: Dict[str, Any],
    user_id: str = Depends(verify_firebase_token)
):
    """
    Update agent memory for current user.
    
    Requires: Authorization: Bearer <token>
    """
    updated = update_memory(user_id, "long_term", data)
    
    return MemoryResponse(
        frequent_skills=updated.get("frequent_skills", []),
        failure_patterns=updated.get("failure_patterns", []),
        success_patterns=updated.get("success_patterns", []),
        updated_at=updated.get("updated_at")
    )
