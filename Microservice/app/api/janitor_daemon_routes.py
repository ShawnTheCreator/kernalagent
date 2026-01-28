"""
Janitor Daemon API Routes - Integration with Conversational Brain
Provides HTTP endpoints for daemon control and WebSocket integration.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging
from datetime import datetime

# Daemon imports
from app.agents.janitor.daemon_service import (
    start_daemon, 
    stop_daemon, 
    get_daemon_status,
    JanitorDaemon,
    DaemonStatus
)

# Conversational brain integration
from app.brain.conversational_brain import ConversationalBrain, BrainOutput, BrainOutputType

# Memory integration
from app.db.memory_bridge import log_event

logger = logging.getLogger(__name__)

# Create router
janitor_daemon_router = APIRouter(prefix="/api/daemon", tags=["janitor-daemon"])

# Global daemon reference
daemon_instance: Optional[JanitorDaemon] = None


# Pydantic Models
class DaemonCommand(BaseModel):
    """Command for daemon operations."""
    command: str
    parameters: Dict[str, Any] = {}
    user_id: Optional[str] = None


class DaemonStatusResponse(BaseModel):
    """Daemon status response."""
    status: str
    stats: Dict[str, Any]
    active_operations: int
    pending_operations: int
    completed_operations: int
    connected_clients: int
    uptime: float


class FileOperationRequest(BaseModel):
    """Request for file operation."""
    operation_type: str  # move, delete, rename, scan
    source_path: str
    destination_path: Optional[str] = None
    parameters: Dict[str, Any] = {}


class PermissionResponse(BaseModel):
    """Response to permission request."""
    operation_id: str
    allowed: bool
    always: bool = False


# Natural Language Command Processing
class JanitorCommandProcessor:
    """Process natural language commands for Janitor operations."""
    
    def __init__(self):
        self.brain = ConversationalBrain()
        
        # Command patterns
        self.command_patterns = {
            "clean_organize": [
                "clean", "organize", "tidy", "sort", "arrange", "clean up", "organize my"
            ],
            "scan_monitor": [
                "scan", "monitor", "watch", "check", "look at", "scan my"
            ],
            "move_files": [
                "move", "relocate", "put away", "move my", "put my"
            ],
            "rename_files": [
                "rename", "fix names", "better names", "rename my"
            ],
            "delete_cleanup": [
                "delete", "remove", "cleanup", "clean up", "delete my"
            ],
            "status_check": [
                "status", "how are you", "what's happening", "show status"
            ]
        }
    
    async def process_command(self, command: str, user_id: str = None) -> Dict[str, Any]:
        """Process natural language command and return structured action."""
        try:
            # Use conversational brain to understand intent
            brain_output = await self.brain.process_message(
                message=command,
                session_id=user_id or "default",
                context={"module": "janitor_daemon"}
            )
            
            # Extract intent and parameters
            if brain_output.type == BrainOutputType.ACT:
                return await self._process_act_command(brain_output, user_id)
            else:
                # Handle chat/ask responses
                return {
                    "type": "chat_response",
                    "message": brain_output.message,
                    "confidence": brain_output.confidence,
                    "reasoning": brain_output.reasoning
                }
                
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                "type": "error",
                "message": f"Failed to process command: {str(e)}",
                "confidence": 0.0
            }
    
    async def _process_act_command(self, brain_output: BrainOutput, user_id: str) -> Dict[str, Any]:
        """Process ACT type brain output."""
        intent = brain_output.intent or ""
        target = brain_output.target or ""
        confidence = brain_output.confidence
        
        # Map intent to daemon commands
        command_mapping = {
            "clean_organize": "scan_and_organize",
            "scan_monitor": "scan_directories",
            "move_files": "move_files",
            "rename_files": "rename_files",
            "delete_cleanup": "delete_files",
            "status_check": "get_status"
        }
        
        # Determine command type
        command_type = None
        for pattern_name, patterns in self.command_patterns.items():
            if any(pattern in intent.lower() for pattern in patterns):
                command_type = pattern_name
                break
        
        if not command_type:
            command_type = "scan_and_organize"  # Default
        
        daemon_command = command_mapping.get(command_type, "scan_and_organize")
        
        # Extract parameters
        parameters = {
            "target": target,
            "confidence": confidence,
            "reasoning": brain_output.reasoning,
            "user_intent": intent
        }
        
        # Add specific parameters based on command type
        if command_type == "clean_organize":
            parameters["auto_approve"] = False  # Ask for permission first
        elif command_type == "scan_monitor":
            parameters["deep_scan"] = True
        elif command_type in ["move_files", "rename_files", "delete_cleanup"]:
            parameters["requires_permission"] = True
        
        return {
            "type": "daemon_command",
            "command": daemon_command,
            "parameters": parameters,
            "confidence": confidence,
            "reasoning": brain_output.reasoning
        }


# Global command processor
command_processor = JanitorCommandProcessor()


# API Endpoints
@janitor_daemon_router.post("/start")
async def start_daemon_endpoint(background_tasks: BackgroundTasks):
    """Start the Janitor daemon."""
    global daemon_instance
    
    try:
        if daemon_instance and daemon_instance.status != DaemonStatus.STOPPED:
            return {"message": "Daemon is already running", "status": daemon_instance.status.value}
        
        # Start daemon in background
        async def start_background():
            global daemon_instance
            daemon_instance = await start_daemon()
            
            # Log to memory
            await log_event(
                user_id="system",
                event_type="daemon_started",
                content="Janitor daemon started via API",
                metadata={"timestamp": datetime.now().isoformat()}
            )
        
        background_tasks.add_task(start_background)
        
        return {"message": "Starting daemon...", "status": "starting"}
        
    except Exception as e:
        logger.error(f"Failed to start daemon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.post("/stop")
async def stop_daemon_endpoint(background_tasks: BackgroundTasks):
    """Stop the Janitor daemon."""
    global daemon_instance
    
    try:
        if not daemon_instance or daemon_instance.status == DaemonStatus.STOPPED:
            return {"message": "Daemon is not running", "status": "stopped"}
        
        # Stop daemon in background
        async def stop_background():
            global daemon_instance
            await stop_daemon()
            daemon_instance = None
            
            # Log to memory
            await log_event(
                user_id="system",
                event_type="daemon_stopped",
                content="Janitor daemon stopped via API",
                metadata={"timestamp": datetime.now().isoformat()}
            )
        
        background_tasks.add_task(stop_background)
        
        return {"message": "Stopping daemon...", "status": "stopping"}
        
    except Exception as e:
        logger.error(f"Failed to stop daemon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.get("/status", response_model=DaemonStatusResponse)
async def get_daemon_status_endpoint():
    """Get current daemon status."""
    try:
        status = await get_daemon_status()
        return DaemonStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get daemon status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.post("/command")
async def process_daemon_command(
    command: DaemonCommand, 
    background_tasks: BackgroundTasks
):
    """Process natural language command for daemon."""
    try:
        # Process command with conversational brain
        result = await command_processor.process_command(
            command.command, 
            command.user_id
        )
        
        # Log command to memory
        await log_event(
            user_id=command.user_id or "anonymous",
            event_type="daemon_command",
            content=f"Command: {command.command}",
            metadata={
                "result_type": result["type"],
                "confidence": result.get("confidence", 0.0),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        if result["type"] == "daemon_command":
            # Execute daemon command
            return await execute_daemon_command(
                result["command"], 
                result["parameters"], 
                background_tasks
            )
        else:
            # Return chat response
            return result
            
    except Exception as e:
        logger.error(f"Failed to process command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def execute_daemon_command(
    command: str, 
    parameters: Dict[str, Any], 
    background_tasks: BackgroundTasks
):
    """Execute specific daemon command."""
    global daemon_instance
    
    if not daemon_instance or daemon_instance.status != DaemonStatus.RUNNING:
        return {
            "message": "Daemon is not running",
            "status": "error",
            "suggestion": "Start the daemon first"
        }
    
    try:
        if command == "scan_and_organize":
            # Start scan and organize
            async def scan_task():
                await daemon_instance.scan_directories()
            
            background_tasks.add_task(scan_task)
            
            return {
                "message": "Starting scan and organization...",
                "command": command,
                "parameters": parameters,
                "status": "executing"
            }
        
        elif command == "scan_directories":
            # Start directory scan
            async def scan_task():
                await daemon_instance.scan_directories()
            
            background_tasks.add_task(scan_task)
            
            return {
                "message": "Starting directory scan...",
                "command": command,
                "parameters": parameters,
                "status": "executing"
            }
        
        elif command == "get_status":
            # Get current status
            status = await daemon_instance.get_status()
            return {
                "message": "Current daemon status",
                "status": "success",
                "data": status
            }
        
        else:
            return {
                "message": f"Unknown command: {command}",
                "status": "error",
                "available_commands": [
                    "scan_and_organize",
                    "scan_directories", 
                    "get_status"
                ]
            }
            
    except Exception as e:
        logger.error(f"Failed to execute command {command}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.post("/permission")
async def handle_permission_response(permission: PermissionResponse):
    """Handle user permission response."""
    try:
        # This would be forwarded to the daemon's permission manager
        # For now, just log it
        await log_event(
            user_id="daemon",
            event_type="permission_response",
            content=f"Permission for {permission.operation_id}: {permission.allowed}",
            metadata={
                "operation_id": permission.operation_id,
                "allowed": permission.allowed,
                "always": permission.always,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "message": "Permission response recorded",
            "operation_id": permission.operation_id,
            "allowed": permission.allowed
        }
        
    except Exception as e:
        logger.error(f"Failed to handle permission response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.post("/operation")
async def create_file_operation(
    operation: FileOperationRequest,
    background_tasks: BackgroundTasks
):
    """Create and queue a file operation."""
    global daemon_instance
    
    if not daemon_instance or daemon_instance.status != DaemonStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Daemon is not running")
    
    try:
        from app.agents.janitor.daemon_service import FileOperation, OperationType
        
        # Create operation
        op_type = OperationType(operation.operation_type.upper())
        file_op = FileOperation(
            operation_id=f"manual_{int(datetime.now().timestamp())}",
            operation_type=op_type,
            source_path=operation.source_path,
            destination_path=operation.destination_path
        )
        
        # Add to queue
        await daemon_instance.operation_queue.add_operation(file_op)
        
        # Log operation
        await log_event(
            user_id="manual",
            event_type="manual_operation",
            content=f"Manual {operation.operation_type} operation: {operation.source_path}",
            metadata={
                "operation_id": file_op.operation_id,
                "operation_type": operation.operation_type,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "message": f"Operation queued: {operation.operation_type}",
            "operation_id": file_op.operation_id,
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to create operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.post("/rollback/{operation_id}")
async def rollback_operation(operation_id: str):
    """Rollback a specific operation."""
    global daemon_instance
    
    if not daemon_instance or daemon_instance.status != DaemonStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Daemon is not running")
    
    try:
        success = await daemon_instance.operation_queue.rollback_operation(operation_id)
        
        if success:
            await log_event(
                user_id="manual",
                event_type="operation_rollback",
                content=f"Rolled back operation: {operation_id}",
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
            return {
                "message": f"Operation {operation_id} rolled back successfully",
                "status": "success"
            }
        else:
            return {
                "message": f"Failed to rollback operation {operation_id}",
                "status": "error"
            }
            
    except Exception as e:
        logger.error(f"Failed to rollback operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.get("/operations")
async def get_operations():
    """Get list of operations."""
    global daemon_instance
    
    if not daemon_instance or daemon_instance.status != DaemonStatus.RUNNING:
        return {"operations": [], "status": "daemon_not_running"}
    
    try:
        operations = {
            "active": [
                {
                    "operation_id": op.operation_id,
                    "type": op.operation_type.value,
                    "source": op.source_path,
                    "destination": op.destination_path,
                    "status": op.status
                }
                for op in daemon_instance.operation_queue.active_operations.values()
            ],
            "completed": [
                {
                    "operation_id": op.operation_id,
                    "type": op.operation_type.value,
                    "source": op.source_path,
                    "destination": op.destination_path,
                    "status": op.status
                }
                for op in daemon_instance.operation_queue.completed_operations[-10:]  # Last 10
            ]
        }
        
        return operations
        
    except Exception as e:
        logger.error(f"Failed to get operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@janitor_daemon_router.get("/logs")
async def get_daemon_logs(limit: int = 50):
    """Get daemon logs."""
    try:
        # Read from daemon log file
        log_file = "janitor_daemon.log"
        logs = []
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-limit:]:
                    logs.append(line.strip())
        except FileNotFoundError:
            logs = ["Log file not found"]
        
        return {
            "logs": logs,
            "limit": limit,
            "total_lines": len(logs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint info
@janitor_daemon_router.get("/websocket/info")
async def get_websocket_info():
    """Get WebSocket connection information."""
    global daemon_instance
    
    if not daemon_instance:
        return {
            "message": "Daemon not running",
            "websocket_available": False
        }
    
    return {
        "websocket_available": True,
        "host": daemon_instance.websocket_manager.host,
        "port": daemon_instance.websocket_manager.port,
        "connected_clients": len(daemon_instance.websocket_manager.clients),
        "connection_url": f"ws://{daemon_instance.websocket_manager.host}:{daemon_instance.websocket_manager.port}"
    }


# Health check
@janitor_daemon_router.get("/health")
async def health_check():
    """Health check endpoint."""
    global daemon_instance
    
    daemon_healthy = daemon_instance and daemon_instance.status == DaemonStatus.RUNNING
    
    return {
        "status": "healthy" if daemon_healthy else "unhealthy",
        "daemon_running": daemon_healthy,
        "timestamp": datetime.now().isoformat()
    }
