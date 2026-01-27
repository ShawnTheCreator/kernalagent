"""
Simple Test Runner for Enhanced Janitor Agent.
Runs basic functionality tests without pytest dependency.
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Simple test runner for enhanced janitor functionality."""
    
    def __init__(self):
        self.temp_dirs = []
        self.test_files = []
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def create_temp_dir(self) -> str:
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="janitor_test_")
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
        """Run a single test."""
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
    """Test that all modules can be imported."""
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        from app.agents.janitor.capabilities.ml_classifier import MLFileClassifierCapability
        from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability
        from app.agents.janitor.parallel_processor import ParallelProcessor
        from app.agents.janitor.smart_cache import SmartCache
        from app.agents.janitor.file_categorizer import FileCategory, categorize_file
        return True
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False


async def test_ml_classifier():
    """Test ML Classifier functionality."""
    try:
        from app.agents.janitor.capabilities.ml_classifier import MLFileClassifierCapability
        
        classifier = MLFileClassifierCapability()
        
        # Test basic analysis
        result = await classifier.analyze("test.pdf", {
            'filename': 'test.pdf',
            'extension': '.pdf',
            'size_bytes': 1024
        })
        
        return result.capability == "ml_classifier" and result.suggestion is not None
    except Exception as e:
        logger.error(f"ML Classifier test error: {e}")
        return False


async def test_smart_renamer():
    """Test Smart Renamer functionality."""
    try:
        from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability
        
        renamer = SmartRenamerCapability()
        
        # Test generic file analysis
        result = await renamer.analyze("file (1).txt", {
            'filename': 'file (1).txt',
            'extension': '.txt',
            'size_bytes': 1024
        })
        
        return result.capability == "smart_renamer" and result.action_required == True
    except Exception as e:
        logger.error(f"Smart Renamer test error: {e}")
        return False


async def test_parallel_processor():
    """Test Parallel Processor functionality."""
    try:
        from app.agents.janitor.parallel_processor import ParallelProcessor
        
        processor = ParallelProcessor(max_workers=2)
        
        # Test resource monitoring
        resources = await processor.resource_monitor()
        
        return ('cpu_percent' in resources and 
                'memory_percent' in resources and 
                'disk_percent' in resources)
    except Exception as e:
        logger.error(f"Parallel Processor test error: {e}")
        return False


def test_smart_cache():
    """Test Smart Cache functionality."""
    try:
        from app.agents.janitor.smart_cache import SmartCache
        
        cache = SmartCache()
        
        # Test cache stats
        stats = cache.get_stats()
        
        return ('total_entries' in stats and 
                'memory_cache_size' in stats and 
                'hit_rate' in stats)
    except Exception as e:
        logger.error(f"Smart Cache test error: {e}")
        return False


def test_file_categorizer():
    """Test File Categorizer functionality."""
    try:
        from app.agents.janitor.file_categorizer import categorize_file, FileCategory
        
        # Test categorization
        category = categorize_file("test.pdf")
        
        return isinstance(category, FileCategory) and category == FileCategory.DOCUMENTS
    except Exception as e:
        logger.error(f"File Categorizer test error: {e}")
        return False


async def test_janitor_agent():
    """Test Janitor Agent integration."""
    try:
        from app.agents.janitor.janitor_agent import JanitorAgent
        
        agent = JanitorAgent()
        
        # Test agent initialization
        return (agent.name == "JANITOR_AGENT" and 
                hasattr(agent, '_parallel_processor') and
                hasattr(agent, '_smart_cache') and
                hasattr(agent, '_ml_classifier') and
                hasattr(agent, '_smart_renamer'))
    except Exception as e:
        logger.error(f"Janitor Agent test error: {e}")
        return False


async def test_file_operations():
    """Test actual file operations with temporary files."""
    try:
        from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability
        
        # Create temporary directory and file
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test_file (1).txt")
        
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Test renamer on actual file
        renamer = SmartRenamerCapability()
        result = await renamer.analyze(test_file, {
            'filename': 'test_file (1).txt',
            'extension': '.txt',
            'size_bytes': 12
        })
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return result.action_required == True and result.action_type == "rename"
    except Exception as e:
        logger.error(f"File Operations test error: {e}")
        return False


def test_performance():
    """Test basic performance metrics."""
    try:
        from app.agents.janitor.parallel_processor import ParallelProcessor
        
        processor = ParallelProcessor()
        
        # Test stats
        stats = processor.get_stats()
        
        return ('max_workers' in stats and 
                'files_processed' in stats and
                'throughput' in stats)
    except Exception as e:
        logger.error(f"Performance test error: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("🧹 Starting Enhanced Janitor Agent Test Suite")
    logger.info("=" * 50)
    
    runner = TestRunner()
    
    # Run synchronous tests
    runner.test("Module Imports", test_imports)
    runner.test("File Categorizer", test_file_categorizer)
    runner.test("Smart Cache", test_smart_cache)
    runner.test("Performance Metrics", test_performance)
    
    # Run asynchronous tests
    await runner.run_async_test("ML Classifier", test_ml_classifier)
    await runner.run_async_test("Smart Renamer", test_smart_renamer)
    await runner.run_async_test("Parallel Processor", test_parallel_processor)
    await runner.run_async_test("Janitor Agent Integration", test_janitor_agent)
    await runner.run_async_test("File Operations", test_file_operations)
    
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
    
    return runner.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
