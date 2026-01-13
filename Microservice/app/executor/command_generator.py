"""
Command Generator for Kernal Agent.

Converts AI decisions into deterministic executor commands.
This bridges the decision engine output → executor command schema.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.executor.schemas import (
    Command,
    CommandBatch,
    Target,
    TargetType,
    RetryPolicy,
    ActionType,
    Origin
)


class CommandGenerator:
    """
    Generates executor command batches from AI decisions.
    
    Usage:
        generator = CommandGenerator(session_id="...")
        batch = generator.from_action_plan(action_plan)
        json_str = batch.to_json()
    """
    
    def __init__(self, session_id: Optional[str] = None, origin: Origin = Origin.PYTHON):
        self.session_id = session_id or str(uuid.uuid4())
        self.origin = origin
        self._sequence_counter = 0
    
    def _next_sequence_id(self) -> int:
        """Get next monotonically increasing sequence ID."""
        self._sequence_counter += 1
        return self._sequence_counter
    
    def _generate_command_id(self, index: int) -> str:
        """Generate unique command ID within batch."""
        return f"cmd_{index:03d}"
    
    def create_batch(
        self,
        commands: List[Command],
        metadata: Optional[Dict[str, Any]] = None
    ) -> CommandBatch:
        """
        Create a command batch from a list of commands.
        """
        return CommandBatch(
            schema_version="1.0.0",
            session_id=self.session_id,
            sequence_id=self._next_sequence_id(),
            origin=self.origin,
            timestamp_utc=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            commands=commands,
            metadata=metadata or {}
        )
    
    def from_action_plan(
        self,
        action_plan: dict,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CommandBatch:
        """
        Convert a Gemini action plan to executor command batch.
        
        Expected action_plan format:
        {
            "action_type": "CLICK" | "TYPE" | "SCROLL" | "WAIT" | "DONE",
            "coordinate_label": 42,          # For CLICK with SoM labels
            "coordinates": {"x": 100, "y": 200},  # For CLICK with coords
            "text_payload": "Hello",         # For TYPE
            "scroll_direction": "down",      # For SCROLL
            "scroll_amount": 300,
            "confidence": 0.9,
            "explanation": "..."
        }
        """
        commands = []
        action_type = action_plan.get("action_type", "").upper()
        confidence = action_plan.get("confidence", 0.5)
        
        # Map action plan to commands
        if action_type == "CLICK":
            target = self._extract_target(action_plan)
            if target:
                commands.append(Command.click(
                    command_id=self._generate_command_id(1),
                    target=target,
                    confidence=confidence,
                    timeout_ms=3000,
                    retry_policy=RetryPolicy(max_attempts=2, backoff_ms=300)
                ))
        
        elif action_type == "TYPE":
            text = action_plan.get("text_payload", "")
            if text:
                commands.append(Command.type_text(
                    command_id=self._generate_command_id(1),
                    text=text,
                    confidence=confidence,
                    timeout_ms=5000
                ))
        
        elif action_type == "SCROLL":
            direction = action_plan.get("scroll_direction", "down")
            amount = action_plan.get("scroll_amount", 300)
            delta_y = amount if direction == "down" else -amount
            commands.append(Command.scroll(
                command_id=self._generate_command_id(1),
                x=512,  # Default center
                delta_y=delta_y,
                confidence=confidence,
                timeout_ms=2000
            ))
        
        elif action_type == "WAIT":
            duration = action_plan.get("wait_duration_ms", 1000)
            commands.append(Command.wait(
                command_id=self._generate_command_id(1),
                duration_ms=duration
            ))
        
        elif action_type == "DONE":
            commands.append(Command.done(
                command_id=self._generate_command_id(1)
            ))
        
        # Build metadata
        batch_metadata = metadata or {}
        batch_metadata["intent"] = action_plan.get("intent_signature", "")
        batch_metadata["explanation"] = action_plan.get("explanation", "")
        if action_plan.get("skill_id"):
            batch_metadata["skill_id"] = action_plan["skill_id"]
        
        return self.create_batch(commands, batch_metadata)
    
    def _extract_target(self, action_plan: dict) -> Optional[Target]:
        """
        Extract target from action plan.
        Priority: label > coordinates > accessibility_id
        """
        # SoM label (highest priority for vision-based actions)
        if action_plan.get("coordinate_label") is not None:
            return Target.from_label(int(action_plan["coordinate_label"]))
        
        # Direct coordinates
        if action_plan.get("coordinates"):
            coords = action_plan["coordinates"]
            return Target.from_coordinates(
                x=coords.get("x", 0),
                y=coords.get("y", 0)
            )
        
        # Accessibility ID (for Android/accessibility-aware actions)
        if action_plan.get("accessibility_id"):
            return Target.from_accessibility_id(action_plan["accessibility_id"])
        
        return None
    
    # =========================================================================
    # Convenience methods for multi-step plans
    # =========================================================================
    
    def click_and_type(
        self,
        target: Target,
        text: str,
        click_confidence: float = 0.9,
        type_confidence: float = 0.95,
        wait_after_click_ms: int = 500
    ) -> CommandBatch:
        """
        Generate click → wait → type sequence.
        Common pattern for form filling.
        """
        commands = [
            Command.click(
                command_id=self._generate_command_id(1),
                target=target,
                confidence=click_confidence,
                timeout_ms=3000
            ),
            Command.wait(
                command_id=self._generate_command_id(2),
                duration_ms=wait_after_click_ms
            ),
            Command.type_text(
                command_id=self._generate_command_id(3),
                text=text,
                confidence=type_confidence
            )
        ]
        return self.create_batch(commands, {"pattern": "click_and_type"})
    
    def find_and_click(
        self,
        target: Target,
        confidence: float = 0.8
    ) -> CommandBatch:
        """
        Generate find → click sequence.
        Validates element exists before clicking.
        """
        commands = [
            Command.find(
                command_id=self._generate_command_id(1),
                target=target,
                confidence=confidence,
                timeout_ms=10000,
                retry_policy=RetryPolicy(max_attempts=3, backoff_ms=1000)
            ),
            Command.click(
                command_id=self._generate_command_id(2),
                target=target,
                confidence=confidence,
                timeout_ms=3000
            )
        ]
        return self.create_batch(commands, {"pattern": "find_and_click"})
    
    def complete_task(self, completion_reason: str = "task_successful") -> CommandBatch:
        """
        Generate DONE command to signal task completion.
        """
        commands = [Command.done(self._generate_command_id(1))]
        return self.create_batch(commands, {"completion_reason": completion_reason})


# =============================================================================
# Response Handler
# =============================================================================

class ResponseHandler:
    """
    Handles executor responses and determines next actions.
    """
    
    @staticmethod
    def should_retry(response: dict) -> bool:
        """Check if the failed batch should be retried."""
        status = response.get("status", "")
        reason = response.get("reason", "")
        
        # Retry on transient failures
        if status == "FAILED" and reason in ["TIMEOUT_EXCEEDED", "TARGET_NOT_FOUND"]:
            return True
        
        return False
    
    @staticmethod
    def get_failed_command(response: dict) -> Optional[str]:
        """Get the ID of the first failed command."""
        return response.get("failed_command_id")
    
    @staticmethod
    def get_success_count(response: dict) -> int:
        """Count successful commands in response."""
        results = response.get("results", [])
        return sum(1 for r in results if r.get("status") == "SUCCESS")
