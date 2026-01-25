"""
Tests for Executor Command Schema v1.0

Verifies that the Python command generator produces valid,
deterministic JSON that matches the frozen schema specification.
"""
import json
import pytest
from datetime import datetime

from app.executor.schemas import (
    ActionType,
    TargetType,
    Origin,
    ExecutionStatus,
    FailureReason,
    Target,
    RetryPolicy,
    Command,
    CommandBatch,
    CommandResult,
    ExecutorResponse
)
from app.executor.command_generator import CommandGenerator, ResponseHandler


class TestTarget:
    """Tests for Target model."""
    
    def test_from_coordinates(self):
        target = Target.from_coordinates(100, 200)
        assert target.type == TargetType.COORDINATES
        assert target.x == 100
        assert target.y == 200
        assert target.label is None
    
    def test_from_label(self):
        target = Target.from_label(42)
        assert target.type == TargetType.LABEL
        assert target.label == 42
        assert target.x is None
    
    def test_from_accessibility_id(self):
        target = Target.from_accessibility_id("com.app:id/button")
        assert target.type == TargetType.ACCESSIBILITY_ID
        assert target.accessibility_id == "com.app:id/button"


class TestCommand:
    """Tests for Command model factory methods."""
    
    def test_click_command(self):
        cmd = Command.click(
            command_id="cmd_001",
            target=Target.from_label(42),
            confidence=0.9
        )
        assert cmd.action == ActionType.CLICK
        assert cmd.command_id == "cmd_001"
        assert cmd.target.label == 42
        assert cmd.confidence == 0.9
    
    def test_type_command(self):
        cmd = Command.type_text(
            command_id="cmd_002",
            text="Hello World",
            confidence=0.95
        )
        assert cmd.action == ActionType.TYPE
        assert cmd.text == "Hello World"
    
    def test_scroll_command(self):
        cmd = Command.scroll(
            command_id="cmd_003",
            x=512,
            delta_y=-300
        )
        assert cmd.action == ActionType.SCROLL
        assert cmd.target.x == 512
        assert cmd.target.y == -300  # Negative = scroll up
    
    def test_wait_command(self):
        cmd = Command.wait(command_id="cmd_004", duration_ms=1500)
        assert cmd.action == ActionType.WAIT
        assert cmd.timeout_ms == 1500
    
    def test_done_command(self):
        cmd = Command.done()
        assert cmd.action == ActionType.DONE
        assert cmd.confidence == 1.0
        assert cmd.timeout_ms == 0


class TestCommandBatch:
    """Tests for CommandBatch model."""
    
    def test_batch_creation(self):
        commands = [
            Command.click("cmd_001", Target.from_label(1), 0.9),
            Command.type_text("cmd_002", "test", 0.95)
        ]
        batch = CommandBatch(
            session_id="test-session",
            sequence_id=1,
            commands=commands
        )
        
        assert batch.schema_version == "1.0.0"
        assert batch.session_id == "test-session"
        assert batch.sequence_id == 1
        assert batch.origin == Origin.PYTHON
        assert len(batch.commands) == 2
    
    def test_batch_serialization(self):
        cmd = Command.click("cmd_001", Target.from_coordinates(100, 200), 0.9)
        batch = CommandBatch(
            session_id="test-session",
            sequence_id=1,
            commands=[cmd]
        )
        
        json_str = batch.to_json()
        data = json.loads(json_str)
        
        assert data["schema_version"] == "1.0.0"
        assert data["origin"] == "python"
        assert len(data["commands"]) == 1
        assert data["commands"][0]["action"] == "CLICK"
    
    def test_batch_has_required_fields(self):
        batch = CommandBatch(
            session_id="test",
            sequence_id=1,
            commands=[Command.done()]
        )
        data = batch.to_dict()
        
        # Verify all required top-level fields exist
        required_fields = [
            "schema_version", "session_id", "sequence_id",
            "origin", "timestamp_utc", "commands", "metadata"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestCommandGenerator:
    """Tests for CommandGenerator."""
    
    def test_generator_session_persistence(self):
        gen = CommandGenerator(session_id="my-session")
        batch1 = gen.create_batch([Command.done()])
        batch2 = gen.create_batch([Command.done()])
        
        assert batch1.session_id == "my-session"
        assert batch2.session_id == "my-session"
        assert batch1.sequence_id == 1
        assert batch2.sequence_id == 2  # Monotonically increasing
    
    def test_from_action_plan_click(self):
        gen = CommandGenerator(session_id="test")
        action_plan = {
            "action_type": "CLICK",
            "coordinate_label": 42,
            "confidence": 0.85,
            "explanation": "Clicking the submit button"
        }
        
        batch = gen.from_action_plan(action_plan)
        
        assert len(batch.commands) == 1
        cmd = batch.commands[0]
        assert cmd.action == ActionType.CLICK
        assert cmd.target.label == 42
        assert cmd.confidence == 0.85
    
    def test_from_action_plan_type(self):
        gen = CommandGenerator(session_id="test")
        action_plan = {
            "action_type": "TYPE",
            "text_payload": "Hello from test",
            "confidence": 0.95
        }
        
        batch = gen.from_action_plan(action_plan)
        
        assert len(batch.commands) == 1
        cmd = batch.commands[0]
        assert cmd.action == ActionType.TYPE
        assert cmd.text == "Hello from test"
    
    def test_from_action_plan_scroll(self):
        gen = CommandGenerator(session_id="test")
        action_plan = {
            "action_type": "SCROLL",
            "scroll_direction": "up",
            "scroll_amount": 500,
            "confidence": 0.8
        }
        
        batch = gen.from_action_plan(action_plan)
        
        assert len(batch.commands) == 1
        cmd = batch.commands[0]
        assert cmd.action == ActionType.SCROLL
        assert cmd.target.y == -500  # Negative for up
    
    def test_from_action_plan_done(self):
        gen = CommandGenerator(session_id="test")
        action_plan = {"action_type": "DONE"}
        
        batch = gen.from_action_plan(action_plan)
        
        assert len(batch.commands) == 1
        assert batch.commands[0].action == ActionType.DONE
    
    def test_click_and_type_pattern(self):
        gen = CommandGenerator(session_id="test")
        batch = gen.click_and_type(
            target=Target.from_label(5),
            text="Username"
        )
        
        assert len(batch.commands) == 3
        assert batch.commands[0].action == ActionType.CLICK
        assert batch.commands[1].action == ActionType.WAIT
        assert batch.commands[2].action == ActionType.TYPE
        assert batch.commands[2].text == "Username"
    
    def test_find_and_click_pattern(self):
        gen = CommandGenerator(session_id="test")
        batch = gen.find_and_click(
            target=Target.from_accessibility_id("button_submit")
        )
        
        assert len(batch.commands) == 2
        assert batch.commands[0].action == ActionType.FIND
        assert batch.commands[1].action == ActionType.CLICK


class TestExecutorResponse:
    """Tests for ExecutorResponse parsing."""
    
    def test_parse_success_response(self):
        json_str = '''
        {
            "schema_version": "1.0.0",
            "session_id": "test-session",
            "sequence_id": 1,
            "status": "SUCCESS",
            "results": [
                {"command_id": "cmd_001", "status": "SUCCESS", "execution_time_ms": 150}
            ],
            "failed_command_id": null,
            "reason": null,
            "total_execution_time_ms": 150,
            "timestamp_utc": "2026-01-13T10:00:00.000Z"
        }
        '''
        
        response = ExecutorResponse.from_json(json_str)
        
        assert response.is_success
        assert not response.is_failed
        assert response.session_id == "test-session"
        assert len(response.results) == 1
    
    def test_parse_failed_response(self):
        json_str = '''
        {
            "schema_version": "1.0.0",
            "session_id": "test-session",
            "sequence_id": 2,
            "status": "FAILED",
            "results": [
                {"command_id": "cmd_001", "status": "SUCCESS", "execution_time_ms": 100},
                {"command_id": "cmd_002", "status": "FAILED", "execution_time_ms": 5000}
            ],
            "failed_command_id": "cmd_002",
            "reason": "TIMEOUT_EXCEEDED",
            "total_execution_time_ms": 5100,
            "timestamp_utc": "2026-01-13T10:00:05.000Z"
        }
        '''
        
        response = ExecutorResponse.from_json(json_str)
        
        assert response.is_failed
        assert response.failed_command_id == "cmd_002"
        assert response.reason == FailureReason.TIMEOUT_EXCEEDED


class TestResponseHandler:
    """Tests for ResponseHandler."""
    
    def test_should_retry_on_timeout(self):
        response = {
            "status": "FAILED",
            "reason": "TIMEOUT_EXCEEDED"
        }
        assert ResponseHandler.should_retry(response) is True
    
    def test_should_retry_on_target_not_found(self):
        response = {
            "status": "FAILED",
            "reason": "TARGET_NOT_FOUND"
        }
        assert ResponseHandler.should_retry(response) is True
    
    def test_should_not_retry_on_success(self):
        response = {"status": "SUCCESS"}
        assert ResponseHandler.should_retry(response) is False
    
    def test_should_not_retry_on_permission_denied(self):
        response = {
            "status": "FAILED",
            "reason": "PERMISSION_DENIED"
        }
        assert ResponseHandler.should_retry(response) is False
    
    def test_get_success_count(self):
        response = {
            "results": [
                {"command_id": "cmd_001", "status": "SUCCESS"},
                {"command_id": "cmd_002", "status": "SUCCESS"},
                {"command_id": "cmd_003", "status": "FAILED"}
            ]
        }
        assert ResponseHandler.get_success_count(response) == 2


class TestSchemaCompliance:
    """Tests ensuring schema matches specification."""
    
    def test_action_enum_is_closed(self):
        """Verify only the 6 allowed actions exist."""
        allowed = {"FIND", "CLICK", "TYPE", "SCROLL", "WAIT", "DONE"}
        actual = {a.value for a in ActionType}
        assert actual == allowed
    
    def test_target_type_enum_is_closed(self):
        """Verify only the 3 target types exist."""
        allowed = {"COORDINATES", "LABEL", "ACCESSIBILITY_ID"}
        actual = {t.value for t in TargetType}
        assert actual == allowed
    
    def test_origin_enum_values(self):
        """Verify origin platforms."""
        allowed = {"python", "android", "web"}
        actual = {o.value for o in Origin}
        assert actual == allowed
    
    def test_command_json_structure(self):
        """Verify command JSON has all required fields."""
        cmd = Command.click("cmd_001", Target.from_label(1), 0.9)
        data = cmd.model_dump()
        
        required = ["command_id", "action", "confidence", "timeout_ms"]
        for field in required:
            assert field in data


# Run with: python -m pytest tests/test_executor_schema.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
