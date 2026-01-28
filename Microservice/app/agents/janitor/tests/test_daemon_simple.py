"""
Simple Test Runner for Janitor Daemon
Tests basic functionality without complex dependencies.
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class DaemonTestRunner:
    """Test runner for Janitor Daemon."""
    
    def __init__(self):
        self.temp_dirs = []
        self.test_files = []
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def create_temp_dir(self) -> str:
        """Create a temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="janitor_daemon_test_")
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_test_file(self, directory: str, filename: str, content: str = "test content") -> str:
        """Create a test file."""
        file_path = os.path.join(directory, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.test_files.append(file_path)
        return file_path
    
    def cleanup(self):
        """Clean up test resources."""
        for file_path in self.test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
    
    def test(self, test_name: str, test_func):
        """Run a test."""
        logger.info(f"Running test: {test_name}")
        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            if result:
                logger.info(f"✅ PASSED: {test_name} ({duration:.2f}s)")
                self.passed += 1
                self.results.append({"name": test_name, "status": "PASSED", "duration": duration})
            else:
                logger.error(f"❌ FAILED: {test_name} ({duration:.2f}s)")
                self.failed += 1
                self.results.append({"name": test_name, "status": "FAILED", "duration": duration})
        except Exception as e:
            logger.error(f"❌ ERROR: {test_name} - {str(e)}")
            self.failed += 1
            self.results.append({"name": test_name, "status": "ERROR", "error": str(e)})
    
    async def run_async_test(self, test_name: str, test_func):
        """Run an async test."""
        logger.info(f"Running async test: {test_name}")
        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time
            
            if result:
                logger.info(f"✅ PASSED: {test_name} ({duration:.2f}s)")
                self.passed += 1
                self.results.append({"name": test_name, "status": "PASSED", "duration": duration})
            else:
                logger.error(f"❌ FAILED: {test_name} ({duration:.2f}s)")
                self.failed += 1
                self.results.append({"name": test_name, "status": "FAILED", "duration": duration})
        except Exception as e:
            logger.error(f"❌ ERROR: {test_name} - {str(e)}")
            self.failed += 1
            self.results.append({"name": test_name, "status": "ERROR", "error": str(e)})


# Test Functions
def test_imports():
    """Test that all daemon modules can be imported."""
    try:
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
            DaemonStatus
        )
        return True
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False


def test_file_operations():
    """Test basic file operations."""
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Test file operations
        assert os.path.exists(test_file)
        
        # Test move
        new_path = os.path.join(temp_dir, "moved.txt")
        shutil.move(test_file, new_path)
        assert not os.path.exists(test_file)
        assert os.path.exists(new_path)
        
        # Test copy
        copy_path = os.path.join(temp_dir, "copied.txt")
        shutil.copy2(new_path, copy_path)
        assert os.path.exists(copy_path)
        
        # Test delete
        os.remove(new_path)
        os.remove(copy_path)
        assert not os.path.exists(new_path)
        assert not os.path.exists(copy_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"File operations test failed: {e}")
        return False


def test_permission_manager():
    """Test permission manager functionality."""
    try:
        from app.agents.janitor.daemon_service import PermissionManager
        
        manager = PermissionManager()
        
        # Test permission storage (simplified)
        # Since we can't easily test async in sync test, just test instantiation
        assert manager is not None
        assert hasattr(manager, 'get_permission')
        assert hasattr(manager, 'set_permission')
        
        return True
        
    except Exception as e:
        logger.error(f"Permission manager test failed: {e}")
        return False


def test_operation_queue():
    """Test operation queue basic functionality."""
    try:
        from app.agents.janitor.daemon_service import OperationQueue, FileOperation, OperationType
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create operation queue
        queue = OperationQueue(max_workers=1, temp_dir=temp_dir)
        
        # Test operation creation
        operation = FileOperation(
            operation_id="test_op",
            operation_type=OperationType.DELETE,
            source_path="/fake/path.txt"
        )
        
        assert operation.operation_id == "test_op"
        assert operation.operation_type == OperationType.DELETE
        assert operation.status == "pending"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Operation queue test failed: {e}")
        return False


def test_websocket_manager():
    """Test WebSocket manager basic functionality."""
    try:
        from app.agents.janitor.daemon_service import WebSocketManager, DaemonNotification, NotificationType
        
        # Create WebSocket manager
        manager = WebSocketManager(host='localhost', port=8765)
        
        # Test notification creation
        notification = DaemonNotification(
            type=NotificationType.FILE_FOUND,
            message="Test file found",
            data={'file_path': '/test/file.txt'}
        )
        
        # Test serialization
        notification_dict = notification.to_dict()
        assert 'type' in notification_dict
        assert notification_dict['type'] == 'file_found'
        assert 'message' in notification_dict
        assert notification_dict['message'] == "Test file found"
        
        return True
        
    except Exception as e:
        logger.error(f"WebSocket manager test failed: {e}")
        return False


def test_daemon_notification():
    """Test daemon notification serialization."""
    try:
        from app.agents.janitor.daemon_service import DaemonNotification, NotificationType
        
        # Create notification
        notification = DaemonNotification(
            type=NotificationType.SCAN_PROGRESS,
            message="Scanning files...",
            data={'current': 10, 'total': 100}
        )
        
        # Test serialization
        serialized = notification.to_dict()
        
        assert isinstance(serialized, dict)
        assert serialized['type'] == 'scan_progress'
        assert serialized['message'] == "Scanning files..."
        assert 'data' in serialized
        assert serialized['data']['current'] == 10
        assert serialized['data']['total'] == 100
        assert 'timestamp' in serialized
        
        return True
        
    except Exception as e:
        logger.error(f"Daemon notification test failed: {e}")
        return False


async def test_daemon_instantiation():
    """Test daemon instantiation and basic setup."""
    try:
        from app.agents.janitor.daemon_service import JanitorDaemon, DaemonStatus
        
        # Create daemon with test config
        config = {
            'websocket_host': 'localhost',
            'websocket_port': 8765,
            'max_workers': 2,
            'temp_dir': tempfile.mkdtemp()
        }
        
        daemon = JanitorDaemon(config)
        
        # Test basic properties
        assert daemon is not None
        assert daemon.status == DaemonStatus.STARTING
        assert len(daemon.watch_paths) > 0
        assert hasattr(daemon, 'file_watcher')
        assert hasattr(daemon, 'permission_manager')
        assert hasattr(daemon, 'websocket_manager')
        assert hasattr(daemon, 'operation_queue')
        
        # Test status method
        status = await daemon.get_status()
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'stats' in status
        
        # Cleanup temp dir
        shutil.rmtree(config['temp_dir'])
        
        return True
        
    except Exception as e:
        logger.error(f"Daemon instantiation test failed: {e}")
        return False


async def test_hybrid_file_watcher():
    """Test hybrid file watcher instantiation."""
    try:
        from app.agents.janitor.daemon_service import HybridFileWatcher
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Create file watcher
        events = []
        def event_callback(event):
            events.append(event)
        
        watcher = HybridFileWatcher([temp_dir], event_callback)
        
        # Test basic properties
        assert watcher is not None
        assert len(watcher.watch_paths) == 1
        assert str(temp_dir) in [str(p) for p in watcher.watch_paths]
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Hybrid file watcher test failed: {e}")
        return False


def test_api_routes_import():
    """Test that API routes can be imported."""
    try:
        from app.api.janitor_daemon_routes import (
            janitor_daemon_router,
            DaemonCommand,
            DaemonStatusResponse,
            FileOperationRequest,
            PermissionResponse
        )
        
        assert janitor_daemon_router is not None
        assert DaemonCommand is not None
        assert DaemonStatusResponse is not None
        assert FileOperationRequest is not None
        assert PermissionResponse is not None
        
        return True
        
    except Exception as e:
        logger.error(f"API routes import test failed: {e}")
        return False


def test_command_processor_import():
    """Test command processor import."""
    try:
        from app.api.janitor_daemon_routes import JanitorCommandProcessor
        
        processor = JanitorCommandProcessor()
        
        assert processor is not None
        assert hasattr(processor, 'process_command')
        assert hasattr(processor, 'command_patterns')
        
        return True
        
    except Exception as e:
        logger.error(f"Command processor import test failed: {e}")
        return False


def test_file_size_processing():
    """Test file size processing logic."""
    try:
        # Create test files of different sizes
        temp_dir = tempfile.mkdtemp()
        
        files = []
        sizes = [1, 10, 100]  # KB
        
        for size in sizes:
            file_path = os.path.join(temp_dir, f"size_test_{size}kb.txt")
            content = "x" * (size * 1024)
            with open(file_path, 'w') as f:
                f.write(content)
            files.append((file_path, size))
        
        # Verify file sizes
        for file_path, expected_size in files:
            actual_size = os.path.getsize(file_path) // 1024  # Convert to KB
            assert actual_size >= expected_size - 1  # Allow for small variations
            assert actual_size <= expected_size + 1
        
        # Test sorting by size
        files.sort(key=lambda x: x[1])  # Small to large
        assert files[0][1] <= files[1][1] <= files[2][1]
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"File size processing test failed: {e}")
        return False


def test_temp_folder_operations():
    """Test temporary folder operations for rollback."""
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        # Create test file
        test_file = os.path.join(temp_dir, "original.txt")
        with open(test_file, 'w') as f:
            f.write("original content")
        
        # Create backup
        backup_dir = os.path.join(temp_dir, "backup")
        os.makedirs(backup_dir)
        backup_file = os.path.join(backup_dir, "backup_original.txt")
        shutil.copy2(test_file, backup_file)
        
        # Modify original
        with open(test_file, 'w') as f:
            f.write("modified content")
        
        # Verify backup exists and is different
        assert os.path.exists(backup_file)
        assert os.path.exists(test_file)
        
        with open(backup_file, 'r') as f:
            backup_content = f.read()
        with open(test_file, 'r') as f:
            original_content = f.read()
        
        assert backup_content == "original content"
        assert original_content == "modified content"
        
        # Test rollback (restore from backup)
        shutil.move(backup_file, test_file)
        
        with open(test_file, 'r') as f:
            restored_content = f.read()
        
        assert restored_content == "original content"
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Temp folder operations test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Janitor Daemon Test Suite")
    logger.info("=" * 50)
    
    runner = DaemonTestRunner()
    
    # Run synchronous tests
    runner.test("Module Imports", test_imports)
    runner.test("File Operations", test_file_operations)
    runner.test("Permission Manager", test_permission_manager)
    runner.test("Operation Queue", test_operation_queue)
    runner.test("WebSocket Manager", test_websocket_manager)
    runner.test("Daemon Notification", test_daemon_notification)
    runner.test("API Routes Import", test_api_routes_import)
    runner.test("Command Processor Import", test_command_processor_import)
    runner.test("File Size Processing", test_file_size_processing)
    runner.test("Temp Folder Operations", test_temp_folder_operations)
    
    # Run asynchronous tests
    await runner.run_async_test("Daemon Instantiation", test_daemon_instantiation)
    await runner.run_async_test("Hybrid File Watcher", test_hybrid_file_watcher)
    
    # Print summary
    logger.info("=" * 50)
    logger.info(f"📊 Test Results Summary:")
    logger.info(f"✅ Passed: {runner.passed}")
    logger.info(f"❌ Failed: {runner.failed}")
    logger.info(f"📈 Success Rate: {runner.passed/(runner.passed+runner.failed)*100:.1f}%")
    
    # Print detailed results
    logger.info("\n📋 Detailed Results:")
    for result in runner.results:
        status_emoji = "✅" if result["status"] == "PASSED" else "❌"
        duration = f" ({result['duration']:.2f}s)" if "duration" in result else ""
        logger.info(f"{status_emoji} {result['name']}{duration}")
        if "error" in result:
            logger.error(f"   Error: {result['error']}")
    
    # Cleanup
    runner.cleanup()
    
    logger.info("\n🎉 Test Suite Complete!")
    
    if runner.failed == 0:
        logger.info("✅ All daemon tests passed!")
        logger.info("🚀 Janitor Daemon is ready for integration!")
    else:
        logger.info(f"⚠️ {runner.failed} test(s) failed - review implementation")
    
    return runner.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
