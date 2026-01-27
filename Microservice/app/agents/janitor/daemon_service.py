"""
Janitor Daemon - Background File Monitoring and Organization Service
Production-ready daemon with hybrid file watching, WebSocket communication, and comprehensive testing.
"""

import os
import sys
import asyncio
import logging
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import hashlib
from concurrent.futures import ThreadPoolExecutor
import psutil

# Hybrid file watching approach
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("Watchdog not available, falling back to polling")

# WebSocket communication
import websockets
from websockets.server import WebSocketServerProtocol

# Cloud storage (Firebase - already in use)
from app.db.firebase_client import get_firestore_client

# Enhanced Janitor capabilities
from app.agents.janitor.janitor_agent import JanitorAgent
from app.agents.janitor.parallel_processor import ParallelProcessor
from app.agents.janitor.smart_cache import SmartCache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('janitor_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JanitorDaemon")


class DaemonStatus(Enum):
    """Daemon operational status."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class NotificationType(Enum):
    """Types of notifications sent to clients."""
    SCAN_PROGRESS = "scan_progress"
    FILE_FOUND = "file_found"
    OPERATION_STARTED = "operation_started"
    OPERATION_PROGRESS = "operation_progress"
    OPERATION_COMPLETE = "operation_complete"
    CONFLICT_DETECTED = "conflict_detected"
    ERROR_OCCURRED = "error_occurred"
    STATUS_UPDATE = "status_update"


class OperationType(Enum):
    """Types of file operations."""
    SCAN = "scan"
    MOVE = "move"
    COPY = "copy"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileOperation:
    """Represents a file operation with rollback capability."""
    operation_id: str
    operation_type: OperationType
    source_path: str
    destination_path: Optional[str] = None
    backup_path: Optional[str] = None
    file_size: int = 0
    created_at: datetime = None
    status: str = "pending"  # pending, running, completed, failed, rolled_back
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DaemonNotification:
    """Notification message sent via WebSocket."""
    type: NotificationType
    message: str
    data: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        result = asdict(self)
        result['type'] = self.type.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


class HybridFileWatcher:
    """
    Hybrid file watching system combining watchdog and polling.
    Uses watchdog for real-time events and polling for reliability.
    """
    
    def __init__(self, watch_paths: List[str], callback: Callable):
        self.watch_paths = [Path(p) for p in watch_paths]
        self.callback = callback
        self.observer = None
        self.polling_active = False
        self.polling_interval = 2.0  # seconds
        self.last_scan_times = {}
        self.file_hashes = {}  # Track file changes
        
        logger.info(f"HybridFileWatcher initialized for paths: {watch_paths}")
    
    async def start(self):
        """Start both watchdog and polling watchers."""
        # Start watchdog if available
        if WATCHDOG_AVAILABLE:
            await self._start_watchdog()
        else:
            logger.info("Using polling-only file watching")
        
        # Start polling as backup
        await self._start_polling()
        
        logger.info("Hybrid file watching started")
    
    async def _start_watchdog(self):
        """Start watchdog observer."""
        try:
            self.observer = Observer()
            
            class JanitorEventHandler(FileSystemEventHandler):
                def __init__(self, callback):
                    self.callback = callback
                
                def on_any_event(self, event):
                    if not event.is_directory:
                        self.callback({
                            'type': 'watchdog_event',
                            'event_type': event.event_type,
                            'path': event.src_path,
                            'timestamp': datetime.now()
                        })
            
            handler = JanitorEventHandler(self.callback)
            
            for path in self.watch_paths:
                if path.exists():
                    self.observer.schedule(handler, str(path), recursive=True)
                    logger.info(f"Watchdog watching: {path}")
            
            self.observer.start()
            logger.info("Watchdog observer started")
            
        except Exception as e:
            logger.error(f"Failed to start watchdog: {e}")
            self.observer = None
    
    async def _start_polling(self):
        """Start polling watcher as backup."""
        self.polling_active = True
        
        async def poll_loop():
            while self.polling_active:
                try:
                    await self._poll_changes()
                    await asyncio.sleep(self.polling_interval)
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    await asyncio.sleep(self.polling_interval)
        
        asyncio.create_task(poll_loop())
        logger.info("Polling watcher started")
    
    async def _poll_changes(self):
        """Poll for file changes."""
        current_time = datetime.now()
        
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
            
            try:
                # Scan for new/modified files
                for file_path in watch_path.rglob('*'):
                    if file_path.is_file():
                        file_stat = file_path.stat()
                        modified_time = datetime.fromtimestamp(file_stat.st_mtime)
                        
                        # Check if file is new or modified
                        last_scan = self.last_scan_times.get(str(file_path), datetime.min)
                        if modified_time > last_scan:
                            # Calculate file hash to detect content changes
                            file_hash = self._calculate_file_hash(file_path)
                            old_hash = self.file_hashes.get(str(file_path))
                            
                            if file_hash != old_hash:
                                self.file_hashes[str(file_path)] = file_hash
                                self.callback({
                                    'type': 'polling_event',
                                    'event_type': 'modified' if old_hash else 'created',
                                    'path': str(file_path),
                                    'timestamp': current_time,
                                    'file_size': file_stat.st_size
                                })
                        
                        self.last_scan_times[str(file_path)] = current_time
                        
            except Exception as e:
                logger.error(f"Error polling {watch_path}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                # Read first 1KB for quick hash
                chunk = f.read(1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    async def stop(self):
        """Stop all watchers."""
        self.polling_active = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("Watchdog observer stopped")
        
        logger.info("Hybrid file watching stopped")


class PermissionManager:
    """
    Manages user permissions and preferences with hybrid local/cloud storage.
    """
    
    def __init__(self):
        self.local_preferences = {}
        self.cloud_client = None
        self.preference_file = Path.home() / ".janitor_preferences.json"
        self._load_local_preferences()
        self._init_cloud_storage()
    
    def _load_local_preferences(self):
        """Load preferences from local file."""
        try:
            if self.preference_file.exists():
                with open(self.preference_file, 'r') as f:
                    self.local_preferences = json.load(f)
                logger.info(f"Loaded {len(self.local_preferences)} local preferences")
        except Exception as e:
            logger.error(f"Failed to load local preferences: {e}")
            self.local_preferences = {}
    
    def _init_cloud_storage(self):
        """Initialize cloud storage connection."""
        try:
            self.cloud_client = get_firestore_client()
            logger.info("Cloud storage initialized")
        except Exception as e:
            logger.warning(f"Cloud storage not available: {e}")
            self.cloud_client = None
    
    async def get_permission(self, operation_type: str, file_path: str, context: Dict = None) -> bool:
        """
        Get permission for an operation.
        Returns True if allowed, False if denied, None if needs user input.
        """
        # Check local preferences first
        preference_key = f"{operation_type}_{Path(file_path).suffix.lower()}"
        
        if preference_key in self.local_preferences:
            return self.local_preferences[preference_key]
        
        # Check cloud preferences
        if self.cloud_client:
            try:
                doc_ref = self.cloud_client.collection('user_preferences').document('janitor_permissions')
                doc = doc_ref.get()
                if doc.exists:
                    cloud_prefs = doc.to_dict()
                    if preference_key in cloud_prefs:
                        return cloud_prefs[preference_key]
            except Exception as e:
                logger.error(f"Failed to check cloud permissions: {e}")
        
        # No preference found, needs user decision
        return None
    
    async def set_permission(self, operation_type: str, file_pattern: str, allowed: bool, always: bool = False):
        """Set permission for future operations."""
        preference_key = f"{operation_type}_{file_pattern}"
        
        # Save locally
        self.local_preferences[preference_key] = allowed
        try:
            with open(self.preference_file, 'w') as f:
                json.dump(self.local_preferences, f, indent=2)
            logger.info(f"Saved local permission: {preference_key} = {allowed}")
        except Exception as e:
            logger.error(f"Failed to save local permission: {e}")
        
        # Save to cloud if available and always=True
        if always and self.cloud_client:
            try:
                doc_ref = self.cloud_client.collection('user_preferences').document('janitor_permissions')
                doc_ref.set({preference_key: allowed}, merge=True)
                logger.info(f"Saved cloud permission: {preference_key} = {allowed}")
            except Exception as e:
                logger.error(f"Failed to save cloud permission: {e}")


class WebSocketManager:
    """
    Manages WebSocket connections for real-time communication.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.notification_queue = asyncio.Queue()
        self.running = False
        
        logger.info(f"WebSocketManager initialized for {host}:{port}")
    
    async def start(self):
        """Start WebSocket server."""
        self.running = True
        
        async def handle_client(websocket: WebSocketServerProtocol, path: str):
            self.clients.add(websocket)
            logger.info(f"Client connected: {websocket.remote_address}")
            
            try:
                # Send welcome message
                await self.send_notification(DaemonNotification(
                    type=NotificationType.STATUS_UPDATE,
                    message="Janitor Daemon connected",
                    data={"status": "connected"}
                ))
                
                # Keep connection alive
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_client_message(websocket, data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON from client: {message}")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected: {websocket.remote_address}")
            finally:
                self.clients.discard(websocket)
        
        # Start notification broadcaster
        asyncio.create_task(self._notification_broadcaster())
        
        # Start server
        self.server = await websockets.serve(handle_client, self.host, self.port)
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
    
    async def _notification_broadcaster(self):
        """Broadcast notifications to all connected clients."""
        while self.running:
            try:
                notification = await self.notification_queue.get()
                message = json.dumps(notification.to_dict())
                
                # Send to all clients
                disconnected = set()
                for client in self.clients:
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        disconnected.add(client)
                
                # Remove disconnected clients
                self.clients -= disconnected
                
            except Exception as e:
                logger.error(f"Error broadcasting notification: {e}")
    
    async def _handle_client_message(self, websocket: WebSocketServerProtocol, data: Dict):
        """Handle incoming messages from clients."""
        message_type = data.get('type')
        
        if message_type == 'ping':
            await websocket.send(json.dumps({'type': 'pong'}))
        elif message_type == 'permission_response':
            # Handle permission responses from user
            operation_id = data.get('operation_id')
            allowed = data.get('allowed')
            always = data.get('always', False)
            
            # This would be handled by the main daemon
            logger.info(f"Permission response for {operation_id}: {allowed} (always: {always})")
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def send_notification(self, notification: DaemonNotification):
        """Queue notification for broadcasting."""
        await self.notification_queue.put(notification)
    
    async def stop(self):
        """Stop WebSocket server."""
        self.running = False
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")


class OperationQueue:
    """
    Manages file operations with parallel processing and rollback capability.
    """
    
    def __init__(self, max_workers: int = 4, temp_dir: str = None):
        self.max_workers = max_workers
        self.temp_dir = Path(temp_dir or Path.home() / ".janitor_temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.pending_operations: queue.Queue = queue.Queue()
        self.active_operations: Dict[str, FileOperation] = {}
        self.completed_operations: List[FileOperation] = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        
        logger.info(f"OperationQueue initialized with {max_workers} workers")
    
    async def start(self):
        """Start operation processing."""
        self.running = True
        asyncio.create_task(self._process_operations())
        logger.info("OperationQueue started")
    
    async def _process_operations(self):
        """Process operations from queue."""
        while self.running:
            try:
                operation = self.pending_operations.get(timeout=1.0)
                
                # Add to active operations
                self.active_operations[operation.operation_id] = operation
                
                # Process in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self._execute_operation, operation)
                
                # Move to completed
                self.completed_operations.append(operation)
                del self.active_operations[operation.operation_id]
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing operation: {e}")
    
    def _execute_operation(self, operation: FileOperation) -> bool:
        """Execute a single file operation with rollback capability."""
        try:
            operation.status = "running"
            
            if operation.operation_type == OperationType.MOVE:
                return self._execute_move(operation)
            elif operation.operation_type == OperationType.DELETE:
                return self._execute_delete(operation)
            elif operation.operation_type == OperationType.RENAME:
                return self._execute_rename(operation)
            else:
                logger.error(f"Unknown operation type: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            operation.status = "failed"
            return False
    
    def _execute_move(self, operation: FileOperation) -> bool:
        """Execute move operation with backup."""
        try:
            source = Path(operation.source_path)
            dest = Path(operation.destination_path)
            
            # Create backup
            backup_path = self.temp_dir / f"backup_{operation.operation_id}_{source.name}"
            shutil.copy2(source, backup_path)
            operation.backup_path = str(backup_path)
            
            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(source), str(dest))
            
            operation.status = "completed"
            logger.info(f"Moved: {source} -> {dest}")
            return True
            
        except Exception as e:
            logger.error(f"Move operation failed: {e}")
            return False
    
    def _execute_delete(self, operation: FileOperation) -> bool:
        """Execute delete operation with backup."""
        try:
            source = Path(operation.source_path)
            
            # Move to temp (trash) instead of permanent delete
            backup_path = self.temp_dir / f"trash_{operation.operation_id}_{source.name}"
            shutil.move(str(source), str(backup_path))
            operation.backup_path = str(backup_path)
            
            operation.status = "completed"
            logger.info(f"Moved to trash: {source}")
            return True
            
        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return False
    
    def _execute_rename(self, operation: FileOperation) -> bool:
        """Execute rename operation with backup."""
        try:
            source = Path(operation.source_path)
            dest = Path(operation.destination_path)
            
            # Create backup
            backup_path = self.temp_dir / f"backup_{operation.operation_id}_{source.name}"
            shutil.copy2(source, backup_path)
            operation.backup_path = str(backup_path)
            
            # Rename
            source.rename(dest)
            
            operation.status = "completed"
            logger.info(f"Renamed: {source} -> {dest}")
            return True
            
        except Exception as e:
            logger.error(f"Rename operation failed: {e}")
            return False
    
    async def add_operation(self, operation: FileOperation):
        """Add operation to queue."""
        await self.pending_operations.put(operation)
        logger.info(f"Queued operation: {operation.operation_id}")
    
    async def rollback_operation(self, operation_id: str) -> bool:
        """Rollback a completed operation."""
        operation = None
        
        # Find operation in completed
        for op in self.completed_operations:
            if op.operation_id == operation_id:
                operation = op
                break
        
        if not operation:
            logger.error(f"Operation not found for rollback: {operation_id}")
            return False
        
        try:
            if operation.backup_path and Path(operation.backup_path).exists():
                backup_path = Path(operation.backup_path)
                
                if operation.operation_type == OperationType.MOVE:
                    # Move back from destination
                    dest_path = Path(operation.destination_path)
                    if dest_path.exists():
                        shutil.move(str(dest_path), str(operation.source_path))
                
                elif operation.operation_type == OperationType.DELETE:
                    # Restore from trash
                    shutil.move(str(backup_path), str(operation.source_path))
                
                elif operation.operation_type == OperationType.RENAME:
                    # Restore original name
                    dest_path = Path(operation.destination_path)
                    if dest_path.exists():
                        dest_path.rename(operation.source_path)
                
                # Clean up backup
                backup_path.unlink()
                
                operation.status = "rolled_back"
                logger.info(f"Rolled back operation: {operation_id}")
                return True
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
        
        return False
    
    async def stop(self):
        """Stop operation processing."""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("OperationQueue stopped")


class JanitorDaemon:
    """
    Main Janitor Daemon - orchestrates all components.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.status = DaemonStatus.STARTING
        
        # Initialize components
        self.watch_paths = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
            str(Path.home() / "Documents"),
        ]
        
        self.file_watcher = HybridFileWatcher(
            watch_paths=self.watch_paths,
            callback=self._handle_file_event
        )
        
        self.permission_manager = PermissionManager()
        self.websocket_manager = WebSocketManager(
            host=self.config.get('websocket_host', 'localhost'),
            port=self.config.get('websocket_port', 8765)
        )
        
        self.operation_queue = OperationQueue(
            max_workers=self.config.get('max_workers', 4),
            temp_dir=self.config.get('temp_dir', str(Path.home() / ".janitor_temp"))
        )
        
        self.janitor_agent = JanitorAgent()
        self.parallel_processor = ParallelProcessor()
        self.smart_cache = SmartCache()
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'operations_completed': 0,
            'conflicts_detected': 0,
            'start_time': datetime.now(),
            'last_activity': None
        }
        
        logger.info("JanitorDaemon initialized")
    
    async def start(self):
        """Start all daemon components."""
        try:
            logger.info("Starting JanitorDaemon...")
            
            # Start components
            await self.websocket_manager.start()
            await self.operation_queue.start()
            await self.file_watcher.start()
            
            self.status = DaemonStatus.RUNNING
            
            # Send startup notification
            await self.websocket_manager.send_notification(DaemonNotification(
                type=NotificationType.STATUS_UPDATE,
                message="Janitor Daemon started successfully",
                data={
                    'status': self.status.value,
                    'watch_paths': self.watch_paths,
                    'max_workers': self.operation_queue.max_workers
                }
            ))
            
            logger.info("JanitorDaemon started successfully")
            
        except Exception as e:
            self.status = DaemonStatus.ERROR
            logger.error(f"Failed to start JanitorDaemon: {e}")
            raise
    
    async def _handle_file_event(self, event: Dict):
        """Handle file system events."""
        try:
            event_type = event.get('event_type')
            file_path = event.get('path')
            timestamp = event.get('timestamp')
            
            if not file_path or not Path(file_path).exists():
                return
            
            # Update statistics
            self.stats['files_processed'] += 1
            self.stats['last_activity'] = timestamp
            
            # Send notification
            await self.websocket_manager.send_notification(DaemonNotification(
                type=NotificationType.FILE_FOUND,
                message=f"File {event_type}: {Path(file_path).name}",
                data={
                    'event_type': event_type,
                    'file_path': file_path,
                    'file_size': event.get('file_size', 0),
                    'timestamp': timestamp.isoformat() if timestamp else None
                }
            ))
            
            # Process file based on event type
            if event_type in ['created', 'modified']:
                await self._process_new_file(file_path, event)
            
        except Exception as e:
            logger.error(f"Error handling file event: {e}")
    
    async def _process_new_file(self, file_path: str, event: Dict):
        """Process a newly created or modified file."""
        try:
            file_path_obj = Path(file_path)
            
            # Get file info
            file_info = {
                'path': file_path,
                'name': file_path_obj.name,
                'extension': file_path_obj.suffix.lower(),
                'size_bytes': file_path_obj.stat().st_size
            }
            
            # Use Janitor Agent to analyze
            analysis_result = await self.janitor_agent.analyze({})
            
            # Check if action is needed
            if analysis_result.recommendations:
                # Create operation based on recommendations
                operation = FileOperation(
                    operation_id=f"op_{int(time.time())}_{hash(file_path) % 10000}",
                    operation_type=OperationType.MOVE,
                    source_path=file_path,
                    file_size=file_info['size_bytes']
                )
                
                # Check permissions
                permission = await self.permission_manager.get_permission(
                    'auto_organize', file_path, file_info
                )
                
                if permission is True:
                    # Auto-execute
                    await self.operation_queue.add_operation(operation)
                elif permission is None:
                    # Ask for permission
                    await self.websocket_manager.send_notification(DaemonNotification(
                        type=NotificationType.OPERATION_STARTED,
                        message=f"New file detected: {file_path_obj.name}. Organize?",
                        data={
                            'operation_id': operation.operation_id,
                            'file_info': file_info,
                            'recommendations': analysis_result.recommendations,
                            'requires_permission': True
                        }
                    ))
                # If permission is False, ignore
            
        except Exception as e:
            logger.error(f"Error processing new file {file_path}: {e}")
    
    async def scan_directories(self):
        """Perform comprehensive directory scan."""
        try:
            await self.websocket_manager.send_notification(DaemonNotification(
                type=NotificationType.SCAN_PROGRESS,
                message="Starting directory scan...",
                data={'phase': 'starting'}
            ))
            
            # Use parallel processor for scanning
            scanned_files = await self.parallel_processor.parallel_scan(self.watch_paths)
            
            # Process files by size (small to large)
            scanned_files.sort(key=lambda x: x.size_bytes)
            
            for i, file_info in enumerate(scanned_files):
                await self.websocket_manager.send_notification(DaemonNotification(
                    type=NotificationType.SCAN_PROGRESS,
                    message=f"Scanning... {i+1}/{len(scanned_files)} files",
                    data={
                        'phase': 'scanning',
                        'current': i+1,
                        'total': len(scanned_files),
                        'current_file': file_info.name
                    }
                ))
                
                # Process file
                await self._process_new_file(file_info.path, {'event_type': 'scan_found'})
            
            await self.websocket_manager.send_notification(DaemonNotification(
                type=NotificationType.SCAN_PROGRESS,
                message=f"Scan complete. Found {len(scanned_files)} files.",
                data={'phase': 'complete', 'total_files': len(scanned_files)}
            ))
            
        except Exception as e:
            logger.error(f"Error during directory scan: {e}")
            await self.websocket_manager.send_notification(DaemonNotification(
                type=NotificationType.ERROR_OCCURRED,
                message=f"Scan failed: {str(e)}",
                data={'error': str(e)}
            ))
    
    async def get_status(self) -> Dict:
        """Get current daemon status."""
        return {
            'status': self.status.value,
            'stats': self.stats.copy(),
            'active_operations': len(self.operation_queue.active_operations),
            'pending_operations': self.operation_queue.pending_operations.qsize(),
            'completed_operations': len(self.operation_queue.completed_operations),
            'connected_clients': len(self.websocket_manager.clients),
            'uptime': (datetime.now() - self.stats['start_time']).total_seconds()
        }
    
    async def stop(self):
        """Stop daemon gracefully."""
        try:
            self.status = DaemonStatus.STOPPING
            logger.info("Stopping JanitorDaemon...")
            
            # Stop components
            await self.file_watcher.stop()
            await self.operation_queue.stop()
            await self.websocket_manager.stop()
            
            self.status = DaemonStatus.STOPPED
            logger.info("JanitorDaemon stopped")
            
        except Exception as e:
            self.status = DaemonStatus.ERROR
            logger.error(f"Error stopping daemon: {e}")


# Global daemon instance
daemon_instance: Optional[JanitorDaemon] = None


async def start_daemon(config: Dict = None) -> JanitorDaemon:
    """Start the global daemon instance."""
    global daemon_instance
    
    if daemon_instance and daemon_instance.status != DaemonStatus.STOPPED:
        logger.warning("Daemon is already running")
        return daemon_instance
    
    daemon_instance = JanitorDaemon(config)
    await daemon_instance.start()
    
    return daemon_instance


async def stop_daemon():
    """Stop the global daemon instance."""
    global daemon_instance
    
    if daemon_instance:
        await daemon_instance.stop()
        daemon_instance = None


async def get_daemon_status() -> Dict:
    """Get status of the global daemon instance."""
    global daemon_instance
    
    if daemon_instance:
        return await daemon_instance.get_status()
    else:
        return {'status': 'stopped'}
