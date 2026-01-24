"""
Autonomous Daemon - Runs Janitor in background with real-time file monitoring.

This is the "beast mode" - Janitor runs continuously:
1. Watches Downloads/Desktop for new files
2. Runs all capabilities on new files
3. Auto-executes safe actions
4. Prompts for permission on risky actions
5. Logs all activity
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable

from app.agents.janitor.file_watcher import FileWatcher, FileEvent, get_file_watcher
from app.agents.janitor.capabilities import (
    run_capabilities,
    register_capability,
    get_all_capabilities,
    CapabilityResult,
)

# Import all capabilities
from app.agents.janitor.capabilities.virus_scanner import VirusScannerCapability
from app.agents.janitor.capabilities.file_namer import FileNamerCapability
from app.agents.janitor.capabilities.auto_organizer import AutoOrganizerCapability
from app.agents.janitor.capabilities.installer_handler import InstallerHandlerCapability
from app.agents.janitor.capabilities.duplicate_hunter import DuplicateHunterCapability
from app.agents.janitor.capabilities.browser_cleaner import BrowserCleanerCapability
from app.agents.janitor.capabilities.disk_reclaimer import DiskReclaimerCapability
from app.agents.janitor.capabilities.privacy_sweep import PrivacySweepCapability
from app.agents.janitor.capabilities.smart_uninstaller import SmartUninstallerCapability
from app.agents.janitor.capabilities.llm_content_analyzer import LLMContentAnalyzerCapability

logger = logging.getLogger(__name__)


class JanitorDaemon:
    """
    Autonomous Janitor that runs in background.
    
    Features:
    - Real-time file monitoring
    - Automatic safe actions (organize media, rename generic files)
    - Permission prompts for risky actions (delete, install)
    - Activity logging
    
    Usage:
        daemon = JanitorDaemon()
        daemon.on_permission_needed = my_permission_handler
        await daemon.start()
    """
    
    def __init__(self):
        self._running = False
        self._watcher = get_file_watcher()
        self._pending_actions: list[dict] = []
        self._completed_actions: list[dict] = []
        
        # Callbacks
        self._on_permission_needed: Optional[Callable] = None
        self._on_action_completed: Optional[Callable] = None
        self._on_file_processed: Optional[Callable] = None
        
        # Register capabilities
        self._setup_capabilities()
    
    def _setup_capabilities(self) -> None:
        """Register all capabilities."""
        # Core capabilities
        register_capability(VirusScannerCapability())
        register_capability(FileNamerCapability())
        register_capability(AutoOrganizerCapability())
        register_capability(InstallerHandlerCapability())
        
        # Killer capabilities
        register_capability(DuplicateHunterCapability())
        register_capability(BrowserCleanerCapability())
        register_capability(DiskReclaimerCapability())
        register_capability(PrivacySweepCapability())
        register_capability(SmartUninstallerCapability())
        register_capability(LLMContentAnalyzerCapability())
        
        logger.info(f"[JanitorDaemon] Registered {len(get_all_capabilities())} capabilities")
    
    @property
    def on_permission_needed(self) -> Optional[Callable]:
        """Callback when permission is needed for an action."""
        return self._on_permission_needed
    
    @on_permission_needed.setter
    def on_permission_needed(self, callback: Callable):
        self._on_permission_needed = callback
    
    @property
    def on_action_completed(self) -> Optional[Callable]:
        """Callback when an action is completed."""
        return self._on_action_completed
    
    @on_action_completed.setter
    def on_action_completed(self, callback: Callable):
        self._on_action_completed = callback
    
    @property
    def on_file_processed(self) -> Optional[Callable]:
        """Callback when a file is processed."""
        return self._on_file_processed
    
    @on_file_processed.setter
    def on_file_processed(self, callback: Callable):
        self._on_file_processed = callback
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def pending_actions(self) -> list[dict]:
        return self._pending_actions.copy()
    
    @property
    def stats(self) -> dict:
        return {
            "running": self._running,
            "capabilities": len(get_all_capabilities()),
            "pending_actions": len(self._pending_actions),
            "completed_actions": len(self._completed_actions),
        }
    
    async def start(self) -> None:
        """Start the daemon."""
        if self._running:
            logger.warning("[JanitorDaemon] Already running")
            return
        
        self._running = True
        
        # Set up file event handler
        self._watcher.on_new_file = self._handle_new_file
        
        # Start the file watcher
        await self._watcher.start()
        
        logger.info("[JanitorDaemon] 🧹 Started in autonomous mode")
    
    async def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        await self._watcher.stop()
        logger.info("[JanitorDaemon] Stopped")
    
    async def _handle_new_file(self, event: FileEvent) -> None:
        """Handle a new file detected by the watcher."""
        logger.info(f"[JanitorDaemon] New file: {event.filename}")
        
        file_info = {
            "filename": event.filename,
            "extension": event.extension,
            "size_bytes": event.size_bytes,
            "path": event.path,
        }
        
        # Run all capabilities
        results = await run_capabilities(event.path, file_info)
        
        if not results:
            logger.debug(f"[JanitorDaemon] No actions needed for {event.filename}")
            return
        
        # Process results
        for result in results:
            await self._process_result(event.path, file_info, result)
        
        # Notify file processed
        if self._on_file_processed:
            await self._on_file_processed(event, results)
    
    async def _process_result(
        self,
        file_path: str,
        file_info: dict,
        result: CapabilityResult
    ) -> None:
        """Process a capability result."""
        
        # If auto-approve, execute immediately
        if not result.requires_permission or result.metadata.get("auto_approve"):
            await self._execute_action(file_path, result)
            return
        
        # Add to pending and request permission
        action = {
            "id": f"{result.capability}_{datetime.now().timestamp()}",
            "file_path": file_path,
            "file_info": file_info,
            "result": result,
            "timestamp": datetime.now(),
            "status": "pending",
        }
        
        self._pending_actions.append(action)
        
        # Request permission
        if self._on_permission_needed:
            await self._on_permission_needed(action)
        else:
            logger.warning(f"[JanitorDaemon] No permission handler for: {result.suggestion}")
    
    async def _execute_action(self, file_path: str, result: CapabilityResult) -> bool:
        """Execute an action."""
        from app.agents.janitor.capabilities import get_capability
        
        capability = get_capability(result.capability)
        if not capability:
            logger.error(f"[JanitorDaemon] Capability not found: {result.capability}")
            return False
        
        try:
            success = await capability.execute(file_path, result)
            
            # Log completion
            self._completed_actions.append({
                "capability": result.capability,
                "action": result.action_type,
                "file_path": file_path,
                "success": success,
                "timestamp": datetime.now(),
            })
            
            if success:
                logger.info(f"[JanitorDaemon] ✅ {result.capability}: {result.suggestion}")
            else:
                logger.warning(f"[JanitorDaemon] ⚠️ {result.capability} failed")
            
            # Notify completion
            if self._on_action_completed:
                await self._on_action_completed(result, success)
            
            return success
            
        except Exception as e:
            logger.error(f"[JanitorDaemon] Action failed: {e}")
            return False
    
    async def approve_action(self, action_id: str) -> bool:
        """Approve a pending action."""
        for action in self._pending_actions:
            if action["id"] == action_id:
                self._pending_actions.remove(action)
                return await self._execute_action(
                    action["file_path"],
                    action["result"]
                )
        return False
    
    async def reject_action(self, action_id: str) -> bool:
        """Reject a pending action."""
        for action in self._pending_actions:
            if action["id"] == action_id:
                self._pending_actions.remove(action)
                action["status"] = "rejected"
                self._completed_actions.append(action)
                return True
        return False


# Singleton instance
_daemon: Optional[JanitorDaemon] = None


def get_janitor_daemon() -> JanitorDaemon:
    """Get the global Janitor daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = JanitorDaemon()
    return _daemon
