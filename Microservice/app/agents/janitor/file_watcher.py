"""
File Watcher - Real-time monitoring for Downloads/Desktop changes.

Uses watchdog library to detect:
- New file created
- File download completed
- File renamed/moved

Triggers Janitor analysis on new files automatically.
"""

import os
import asyncio
import logging
from typing import Callable, Optional
from pathlib import Path
from datetime import datetime, timedelta
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Try to import watchdog, graceful fallback if not installed
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("[FileWatcher] watchdog not installed. Run: pip install watchdog")


class FileEvent(BaseModel):
    """Represents a file system event."""
    event_type: str  # "created", "modified", "completed"
    path: str
    filename: str
    extension: str
    size_bytes: int
    timestamp: datetime


class FileWatcher:
    """
    Watches directories for new files and triggers callbacks.
    
    Features:
    - Debounces rapid changes (waits for download to complete)
    - Filters by extension if needed
    - Runs in background asyncio task
    
    Usage:
        watcher = FileWatcher()
        watcher.on_new_file = my_callback
        await watcher.start()
    """
    
    def __init__(
        self,
        watch_paths: Optional[list[str]] = None,
        debounce_seconds: float = 2.0,
    ):
        self._user_home = os.path.expanduser("~")
        self._watch_paths = watch_paths or [
            os.path.join(self._user_home, "Downloads"),
            os.path.join(self._user_home, "Desktop"),
        ]
        self._debounce_seconds = debounce_seconds
        self._pending_files: dict[str, datetime] = {}
        self._observer = None
        self._running = False
        self._callback: Optional[Callable] = None
        
    @property
    def on_new_file(self) -> Optional[Callable]:
        """Callback for new file events."""
        return self._callback
    
    @on_new_file.setter
    def on_new_file(self, callback: Callable):
        self._callback = callback
    
    async def start(self) -> None:
        """Start watching directories."""
        if not WATCHDOG_AVAILABLE:
            logger.error("[FileWatcher] Cannot start: watchdog not installed")
            return
        
        if self._running:
            return
        
        self._running = True
        self._observer = Observer()
        
        handler = _FileEventHandler(self._on_file_event)
        
        for path in self._watch_paths:
            if os.path.exists(path):
                self._observer.schedule(handler, path, recursive=False)
                logger.info(f"[FileWatcher] Watching: {path}")
        
        self._observer.start()
        
        # Start debounce processor
        asyncio.create_task(self._process_pending())
        
        logger.info("[FileWatcher] Started")
    
    async def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
        logger.info("[FileWatcher] Stopped")
    
    def _on_file_event(self, event) -> None:
        """Handle raw file event (from watchdog thread)."""
        if event.is_directory:
            return
        
        path = event.src_path
        
        # Skip temporary files
        if path.endswith('.tmp') or path.endswith('.crdownload') or path.endswith('.part'):
            return
        
        # Add to pending (debounce)
        self._pending_files[path] = datetime.now()
    
    async def _process_pending(self) -> None:
        """Process pending files after debounce period."""
        while self._running:
            await asyncio.sleep(0.5)
            
            now = datetime.now()
            threshold = timedelta(seconds=self._debounce_seconds)
            
            # Find files that have settled
            ready = []
            for path, timestamp in list(self._pending_files.items()):
                if now - timestamp >= threshold:
                    ready.append(path)
            
            # Process ready files
            for path in ready:
                del self._pending_files[path]
                await self._handle_new_file(path)
    
    async def _handle_new_file(self, path: str) -> None:
        """Handle a new file that has completed downloading."""
        if not os.path.exists(path):
            return
        
        try:
            stat = os.stat(path)
            p = Path(path)
            
            event = FileEvent(
                event_type="completed",
                path=path,
                filename=p.name,
                extension=p.suffix.lower(),
                size_bytes=stat.st_size,
                timestamp=datetime.now(),
            )
            
            logger.info(f"[FileWatcher] New file: {event.filename} ({event.size_bytes} bytes)")
            
            if self._callback:
                # Call async or sync callback
                if asyncio.iscoroutinefunction(self._callback):
                    await self._callback(event)
                else:
                    self._callback(event)
                    
        except Exception as e:
            logger.error(f"[FileWatcher] Error handling {path}: {e}")


if WATCHDOG_AVAILABLE:
    class _FileEventHandler(FileSystemEventHandler):
        """Watchdog event handler bridge."""
        
        def __init__(self, callback):
            self._callback = callback
            
        def on_created(self, event):
            self._callback(event)
            
        def on_modified(self, event):
            self._callback(event)


# Singleton instance
_watcher: Optional[FileWatcher] = None

def get_file_watcher() -> FileWatcher:
    """Get the global file watcher instance."""
    global _watcher
    if _watcher is None:
        _watcher = FileWatcher()
    return _watcher
