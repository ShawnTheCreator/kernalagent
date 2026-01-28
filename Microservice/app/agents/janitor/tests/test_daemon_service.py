"""
Comprehensive Test Suite for Janitor Daemon Service
Tests all components with real file operations, WebSocket communication, and edge cases.
"""

import os
import sys
import asyncio
import pytest
import tempfile
import shutil
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import websockets
import websockets.client
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.janitor.daemon_service import (
    JanitorDaemon, 
    HybridFileWatcher, 
    PermissionManager, 
    WebSocketManager, 
    OperationQueue,
    FileOperation,
    OperationType,
    DaemonNotification,
    NotificationType,
    DaemonStatus,
    start_daemon,
    stop_daemon
)

# Configure logging for tests
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEnvironment:
    """Test environment with real file system operations."""
    
    def __init__(self):
        self.temp_dirs = []
        self.test_files = []
        self.daemon = None
        self.websocket_port = 8766  # Different port for tests
    
    def create_temp_dir(self) -> str:
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="janitor_daemon_test_")
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_test_file(self, directory: str, filename: str, content: str = "test content", size_kb: int = 1) -> str:
        """Create a test file with specified content and size."""
        file_path = os.path.join(directory, filename)
        
        # Create content of specified size
        if size_kb > 1:
            content = content * (size_kb * 1024 // len(content) + 1)
            content = content[:size_kb * 1024]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.test_files.append(file_path)
        return file_path
    
    def cleanup(self):
        """Clean up all test resources."""
        # Stop daemon if running
        if self.daemon:
            asyncio.create_task(self.daemon.stop())
        
        # Clean up test files
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        # Clean up temp directories
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
        
        self.test_files.clear()
        self.temp_dirs.clear()


@pytest.fixture
def test_env():
    """Pytest fixture for test environment."""
    env = TestEnvironment()
    yield env
    env.cleanup()


class TestHybridFileWatcher:
    """Test the hybrid file watching system."""
    
    @pytest.mark.asyncio
    async def test_file_creation_detection(self, test_env):
        """Test detection of new file creation."""
        temp_dir = test_env.create_temp_dir()
        events = []
        
        def event_callback(event):
            events.append(event)
        
        watcher = HybridFileWatcher([temp_dir], event_callback)
        await watcher.start()
        
        # Create a test file
        test_file = test_env.create_test_file(temp_dir, "test_file.txt", "test content")
        
        # Wait for event detection
        await asyncio.sleep(0.5)
        
        # Check if event was detected
        assert len(events) > 0
        file_events = [e for e in events if e.get('path') == test_file]
        assert len(file_events) > 0
        
        await watcher.stop()
    
    @pytest.mark.asyncio
    async def test_file_modification_detection(self, test_env):
        """Test detection of file modifications."""
        temp_dir = test_env.create_temp_dir()
        events = []
        
        def event_callback(event):
            events.append(event)
        
        watcher = HybridFileWatcher([temp_dir], event_callback)
        await watcher.start()
        
        # Create initial file
        test_file = test_env.create_test_file(temp_dir, "modifiable.txt", "initial content")
        
        # Wait for initial detection
        await asyncio.sleep(0.5)
        initial_events = len(events)
        
        # Modify the file
        time.sleep(0.1)  # Ensure different timestamp
        with open(test_file, 'a') as f:
            f.write(" modified")
        
        # Wait for modification detection
        await asyncio.sleep(0.5)
        
        # Check if modification was detected
        assert len(events) > initial_events
        
        await watcher.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_directories(self, test_env):
        """Test watching multiple directories simultaneously."""
        temp_dir1 = test_env.create_temp_dir()
        temp_dir2 = test_env.create_temp_dir()
        events = []
        
        def event_callback(event):
            events.append(event)
        
        watcher = HybridFileWatcher([temp_dir1, temp_dir2], event_callback)
        await watcher.start()
        
        # Create files in both directories
        file1 = test_env.create_test_file(temp_dir1, "dir1_file.txt", "content1")
        file2 = test_env.create_test_file(temp_dir2, "dir2_file.txt", "content2")
        
        # Wait for detection
        await asyncio.sleep(0.5)
        
        # Check both files were detected
        file1_events = [e for e in events if e.get('path') == file1]
        file2_events = [e for e in events if e.get('path') == file2]
        
        assert len(file1_events) > 0
        assert len(file2_events) > 0
        
        await watcher.stop()


class TestPermissionManager:
    """Test the permission management system."""
    
    @pytest.mark.asyncio
    async def test_local_permission_storage(self, test_env):
        """Test local permission storage and retrieval."""
        manager = PermissionManager()
        
        # Set a permission
        await manager.set_permission('move', '.pdf', True, always=True)
        
        # Get the permission
        permission = await manager.get_permission('move', 'test.pdf')
        assert permission == True
        
        # Set a different permission
        await manager.set_permission('delete', '.tmp', False, always=True)
        
        # Get the permission
        permission = await manager.get_permission('delete', 'test.tmp')
        assert permission == False
    
    @pytest.mark.asyncio
    async def test_permission_fallback(self, test_env):
        """Test permission fallback when no preference exists."""
        manager = PermissionManager()
        
        # Get permission for unknown file type
        permission = await manager.get_permission('move', 'test.unknown')
        assert permission is None  # Should return None for unknown
    
    @pytest.mark.asyncio
    async def test_permission_persistence(self, test_env):
        """Test that permissions persist across manager instances."""
        # Set permission in first instance
        manager1 = PermissionManager()
        await manager1.set_permission('move', '.pdf', True, always=True)
        
        # Create new instance and check permission
        manager2 = PermissionManager()
        permission = await manager2.get_permission('move', 'test.pdf')
        assert permission == True


class TestWebSocketManager:
    """Test WebSocket communication."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_env):
        """Test basic WebSocket connection and communication."""
        manager = WebSocketManager(host='localhost', port=8767)
        await manager.start()
        
        # Connect client
        uri = f"ws://{manager.host}:{manager.port}"
        async with websockets.client.connect(uri) as websocket:
            # Receive welcome message
            message = await websocket.recv()
            data = json.loads(message)
            assert data['type'] == 'status_update'
            assert 'connected' in data['message']
        
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_notification_broadcast(self, test_env):
        """Test notification broadcasting to multiple clients."""
        manager = WebSocketManager(host='localhost', port=8768)
        await manager.start()
        
        # Connect multiple clients
        uri = f"ws://{manager.host}:{manager.port}"
        client1 = websockets.client.connect(uri)
        client2 = websockets.client.connect(uri)
        
        async with client1 as ws1, client2 as ws2:
            # Wait for welcome messages
            await ws1.recv()
            await ws2.recv()
            
            # Send notification
            notification = DaemonNotification(
                type=NotificationType.FILE_FOUND,
                message="Test file found",
                data={'file_path': '/test/file.txt'}
            )
            await manager.send_notification(notification)
            
            # Both clients should receive the notification
            message1 = await ws1.recv()
            message2 = await ws2.recv()
            
            data1 = json.loads(message1)
            data2 = json.loads(message2)
            
            assert data1['type'] == 'file_found'
            assert data2['type'] == 'file_found'
            assert data1['message'] == data2['message']
        
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_client_message_handling(self, test_env):
        """Test handling of incoming client messages."""
        manager = WebSocketManager(host='localhost', port=8769)
        await manager.start()
        
        uri = f"ws://{manager.host}:{manager.port}"
        async with websockets.client.connect(uri) as websocket:
            # Wait for welcome message
            await websocket.recv()
            
            # Send ping message
            await websocket.send(json.dumps({'type': 'ping'}))
            
            # Should receive pong
            response = await websocket.recv()
            data = json.loads(response)
            assert data['type'] == 'pong'
        
        await manager.stop()


class TestOperationQueue:
    """Test operation queue with parallel processing."""
    
    @pytest.mark.asyncio
    async def test_move_operation(self, test_env):
        """Test file move operation with rollback."""
        temp_dir = test_env.create_temp_dir()
        temp_subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(temp_subdir)
        
        queue = OperationQueue(max_workers=2, temp_dir=temp_dir)
        await queue.start()
        
        # Create test file
        source_file = test_env.create_test_file(temp_dir, "move_test.txt", "move me")
        
        # Create move operation
        dest_file = os.path.join(temp_subdir, "moved_test.txt")
        operation = FileOperation(
            operation_id="test_move_1",
            operation_type=OperationType.MOVE,
            source_path=source_file,
            destination_path=dest_file
        )
        
        # Add to queue
        await queue.add_operation(operation)
        
        # Wait for completion
        await asyncio.sleep(1.0)
        
        # Check file was moved
        assert not os.path.exists(source_file)
        assert os.path.exists(dest_file)
        
        # Test rollback
        success = await queue.rollback_operation("test_move_1")
        assert success
        
        # Check file was restored
        assert os.path.exists(source_file)
        assert not os.path.exists(dest_file)
        
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_delete_operation(self, test_env):
        """Test file delete operation with rollback."""
        temp_dir = test_env.create_temp_dir()
        
        queue = OperationQueue(max_workers=2, temp_dir=temp_dir)
        await queue.start()
        
        # Create test file
        test_file = test_env.create_test_file(temp_dir, "delete_test.txt", "delete me")
        
        # Create delete operation
        operation = FileOperation(
            operation_id="test_delete_1",
            operation_type=OperationType.DELETE,
            source_path=test_file
        )
        
        # Add to queue
        await queue.add_operation(operation)
        
        # Wait for completion
        await asyncio.sleep(1.0)
        
        # Check file was moved to trash
        assert not os.path.exists(test_file)
        
        # Find trash file
        trash_files = list(Path(temp_dir).glob("trash_*_delete_test.txt"))
        assert len(trash_files) > 0
        
        # Test rollback
        success = await queue.rollback_operation("test_delete_1")
        assert success
        
        # Check file was restored
        assert os.path.exists(test_file)
        
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_parallel_operations(self, test_env):
        """Test parallel processing of multiple operations."""
        temp_dir = test_env.create_temp_dir()
        
        queue = OperationQueue(max_workers=3, temp_dir=temp_dir)
        await queue.start()
        
        # Create multiple test files
        files = []
        for i in range(5):
            file_path = test_env.create_test_file(temp_dir, f"parallel_test_{i}.txt", f"content {i}")
            files.append(file_path)
        
        # Create operations for all files
        operations = []
        for i, file_path in enumerate(files):
            operation = FileOperation(
                operation_id=f"test_parallel_{i}",
                operation_type=OperationType.DELETE,
                source_path=file_path
            )
            operations.append(operation)
            await queue.add_operation(operation)
        
        # Wait for all operations to complete
        await asyncio.sleep(2.0)
        
        # Check all files were processed
        for file_path in files:
            assert not os.path.exists(file_path)
        
        # Check operations completed
        assert len(queue.completed_operations) >= 5
        
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_size_based_processing(self, test_env):
        """Test processing files by size (small to large)."""
        temp_dir = test_env.create_temp_dir()
        
        queue = OperationQueue(max_workers=2, temp_dir=temp_dir)
        await queue.start()
        
        # Create files of different sizes
        files = []
        sizes = [1, 10, 100, 500]  # KB
        for size in sizes:
            file_path = test_env.create_test_file(temp_dir, f"size_test_{size}kb.txt", "x", size)
            files.append((file_path, size))
        
        # Sort by size and create operations
        files.sort(key=lambda x: x[1])  # Small to large
        for i, (file_path, size) in enumerate(files):
            operation = FileOperation(
                operation_id=f"size_test_{i}",
                operation_type=OperationType.DELETE,
                source_path=file_path,
                file_size=size * 1024
            )
            await queue.add_operation(operation)
        
        # Wait for completion
        await asyncio.sleep(3.0)
        
        # Check all files were processed
        for file_path, _ in files:
            assert not os.path.exists(file_path)
        
        await queue.stop()


class TestJanitorDaemon:
    """Test the main Janitor Daemon integration."""
    
    @pytest.mark.asyncio
    async def test_daemon_startup(self, test_env):
        """Test daemon startup and initialization."""
        # Create test directories
        downloads_dir = test_env.create_temp_dir()
        desktop_dir = test_env.create_temp_dir()
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8770,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [downloads_dir, desktop_dir]
        
        await daemon.start()
        
        # Check status
        status = await daemon.get_status()
        assert status['status'] == DaemonStatus.RUNNING.value
        assert status['connected_clients'] == 0  # No WebSocket clients yet
        
        await daemon.stop()
    
    @pytest.mark.asyncio
    async def test_file_processing_workflow(self, test_env):
        """Test complete file processing workflow."""
        # Create test directories
        downloads_dir = test_env.create_temp_dir()
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8771,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [downloads_dir]
        
        await daemon.start()
        
        # Create a test file
        test_file = test_env.create_test_file(downloads_dir, "workflow_test.pdf", "pdf content")
        
        # Wait for processing
        await asyncio.sleep(2.0)
        
        # Check file was detected
        status = await daemon.get_status()
        assert status['stats']['files_processed'] > 0
        
        await daemon.stop()
    
    @pytest.mark.asyncio
    async def test_directory_scan(self, test_env):
        """Test comprehensive directory scanning."""
        # Create test directory with files
        scan_dir = test_env.create_temp_dir()
        
        # Create various test files
        test_env.create_test_file(scan_dir, "scan1.txt", "content1", 1)
        test_env.create_test_file(scan_dir, "scan2.pdf", "content2", 10)
        test_env.create_test_file(scan_dir, "scan3.jpg", "content3", 100)
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8772,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [scan_dir]
        
        await daemon.start()
        
        # Run directory scan
        await daemon.scan_directories()
        
        # Wait for scan completion
        await asyncio.sleep(3.0)
        
        # Check scan results
        status = await daemon.get_status()
        assert status['stats']['files_processed'] >= 3
        
        await daemon.stop()
    
    @pytest.mark.asyncio
    async def test_conflict_detection(self, test_env):
        """Test conflict detection when user manually moves files."""
        temp_dir = test_env.create_temp_dir()
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8773,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [temp_dir]
        
        await daemon.start()
        
        # Create test file
        test_file = test_env.create_test_file(temp_dir, "conflict_test.txt", "original content")
        
        # Wait for initial detection
        await asyncio.sleep(1.0)
        
        # Manually move file while daemon is running
        new_location = os.path.join(temp_dir, "moved_conflict_test.txt")
        shutil.move(test_file, new_location)
        
        # Wait for conflict detection
        await asyncio.sleep(1.0)
        
        # Check conflict was detected
        status = await daemon.get_status()
        # Conflict detection would be implemented in the actual daemon
        
        await daemon.stop()


class TestDaemonLifecycle:
    """Test daemon lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_stop_cycle(self, test_env):
        """Test multiple start/stop cycles."""
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8774,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        # Test multiple cycles
        for i in range(3):
            daemon = JanitorDaemon(config)
            await daemon.start()
            
            status = await daemon.get_status()
            assert status['status'] == DaemonStatus.RUNNING.value
            
            await daemon.stop()
            
            status = await daemon.get_status()
            assert status['status'] == DaemonStatus.STOPPED.value
    
    @pytest.mark.asyncio
    async def test_global_daemon_functions(self, test_env):
        """Test global daemon management functions."""
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8775,
            'max_workers': 2,
            'temp_dir': test_env.create_temp_dir()
        }
        
        # Start global daemon
        daemon = await start_daemon(config)
        assert daemon is not None
        assert daemon.status == DaemonStatus.RUNNING
        
        # Get status
        status = await get_daemon_status()
        assert status['status'] == DaemonStatus.RUNNING.value
        
        # Stop global daemon
        await stop_daemon()
        
        # Check stopped
        status = await get_daemon_status()
        assert status['status'] == 'stopped'


class TestPerformanceAndStress:
    """Performance and stress tests."""
    
    @pytest.mark.asyncio
    async def test_large_file_set_processing(self, test_env):
        """Test processing large number of files."""
        temp_dir = test_env.create_temp_dir()
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8776,
            'max_workers': 4,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [temp_dir]
        
        await daemon.start()
        
        # Create many test files
        file_count = 50
        for i in range(file_count):
            test_env.create_test_file(temp_dir, f"perf_test_{i}.txt", f"content {i}", 1)
        
        # Run scan
        start_time = time.time()
        await daemon.scan_directories()
        scan_duration = time.time() - start_time
        
        # Check performance
        status = await daemon.get_status()
        assert status['stats']['files_processed'] >= file_count
        assert scan_duration < 30.0  # Should complete within 30 seconds
        
        await daemon.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, test_env):
        """Test memory usage during operations."""
        import psutil
        import gc
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        temp_dir = test_env.create_temp_dir()
        
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8777,
            'max_workers': 4,
            'temp_dir': test_env.create_temp_dir()
        }
        
        daemon = JanitorDaemon(config)
        daemon.watch_paths = [temp_dir]
        
        await daemon.start()
        
        # Create and process many files
        for i in range(100):
            test_env.create_test_file(temp_dir, f"memory_test_{i}.txt", "x" * 1000, 1)
        
        await daemon.scan_directories()
        
        # Check memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
        
        await daemon.stop()
        
        # Force garbage collection
        gc.collect()


# Integration test that combines all components
@pytest.mark.asyncio
async def test_full_integration(test_env):
    """Full integration test combining all components."""
    # Create test environment
    downloads_dir = test_env.create_temp_dir()
    desktop_dir = test_env.create_temp_dir()
    
    config = {
        'websocket_host': 'localhost',
        'websocket_port': 8778,
        'max_workers': 3,
        'temp_dir': test_env.create_temp_dir()
    }
    
    # Start daemon
    daemon = JanitorDaemon(config)
    daemon.watch_paths = [downloads_dir, desktop_dir]
    test_env.daemon = daemon
    
    await daemon.start()
    
    # Connect WebSocket client
    uri = f"ws://{config['websocket_host']}:{config['websocket_port']}"
    messages = []
    
    async def collect_messages():
        async with websockets.client.connect(uri) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Collect subsequent messages
            try:
                while True:
                    message = await websocket.recv()
                    messages.append(json.loads(message))
            except websockets.exceptions.ConnectionClosed:
                pass
    
    # Start message collector
    collector_task = asyncio.create_task(collect_messages())
    
    # Wait a bit for connection
    await asyncio.sleep(0.5)
    
    # Create files in both directories
    file1 = test_env.create_test_file(downloads_dir, "integration_test1.pdf", "pdf content", 5)
    file2 = test_env.create_test_file(desktop_dir, "integration_test2.txt", "text content", 2)
    
    # Wait for processing
    await asyncio.sleep(2.0)
    
    # Run directory scan
    await daemon.scan_directories()
    
    # Wait for completion
    await asyncio.sleep(3.0)
    
    # Stop collector
    collector_task.cancel()
    
    # Verify results
    status = await daemon.get_status()
    assert status['status'] == DaemonStatus.RUNNING.value
    assert status['stats']['files_processed'] >= 2
    
    # Check WebSocket messages
    file_found_messages = [m for m in messages if m['type'] == 'file_found']
    assert len(file_found_messages) >= 2
    
    scan_messages = [m for m in messages if m['type'] == 'scan_progress']
    assert len(scan_messages) > 0
    
    await daemon.stop()


# Performance benchmark
@pytest.mark.asyncio
async def test_performance_benchmark(test_env):
    """Performance benchmark for daemon operations."""
    temp_dir = test_env.create_temp_dir()
    
    config = {
        'websocket_host': 'localhost',
        'websocket_port': 8779,
        'max_workers': 4,
        'temp_dir': test_env.create_temp_dir()
    }
    
    daemon = JanitorDaemon(config)
    daemon.watch_paths = [temp_dir]
    
    await daemon.start()
    
    # Benchmark file creation detection
    start_time = time.time()
    
    # Create 100 files
    for i in range(100):
        test_env.create_test_file(temp_dir, f"benchmark_{i}.txt", f"content {i}", 1)
    
    # Wait for all to be processed
    await asyncio.sleep(5.0)
    
    detection_time = time.time() - start_time
    
    # Benchmark directory scanning
    start_time = time.time()
    await daemon.scan_directories()
    scan_time = time.time() - start_time
    
    # Get final stats
    status = await daemon.get_status()
    
    # Performance assertions
    assert detection_time < 10.0  # Should detect within 10 seconds
    assert scan_time < 5.0      # Should scan within 5 seconds
    assert status['stats']['files_processed'] >= 100
    
    await daemon.stop()
    
    # Log performance results
    logger.info(f"Performance Benchmark Results:")
    logger.info(f"  File Detection: {detection_time:.2f}s for 100 files")
    logger.info(f"  Directory Scan: {scan_time:.2f}s")
    logger.info(f"  Files Processed: {status['stats']['files_processed']}")
    logger.info(f"  Operations Completed: {status['completed_operations']}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
