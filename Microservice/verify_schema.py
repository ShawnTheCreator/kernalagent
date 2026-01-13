"""
Quick verification script for Executor Command Schema v1.0
Runs without pytest dependency.
"""
import sys
import json
sys.path.insert(0, '.')

def test_all():
    print("=" * 60)
    print("EXECUTOR COMMAND SCHEMA v1.0 - VERIFICATION")
    print("=" * 60)
    
    try:
        # Import modules
        print("\n[1] Importing modules...")
        from app.executor.schemas import (
            ActionType, TargetType, Origin, ExecutionStatus, FailureReason,
            Target, RetryPolicy, Command, CommandBatch, CommandResult, ExecutorResponse
        )
        from app.executor.command_generator import CommandGenerator, ResponseHandler
        print("    ✓ All imports successful")
        
        # Test Target creation
        print("\n[2] Testing Target creation...")
        t1 = Target.from_coordinates(100, 200)
        assert t1.type == TargetType.COORDINATES and t1.x == 100 and t1.y == 200
        t2 = Target.from_label(42)
        assert t2.type == TargetType.LABEL and t2.label == 42
        t3 = Target.from_accessibility_id("com.app:id/btn")
        assert t3.type == TargetType.ACCESSIBILITY_ID
        print("    ✓ Target.from_coordinates(): OK")
        print("    ✓ Target.from_label(): OK")
        print("    ✓ Target.from_accessibility_id(): OK")
        
        # Test Command factory methods
        print("\n[3] Testing Command factory methods...")
        cmd_click = Command.click("cmd_001", t2, 0.9)
        assert cmd_click.action == ActionType.CLICK
        cmd_type = Command.type_text("cmd_002", "Hello World", 0.95)
        assert cmd_type.action == ActionType.TYPE and cmd_type.text == "Hello World"
        cmd_scroll = Command.scroll("cmd_003", 512, -300, 0.85)
        assert cmd_scroll.action == ActionType.SCROLL
        cmd_wait = Command.wait("cmd_004", 1500)
        assert cmd_wait.action == ActionType.WAIT
        cmd_done = Command.done()
        assert cmd_done.action == ActionType.DONE
        print("    ✓ Command.click(): OK")
        print("    ✓ Command.type_text(): OK")
        print("    ✓ Command.scroll(): OK")
        print("    ✓ Command.wait(): OK")
        print("    ✓ Command.done(): OK")
        
        # Test CommandBatch
        print("\n[4] Testing CommandBatch...")
        batch = CommandBatch(
            session_id="test-session",
            sequence_id=1,
            commands=[cmd_click, cmd_type]
        )
        assert batch.schema_version == "1.0.0"
        assert batch.origin == Origin.PYTHON
        assert len(batch.commands) == 2
        print("    ✓ CommandBatch creation: OK")
        
        # Test JSON serialization
        json_str = batch.to_json()
        data = json.loads(json_str)
        assert "schema_version" in data
        assert data["commands"][0]["action"] == "CLICK"
        print("    ✓ JSON serialization: OK")
        print(f"    Sample JSON size: {len(json_str)} bytes")
        
        # Test CommandGenerator
        print("\n[5] Testing CommandGenerator...")
        gen = CommandGenerator(session_id="gen-test")
        
        # Test from_action_plan
        action_plan = {
            "action_type": "CLICK",
            "coordinate_label": 42,
            "confidence": 0.85,
            "explanation": "Clicking submit"
        }
        batch1 = gen.from_action_plan(action_plan)
        assert len(batch1.commands) == 1
        assert batch1.commands[0].action == ActionType.CLICK
        assert batch1.commands[0].target.label == 42
        print("    ✓ from_action_plan(CLICK): OK")
        
        action_plan_type = {"action_type": "TYPE", "text_payload": "test text", "confidence": 0.9}
        batch2 = gen.from_action_plan(action_plan_type)
        assert batch2.commands[0].action == ActionType.TYPE
        print("    ✓ from_action_plan(TYPE): OK")
        
        action_plan_scroll = {"action_type": "SCROLL", "scroll_direction": "up", "scroll_amount": 500}
        batch3 = gen.from_action_plan(action_plan_scroll)
        assert batch3.commands[0].target.y == -500  # Negative for up
        print("    ✓ from_action_plan(SCROLL): OK")
        
        # Test sequence ID increment
        assert batch1.sequence_id == 1
        assert batch2.sequence_id == 2
        assert batch3.sequence_id == 3
        print("    ✓ Sequence ID monotonic: OK")
        
        # Test multi-step patterns
        print("\n[6] Testing multi-step patterns...")
        batch_ct = gen.click_and_type(Target.from_label(5), "Username")
        assert len(batch_ct.commands) == 3
        assert batch_ct.commands[0].action == ActionType.CLICK
        assert batch_ct.commands[1].action == ActionType.WAIT
        assert batch_ct.commands[2].action == ActionType.TYPE
        print("    ✓ click_and_type(): 3 commands generated")
        
        batch_fc = gen.find_and_click(Target.from_accessibility_id("button"))
        assert len(batch_fc.commands) == 2
        assert batch_fc.commands[0].action == ActionType.FIND
        assert batch_fc.commands[1].action == ActionType.CLICK
        print("    ✓ find_and_click(): 2 commands generated")
        
        # Test ExecutorResponse parsing
        print("\n[7] Testing ExecutorResponse...")
        success_response = '''
        {
            "schema_version": "1.0.0",
            "session_id": "test-session",
            "sequence_id": 1,
            "status": "SUCCESS",
            "results": [{"command_id": "cmd_001", "status": "SUCCESS", "execution_time_ms": 150}],
            "failed_command_id": null,
            "reason": null,
            "total_execution_time_ms": 150,
            "timestamp_utc": "2026-01-13T10:00:00.000Z"
        }
        '''
        resp = ExecutorResponse.from_json(success_response)
        assert resp.is_success
        print("    ✓ SUCCESS response parsing: OK")
        
        failed_response = '''
        {
            "schema_version": "1.0.0",
            "session_id": "test-session",
            "sequence_id": 2,
            "status": "FAILED",
            "results": [{"command_id": "cmd_001", "status": "FAILED", "execution_time_ms": 5000}],
            "failed_command_id": "cmd_001",
            "reason": "TIMEOUT_EXCEEDED",
            "total_execution_time_ms": 5000,
            "timestamp_utc": "2026-01-13T10:00:05.000Z"
        }
        '''
        resp2 = ExecutorResponse.from_json(failed_response)
        assert resp2.is_failed
        assert resp2.reason == FailureReason.TIMEOUT_EXCEEDED
        print("    ✓ FAILED response parsing: OK")
        
        # Test ResponseHandler
        print("\n[8] Testing ResponseHandler...")
        assert ResponseHandler.should_retry({"status": "FAILED", "reason": "TIMEOUT_EXCEEDED"}) == True
        assert ResponseHandler.should_retry({"status": "FAILED", "reason": "PERMISSION_DENIED"}) == False
        assert ResponseHandler.should_retry({"status": "SUCCESS"}) == False
        print("    ✓ should_retry() logic: OK")
        
        # Test schema compliance
        print("\n[9] Verifying schema compliance...")
        allowed_actions = {"FIND", "CLICK", "TYPE", "SCROLL", "WAIT", "DONE"}
        actual_actions = {a.value for a in ActionType}
        assert actual_actions == allowed_actions
        print(f"    ✓ Action ENUM is closed: {allowed_actions}")
        
        allowed_targets = {"COORDINATES", "LABEL", "ACCESSIBILITY_ID"}
        actual_targets = {t.value for t in TargetType}
        assert actual_targets == allowed_targets
        print(f"    ✓ Target ENUM is closed: {allowed_targets}")
        
        # Final output example
        print("\n[10] Example JSON output:")
        print("-" * 50)
        example_gen = CommandGenerator(session_id="example-session")
        example_batch = example_gen.click_and_type(Target.from_label(7), "hello@example.com")
        print(example_batch.to_json())
        print("-" * 50)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Schema v1.0 is VERIFIED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
