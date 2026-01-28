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
    
    # Ensure Janitor & Recovery are registered
    _ensure_janitor_registered()
    _ensure_recovery_registered()
    _ensure_sentinel_registered()
    
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
    _ensure_janitor_registered()
    
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
    _ensure_janitor_registered()
    
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


@router.get("/janitor/quick-scan")
async def janitor_quick_scan():
    """
    Quick scan of Downloads/Desktop for cleanup opportunities.
    
    Fast endpoint that returns summary stats without full analysis.
    """
    logger.info("[AgentHub] Starting Janitor quick scan...")
    _ensure_janitor_registered()
    
    registry = get_registry()
    janitor = registry.get("JANITOR_AGENT")
    
    if janitor is None:
        logger.error("[AgentHub] Janitor agent not available")
        raise HTTPException(status_code=500, detail="Janitor agent not available")
    
    try:
        logger.info("[AgentHub] Executing quick scan...")
        result = await janitor.quick_scan()
        logger.info(f"[AgentHub] Quick scan completed: {result.get('scan_status', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"[AgentHub] Quick scan error: {e}")
        import traceback
        logger.error(f"[AgentHub] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route")
async def route_intent(request: AgentIntentRequest):
    """
    Route an intent to the appropriate agent via LLM planner.
    
    Checks if a specialized agent should handle the intent.
    Returns the agent name and plan if matched.
    """
    _ensure_janitor_registered()
    
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
# Daemon Control Endpoints
# =============================================================================

@router.get("/janitor/daemon/status")
async def get_daemon_status():
    """Get Janitor daemon status."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        return {
            "running": daemon.is_running,
            "stats": daemon.stats,
            "pending_actions": len(daemon.pending_actions),
        }
    except Exception as e:
        return {"running": False, "error": str(e)}


@router.post("/janitor/daemon/start")
async def start_daemon():
    """Start the Janitor daemon."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        await daemon.start()
        return {"success": True, "message": "Daemon started"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/janitor/daemon/stop")
async def stop_daemon():
    """Stop the Janitor daemon."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        await daemon.stop()
        return {"success": True, "message": "Daemon stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/janitor/pending-actions")
async def get_pending_actions():
    """Get pending actions awaiting user approval."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        
        actions = []
        for action in daemon.pending_actions:
            actions.append({
                "id": action["id"],
                "file": action["file_info"].get("filename"),
                "capability": action["result"].capability,
                "action_type": action["result"].action_type,
                "suggestion": action["result"].suggestion,
                "confidence": action["result"].confidence,
            })
        
        return {"pending": actions, "count": len(actions)}
    except Exception as e:
        return {"pending": [], "error": str(e)}


@router.post("/janitor/approve/{action_id}")
async def approve_action(action_id: str):
    """Approve a pending action."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        success = await daemon.approve_action(action_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/janitor/reject/{action_id}")
async def reject_action(action_id: str):
    """Reject a pending action."""
    try:
        from app.agents.janitor.daemon import get_janitor_daemon
        daemon = get_janitor_daemon()
        success = await daemon.reject_action(action_id)
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Killer Capability Endpoints
# =============================================================================

@router.get("/janitor/scan/duplicates")
async def scan_duplicates():
    """Scan for duplicate files across user directories."""
    try:
        from app.agents.janitor.capabilities.duplicate_hunter import DuplicateHunterCapability
        hunter = DuplicateHunterCapability()
        result = await hunter.full_scan()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/janitor/scan/browsers")
async def scan_browsers():
    """Scan browser data sizes."""
    try:
        from app.agents.janitor.capabilities.browser_cleaner import BrowserCleanerCapability
        cleaner = BrowserCleanerCapability()
        result = await cleaner.scan()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/janitor/clean/browsers")
async def clean_browsers(browsers: list[str] = None, clean_type: str = "cache"):
    """Clean browser data (cache, cookies, history, or all)."""
    try:
        from app.agents.janitor.capabilities.browser_cleaner import BrowserCleanerCapability
        cleaner = BrowserCleanerCapability()
        result = await cleaner.clean(browsers, clean_type)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/janitor/scan/large-files")
async def scan_large_files(min_size_mb: int = 100):
    """Scan for large files that can be deleted."""
    try:
        from app.agents.janitor.capabilities.disk_reclaimer import DiskReclaimerCapability
        reclaimer = DiskReclaimerCapability()
        result = await reclaimer.scan(min_size_mb)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/janitor/scan/old-installers")
async def scan_old_installers(days: int = 30):
    """Find old installer files safe to delete."""
    try:
        from app.agents.janitor.capabilities.disk_reclaimer import DiskReclaimerCapability
        reclaimer = DiskReclaimerCapability()
        result = await reclaimer.find_old_installers(days)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/janitor/scan/privacy")
async def scan_privacy():
    """Scan privacy-sensitive data locations."""
    try:
        from app.agents.janitor.capabilities.privacy_sweep import PrivacySweepCapability
        sweeper = PrivacySweepCapability()
        result = await sweeper.scan()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/janitor/sweep/privacy")
async def sweep_privacy(deep: bool = False):
    """Perform privacy sweep (clears temp, recent docs, etc.)."""
    try:
        from app.agents.janitor.capabilities.privacy_sweep import PrivacySweepCapability
        sweeper = PrivacySweepCapability()
        result = await sweeper.sweep(deep)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/janitor/scan/programs")
async def scan_programs():
    """Scan installed programs and detect unused ones."""
    try:
        from app.agents.janitor.capabilities.smart_uninstaller import SmartUninstallerCapability
        uninstaller = SmartUninstallerCapability()
        result = await uninstaller.scan()
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/janitor/uninstall")
async def uninstall_program(program_name: str):
    """Trigger uninstall for a program."""
    try:
        from app.agents.janitor.capabilities.smart_uninstaller import SmartUninstallerCapability
        uninstaller = SmartUninstallerCapability()
        result = await uninstaller.uninstall(program_name)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


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
# Janitor V3 - Smart Organizer Endpoints
# =============================================================================

@router.post("/janitor/clean-folder")
async def clean_folder(request: dict):
    """
    Scan and organize all files in a folder.
    
    Request:
        {
            "folder_path": "C:/Users/xyz/Downloads",
            "auto_approve": ["IMAGES", "VIDEOS", "AUDIO"],  # optional
            "preview_only": true  # if true, return suggestions without moving
        }
    
    Returns:
        Summary of actions taken or suggested
    """
    try:
        folder_path = request.get("folder_path", "")
        auto_approve = request.get("auto_approve", ["IMAGES", "VIDEOS", "AUDIO", "SCREENSHOTS"])
        preview_only = request.get("preview_only", False)
        
        if not folder_path or not os.path.isdir(folder_path):
            return {"success": False, "error": "Invalid folder path"}
        
        from app.agents.janitor.capabilities.auto_organizer import AutoOrganizerCapability
        organizer = AutoOrganizerCapability()
        
        if preview_only:
            # Just scan and return suggestions
            results = await organizer.scan_folder(folder_path)
            suggestions = [
                {
                    "file": os.path.basename(r.metadata.get("source", "")),
                    "suggestion": r.suggestion,
                    "category": r.metadata.get("category", ""),
                    "destination": r.metadata.get("destination", ""),
                    "auto_approve": r.metadata.get("auto_approve", False),
                }
                for r in results
            ]
            return {
                "success": True,
                "preview_only": True,
                "count": len(suggestions),
                "suggestions": suggestions
            }
        else:
            # Actually organize
            summary = await organizer.organize_folder(folder_path, auto_approve)
            return {"success": True, **summary}
            
    except Exception as e:
        logger.error(f"[Janitor V3] Clean folder failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/janitor/scan-file")
async def scan_file(request: dict):
    """
    Scan a single file with all Janitor capabilities.
    
    Request:
        {"file_path": "C:/Users/xyz/Downloads/file.jpg"}
    
    Returns:
        List of suggested actions from all capabilities
    """
    try:
        file_path = request.get("file_path", "")
        
        if not file_path or not os.path.isfile(file_path):
            return {"success": False, "error": "Invalid file path"}
        
        from app.agents.janitor.capabilities import run_capabilities
        
        file_info = {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
        }
        
        results = await run_capabilities(file_path, file_info)
        
        suggestions = [
            {
                "capability": r.capability,
                "action_type": r.action_type,
                "suggestion": r.suggestion,
                "confidence": r.confidence,
                "requires_permission": r.requires_permission,
                "metadata": r.metadata,
            }
            for r in results
        ]
        
        return {
            "success": True,
            "file": os.path.basename(file_path),
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"[Janitor V3] Scan file failed: {e}")
        return {"success": False, "error": str(e)}


@router.post("/janitor/rename-file")
async def rename_file_smart(request: dict):
    """
    Smart rename a file using AI analysis.
    
    Request:
        {
            "file_path": "C:/Users/xyz/Downloads/IMG_20240124_123456.jpg",
            "custom_name": null  # optional, if provided uses this instead of AI
        }
    """
    try:
        file_path = request.get("file_path", "")
        custom_name = request.get("custom_name")
        
        if not file_path or not os.path.isfile(file_path):
            return {"success": False, "error": "Invalid file path"}
        
        from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability
        renamer = SmartRenamerCapability()
        
        file_info = {
            "filename": os.path.basename(file_path),
            "size": os.path.getsize(file_path),
        }
        
        if custom_name:
            # Use custom name directly
            directory = os.path.dirname(file_path)
            new_path = os.path.join(directory, custom_name)
            os.rename(file_path, new_path)
            return {
                "success": True,
                "old_name": os.path.basename(file_path),
                "new_name": custom_name,
                "new_path": new_path
            }
        
        # Use smart renaming
        result = await renamer.analyze(file_path, file_info)
        
        if not result.action_required:
            return {
                "success": True,
                "renamed": False,
                "message": "File name is already clean"
            }
        
        # Execute the rename
        success = await renamer.execute(file_path, result)
        
        return {
            "success": success,
            "renamed": success,
            "old_name": result.metadata.get("old_name"),
            "new_name": result.metadata.get("new_name"),
            "issues_fixed": result.metadata.get("issues", [])
        }
        
    except Exception as e:
        logger.error(f"[Janitor V3] Rename file failed: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Sentinel Agent Endpoints
# =============================================================================

@router.get("/sentinel/health-report")
async def get_sentinel_health_report():
    """
    Get comprehensive system health report from Sentinel Agent.
    
    Returns CPU, RAM, temperature, disk, network metrics and alerts.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        report = await sentinel.get_health_report()
        return report
    except Exception as e:
        logger.error(f"Sentinel health report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentinel/optimize-focus")
async def optimize_for_focus(request: dict):
    """
    Optimize system for a specific target application.
    
    Request:
        {"target_app": "chrome.exe" or "Visual Studio" or "game"}
    
    Sets target app to HIGH priority, throttles background processes.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        target_app = request.get("target_app", "")
        if not target_app:
            return {"success": False, "error": "target_app required"}
        
        result = await sentinel.optimize_for_focus(target_app)
        return result
    except Exception as e:
        logger.error(f"Sentinel focus optimization error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/sentinel/kill-hogs")
async def kill_resource_hogs(request: dict):
    """
    Kill resource hog processes.
    
    Request:
        {
            "cpu_threshold": 90.0,  # optional, default 90%
            "memory_threshold": 95.0  # optional, default 95%
        }
    
    Terminates processes exceeding resource thresholds.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        cpu_threshold = request.get("cpu_threshold", 90.0)
        memory_threshold = request.get("memory_threshold", 95.0)
        
        result = await sentinel.kill_resource_hogs(cpu_threshold, memory_threshold)
        return result
    except Exception as e:
        logger.error(f"Sentinel resource hog killing error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/sentinel/cleanup-ghosts")
async def cleanup_ghost_processes(request: dict):
    """
    Clean up ghost (zombie/idle) processes.
    
    Request:
        {"idle_hours": 2.0}  # optional, default 2 hours
    
    Terminates processes that have been idle for specified hours.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        idle_hours = request.get("idle_hours", 2.0)
        
        result = await sentinel.cleanup_ghost_processes(idle_hours)
        return result
    except Exception as e:
        logger.error(f"Sentinel ghost cleanup error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/sentinel/power-profile")
async def set_power_profile(request: dict):
    """
    Set Windows power profile.
    
    Request:
        {"profile": "high_performance"}  # options: high_performance, balanced, power_saver
    
    Changes Windows power scheme for thermal/performance management.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        profile = request.get("profile", "")
        if profile not in ["high_performance", "balanced", "power_saver"]:
            return {"success": False, "error": "Invalid profile. Use: high_performance, balanced, power_saver"}
        
        result = await sentinel.set_power_profile(profile)
        return result
    except Exception as e:
        logger.error(f"Sentinel power profile error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/sentinel/metrics")
async def get_sentinel_metrics():
    """
    Get Sentinel Agent performance metrics.
    
    Returns optimization history, success rates, and performance stats.
    """
    _ensure_sentinel_registered()
    
    registry = get_registry()
    sentinel = registry.get("SENTINEL_AGENT")
    
    if sentinel is None:
        raise HTTPException(status_code=500, detail="Sentinel agent not available")
    
    try:
        metrics = sentinel.get_metrics()
        status = sentinel.get_status()
        
        return {
            "metrics": metrics,
            "status": status,
        }
    except Exception as e:
        logger.error(f"Sentinel metrics error: {e}")
        return {"error": str(e)}


# =============================================================================
# Helper Functions
# =============================================================================

def _ensure_janitor_registered():
    """Ensure the Janitor agent is registered."""
    registry = get_registry()
    
    if registry.get("JANITOR_AGENT") is None:
        from app.agents.janitor.janitor_agent import JanitorAgent
        janitor = JanitorAgent()
        registry.register(janitor)
        logger.info("Registered JANITOR_AGENT")


def _ensure_recovery_registered():
    """Ensure the Recovery agent is registered."""
    registry = get_registry()
    
    if registry.get("RECOVERY_AGENT") is None:
        from app.agents.recovery.recovery_agent import RecoveryAgent
        recovery = RecoveryAgent()
        registry.register(recovery)
        logger.info("Registered RECOVERY_AGENT")


def _ensure_sentinel_registered():
    """Ensure the Sentinel agent is registered."""
    registry = get_registry()
    
    if registry.get("SENTINEL_AGENT") is None:
        from app.agents.sentinel.sentinel_agent import SentinelAgent
        sentinel = SentinelAgent()
        registry.register(sentinel)
        logger.info("Registered SENTINEL_AGENT")
