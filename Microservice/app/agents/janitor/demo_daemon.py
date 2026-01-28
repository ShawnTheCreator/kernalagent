"""
Janitor Daemon Demonstration
Standalone script to demonstrate daemon functionality without import issues.
"""

import os
import sys
import asyncio
import tempfile
import shutil
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import hashlib
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Simplified daemon components for demonstration
class DaemonStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class NotificationType(Enum):
    SCAN_PROGRESS = "scan_progress"
    FILE_FOUND = "file_found"
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETE = "operation_complete"
    STATUS_UPDATE = "status_update"


class OperationType(Enum):
    SCAN = "scan"
    MOVE = "move"
    DELETE = "delete"
    RENAME = "rename"


@dataclass
class FileOperation:
    operation_id: str
    operation_type: OperationType
    source_path: str
    destination_path: Optional[str] = None
    backup_path: Optional[str] = None
    file_size: int = 0
    created_at: datetime = None
    status: str = "pending"
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class DaemonNotification:
    type: NotificationType
    message: str
    data: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['type'] = self.type.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


class SimpleFileWatcher:
    """Simplified file watcher for demonstration."""
    
    def __init__(self, watch_paths: List[str], callback: Callable):
        self.watch_paths = [Path(p) for p in watch_paths]
        self.callback = callback
        self.running = False
        self.file_hashes = {}
        
    async def start(self):
        """Start file watching."""
        self.running = True
        logger.info(f"File watcher started for: {self.watch_paths}")
        
        # Initial scan
        await self._scan_directories()
        
        # Start monitoring loop
        asyncio.create_task(self._monitor_loop())
    
    async def _scan_directories(self):
        """Scan directories for files."""
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
                
            for file_path in watch_path.rglob('*'):
                if file_path.is_file():
                    await self._process_file(file_path, 'created')
    
    async def _process_file(self, file_path: Path, event_type: str):
        """Process a file event."""
        try:
            file_hash = self._calculate_file_hash(file_path)
            old_hash = self.file_hashes.get(str(file_path))
            
            if file_hash != old_hash:
                self.file_hashes[str(file_path)] = file_hash
                
                await self.callback({
                    'type': 'file_event',
                    'event_type': event_type,
                    'path': str(file_path),
                    'timestamp': datetime.now(),
                    'file_size': file_path.stat().st_size
                })
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate simple file hash."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    async def _monitor_loop(self):
        """Monitor for file changes."""
        while self.running:
            try:
                await self._scan_directories()
                await asyncio.sleep(2.0)  # Check every 2 seconds
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(2.0)
    
    async def stop(self):
        """Stop file watching."""
        self.running = False
        logger.info("File watcher stopped")


class SimpleOperationQueue:
    """Simplified operation queue for demonstration."""
    
    def __init__(self, max_workers: int = 2, temp_dir: str = None):
        self.max_workers = max_workers
        self.temp_dir = Path(temp_dir or Path.home() / ".janitor_demo_temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.pending_operations = asyncio.Queue()
        self.active_operations: Dict[str, FileOperation] = {}
        self.completed_operations: List[FileOperation] = []
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
                operation = await self.pending_operations.get()
                self.active_operations[operation.operation_id] = operation
                
                # Process operation
                success = await self._execute_operation(operation)
                
                # Move to completed
                self.completed_operations.append(operation)
                del self.active_operations[operation.operation_id]
                
                logger.info(f"Operation {operation.operation_id} completed: {success}")
                
            except Exception as e:
                logger.error(f"Error processing operation: {e}")
    
    async def _execute_operation(self, operation: FileOperation) -> bool:
        """Execute a file operation."""
        try:
            operation.status = "running"
            
            if operation.operation_type == OperationType.DELETE:
                return await self._execute_delete(operation)
            elif operation.operation_type == OperationType.MOVE:
                return await self._execute_move(operation)
            else:
                logger.warning(f"Unsupported operation: {operation.operation_type}")
                return False
                
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            operation.status = "failed"
            return False
    
    async def _execute_delete(self, operation: FileOperation) -> bool:
        """Execute delete operation with backup."""
        try:
            source = Path(operation.source_path)
            
            # Move to temp instead of permanent delete
            backup_path = self.temp_dir / f"trash_{operation.operation_id}_{source.name}"
            shutil.move(str(source), str(backup_path))
            operation.backup_path = str(backup_path)
            
            operation.status = "completed"
            logger.info(f"Moved to trash: {source}")
            return True
            
        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return False
    
    async def _execute_move(self, operation: FileOperation) -> bool:
        """Execute move operation."""
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
    
    async def add_operation(self, operation: FileOperation):
        """Add operation to queue."""
        await self.pending_operations.put(operation)
        logger.info(f"Queued operation: {operation.operation_id}")
    
    async def stop(self):
        """Stop operation processing."""
        self.running = False
        logger.info("OperationQueue stopped")


class SimpleJanitorDaemon:
    """Simplified Janitor Daemon for demonstration."""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.status = DaemonStatus.STARTING
        
        # Initialize components
        self.watch_paths = [
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
        ]
        
        self.file_watcher = SimpleFileWatcher(
            watch_paths=self.watch_paths,
            callback=self._handle_file_event
        )
        
        self.operation_queue = SimpleOperationQueue(
            max_workers=self.config.get('max_workers', 2),
            temp_dir=self.config.get('temp_dir', str(Path.home() / ".janitor_demo_temp"))
        )
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'operations_completed': 0,
            'start_time': datetime.now(),
            'last_activity': None
        }
        
        # Notifications for demo
        self.notifications = []
        
        logger.info("SimpleJanitorDaemon initialized")
    
    async def start(self):
        """Start daemon components."""
        try:
            logger.info("Starting SimpleJanitorDaemon...")
            
            # Start components
            await self.operation_queue.start()
            await self.file_watcher.start()
            
            self.status = DaemonStatus.RUNNING
            
            # Send startup notification
            self._add_notification(DaemonNotification(
                type=NotificationType.STATUS_UPDATE,
                message="Janitor Daemon started successfully",
                data={
                    'status': self.status.value,
                    'watch_paths': self.watch_paths,
                    'max_workers': self.operation_queue.max_workers
                }
            ))
            
            logger.info("SimpleJanitorDaemon started successfully")
            
        except Exception as e:
            self.status = DaemonStatus.ERROR
            logger.error(f"Failed to start daemon: {e}")
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
            self._add_notification(DaemonNotification(
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
            if event_type == 'created':
                await self._process_new_file(file_path, event)
            
        except Exception as e:
            logger.error(f"Error handling file event: {e}")
    
    async def _process_new_file(self, file_path: str, event: Dict):
        """Process a newly created file."""
        try:
            file_path_obj = Path(file_path)
            
            # Simple file categorization
            extension = file_path_obj.suffix.lower()
            
            # Decide what to do based on file type
            if extension in ['.tmp', '.temp']:
                # Delete temp files
                operation = FileOperation(
                    operation_id=f"delete_{int(time.time())}_{hash(file_path) % 10000}",
                    operation_type=OperationType.DELETE,
                    source_path=file_path,
                    file_size=file_path_obj.stat().st_size
                )
                
                await self.operation_queue.add_operation(operation)
                
                self._add_notification(DaemonNotification(
                    type=NotificationType.OPERATION_STARTED,
                    message=f"Deleting temp file: {file_path_obj.name}",
                    data={'operation_id': operation.operation_id}
                ))
            
            elif extension in ['.pdf', '.doc', '.docx']:
                # Suggest organizing documents
                self._add_notification(DaemonNotification(
                    type=NotificationType.OPERATION_STARTED,
                    message=f"Document detected: {file_path_obj.name}. Consider organizing to Documents folder.",
                    data={'file_info': {'name': file_path_obj.name, 'type': 'document'}}
                ))
            
        except Exception as e:
            logger.error(f"Error processing new file {file_path}: {e}")
    
    def _add_notification(self, notification: DaemonNotification):
        """Add notification to list."""
        self.notifications.append(notification)
        
        # Keep only last 50 notifications
        if len(self.notifications) > 50:
            self.notifications = self.notifications[-50:]
        
        # Log notification
        logger.info(f"NOTIFICATION: {notification.message}")
    
    async def scan_directories(self):
        """Perform comprehensive directory scan."""
        try:
            self._add_notification(DaemonNotification(
                type=NotificationType.SCAN_PROGRESS,
                message="Starting directory scan...",
                data={'phase': 'starting'}
            ))
            
            # Count files
            total_files = 0
            for watch_path in self.watch_paths:
                path = Path(watch_path)
                if path.exists():
                    total_files += len(list(path.rglob('*')))
            
            self._add_notification(DaemonNotification(
                type=NotificationType.SCAN_PROGRESS,
                message=f"Scanning {total_files} files...",
                data={'phase': 'scanning', 'total_files': total_files}
            ))
            
            # Process files by size (small to large)
            all_files = []
            for watch_path in self.watch_paths:
                path = Path(watch_path)
                if path.exists():
                    for file_path in path.rglob('*'):
                        if file_path.is_file():
                            all_files.append(file_path)
            
            # Sort by size
            all_files.sort(key=lambda x: x.stat().st_size)
            
            # Process files
            for i, file_path in enumerate(all_files):
                self._add_notification(DaemonNotification(
                    type=NotificationType.SCAN_PROGRESS,
                    message=f"Processing {i+1}/{len(all_files)}: {file_path.name}",
                    data={
                        'phase': 'processing',
                        'current': i+1,
                        'total': len(all_files),
                        'current_file': file_path.name
                    }
                ))
                
                # Simulate processing time
                await asyncio.sleep(0.01)
                
                # Process the file
                await self._process_new_file(str(file_path), {'event_type': 'scan_found'})
            
            self._add_notification(DaemonNotification(
                type=NotificationType.SCAN_PROGRESS,
                message=f"Scan complete. Processed {len(all_files)} files.",
                data={'phase': 'complete', 'total_files': len(all_files)}
            ))
            
        except Exception as e:
            logger.error(f"Error during directory scan: {e}")
            self._add_notification(DaemonNotification(
                type=NotificationType.STATUS_UPDATE,
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
            'notifications': len(self.notifications),
            'uptime': (datetime.now() - self.stats['start_time']).total_seconds()
        }
    
    async def stop(self):
        """Stop daemon gracefully."""
        try:
            self.status = DaemonStatus.STOPPED
            logger.info("Stopping SimpleJanitorDaemon...")
            
            # Stop components
            await self.file_watcher.stop()
            await self.operation_queue.stop()
            
            logger.info("SimpleJanitorDaemon stopped")
            
        except Exception as e:
            self.status = DaemonStatus.ERROR
            logger.error(f"Error stopping daemon: {e}")


async def demonstrate_daemon():
    """Demonstrate daemon functionality."""
    print("🚀 Janitor Daemon Demonstration")
    print("=" * 50)
    
    # Create test environment
    demo_dir = tempfile.mkdtemp(prefix="janitor_demo_")
    print(f"📁 Created demo directory: {demo_dir}")
    
    # Configure daemon to watch demo directory
    config = {
        'max_workers': 2,
        'temp_dir': os.path.join(demo_dir, "temp")
    }
    
    daemon = SimpleJanitorDaemon(config)
    daemon.watch_paths = [demo_dir]  # Only watch demo directory
    
    try:
        # Start daemon
        print("\n🔧 Starting daemon...")
        await daemon.start()
        
        # Show initial status
        status = await daemon.get_status()
        print(f"📊 Status: {status['status']}")
        print(f"📂 Watching: {daemon.watch_paths}")
        
        # Create some test files
        print("\n📄 Creating test files...")
        test_files = [
            ("document.pdf", "This is a PDF document"),
            ("temp_file.tmp", "Temporary content"),
            ("image.jpg", "Fake image content"),
            ("another_temp.temp", "Another temp file"),
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(demo_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"  Created: {filename}")
        
        # Wait for processing
        print("\n⏳ Waiting for file processing...")
        await asyncio.sleep(2.0)
        
        # Show notifications
        print("\n📢 Notifications:")
        for notification in daemon.notifications[-10:]:  # Last 10
            print(f"  • {notification.message}")
        
        # Run directory scan
        print("\n🔍 Running directory scan...")
        await daemon.scan_directories()
        
        # Wait for scan completion
        await asyncio.sleep(1.0)
        
        # Show final status
        status = await daemon.get_status()
        print(f"\n📊 Final Status:")
        print(f"  Status: {status['status']}")
        print(f"  Files processed: {status['stats']['files_processed']}")
        print(f"  Operations completed: {status['completed_operations']}")
        print(f"  Uptime: {status['uptime']:.2f} seconds")
        
        # Show operations
        print(f"\n🔄 Operations:")
        for op in daemon.operation_queue.completed_operations:
            print(f"  • {op.operation_type.value}: {Path(op.source_path).name} -> {op.status}")
        
        # Show temp directory contents
        temp_dir = Path(config['temp_dir'])
        if temp_dir.exists():
            temp_files = list(temp_dir.glob('*'))
            print(f"\n🗂️  Temp directory contains {len(temp_files)} files:")
            for temp_file in temp_files:
                print(f"  • {temp_file.name}")
        
    finally:
        # Stop daemon
        print("\n🛑 Stopping daemon...")
        await daemon.stop()
        
        # Cleanup
        shutil.rmtree(demo_dir)
        print(f"🧹 Cleaned up demo directory")
    
    print("\n✅ Demonstration complete!")


if __name__ == "__main__":
    # Run demonstration
    asyncio.run(demonstrate_daemon())
