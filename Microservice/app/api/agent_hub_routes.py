"""
Agent Hub Routes - REST API for agent interactions.

Provides endpoints for:
- Listing available agents
- Triggering agent analysis
- Creating and approving cleaning plans
- Quick scans for the Janitor agent

"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import os

from app.agents.agent_registry import get_registry
from app.agents.agent_planner import AgentPlanner
from app.agents.agent_router import ControlTower, SystemPulse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# =============================================================================
# Request/Response Models
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to trigger agent analysis."""
    deep_scan: bool = False
    

class PlanApprovalRequest(BaseModel):
    """Request to approve a plan."""
    plan_id: str
    approved: bool = True


class AgentIntentRequest(BaseModel):
    """Request to route an intent to agents."""
    intent: str
    session_id: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("")
async def list_agents():
    """
    List all registered agents.
    
    Returns info about each agent including:
    - Name, specialization, type
    - Triggers
    - Current status
    """
    logger.info("[AgentHub] Listing all agents...")
    registry = get_registry()
    
    # Ensure Recovery is registered
    _ensure_recovery_registered()
    
    agents_info = registry.list_info()
    logger.info(f"[AgentHub] Found {len(agents_info)} agents: {[a.get('name', 'unknown') for a in agents_info]}")
    
    return {
        "agents": agents_info,
        "count": len(registry.get_all()),
        "registry_status": "active"
    }


@router.post("/recovery/undo")
async def undo_last_action(count: int = 1):
    """
    Undo the last operational changes.
    
    Reverses recent move/delete/rename actions logged by the TransactionManager.
    """
    _ensure_recovery_registered()
    try:
        from app.agents.common.transaction_manager import get_transaction_manager
        tm = get_transaction_manager()
        undone = await tm.undo_last(count)
        
        if not undone:
            return {"success": False, "message": "Nothing to undo found"}
            
        return {
            "success": True, 
            "undone_count": len(undone),
            "details": undone
        }
    except Exception as e:
        logger.error(f"Undo failed: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{agent_name}")
async def get_agent(agent_name: str):
    """Get info about a specific agent."""
    registry = get_registry()
    agent = registry.get(agent_name.upper())
    
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    return agent.get_info()


@router.post("/{agent_name}/analyze")
async def trigger_analysis(agent_name: str, request: AnalyzeRequest):
    """
    Trigger an agent's analysis phase.
    
    Returns analysis findings without making any changes.
    """
    registry = get_registry()
    
    agent = registry.get(agent_name.upper())
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    try:
        context = {"deep_scan": request.deep_scan}
        result = await agent.analyze(context)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/plan")
async def create_plan(agent_name: str, analysis_id: str):
    """
    Create an action plan from a previous analysis.
    
    The plan requires user approval before execution.
    """
    # For now, we re-run analysis to create plan
    # In production, cache analysis results
    registry = get_registry()
    
    agent = registry.get(agent_name.upper())
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    try:
        analysis = await agent.analyze({})
        plan = await agent.plan(analysis)
        return plan.model_dump()
    except Exception as e:
        logger.error(f"Planning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/execute")
async def execute_plan(agent_name: str, request: PlanApprovalRequest):
    """
    Execute an approved plan.
    
    Only executes if the plan is marked as approved.
    """
    registry = get_registry()
    agent = registry.get(agent_name.upper())
    
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    try:
        # Create plan and approve it
        analysis = await agent.analyze({})
        plan = await agent.plan(analysis)
        
        if request.approved:
            plan.approve()
        
        result = await agent.execute(plan)
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route")
async def route_intent(request: AgentIntentRequest):
    """
    Route an intent to the appropriate agent via LLM planner.
    
    Checks if a specialized agent should handle the intent.
    Returns the agent name and plan if matched.
    """
    planner = AgentPlanner()
    plan = await planner.plan(request.intent, request.session_id)
    
    if plan is None:
        return {
            "routed": False,
            "agent": None,
            "message": "No agent matched this intent"
        }
    
    return {
        "routed": True,
        "agent": plan.agent_name,
        "plan": plan.model_dump()
    }


@router.get("/system/pulse")
async def get_system_pulse():
    """
    Get current system pulse (for Control Tower triggers).
    
    Returns disk usage, idle time, folder stats.
    """
    tower = ControlTower()
    pulse = await tower.get_system_pulse()
    return pulse.model_dump()


@router.get("/system/status")
async def get_control_tower_status():
    """Get Control Tower status."""
    tower = ControlTower()
    return tower.get_status()


# =============================================================================
# Memory / Timeline Endpoints
# =============================================================================

@router.get("/memory/timeline")
async def get_memory_timeline(limit: int = 50, user_id: str = "default_user"):
    """
    Get the episodic memory timeline (recent history).
    
    Returns a chronological feed of actions, chats, and thoughts.
    """
    try:
        from app.db.memory_bridge import get_timeline
        events = await get_timeline(user_id, limit)
        return {"events": events, "count": len(events)}
    except Exception as e:
        return {"events": [], "error": str(e)}

@router.post("/memory/timeline")
async def log_timeline_event(event: dict, user_id: str = "default_user"):
    """
    Log an external event to the timeline (e.g. from C# app).
    """
    try:
        from app.db.memory_bridge import log_event
        
        event_type = event.get("type", "system_alert")
        content = event.get("content", "")
        metadata = event.get("metadata", {})
        
        event_id = await log_event(user_id, event_type, content, metadata)
        return {"success": True, "event_id": event_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.delete("/memory/timeline")
async def clear_memory_timeline(user_id: str = "default_user"):
    """Clear the episodic timeline."""
    try:
        from app.db.memory_bridge import clear_timeline
        success = await clear_timeline(user_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================


def _ensure_recovery_registered():
    """Ensure the Recovery agent is registered."""
    registry = get_registry()
    
    if registry.get("RECOVERY_AGENT") is None:
        from app.agents.recovery.recovery_agent import RecoveryAgent
        recovery = RecoveryAgent()
        registry.register(recovery)
        logger.info("Registered RECOVERY_AGENT")
