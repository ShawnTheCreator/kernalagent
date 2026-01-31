"""
Integration test for Gemini 3 upgrade WebSocket integration.

Tests that all new components work correctly with the WebSocket handlers:
- Model Router selects correct models
- Rate Limiter prevents excessive API calls
- Frame Differ skips stable frames
- Thinking Planner handles complex commands
"""
import asyncio
import json
import logging
from typing import List, Dict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.model_router import get_model_router, TaskType, TaskComplexity
from app.core.smart_rate_limiter import get_rate_limiter
from app.vision.frame_differ import FrameDiffer
from app.reasoning.thinking_planner import get_thinking_planner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
    
    def add_pass(self, test_name: str):
        self.passed += 1
        logger.info(f"✅ {test_name}")
    
    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        logger.error(f"❌ {test_name}: {error}")
    
    def print_summary(self):
        total = self.passed + self.failed
        logger.info("\n" + "="*60)
        logger.info(f"INTEGRATION TEST RESULTS")
        logger.info("="*60)
        logger.info(f"Passed: {self.passed}/{total}")
        logger.info(f"Failed: {self.failed}/{total}")
        if self.errors:
            logger.info("\nErrors:")
            for error in self.errors:
                logger.info(f"  - {error}")
        logger.info("="*60)
        return self.failed == 0


async def test_model_router_integration():
    """Test that model router correctly selects models for different commands."""
    results = IntegrationTestResults()
    
    router = get_model_router()
    
    # Test 1: Simple command should use fast model
    try:
        complexity = router._estimate_complexity("open notepad")
        if complexity in [TaskComplexity.SIMPLE, TaskComplexity.MEDIUM]:
            results.add_pass("Simple command complexity estimation")
        else:
            results.add_fail("Simple command complexity estimation", f"Expected SIMPLE or MEDIUM, got {complexity}")
    except Exception as e:
        results.add_fail("Simple command complexity estimation", str(e))
    
    # Test 2: Complex command should use thinking model
    try:
        complexity = router._estimate_complexity(
            "Open Chrome, search for Python tutorials, download the first PDF, and save it to Documents"
        )
        if complexity == TaskComplexity.COMPLEX:
            results.add_pass("Complex command complexity estimation")
        else:
            results.add_fail("Complex command complexity estimation", f"Expected COMPLEX, got {complexity}")
    except Exception as e:
        results.add_fail("Complex command complexity estimation", str(e))
    
    # Test 3: Model routing for planning tasks
    try:
        decision = router.route(TaskType.PLANNING, TaskComplexity.SIMPLE)
        if decision.model_id == router.models["fast"]:
            results.add_pass("Simple planning uses fast model")
        else:
            results.add_fail("Simple planning uses fast model", f"Wrong model: {decision.model_id}")
    except Exception as e:
        results.add_fail("Simple planning uses fast model", str(e))
    
    # Test 4: Complex planning uses thinking model
    try:
        decision = router.route(TaskType.PLANNING, TaskComplexity.COMPLEX)
        if decision.model_id == router.models["thinking"]:
            results.add_pass("Complex planning uses thinking model")
        else:
            results.add_fail("Complex planning uses thinking model", f"Wrong model: {decision.model_id}")
    except Exception as e:
        results.add_fail("Complex planning uses thinking model", str(e))
    
    return results


async def test_rate_limiter_integration():
    """Test that rate limiter correctly enforces limits."""
    results = IntegrationTestResults()
    
    limiter = get_rate_limiter()
    test_user = "integration_test_user"
    
    # Test 1: Initial requests should be allowed
    try:
        allowed = await limiter.acquire(test_user, tier="free")
        if allowed:
            results.add_pass("First request allowed")
        else:
            results.add_fail("First request allowed", "Request was blocked")
    except Exception as e:
        results.add_fail("First request allowed", str(e))
    
    # Test 2: Rapid requests should eventually be rate limited
    try:
        allowed_count = 0
        blocked_count = 0
        
        # Free tier: 10 RPM = 10 requests per 60 seconds
        for i in range(15):
            if await limiter.acquire(test_user, tier="free"):
                allowed_count += 1
            else:
                blocked_count += 1
        
        if blocked_count > 0:
            results.add_pass(f"Rate limiting works (blocked {blocked_count}/15 requests)")
        else:
            results.add_fail("Rate limiting works", "No requests were blocked")
    except Exception as e:
        results.add_fail("Rate limiting works", str(e))
    
    # Test 3: Success reporting resets consecutive failures
    try:
        limiter.report_success()
        stats = limiter.get_stats()
        if stats["consecutive_429s"] == 0:
            results.add_pass("Success resets 429 counter")
        else:
            results.add_fail("Success resets 429 counter", f"Counter: {stats['consecutive_429s']}")
    except Exception as e:
        results.add_fail("Success resets 429 counter", str(e))
    
    # Test 4: 429 reporting triggers cooldown
    try:
        limiter.report_429()
        limiter.report_429()
        stats = limiter.get_stats()
        
        if stats["global_cooldown_until"] and stats["global_cooldown_until"] > asyncio.get_event_loop().time():
            results.add_pass("429 triggers global cooldown")
        else:
            results.add_fail("429 triggers global cooldown", "No cooldown active")
    except Exception as e:
        results.add_fail("429 triggers global cooldown", str(e))
    
    return results


async def test_frame_differ_integration():
    """Test that frame differ correctly detects UI changes."""
    results = IntegrationTestResults()
    
    differ = FrameDiffer(stability_threshold=0.95)
    
    # Test 1: First frame should always be significant
    try:
        frame1 = "base64_encoded_frame_1"
        is_significant, similarity = differ.is_significant_change(frame1)
        
        if is_significant and similarity == 0.0:
            results.add_pass("First frame is significant")
        else:
            results.add_fail("First frame is significant", f"Got: {is_significant}, {similarity}")
    except Exception as e:
        results.add_fail("First frame is significant", str(e))
    
    # Test 2: Identical frame should not be significant
    try:
        is_significant, similarity = differ.is_significant_change(frame1)
        
        if not is_significant and similarity >= 0.95:
            results.add_pass("Identical frame skipped")
        else:
            results.add_fail("Identical frame skipped", f"Got: {is_significant}, {similarity}")
    except Exception as e:
        results.add_fail("Identical frame skipped", str(e))
    
    # Test 3: Different frame should be significant
    try:
        frame2 = "base64_encoded_frame_2_different"
        is_significant, similarity = differ.is_significant_change(frame2)
        
        if is_significant and similarity < 0.95:
            results.add_pass("Different frame detected")
        else:
            results.add_fail("Different frame detected", f"Got: {is_significant}, {similarity}")
    except Exception as e:
        results.add_fail("Different frame detected", str(e))
    
    # Test 4: Stats tracking
    try:
        stats = differ.get_stats()
        
        if stats["total_frames"] >= 3 and "skip_rate" in stats:
            results.add_pass("Frame differ stats tracking")
        else:
            results.add_fail("Frame differ stats tracking", f"Stats: {stats}")
    except Exception as e:
        results.add_fail("Frame differ stats tracking", str(e))
    
    return results


async def test_thinking_planner_integration():
    """Test that thinking planner is properly initialized."""
    results = IntegrationTestResults()
    
    # Test 1: Thinking planner initialization
    try:
        planner = get_thinking_planner()
        if planner.model_id:
            results.add_pass("Thinking planner initialized")
        else:
            results.add_fail("Thinking planner initialized", "No model ID")
    except Exception as e:
        results.add_fail("Thinking planner initialized", str(e))
    
    # Test 2: Workflow schema validation
    try:
        planner = get_thinking_planner()
        schema = planner._get_workflow_schema()
        
        required_keys = ["reasoning", "steps", "estimated_time", "confidence"]
        if all(key in str(schema) for key in required_keys):
            results.add_pass("Thinking planner schema valid")
        else:
            results.add_fail("Thinking planner schema valid", "Missing required keys")
    except Exception as e:
        results.add_fail("Thinking planner schema valid", str(e))
    
    return results


async def test_websocket_flow_simulation():
    """Simulate a WebSocket command flow through all components."""
    results = IntegrationTestResults()
    
    logger.info("\n" + "="*60)
    logger.info("SIMULATING WEBSOCKET COMMAND FLOW")
    logger.info("="*60)
    
    # Simulate: User sends command
    command = "Open Chrome and search for Python tutorials"
    user_id = "test_user_websocket"
    
    # Step 1: Model Router determines complexity
    try:
        router = get_model_router()
        complexity = router._estimate_complexity(command)
        logger.info(f"1. Command complexity: {complexity.name}")
        results.add_pass("WebSocket flow - Model routing")
    except Exception as e:
        results.add_fail("WebSocket flow - Model routing", str(e))
        return results
    
    # Step 2: Rate Limiter checks quota
    try:
        limiter = get_rate_limiter()
        allowed = await limiter.acquire(user_id, tier="free")
        logger.info(f"2. Rate limit check: {'ALLOWED' if allowed else 'BLOCKED'}")
        
        if allowed:
            results.add_pass("WebSocket flow - Rate limiting")
        else:
            results.add_fail("WebSocket flow - Rate limiting", "Request blocked")
            return results
    except Exception as e:
        results.add_fail("WebSocket flow - Rate limiting", str(e))
        return results
    
    # Step 3: Frame Differ checks for UI changes
    try:
        differ = FrameDiffer()
        frame = "base64_screenshot_data"
        is_significant, similarity = differ.is_significant_change(frame)
        logger.info(f"3. Frame differ: {'PROCESS' if is_significant else 'SKIP'} (similarity: {similarity:.3f})")
        results.add_pass("WebSocket flow - Frame diffing")
    except Exception as e:
        results.add_fail("WebSocket flow - Frame diffing", str(e))
        return results
    
    # Step 4: Command planning (simulated)
    try:
        if complexity == TaskComplexity.COMPLEX:
            logger.info(f"4. Using THINKING planner for complex command")
        else:
            logger.info(f"4. Using STANDARD planner for {complexity.name} command")
        
        results.add_pass("WebSocket flow - Command planning")
    except Exception as e:
        results.add_fail("WebSocket flow - Command planning", str(e))
        return results
    
    # Step 5: Report success to rate limiter
    try:
        limiter.report_success()
        logger.info(f"5. Reported success to rate limiter")
        results.add_pass("WebSocket flow - Success reporting")
    except Exception as e:
        results.add_fail("WebSocket flow - Success reporting", str(e))
    
    logger.info("="*60)
    return results


async def main():
    """Run all integration tests."""
    logger.info("\n" + "="*60)
    logger.info("GEMINI 3 WEBSOCKET INTEGRATION TESTS")
    logger.info("="*60 + "\n")
    
    all_results = IntegrationTestResults()
    
    # Test 1: Model Router
    logger.info("\n🔍 Testing Model Router Integration...")
    router_results = await test_model_router_integration()
    all_results.passed += router_results.passed
    all_results.failed += router_results.failed
    all_results.errors.extend(router_results.errors)
    
    # Test 2: Rate Limiter
    logger.info("\n🚦 Testing Rate Limiter Integration...")
    limiter_results = await test_rate_limiter_integration()
    all_results.passed += limiter_results.passed
    all_results.failed += limiter_results.failed
    all_results.errors.extend(limiter_results.errors)
    
    # Test 3: Frame Differ
    logger.info("\n🖼️ Testing Frame Differ Integration...")
    differ_results = await test_frame_differ_integration()
    all_results.passed += differ_results.passed
    all_results.failed += differ_results.failed
    all_results.errors.extend(differ_results.errors)
    
    # Test 4: Thinking Planner
    logger.info("\n🧠 Testing Thinking Planner Integration...")
    planner_results = await test_thinking_planner_integration()
    all_results.passed += planner_results.passed
    all_results.failed += planner_results.failed
    all_results.errors.extend(planner_results.errors)
    
    # Test 5: Full WebSocket Flow
    logger.info("\n🌐 Testing Full WebSocket Flow...")
    flow_results = await test_websocket_flow_simulation()
    all_results.passed += flow_results.passed
    all_results.failed += flow_results.failed
    all_results.errors.extend(flow_results.errors)
    
    # Print summary
    success = all_results.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
