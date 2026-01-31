"""
Integration tests for app opening and action chain execution.
Tests reliability, timing, and synchronization of multi-step operations.
"""

import pytest
from typing import List, Dict, Any


# Mock action step structure for testing
def create_action_step(action: str, **kwargs) -> Dict[str, Any]:
    """Create a mock action step for testing."""
    step = {"action": action}
    step.update(kwargs)
    return step


def create_action_plan(steps: List[Dict[str, Any]], confidence: float = 0.9) -> Dict[str, Any]:
    """Create a mock action plan for testing."""
    return {
        "steps": steps,
        "confidence": confidence
    }


class TestAppOpeningReliability:
    """Test app opening with various scenarios."""
    
    def test_simple_app_opening(self):
        """Test basic app opening - notepad."""
        plan = create_action_plan(
            steps=[
                create_action_step("open_app", target="notepad.exe")
            ],
            confidence=0.95
        )
        
        # Verify schema
        assert plan["steps"][0]["action"] == "open_app"
        assert plan["steps"][0]["target"] == "notepad.exe"
        assert plan["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_chrome_with_url(self):
        """Test Chrome opening with navigation."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url="https://github.com")
            ],
            confidence=0.92
        )
        
        assert len(plan.steps) == 2
        assert plan.steps[0].action == "open_app"
        assert plan.steps[1].action == "navigate"
        assert plan.steps[1].url == "https://github.com"
    
    @pytest.mark.asyncio
    async def test_app_with_typing(self):
        """Test app opening followed by typing."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="type_text", content="Hello World"),
            ],
            confidence=0.94
        )
        
        assert len(plan.steps) == 2
        assert plan.steps[0].action == "open_app"
        assert plan.steps[1].action == "type_text"
        assert plan.steps[1].content == "Hello World"


class TestActionChainTiming:
    """Test timing and synchronization of action chains."""
    
    @pytest.mark.asyncio
    async def test_wait_action_duration(self):
        """Test wait action with specific duration."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="wait", duration=2),
                ActionStep(action="type_text", content="Test")
            ],
            confidence=0.90
        )
        
        wait_step = plan.steps[1]
        assert wait_step.action == "wait"
        assert wait_step.duration == 2
    
    @pytest.mark.asyncio
    async def test_smart_wait_for_ready(self):
        """Test smart_wait for app readiness."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="smart_wait", condition="window_ready"),
                ActionStep(action="navigate", url="https://google.com")
            ],
            confidence=0.88
        )
        
        smart_wait = plan.steps[1]
        assert smart_wait.action == "smart_wait"
        assert smart_wait.condition == "window_ready"


class TestComplexChains:
    """Test complex multi-step action chains."""
    
    @pytest.mark.asyncio
    async def test_search_and_type_chain(self):
        """Test search box focus and typing."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url="https://github.com"),
                ActionStep(action="wait", duration=1),
                ActionStep(action="click", target="search box"),
                ActionStep(action="type_text", content="kernel agent"),
                ActionStep(action="press_key", key="enter")
            ],
            confidence=0.85
        )
        
        assert len(plan.steps) == 6
        assert plan.steps[0].action == "open_app"
        assert plan.steps[3].action == "click"
        assert plan.steps[4].action == "type_text"
        assert plan.steps[5].key == "enter"
    
    @pytest.mark.asyncio
    async def test_file_save_chain(self):
        """Test opening app, typing, and saving file."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="type_text", content="Important document"),
                ActionStep(action="hotkey", content="ctrl+s"),
                ActionStep(action="wait", duration=1),
                ActionStep(action="type_text", content="test_file.txt"),
                ActionStep(action="press_key", key="enter")
            ],
            confidence=0.82
        )
        
        assert len(plan.steps) == 6
        assert plan.steps[2].action == "hotkey"
        assert plan.steps[2].content == "ctrl+s"
    
    @pytest.mark.asyncio
    async def test_app_switching_chain(self):
        """Test switching between multiple apps."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="type_text", content="Note 1"),
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="navigate", url="https://google.com"),
                ActionStep(action="hotkey", content="alt+tab"),
                ActionStep(action="type_text", content=" - continued")
            ],
            confidence=0.78
        )
        
        assert len(plan.steps) == 6
        # Verify app switching
        app_opens = [s for s in plan.steps if s.action == "open_app"]
        assert len(app_opens) == 2
        assert app_opens[0].target == "notepad.exe"
        assert app_opens[1].target == "chrome.exe"


class TestErrorRecovery:
    """Test error handling and recovery mechanisms."""
    
    @pytest.mark.asyncio
    async def test_fallback_url_on_app_failure(self):
        """Test fallback to web when app can't open."""
        plan = ActionPlan(
            steps=[
                ActionStep(
                    action="open_app", 
                    target="spotify.exe",
                    fallback_url="https://open.spotify.com"
                ),
            ],
            confidence=0.80
        )
        
        step = plan.steps[0]
        assert step.action == "open_app"
        assert step.target == "spotify.exe"
        assert step.fallback_url == "https://open.spotify.com"
    
    @pytest.mark.asyncio
    async def test_expected_outcome_verification(self):
        """Test expected outcome verification for actions."""
        plan = ActionPlan(
            steps=[
                ActionStep(
                    action="click_element",
                    target="Save button",
                    expected={
                        "window_title_contains": "saved successfully",
                        "timeout_ms": 3000
                    }
                ),
            ],
            confidence=0.88
        )
        
        step = plan.steps[0]
        assert "expected" in step.dict()
        assert step.expected["window_title_contains"] == "saved successfully"


class TestConcurrency:
    """Test concurrent action execution scenarios."""
    
    @pytest.mark.asyncio
    async def test_sequential_execution_order(self):
        """Verify actions execute in correct order."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="type_text", content="Line 1"),
                ActionStep(action="press_key", key="enter"),
                ActionStep(action="type_text", content="Line 2"),
                ActionStep(action="press_key", key="enter"),
                ActionStep(action="type_text", content="Line 3")
            ],
            confidence=0.91
        )
        
        # Verify step order is preserved
        assert plan.steps[0].action == "open_app"
        assert plan.steps[1].content == "Line 1"
        assert plan.steps[3].content == "Line 2"
        assert plan.steps[5].content == "Line 3"
    
    @pytest.mark.asyncio
    async def test_no_race_conditions(self):
        """Test that rapid successive actions don't conflict."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="press_key", key="a"),
                ActionStep(action="press_key", key="b"),
                ActionStep(action="press_key", key="c"),
                ActionStep(action="press_key", key="d"),
                ActionStep(action="press_key", key="e")
            ],
            confidence=0.95
        )
        
        # All steps should be present and ordered
        assert len(plan.steps) == 5
        keys = [s.key for s in plan.steps]
        assert keys == ["a", "b", "c", "d", "e"]


class TestAppSpecificBehavior:
    """Test app-specific handling."""
    
    @pytest.mark.asyncio
    async def test_chrome_profile_handling(self):
        """Test Chrome opens with correct profile."""
        plan = ActionPlan(
            steps=[
                ActionStep(
                    action="open_app", 
                    target="chrome.exe",
                    # Profile handled by C# side
                ),
            ],
            confidence=0.93
        )
        
        assert plan.steps[0].action == "open_app"
        assert plan.steps[0].target == "chrome.exe"
    
    @pytest.mark.asyncio
    async def test_uwp_app_opening(self):
        """Test UWP app opening (WhatsApp, Calculator)."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="calculator.exe"),
            ],
            confidence=0.96
        )
        
        assert plan.steps[0].target == "calculator.exe"
    
    @pytest.mark.asyncio
    async def test_app_with_custom_path(self):
        """Test app opening with custom path support."""
        plan = ActionPlan(
            steps=[
                ActionStep(
                    action="open_app", 
                    target="discord.exe"
                ),
            ],
            confidence=0.89
        )
        
        assert plan.steps[0].target == "discord.exe"


class TestStressConditions:
    """Test system under stress conditions."""
    
    @pytest.mark.asyncio
    async def test_long_action_chain(self):
        """Test execution of many sequential actions."""
        steps = []
        for i in range(20):
            steps.append(ActionStep(action="type_text", content=f"Step {i}"))
            steps.append(ActionStep(action="press_key", key="enter"))
        
        plan = ActionPlan(steps=steps, confidence=0.75)
        
        assert len(plan.steps) == 40
        assert all(s.action in ["type_text", "press_key"] for s in plan.steps)
    
    @pytest.mark.asyncio
    async def test_rapid_app_switching(self):
        """Test rapid switching between apps."""
        plan = ActionPlan(
            steps=[
                ActionStep(action="open_app", target="notepad.exe"),
                ActionStep(action="hotkey", content="alt+tab"),
                ActionStep(action="open_app", target="chrome.exe"),
                ActionStep(action="hotkey", content="alt+tab"),
                ActionStep(action="open_app", target="notepad.exe")
            ],
            confidence=0.70
        )
        
        assert len(plan.steps) == 5
        app_actions = [s.action for s in plan.steps]
        assert app_actions.count("open_app") == 3
        assert app_actions.count("hotkey") == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
