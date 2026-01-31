"""
Tests for Gemini 3 upgrade components.
Validates model router, thinking planner, structured outputs, and rate limiting.
"""
import pytest
from app.core.model_router import (
    ModelRouter, 
    TaskType, 
    TaskComplexity, 
    get_model_router
)
from app.core.smart_rate_limiter import SmartRateLimiter, get_rate_limiter
from app.vision.frame_differ import FrameDiffer
from PIL import Image
import numpy as np


class TestModelRouter:
    """Test intelligent model routing."""
    
    def test_router_initialization(self):
        """Test model router initializes correctly."""
        router = ModelRouter()
        
        assert router.THINKING == "gemini-2.0-flash-thinking-exp-01-21"
        assert router.FLASH == "gemini-2.0-flash-exp"
        assert router.LEGACY == "gemini-1.5-flash-002"
    
    def test_simple_task_routing(self):
        """Test routing for simple tasks."""
        router = ModelRouter()
        decision = router.route(TaskType.PLANNING, TaskComplexity.SIMPLE)
        
        assert decision.model_id == router.FLASH
        assert decision.temperature == 0.1
        assert decision.use_thinking is False
        assert decision.use_structured_output is True
    
    def test_complex_task_routing(self):
        """Test routing for complex tasks."""
        router = ModelRouter()
        decision = router.route(TaskType.PLANNING, TaskComplexity.VERY_COMPLEX)
        
        # Should use thinking model for complex tasks
        assert decision.model_id == router.THINKING
        assert decision.temperature == 0.3
        assert decision.use_thinking is True
        assert decision.max_tokens == 2048
    
    def test_vision_task_routing(self):
        """Test routing for vision tasks."""
        router = ModelRouter()
        decision = router.route(TaskType.VISION, TaskComplexity.SIMPLE)
        
        assert decision.model_id == router.FLASH
        assert decision.temperature == 0.2
        assert "vision" in decision.reasoning.lower()
    
    def test_recovery_task_routing(self):
        """Test routing for recovery tasks."""
        router = ModelRouter()
        decision = router.route(TaskType.RECOVERY, TaskComplexity.MEDIUM)
        
        # Recovery should use thinking mode
        assert decision.model_id == router.THINKING
        assert decision.use_thinking is True
        assert decision.temperature == 0.4
    
    def test_chat_task_routing(self):
        """Test routing for chat tasks."""
        router = ModelRouter()
        decision = router.route(TaskType.CHAT, TaskComplexity.SIMPLE)
        
        assert decision.model_id == router.FLASH
        assert decision.temperature == 0.7  # Higher for natural conversation
        assert decision.use_structured_output is False  # Chat doesn't need JSON
    
    def test_complexity_estimation_simple(self):
        """Test complexity estimation for simple commands."""
        router = ModelRouter()
        
        simple_intents = [
            "open notepad",
            "type hello",
            "click the button"
        ]
        
        for intent in simple_intents:
            complexity = router.estimate_complexity(intent)
            assert complexity == TaskComplexity.SIMPLE
    
    def test_complexity_estimation_medium(self):
        """Test complexity estimation for medium commands."""
        router = ModelRouter()
        
        medium_intents = [
            "open notepad and type hello",
            "go to google then search for cats"
        ]
        
        for intent in medium_intents:
            complexity = router.estimate_complexity(intent)
            assert complexity in [TaskComplexity.MEDIUM, TaskComplexity.SIMPLE]
    
    def test_complexity_estimation_complex(self):
        """Test complexity estimation for complex commands."""
        router = ModelRouter()
        
        complex_intents = [
            "open notepad and type hello then save as test.txt and close it",
            "open chrome and go to github then slack and discord",
            "if the window shows error then retry the operation",
            "download the file and if it fails then try again"
        ]
        
        for intent in complex_intents:
            complexity = router.estimate_complexity(intent)
            assert complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX, TaskComplexity.MEDIUM]
    
    def test_singleton_pattern(self):
        """Test that get_model_router returns same instance."""
        router1 = get_model_router()
        router2 = get_model_router()
        
        assert router1 is router2


class TestSmartRateLimiter:
    """Test smart rate limiting."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with correct limits."""
        limiter = SmartRateLimiter()
        
        assert limiter.limits["free"] == 10
        assert limiter.limits["pro"] == 50
        assert limiter.limits["enterprise"] == 200
    
    @pytest.mark.asyncio
    async def test_free_tier_limit(self):
        """Test free tier rate limiting."""
        limiter = SmartRateLimiter()
        
        # Should allow 10 requests
        for i in range(10):
            allowed = await limiter.acquire("test_user", "free")
            assert allowed is True
        
        # 11th request should be blocked
        allowed = await limiter.acquire("test_user", "free")
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_pro_tier_higher_limit(self):
        """Test pro tier has higher limit."""
        limiter = SmartRateLimiter()
        
        # Pro tier should allow more requests
        for i in range(50):
            allowed = await limiter.acquire("pro_user", "pro")
            assert allowed is True
        
        # 51st should be blocked
        allowed = await limiter.acquire("pro_user", "pro")
        assert allowed is False
    
    def test_429_cooldown(self):
        """Test that 429 error triggers cooldown."""
        limiter = SmartRateLimiter()
        
        limiter.report_429(retry_after=5)
        
        assert limiter.global_cooldown_until > 0
        assert limiter.consecutive_429s == 1
        assert limiter.cooldowns_triggered == 1
    
    def test_success_resets_429_counter(self):
        """Test that successful request resets 429 counter."""
        limiter = SmartRateLimiter()
        
        limiter.report_429()
        assert limiter.consecutive_429s == 1
        
        limiter.report_success()
        assert limiter.consecutive_429s == 0
    
    def test_get_user_stats(self):
        """Test retrieving user statistics."""
        limiter = SmartRateLimiter()
        
        # Make some requests
        import asyncio
        asyncio.run(limiter.acquire("test_user", "free"))
        asyncio.run(limiter.acquire("test_user", "free"))
        
        stats = limiter.get_user_stats("test_user")
        
        assert stats is not None
        assert stats["user_id"] == "test_user"
        assert stats["tier"] == "free"
        assert stats["requests_used"] == 2
        assert stats["limit"] == 10
        assert stats["remaining"] == 8
    
    def test_get_global_stats(self):
        """Test retrieving global statistics."""
        limiter = SmartRateLimiter()
        
        stats = limiter.get_global_stats()
        
        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "block_rate" in stats
        assert "global_cooldown_remaining" in stats


class TestFrameDiffer:
    """Test frame diffing for UI change detection."""
    
    def test_frame_differ_initialization(self):
        """Test frame differ initializes correctly."""
        differ = FrameDiffer()
        
        assert differ.stability_threshold == 0.95
        assert differ.frame_count == 0
        assert differ.previous_hash is None
    
    def test_first_frame_is_significant(self):
        """Test that first frame is always considered significant."""
        differ = FrameDiffer()
        
        # Create test image
        image = Image.new('RGB', (100, 100), color='white')
        
        is_significant, similarity = differ.is_significant_change(image)
        
        assert is_significant is True
        assert differ.frame_count == 1
    
    def test_identical_frames_not_significant(self):
        """Test that identical frames are not significant."""
        differ = FrameDiffer()
        
        # Create identical images
        image1 = Image.new('RGB', (100, 100), color='white')
        image2 = Image.new('RGB', (100, 100), color='white')
        
        differ.is_significant_change(image1)
        is_significant, similarity = differ.is_significant_change(image2)
        
        assert is_significant is False
        assert similarity == 1.0  # Identical
    
    def test_different_frames_are_significant(self):
        """Test that different frames are significant."""
        differ = FrameDiffer()
        
        # Create different images
        image1 = Image.new('RGB', (100, 100), color='white')
        image2 = Image.new('RGB', (100, 100), color='black')
        
        differ.is_significant_change(image1)
        is_significant, similarity = differ.is_significant_change(image2)
        
        assert is_significant is True
        assert similarity < 0.5  # Very different
    
    def test_perceptual_hash(self):
        """Test perceptual hashing."""
        differ = FrameDiffer()
        
        image1 = Image.new('RGB', (100, 100), color='white')
        image2 = Image.new('RGB', (100, 100), color='white')
        
        hash1 = differ._perceptual_hash(image1)
        hash2 = differ._perceptual_hash(image2)
        
        assert hash1 == hash2  # Same content = same hash
        assert len(hash1) == 32  # MD5 hex digest length
    
    def test_get_stats(self):
        """Test statistics tracking."""
        differ = FrameDiffer()
        
        image1 = Image.new('RGB', (100, 100), color='white')
        image2 = Image.new('RGB', (100, 100), color='white')
        image3 = Image.new('RGB', (100, 100), color='black')
        
        differ.is_significant_change(image1)
        differ.is_significant_change(image2)  # Stable
        differ.is_significant_change(image3)  # Changed
        
        stats = differ.get_stats()
        
        assert stats["total_frames"] == 3
        assert stats["stable_frames"] == 1
        assert stats["changed_frames"] == 2
        assert "skip_rate" in stats
        assert stats["api_calls_saved"] == 1
    
    def test_reset(self):
        """Test resetting frame differ state."""
        differ = FrameDiffer()
        
        image = Image.new('RGB', (100, 100), color='white')
        differ.is_significant_change(image)
        
        assert differ.previous_hash is not None
        
        differ.reset()
        
        assert differ.previous_hash is None
        assert differ.previous_pixels is None


class TestStructuredOutputs:
    """Test structured output capabilities."""
    
    def test_json_schema_format(self):
        """Test that JSON schema is properly formatted."""
        # This would test the actual schema used in thinking planner
        from app.reasoning.thinking_planner import ThinkingPlanner
        
        planner = ThinkingPlanner()
        schema = planner._get_workflow_schema()
        
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "steps" in schema["properties"]
        assert "confidence" in schema["properties"]
        assert schema["properties"]["confidence"]["type"] == "number"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
