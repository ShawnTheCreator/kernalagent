"""
Parallel Processing Engine - High-performance batch file operations.

Implements parallel processing for:
- Async file scanning with concurrency control
- Batch move/delete operations
- Parallel capability execution
- Resource-aware task scheduling
"""

import asyncio
import os
import logging
from typing import List, Dict, Optional, Callable, Any
from pathlib import Path
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

from app.agents.janitor.janitor_tools import FileInfo, scan_folder, safe_move, safe_delete
from app.agents.janitor.capabilities import run_capabilities, CapabilityResult

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """High-performance parallel processing engine for file operations."""
    
    def __init__(self, max_workers: Optional[int] = None):
        # Determine optimal worker count
        if max_workers is None:
            self.max_workers = min(multiprocessing.cpu_count(), 8)  # Cap at 8 to avoid overwhelming
        else:
            self.max_workers = max_workers
            
        # Thread pool for CPU-bound tasks
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Semaphore for I/O-bound operations (limit concurrent file operations)
        self.io_semaphore = asyncio.Semaphore(min(self.max_workers * 2, 16))
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'operations_completed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
        }
    
    async def parallel_scan(
        self,
        paths: List[str],
        extensions: Optional[List[str]] = None,
        min_age_days: int = 0,
        max_size_mb: Optional[float] = None,
        batch_size: int = 50
    ) -> List[FileInfo]:
        """Scan multiple folders in parallel."""
        logger.info(f"[ParallelProcessor] Starting parallel scan of {len(paths)} paths")
        self.stats['start_time'] = time.time()
        
        async def scan_single_folder(path: str) -> List[FileInfo]:
            async with self.io_semaphore:
                try:
                    return await scan_folder(
                        path,
                        extensions=extensions,
                        min_age_days=min_age_days,
                        max_size_mb=max_size_mb
                    )
                except Exception as e:
                    logger.error(f"[ParallelProcessor] Scan failed for {path}: {e}")
                    return []
        
        # Process folders in parallel batches
        all_files = []
        for i in range(0, len(paths), batch_size):
            batch = paths[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[scan_single_folder(path) for path in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, list):
                    all_files.extend(result)
                    self.stats['files_processed'] += len(result)
                else:
                    self.stats['errors'] += 1
        
        self.stats['end_time'] = time.time()
        duration = self.stats['end_time'] - self.stats['start_time']
        logger.info(f"[ParallelProcessor] Scanned {len(all_files)} files in {duration:.2f}s")
        
        return all_files
    
    async def parallel_capability_execution(
        self,
        files: List[FileInfo],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, List[CapabilityResult]]:
        """Run capabilities on all files in parallel."""
        logger.info(f"[ParallelProcessor] Running capabilities on {len(files)} files")
        
        async def run_on_single_file(file_info: FileInfo) -> tuple[str, List[CapabilityResult]]:
            async with self.io_semaphore:
                try:
                    results = await run_capabilities(
                        file_info.path,
                        {
                            'filename': file_info.name,
                            'extension': file_info.extension,
                            'size_bytes': file_info.size_bytes,
                        }
                    )
                    return file_info.path, results
                except Exception as e:
                    logger.error(f"[ParallelProcessor] Capability execution failed for {file_info.path}: {e}")
                    return file_info.path, []
        
        # Process files in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(min(self.max_workers, 4))  # Limit for capability execution
        
        async def controlled_execution(file_info: FileInfo):
            async with semaphore:
                return await run_on_single_file(file_info)
        
        # Execute all tasks
        tasks = [controlled_execution(file_info) for file_info in files]
        completed_count = 0
        
        results_dict = {}
        for task in asyncio.as_completed(tasks):
            file_path, results = await task
            results_dict[file_path] = results
            completed_count += 1
            
            # Progress callback
            if progress_callback:
                await progress_callback(completed_count, len(files), file_path)
        
        # Filter files that need actions
        actionable_files = {
            path: results for path, results in results_dict.items() 
            if results and any(r.action_required for r in results)
        }
        
        logger.info(f"[ParallelProcessor] Found {len(actionable_files)} files needing actions")
        return actionable_files
    
    async def parallel_batch_operations(
        self,
        operations: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute batch file operations (move/delete) in parallel."""
        logger.info(f"[ParallelProcessor] Executing {len(operations)} operations in parallel")
        
        async def execute_single_operation(op: Dict[str, Any]) -> Dict[str, Any]:
            async with self.io_semaphore:
                start_time = time.time()
                try:
                    op_type = op.get('type')
                    source = op.get('source')
                    destination = op.get('destination')
                    
                    if op_type == 'move':
                        result = await safe_move(source, destination)
                    elif op_type == 'delete':
                        result = await safe_delete(source, to_recycle=True)
                    else:
                        result = type('Result', (), {'success': False, 'error': f'Unknown operation: {op_type}'})()
                    
                    duration = time.time() - start_time
                    
                    return {
                        'success': result.success,
                        'source': source,
                        'destination': destination,
                        'error': getattr(result, 'error', None),
                        'duration': duration,
                        'operation': op_type
                    }
                    
                except Exception as e:
                    duration = time.time() - start_time
                    return {
                        'success': False,
                        'source': op.get('source'),
                        'error': str(e),
                        'duration': duration,
                        'operation': op.get('type')
                    }
        
        # Execute operations in parallel
        completed_count = 0
        successful_ops = 0
        failed_ops = 0
        total_duration = 0
        
        for task in asyncio.as_completed([execute_single_operation(op) for op in operations]):
            result = await task
            completed_count += 1
            total_duration += result['duration']
            
            if result['success']:
                successful_ops += 1
            else:
                failed_ops += 1
                logger.warning(f"[ParallelProcessor] Operation failed: {result['error']}")
            
            # Progress callback
            if progress_callback:
                await progress_callback(completed_count, len(operations), result)
            
            self.stats['operations_completed'] += 1
        
        # Summary statistics
        avg_duration = total_duration / len(operations) if operations else 0
        
        summary = {
            'total_operations': len(operations),
            'successful': successful_ops,
            'failed': failed_ops,
            'success_rate': successful_ops / len(operations) if operations else 0,
            'total_duration': total_duration,
            'average_duration': avg_duration,
            'throughput': len(operations) / total_duration if total_duration > 0 else 0
        }
        
        logger.info(f"[ParallelProcessor] Batch complete: {successful_ops}/{len(operations)} successful, "
                   f"avg {avg_duration:.3f}s per operation")
        
        return summary
    
    async def parallel_file_hashing(
        self,
        file_paths: List[str],
        batch_size: int = 100
    ) -> Dict[str, str]:
        """Calculate file hashes in parallel for duplicate detection."""
        logger.info(f"[ParallelProcessor] Hashing {len(file_paths)} files")
        
        def calculate_hash(file_path: str) -> tuple[str, Optional[str]]:
            try:
                import hashlib
                with open(file_path, 'rb') as f:
                    return file_path, hashlib.md5(f.read()).hexdigest()
            except Exception as e:
                logger.debug(f"[ParallelProcessor] Failed to hash {file_path}: {e}")
                return file_path, None
        
        # Process in batches to avoid memory issues
        hash_results = {}
        
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            # Run hashing in thread pool
            loop = asyncio.get_event_loop()
            batch_results = await loop.run_in_executor(
                self.thread_pool,
                lambda: [calculate_hash(path) for path in batch]
            )
            
            for file_path, file_hash in batch_results:
                if file_hash:
                    hash_results[file_path] = file_hash
        
        logger.info(f"[ParallelProcessor] Hashed {len(hash_results)} files successfully")
        return hash_results
    
    async def resource_monitor(self) -> Dict[str, float]:
        """Monitor system resources for adaptive scheduling."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'disk_read_mb': disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                'disk_write_mb': disk_io.write_bytes / (1024 * 1024) if disk_io else 0
            }
            
        except ImportError:
            # psutil not available, return dummy values
            return {
                'cpu_percent': 50.0,
                'memory_percent': 50.0,
                'disk_percent': 50.0,
                'disk_read_mb': 0,
                'disk_write_mb': 0
            }
    
    async def adaptive_batch_size(self) -> int:
        """Determine optimal batch size based on system resources."""
        resources = await self.resource_monitor()
        
        # Adjust batch size based on system load
        base_batch_size = 50
        
        if resources['cpu_percent'] > 80:
            base_batch_size = max(10, base_batch_size // 2)
        elif resources['memory_percent'] > 80:
            base_batch_size = max(20, base_batch_size // 2)
        elif resources['disk_percent'] > 90:
            base_batch_size = max(15, base_batch_size // 3)
        
        return base_batch_size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = self.stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            stats['total_duration'] = stats['end_time'] - stats['start_time']
            stats['throughput'] = stats['files_processed'] / stats['total_duration'] if stats['total_duration'] > 0 else 0
        else:
            stats['total_duration'] = 0
            stats['throughput'] = 0
        
        stats['max_workers'] = self.max_workers
        stats['error_rate'] = stats['errors'] / max(stats['files_processed'], 1)
        
        return stats
    
    async def cleanup(self):
        """Clean up resources."""
        self.thread_pool.shutdown(wait=True)
        logger.info("[ParallelProcessor] Cleaned up resources")


# Global instance
_parallel_processor: Optional[ParallelProcessor] = None


def get_parallel_processor() -> ParallelProcessor:
    """Get the global parallel processor instance."""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor()
    return _parallel_processor


async def parallel_scan_and_analyze(
    paths: List[str],
    extensions: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """High-level function for parallel scanning and analysis."""
    processor = get_parallel_processor()
    
    # Step 1: Parallel scan
    files = await processor.parallel_scan(
        paths=paths,
        extensions=extensions,
        batch_size=await processor.adaptive_batch_size()
    )
    
    # Step 2: Parallel capability execution
    actionable_files = await processor.parallel_capability_execution(
        files=files,
        progress_callback=progress_callback
    )
    
    return {
        'total_files_scanned': len(files),
        'files_needing_actions': len(actionable_files),
        'actionable_files': actionable_files,
        'stats': processor.get_stats()
    }
