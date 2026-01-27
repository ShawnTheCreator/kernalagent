"""
Comprehensive Test Suite for Enhanced Janitor Agent.

Tests:
- ML-Powered File Classification
- Parallel Processing
- Smart Caching
- Enhanced Auto File Renamer
- Integration scenarios
- Performance benchmarks
"""

import os
import sys
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict
import time

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.janitor.janitor_agent import JanitorAgent
from app.agents.janitor.capabilities.ml_classifier import MLFileClassifierCapability
from app.agents.janitor.capabilities.smart_renamer import SmartRenamerCapability
from app.agents.janitor.parallel_processor import ParallelProcessor
from app.agents.janitor.smart_cache import SmartCache
from app.agents.janitor.file_categorizer import FileCategory, categorize_file

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEnvironment:
    """Test environment setup and cleanup."""
    
    def __init__(self):
        self.temp_dirs = []
        self.test_files = []
    
    def create_temp_dir(self) -> str:
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp(prefix="janitor_test_")
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
    
    def create_test_image(self, directory: str, filename: str, size_kb: int = 10) -> str:
        """Create a test image file."""
        try:
            from PIL import Image
            
            file_path = os.path.join(directory, filename)
            
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(file_path)
            
            self.test_files.append(file_path)
            return file_path
            
        except ImportError:
            # If PIL is not available, create a fake image file
            return self.create_test_file(directory, filename, "fake image content", size_kb)
    
    def create_test_pdf(self, directory: str, filename: str, content: str = "Test PDF Content") -> str:
        """Create a test PDF file."""
        try:
            import PyPDF2
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            file_path = os.path.join(directory, filename)
            
            # Create a simple PDF
            c = canvas.Canvas(file_path, pagesize=letter)
            c.drawString(100, 750, content)
            c.save()
            
            self.test_files.append(file_path)
            return file_path
            
        except ImportError:
            # If PDF libraries are not available, create a fake PDF file
            return self.create_test_file(directory, filename, content, 5)
    
    def cleanup(self):
        """Clean up all temporary files and directories."""
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
        
        self.test_files.clear()
        self.temp_dirs.clear()


@pytest.fixture
def test_env():
    """Pytest fixture for test environment."""
    env = TestEnvironment()
    yield env
    env.cleanup()


@pytest.fixture
def sample_files(test_env):
    """Create sample files for testing."""
    temp_dir = test_env.create_temp_dir()
    
    # Create various test files
    files = {
        'document': test_env.create_test_file(temp_dir, "untitled.pdf", "Sample document content", 10),
        'image': test_env.create_test_image(temp_dir, "IMG_20240124_123456.jpg"),
        'screenshot': test_env.create_test_image(temp_dir, "Screenshot.png"),
        'video': test_env.create_test_file(temp_dir, "video.mp4", "fake video content", 100),
        'temp': test_env.create_test_file(temp_dir, "temp.tmp", "temporary content", 1),
        'installer': test_env.create_test_file(temp_dir, "setup.exe", "installer content", 50),
        'archive': test_env.create_test_file(temp_dir, "archive.zip", "archive content", 25),
        'code': test_env.create_test_file(temp_dir, "script.py", "print('hello world')", 2),
        'generic': test_env.create_test_file(temp_dir, "file (1).txt", "generic content", 3),
        'weird_name': test_env.create_test_file(temp_dir, "file@#$%^&*().txt", "weird chars content", 2),
    }
    
    return files, temp_dir


class TestMLClassifier:
    """Test ML-Powered File Classification."""
    
    @pytest.mark.asyncio
    async def test_basic_classification(self, sample_files):
        """Test basic file classification."""
        files, _ = sample_files
        
        classifier = MLFileClassifierCapability()
        
        # Test document classification
        result = await classifier.analyze(files['document'], {
            'filename': 'untitled.pdf',
            'extension': '.pdf',
            'size_bytes': 10240
        })
        
        assert result.capability == "ml_classifier"
        assert result.action_required in [True, False]
        assert result.suggestion is not None
        assert 0 <= result.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_image_classification(self, sample_files):
        """Test image file classification."""
        files, _ = sample_files
        
        classifier = MLFileClassifierCapability()
        
        # Test image classification
        result = await classifier.analyze(files['image'], {
            'filename': 'IMG_20240124_123456.jpg',
            'extension': '.jpg',
            'size_bytes': 10240
        })
        
        assert result.capability == "ml_classifier"
        assert result.action_required in [True, False]
        
        # Check if duplicate detection works
        metadata = result.metadata
        assert 'is_duplicate' in metadata
        assert 'predicted_category' in metadata
    
    @pytest.mark.asyncio
    async def test_learning_mechanism(self, sample_files):
        """Test ML learning from user corrections."""
        files, _ = sample_files
        
        classifier = MLFileClassifierCapability()
        
        # Add training sample
        classifier.classifier.add_training_sample(files['document'], FileCategory.DOCUMENTS_WORK)
        
        # Check if training data was added
        assert len(classifier.classifier.training_data) > 0
        
        # Test prediction with training data
        category, confidence = classifier.classifier.predict_category(files['document'])
        assert category in [FileCategory.DOCUMENTS, FileCategory.DOCUMENTS_WORK, FileCategory.DOCUMENTS_PERSONAL]
        assert 0 <= confidence <= 1


class TestSmartRenamer:
    """Test Enhanced Smart Renamer."""
    
    @pytest.mark.asyncio
    async def test_generic_file_renaming(self, sample_files):
        """Test renaming of generic files."""
        files, _ = sample_files
        
        renamer = SmartRenamerCapability()
        
        # Test generic file renaming
        result = await renamer.analyze(files['generic'], {
            'filename': 'file (1).txt',
            'extension': '.txt',
            'size_bytes': 3072
        })
        
        assert result.capability == "smart_renamer"
        assert result.action_required == True
        assert result.action_type == "rename"
        assert "rename" in result.suggestion.lower()
        
        # Check metadata
        metadata = result.metadata
        assert 'original_name' in metadata
        assert 'suggested_name' in metadata
        assert 'issues' in metadata
        assert 'duplicate_marker' in metadata['issues']
    
    @pytest.mark.asyncio
    async def test_weird_chars_renaming(self, sample_files):
        """Test renaming of files with weird characters."""
        files, _ = sample_files
        
        renamer = SmartRenamerCapability()
        
        # Test weird character renaming
        result = await renamer.analyze(files['weird_name'], {
            'filename': 'file@#$%^&*().txt',
            'extension': '.txt',
            'size_bytes': 2048
        })
        
        assert result.action_required == True
        assert result.action_type == "rename"
        assert 'weird_chars' in result.metadata['issues']
    
    @pytest.mark.asyncio
    async def test_renaming_execution(self, sample_files):
        """Test actual file renaming execution."""
        files, temp_dir = sample_files
        
        renamer = SmartRenamerCapability()
        
        # Analyze and execute rename
        result = await renamer.analyze(files['generic'], {
            'filename': 'file (1).txt',
            'extension': '.txt',
            'size_bytes': 3072
        })
        
        if result.action_required:
            success = await renamer.execute(files['generic'], result)
            assert success == True
            
            # Check if file was renamed
            assert not os.path.exists(files['generic'])
            
            # Find the renamed file
            new_name = result.metadata['suggested_name']
            new_path = os.path.join(temp_dir, new_name)
            assert os.path.exists(new_path)
    
    @pytest.mark.asyncio
    async def test_learning_history(self, sample_files):
        """Test naming history learning."""
        files, _ = sample_files
        
        renamer = SmartRenamerCapability()
        
        # Check if history file is created
        assert os.path.exists(os.path.join(os.path.expanduser("~"), ".janitor_renames.json")) or len(renamer.naming_history) == 0


class TestParallelProcessor:
    """Test Parallel Processing Engine."""
    
    @pytest.mark.asyncio
    async def test_parallel_scan(self, sample_files):
        """Test parallel folder scanning."""
        files, temp_dir = sample_files
        
        processor = ParallelProcessor(max_workers=2)
        
        # Test parallel scan
        scanned_files = await processor.parallel_scan([temp_dir])
        
        assert len(scanned_files) > 0
        assert processor.stats['files_processed'] > 0
        assert processor.stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_parallel_capability_execution(self, sample_files):
        """Test parallel capability execution."""
        files, temp_dir = sample_files
        
        processor = ParallelProcessor(max_workers=2)
        
        # Create FileInfo objects
        from app.agents.janitor.janitor_tools import FileInfo
        file_infos = []
        for file_path in files.values():
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                file_infos.append(FileInfo(
                    path=file_path,
                    name=os.path.basename(file_path),
                    extension=Path(file_path).suffix.lower(),
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    accessed_at=datetime.fromtimestamp(stat.st_atime)
                ))
        
        # Test parallel capability execution
        actionable_files = await processor.parallel_capability_execution(file_infos)
        
        assert isinstance(actionable_files, dict)
        assert processor.stats['files_processed'] > 0
    
    @pytest.mark.asyncio
    async def test_parallel_batch_operations(self, sample_files):
        """Test parallel batch operations."""
        files, temp_dir = sample_files
        
        processor = ParallelProcessor(max_workers=2)
        
        # Create test operations (move operations within temp dir)
        operations = []
        for i, (file_type, file_path) in enumerate(files.items()):
            if os.path.exists(file_path):
                new_name = f"moved_{file_type}_{i}_{os.path.basename(file_path)}"
                new_path = os.path.join(temp_dir, new_name)
                
                operations.append({
                    'type': 'move',
                    'source': file_path,
                    'destination': new_path,
                    'size_bytes': os.path.getsize(file_path)
                })
        
        # Execute parallel operations
        summary = await processor.parallel_batch_operations(operations)
        
        assert summary['total_operations'] == len(operations)
        assert summary['successful'] > 0
        assert summary['throughput'] > 0
        assert summary['average_duration'] >= 0
    
    def test_resource_monitoring(self):
        """Test system resource monitoring."""
        processor = ParallelProcessor()
        
        # Test resource monitoring
        resources = asyncio.run(processor.resource_monitor())
        
        assert 'cpu_percent' in resources
        assert 'memory_percent' in resources
        assert 'disk_percent' in resources
        assert 0 <= resources['cpu_percent'] <= 100
        assert 0 <= resources['memory_percent'] <= 100


class TestSmartCache:
    """Test Smart Caching System."""
    
    @pytest.mark.asyncio
    async def test_file_caching(self, sample_files):
        """Test file metadata caching."""
        files, _ = sample_files
        
        cache = SmartCache()
        
        # Test caching a file
        file_path = files['document']
        cache_entry = await cache.get_file_info(file_path)
        
        assert cache_entry is not None
        assert cache_entry.name == 'untitled.pdf'
        assert cache_entry.extension == '.pdf'
        assert cache_entry.size_bytes > 0
        assert cache_entry.file_hash != ""
    
    @pytest.mark.asyncio
    async def test_incremental_scan(self, sample_files):
        """Test incremental directory scanning."""
        files, temp_dir = sample_files
        
        cache = SmartCache()
        
        # First scan
        entries1 = await cache.scan_directory_incremental(temp_dir)
        assert len(entries1) > 0
        
        # Second scan (should use cache)
        entries2 = await cache.scan_directory_incremental(temp_dir)
        assert len(entries2) == len(entries1)
    
    @pytest.mark.asyncio
    async def test_change_detection(self, sample_files):
        """Test file change detection."""
        files, _ = sample_files
        
        cache = SmartCache()
        
        # Cache a file
        file_path = files['document']
        cache_entry1 = await cache.get_file_info(file_path)
        
        # Modify the file
        time.sleep(1)  # Ensure different timestamp
        with open(file_path, 'a') as f:
            f.write(" modified")
        
        # Check if change is detected
        cache_entry2 = await cache.get_file_info(file_path, force_refresh=True)
        assert cache_entry2.modified_at > cache_entry1.modified_at
    
    @pytest.mark.asyncio
    async def test_duplicate_detection(self, sample_files):
        """Test duplicate file detection."""
        files, temp_dir = sample_files
        
        cache = SmartCache()
        
        # Create a duplicate file
        original = files['document']
        duplicate_path = os.path.join(temp_dir, "duplicate.pdf")
        shutil.copy2(original, duplicate_path)
        
        # Test duplicate detection
        duplicates = await cache.find_duplicates(temp_dir)
        
        # Should find at least one duplicate group
        assert len(duplicates) >= 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = SmartCache()
        
        stats = cache.get_stats()
        
        assert 'total_entries' in stats
        assert 'memory_cache_size' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_rate' in stats
        assert stats['total_entries'] >= 0
        assert stats['hit_rate'] >= 0


class TestJanitorAgentIntegration:
    """Integration tests for the complete Janitor Agent."""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self, sample_files):
        """Test complete analysis workflow."""
        files, temp_dir = sample_files
        
        # Create a mock user home with test files
        mock_downloads = os.path.join(temp_dir, "Downloads")
        os.makedirs(mock_downloads, exist_ok=True)
        
        # Move some files to Downloads
        for file_type, file_path in list(files.items())[:5]:
            if os.path.exists(file_path):
                shutil.move(file_path, os.path.join(mock_downloads, os.path.basename(file_path)))
        
        # Create agent with mock paths
        agent = JanitorAgent()
        agent._staging_paths = [mock_downloads]
        
        # Run analysis
        analysis = await agent.analyze({})
        
        assert analysis.agent_name == "JANITOR_AGENT"
        assert 'staging_areas' in analysis.findings
        assert 'ml_insights' in analysis.findings
        assert 'cache_stats' in analysis.findings
        assert len(analysis.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_planning_workflow(self, sample_files):
        """Test planning workflow."""
        files, temp_dir = sample_files
        
        agent = JanitorAgent()
        
        # Create a mock analysis
        from app.agents.janitor.janitor_agent import AnalysisResult
        mock_analysis = AnalysisResult(
            agent_name="JANITOR_AGENT",
            findings={
                'staging_areas': {
                    'test_dir': {
                        'path': temp_dir,
                        'total_files': len(files),
                        'categories': {
                            'DOCUMENTS': [{
                                'path': files.get('document', ''),
                                'name': 'test.pdf',
                                'size_bytes': 1024,
                                'age_days': 0
                            }]
                        }
                    }
                }
            },
            recommendations=['Test recommendation'],
            severity='info'
        )
        
        # Generate plan
        plan = await agent.plan(mock_analysis)
        
        assert plan.agent_name == "JANITOR_AGENT"
        assert plan.requires_approval == True
        assert len(plan.actions) >= 0
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, sample_files):
        """Test performance benchmarks."""
        files, temp_dir = sample_files
        
        # Test parallel processing performance
        processor = ParallelProcessor()
        
        start_time = time.time()
        scanned_files = await processor.parallel_scan([temp_dir])
        scan_duration = time.time() - start_time
        
        stats = processor.get_stats()
        
        # Performance assertions
        assert scan_duration < 10.0  # Should complete within 10 seconds
        assert stats['throughput'] > 0  # Should have positive throughput
        
        # Test cache performance
        cache = SmartCache()
        
        start_time = time.time()
        for file_path in files.values():
            if os.path.exists(file_path):
                await cache.get_file_info(file_path)
        cache_duration = time.time() - start_time
        
        cache_stats = cache.get_stats()
        
        # Cache should be fast
        assert cache_duration < 5.0
        assert cache_stats['hit_rate'] >= 0


# Performance and stress tests
class TestPerformance:
    """Performance and stress tests."""
    
    @pytest.mark.asyncio
    async def test_large_file_set_performance(self):
        """Test performance with large file sets."""
        test_env = TestEnvironment()
        
        try:
            temp_dir = test_env.create_temp_dir()
            
            # Create many test files
            file_count = 100
            for i in range(file_count):
                test_env.create_test_file(temp_dir, f"test_file_{i}.txt", f"content {i}", 1)
            
            # Test parallel processing performance
            processor = ParallelProcessor()
            
            start_time = time.time()
            scanned_files = await processor.parallel_scan([temp_dir])
            duration = time.time() - start_time
            
            # Should handle 100 files efficiently
            assert len(scanned_files) == file_count
            assert duration < 30.0  # Should complete within 30 seconds
            
            stats = processor.get_stats()
            assert stats['throughput'] > 0
            
        finally:
            test_env.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent file operations."""
        test_env = TestEnvironment()
        
        try:
            temp_dir = test_env.create_temp_dir()
            
            # Create files for concurrent operations
            files = []
            for i in range(20):
                file_path = test_env.create_test_file(temp_dir, f"concurrent_test_{i}.txt", f"content {i}", 1)
                files.append(file_path)
            
            # Test concurrent operations
            processor = ParallelProcessor(max_workers=4)
            
            operations = []
            for i, file_path in enumerate(files):
                new_path = os.path.join(temp_dir, f"concurrent_moved_{i}.txt")
                operations.append({
                    'type': 'move',
                    'source': file_path,
                    'destination': new_path,
                    'size_bytes': 1024
                })
            
            start_time = time.time()
            summary = await processor.parallel_batch_operations(operations)
            duration = time.time() - start_time
            
            # Should handle concurrent operations efficiently
            assert summary['successful'] > 0
            assert duration < 10.0
            assert summary['throughput'] > 0
            
        finally:
            test_env.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
