"""
Standalone test for Agent STM (Short-Term Memory) Module.
Tests the memory logic without requiring server or API keys.
"""
import sys
sys.path.insert(0, '.')

from app.agent.memory import AgentMemory


def test_memory_creation():
    """Test basic memory creation and initialization."""
    print("=" * 60)
    print("TEST 1: Memory Creation")
    print("=" * 60)
    
    memory = AgentMemory()
    
    assert memory.last_action is None
    assert memory.last_skill is None
    assert memory.last_signal is None
    assert memory.failure_count == 0
    assert memory.action_history == []
    
    print("✅ Memory initialized correctly")
    print(memory.format_for_log())
    print()


def test_action_recording():
    """Test action recording."""
    print("=" * 60)
    print("TEST 2: Action Recording")
    print("=" * 60)
    
    memory = AgentMemory()
    
    memory.record_action(
        action_type="CLICK",
        skill_name="Open File Menu",
        signal="UI_STABLE"
    )
    
    assert memory.last_action == "CLICK"
    assert memory.last_skill == "Open File Menu"
    assert memory.last_signal == "UI_STABLE"
    assert "CLICK" in memory.action_history
    
    print("✅ Action recorded correctly")
    print(memory.format_for_log())
    print()


def test_failure_counting():
    """Test failure recording and penalty."""
    print("=" * 60)
    print("TEST 3: Failure Counting & Penalty")
    print("=" * 60)
    
    memory = AgentMemory()
    
    # No failures - modifier should be 1.0
    assert memory.get_confidence_modifier() == 1.0
    print(f"✅ 0 failures → modifier = {memory.get_confidence_modifier()}")
    
    # 1 failure - modifier still 1.0
    memory.record_failure()
    assert memory.get_confidence_modifier() == 1.0
    print(f"✅ 1 failure → modifier = {memory.get_confidence_modifier()}")
    
    # 2 failures - modifier should be 0.8
    memory.record_failure()
    assert memory.get_confidence_modifier() == 0.8
    print(f"✅ 2 failures → modifier = {memory.get_confidence_modifier()}")
    
    # 3 failures - modifier still 0.8
    memory.record_failure()
    assert memory.get_confidence_modifier() == 0.8
    print(f"✅ 3 failures → modifier = {memory.get_confidence_modifier()}")
    
    print(memory.format_for_log())
    print()


def test_loop_detection():
    """Test loop detection."""
    print("=" * 60)
    print("TEST 4: Loop Detection")
    print("=" * 60)
    
    memory = AgentMemory()
    
    # First action
    memory.record_action("CLICK", "File Menu", "UI_STABLE")
    
    # Same action + same signal = loop
    assert memory.is_loop_detected("CLICK", "UI_STABLE") == True
    print("✅ Same action + same signal → LOOP DETECTED")
    
    # Different action = no loop
    assert memory.is_loop_detected("SCROLL", "UI_STABLE") == False
    print("✅ Different action + same signal → NO LOOP")
    
    # Same action + different signal = no loop
    assert memory.is_loop_detected("CLICK", "SCREEN_CHANGED") == False
    print("✅ Same action + different signal → NO LOOP")
    
    print()


def test_skill_boost():
    """Test skill reuse boost."""
    print("=" * 60)
    print("TEST 5: Skill Reuse Boost")
    print("=" * 60)
    
    memory = AgentMemory()
    
    # Record a successful action with a skill
    memory.record_action("CLICK", "Open File", "UI_STABLE")
    
    # Same skill with no failures = +0.1 boost
    boost = memory.get_skill_boost("Open File")
    assert boost == 0.1
    print(f"✅ Same skill, no failures → boost = +{boost}")
    
    # Different skill = no boost
    boost = memory.get_skill_boost("Other Skill")
    assert boost == 0.0
    print(f"✅ Different skill → boost = {boost}")
    
    # Same skill but with failures = no boost
    memory.record_failure()
    memory.record_failure()
    boost = memory.get_skill_boost("Open File")
    assert boost == 0.0
    print(f"✅ Same skill, but failures → boost = {boost}")
    
    print()


def test_reset():
    """Test memory reset."""
    print("=" * 60)
    print("TEST 6: Memory Reset")
    print("=" * 60)
    
    memory = AgentMemory()
    
    # Fill memory with data
    memory.record_action("CLICK", "Test Skill", "UI_STABLE")
    memory.record_failure()
    memory.record_failure()
    
    print("Before reset:")
    print(memory.format_for_log())
    
    # Reset
    memory.reset()
    
    assert memory.last_action is None
    assert memory.last_skill is None
    assert memory.failure_count == 0
    
    print("\nAfter reset:")
    print(memory.format_for_log())
    print("✅ Memory reset correctly")
    print()


def test_explainability():
    """Test explainability output."""
    print("=" * 60)
    print("TEST 7: Explainability Output")
    print("=" * 60)
    
    memory = AgentMemory()
    memory.record_action("SCROLL", "Scroll Page", "LAYOUT_CHANGE")
    memory.record_failure()
    
    context = memory.get_context()
    
    assert context["last_action"] == "SCROLL"
    assert context["last_skill"] == "Scroll Page"
    assert context["last_signal"] == "LAYOUT_CHANGE"
    assert context["failure_count"] == 1
    
    print("Context dictionary:")
    for key, value in context.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Explainability output correct")
    print()


def run_all_tests():
    """Run all STM tests."""
    print("\n" + "🧠" * 30)
    print("  AGENT SHORT-TERM MEMORY (STM) TEST SUITE")
    print("🧠" * 30 + "\n")
    
    test_memory_creation()
    test_action_recording()
    test_failure_counting()
    test_loop_detection()
    test_skill_boost()
    test_reset()
    test_explainability()
    
    print("=" * 60)
    print("🎉 ALL TESTS PASSED! STM Module is working correctly.")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
