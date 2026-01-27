"""
Smart Caching System - Intelligent file metadata caching with change detection.

Features:
- File hash tracking for change detection
- Incremental scans (only new/modified files)
- TTL-based cache invalidation
- Persistent cache storage
- Memory-efficient LRU eviction
"""

import os
import json
import hashlib
import sqlite3
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import threading
from dataclasses import dataclass, asdict
import pickle

from app.agents.janitor.janitor_tools import FileInfo

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for file metadata."""
    path: str
    name: str
    extension: str
    size_bytes: int
    modified_at: datetime
    created_at: datetime
    accessed_at: datetime
    file_hash: str
    is_hidden: bool = False
    is_readonly: bool = False
    category: Optional[str] = None
    metadata_hash: Optional[str] = None
    last_scanned: datetime = None
    
    def __post_init__(self):
        if isinstance(self.modified_at, str):
            self.modified_at = datetime.fromisoformat(self.modified_at)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.accessed_at, str):
            self.accessed_at = datetime.fromisoformat(self.accessed_at)
        if isinstance(self.last_scanned, str):
            self.last_scanned = datetime.fromisoformat(self.last_scanned)
        elif self.last_scanned is None:
            self.last_scanned = datetime.now()


class SmartCache:
    """Smart caching system with change detection and incremental updates."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        # Cache directory
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".janitor_cache")
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Database path
        self.db_path = os.path.join(cache_dir, "file_cache.db")
        
        # Cache settings
        self.default_ttl = timedelta(days=7)  # Cache entries valid for 7 days
        self.max_entries = 100000  # Maximum cache entries
        self.cleanup_threshold = 0.8  # Clean when 80% full
        
        # In-memory cache for frequently accessed items
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_cache_size = 1000
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Background cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        # Initialize database
        self._init_database()
        
        # Start background cleanup
        self._start_cleanup_thread()
    
    def _init_database(self):
        """Initialize SQLite database for persistent caching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS file_cache (
                        path TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        extension TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        modified_at TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        accessed_at TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        is_hidden BOOLEAN DEFAULT FALSE,
                        is_readonly BOOLEAN DEFAULT FALSE,
                        category TEXT,
                        metadata_hash TEXT,
                        last_scanned TEXT NOT NULL,
                        cache_created TEXT NOT NULL
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_extension ON file_cache(extension)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON file_cache(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_last_scanned ON file_cache(last_scanned)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_file_hash ON file_cache(file_hash)")
                
                conn.commit()
                logger.info("[SmartCache] Database initialized")
                
        except Exception as e:
            logger.error(f"[SmartCache] Failed to initialize database: {e}")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while not self._stop_cleanup.wait(3600):  # Run every hour
                try:
                    self._cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"[SmartCache] Background cleanup failed: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("[SmartCache] Background cleanup thread started")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.debug(f"[SmartCache] Failed to hash {file_path}: {e}")
            return ""
    
    def _file_to_cache_entry(self, file_path: str) -> Optional[CacheEntry]:
        """Convert file to cache entry."""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            p = Path(file_path)
            
            return CacheEntry(
                path=file_path,
                name=p.name,
                extension=p.suffix.lower(),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                accessed_at=datetime.fromtimestamp(stat.st_atime),
                file_hash=self._calculate_file_hash(file_path),
                is_hidden=p.name.startswith('.') or bool(stat.st_file_attributes & 2) if hasattr(stat, 'st_file_attributes') else False,
                is_readonly=not os.access(file_path, os.W_OK),
                last_scanned=datetime.now()
            )
            
        except Exception as e:
            logger.debug(f"[SmartCache] Failed to create cache entry for {file_path}: {e}")
            return None
    
    def _is_file_changed(self, file_path: str, cached_entry: CacheEntry) -> bool:
        """Check if file has changed since last cache."""
        try:
            if not os.path.exists(file_path):
                return True  # File deleted
            
            stat = os.stat(file_path)
            
            # Quick check: modification time and size
            if (datetime.fromtimestamp(stat.st_mtime) != cached_entry.modified_at or
                stat.st_size != cached_entry.size_bytes):
                return True
            
            # Deep check: file hash (only if quick check passed)
            current_hash = self._calculate_file_hash(file_path)
            return current_hash != cached_entry.file_hash
            
        except Exception as e:
            logger.debug(f"[SmartCache] Change detection failed for {file_path}: {e}")
            return True  # Assume changed to be safe
    
    async def get_file_info(self, file_path: str, force_refresh: bool = False) -> Optional[CacheEntry]:
        """Get file info from cache or filesystem."""
        # Check memory cache first
        if not force_refresh and file_path in self._memory_cache:
            cached_entry = self._memory_cache[file_path]
            if not self._is_file_changed(file_path, cached_entry):
                self._cache_hits += 1
                return cached_entry
        
        # Check database cache
        if not force_refresh:
            cached_entry = await self._get_from_database(file_path)
            if cached_entry and not self._is_file_changed(file_path, cached_entry):
                # Update memory cache
                self._update_memory_cache(file_path, cached_entry)
                self._cache_hits += 1
                return cached_entry
        
        # File not in cache or changed, read from filesystem
        cache_entry = self._file_to_cache_entry(file_path)
        if cache_entry:
            await self._store_in_database(cache_entry)
            self._update_memory_cache(file_path, cache_entry)
            self._cache_misses += 1
            return cache_entry
        
        self._cache_misses += 1
        return None
    
    async def _get_from_database(self, file_path: str) -> Optional[CacheEntry]:
        """Get cache entry from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM file_cache WHERE path = ?",
                    (file_path,)
                )
                row = cursor.fetchone()
                
                if row:
                    data = dict(row)
                    # Remove database-specific fields
                    data.pop('cache_created', None)
                    return CacheEntry(**data)
                    
        except Exception as e:
            logger.debug(f"[SmartCache] Database lookup failed for {file_path}: {e}")
        
        return None
    
    async def _store_in_database(self, entry: CacheEntry):
        """Store cache entry in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = asdict(entry)
                data['cache_created'] = datetime.now().isoformat()
                
                conn.execute("""
                    INSERT OR REPLACE INTO file_cache (
                        path, name, extension, size_bytes, modified_at, created_at,
                        accessed_at, file_hash, is_hidden, is_readonly, category,
                        metadata_hash, last_scanned, cache_created
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['path'], data['name'], data['extension'], data['size_bytes'],
                    data['modified_at'].isoformat(), data['created_at'].isoformat(),
                    data['accessed_at'].isoformat(), data['file_hash'], data['is_hidden'],
                    data['is_readonly'], data['category'], data['metadata_hash'],
                    data['last_scanned'].isoformat(), data['cache_created']
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.debug(f"[SmartCache] Database store failed for {entry.path}: {e}")
    
    def _update_memory_cache(self, file_path: str, entry: CacheEntry):
        """Update memory cache with LRU eviction."""
        # Remove oldest entry if cache is full
        if len(self._memory_cache) >= self._memory_cache_size:
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
        
        self._memory_cache[file_path] = entry
    
    async def get_changed_files(self, directory: str) -> Tuple[List[str], List[str]]:
        """Get lists of new, modified, and deleted files in directory."""
        new_files = []
        modified_files = []
        
        try:
            # Get all files in directory
            current_files = set()
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    current_files.add(file_path)
            
            # Get cached files for this directory
            cached_files = set()
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT path FROM file_cache WHERE path LIKE ?",
                        (directory + '%',)
                    )
                    cached_files = {row[0] for row in cursor.fetchall()}
            except Exception as e:
                logger.debug(f"[SmartCache] Failed to get cached files: {e}")
            
            # Find new and modified files
            for file_path in current_files:
                if file_path not in cached_files:
                    new_files.append(file_path)
                else:
                    cached_entry = await self._get_from_database(file_path)
                    if cached_entry and self._is_file_changed(file_path, cached_entry):
                        modified_files.append(file_path)
            
            # Note: Deleted files are cached_files - current_files
            # We don't return them here but they could be cleaned up
            
        except Exception as e:
            logger.error(f"[SmartCache] Change detection failed for {directory}: {e}")
        
        return new_files, modified_files
    
    async def scan_directory_incremental(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        max_files: int = 1000  # Limit to prevent overwhelming the system
    ) -> List[CacheEntry]:
        """Perform incremental scan of directory using cache."""
        logger.info(f"[SmartCache] Incremental scan of {directory}")
        
        new_files, modified_files = await self.get_changed_files(directory)
        files_to_scan = new_files + modified_files
        
        # Limit the number of files to process at once
        if len(files_to_scan) > max_files:
            logger.warning(f"[SmartCache] Too many files ({len(files_to_scan)}), limiting to {max_files}")
            files_to_scan = files_to_scan[:max_files]
        
        logger.info(f"[SmartCache] Found {len(new_files)} new, {len(modified_files)} modified files (processing {len(files_to_scan)} total)")
        
        # Get file info for changed files
        entries = []
        for file_path in files_to_scan:
            if extensions:
                ext = Path(file_path).suffix.lower()
                if ext not in extensions:
                    continue
            
            entry = await self.get_file_info(file_path, force_refresh=True)
            if entry:
                entries.append(entry)
        
        # Also get unchanged files from cache
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM file_cache WHERE path LIKE ?"
                params = [directory + '%']
                
                if extensions:
                    placeholders = ','.join(['?' for _ in extensions])
                    query += f" AND extension IN ({placeholders})"
                    params.extend(extensions)
                
                cursor = conn.execute(query, params)
                for row in cursor.fetchall():
                    data = dict(row)
                    data.pop('cache_created', None)
                    
                    # Skip if file was already processed as changed
                    file_path = data['path']
                    if file_path not in files_to_scan and os.path.exists(file_path):
                        entry = CacheEntry(**data)
                        entries.append(entry)
        
        except Exception as e:
            logger.error(f"[SmartCache] Failed to get cached entries: {e}")
        
        logger.info(f"[SmartCache] Incremental scan complete: {len(entries)} total files")
        return entries
    
    async def find_duplicates(self, directory: str) -> Dict[str, List[str]]:
        """Find duplicate files using cached hashes."""
        logger.info(f"[SmartCache] Finding duplicates in {directory}")
        
        duplicates = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT file_hash, GROUP_CONCAT(path, '|') as paths
                    FROM file_cache 
                    WHERE path LIKE ? AND file_hash != ''
                    GROUP BY file_hash
                    HAVING COUNT(*) > 1
                """, (directory + '%',))
                
                for row in cursor.fetchall():
                    file_hash, paths_str = row
                    paths = paths_str.split('|')
                    if len(paths) > 1:
                        duplicates[file_hash] = paths
        
        except Exception as e:
            logger.error(f"[SmartCache] Duplicate detection failed: {e}")
        
        logger.info(f"[SmartCache] Found {len(duplicates)} duplicate groups")
        return duplicates
    
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries."""
        try:
            cutoff_date = datetime.now() - self.default_ttl
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete expired entries
                cursor = conn.execute(
                    "DELETE FROM file_cache WHERE last_scanned < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                
                # Check if we need to free more space
                cursor = conn.execute("SELECT COUNT(*) FROM file_cache")
                total_count = cursor.fetchone()[0]
                
                if total_count > self.max_entries * self.cleanup_threshold:
                    # Delete oldest entries beyond limit
                    limit = self.max_entries - int(self.max_entries * 0.2)  # Keep 80% of max
                    cursor = conn.execute("""
                        DELETE FROM file_cache 
                        WHERE path NOT IN (
                            SELECT path FROM file_cache 
                            ORDER BY last_scanned DESC 
                            LIMIT ?
                        )
                    """, (limit,))
                    deleted_count += cursor.rowcount
                
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"[SmartCache] Cleaned up {deleted_count} expired cache entries")
        
        except Exception as e:
            logger.error(f"[SmartCache] Cleanup failed: {e}")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM file_cache")
                total_entries = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT extension) FROM file_cache")
                unique_extensions = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(DISTINCT category) FROM file_cache WHERE category IS NOT NULL")
                categorized_files = cursor.fetchone()[0]
        except:
            total_entries = 0
            unique_extensions = 0
            categorized_files = 0
        
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'total_entries': total_entries,
            'memory_cache_size': len(self._memory_cache),
            'unique_extensions': unique_extensions,
            'categorized_files': categorized_files,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'cache_directory': self.cache_dir
        }
    
    def clear_cache(self):
        """Clear all cache data."""
        try:
            # Clear memory cache
            self._memory_cache.clear()
            
            # Clear database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM file_cache")
                conn.commit()
            
            logger.info("[SmartCache] Cache cleared")
            
        except Exception as e:
            logger.error(f"[SmartCache] Failed to clear cache: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)


# Global cache instance
_smart_cache: Optional[SmartCache] = None


def get_smart_cache() -> SmartCache:
    """Get the global smart cache instance."""
    global _smart_cache
    if _smart_cache is None:
        _smart_cache = SmartCache()
    return _smart_cache
