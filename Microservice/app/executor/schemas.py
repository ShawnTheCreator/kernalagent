"""
Kernal Agent Executor Command Schema v1.0

Pydantic models for the Python → C# execution contract.
This is a FROZEN schema - do not modify without version bump.

Philosophy: "Python thinks. C# executes. JSON is the contract."
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# =============================================================================
# ENUMS (CLOSED - No extensions without version bump)
# =============================================================================

class ActionType(str, Enum):
    """
    Allowed executor actions. This is a CLOSED enum.
    """
    FIND = "FIND"       # Locate an element on screen
    CLICK = "CLICK"     # Click/tap at target location
    TYPE = "TYPE"       # Input text at current cursor
    SCROLL = "SCROLL"   # Scroll in specified direction
    WAIT = "WAIT"       # Wait for specified duration
    DONE = "DONE"       # Signal task completion


class TargetType(str, Enum):
    """
    Target specification types.
    """
    COORDINATES = "COORDINATES"         # x, y pixel coordinates
    LABEL = "LABEL"                     # Set-of-Mark label ID
    ACCESSIBILITY_ID = "ACCESSIBILITY_ID"  # Platform accessibility ID


class Origin(str, Enum):
    """
    Command origin platform.
    """
    PYTHON = "python"
    ANDROID = "android"
    WEB = "web"


class ExecutionStatus(str, Enum):
    """
    Batch execution status.
    """
    SUCCESS = "SUCCESS"     # All commands executed successfully
    FAILED = "FAILED"       # Execution stopped at a failed command
    PARTIAL = "PARTIAL"     # Some commands succeeded before failure


class FailureReason(str, Enum):
    """
    Standardized failure reasons.
    """
    TIMEOUT_EXCEEDED = "TIMEOUT_EXCEEDED"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"


# =============================================================================
# COMMAND MODELS (Python → C#)
# =============================================================================

class Target(BaseModel):
    """
    Target specification for actions that require a location.
    """
    type: TargetType
    x: Optional[int] = None
    y: Optional[int] = None
    label: Optional[int] = None
    accessibility_id: Optional[str] = None

    @classmethod
    def from_coordinates(cls, x: int, y: int) -> "Target":
        return cls(type=TargetType.COORDINATES, x=x, y=y)

    @classmethod
    def from_label(cls, label: int) -> "Target":
        return cls(type=TargetType.LABEL, label=label)

    @classmethod
    def from_accessibility_id(cls, aid: str) -> "Target":
        return cls(type=TargetType.ACCESSIBILITY_ID, accessibility_id=aid)


class RetryPolicy(BaseModel):
    """
    Retry configuration for failed commands.
    """
    max_attempts: int = Field(default=1, ge=1)
    backoff_ms: int = Field(default=500, ge=0)


class Command(BaseModel):
    """
    Single executable command.
    """
    command_id: str
    action: ActionType
    target: Optional[Target] = None
    text: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    timeout_ms: int = Field(default=5000, ge=0)
    retry_policy: Optional[RetryPolicy] = None

    @classmethod
    def click(
        cls,
        command_id: str,
        target: Target,
        confidence: float = 0.9,
        timeout_ms: int = 3000,
        retry_policy: Optional[RetryPolicy] = None
    ) -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.CLICK,
            target=target,
            confidence=confidence,
            timeout_ms=timeout_ms,
            retry_policy=retry_policy
        )

    @classmethod
    def type_text(
        cls,
        command_id: str,
        text: str,
        confidence: float = 0.95,
        timeout_ms: int = 5000
    ) -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.TYPE,
            text=text,
            confidence=confidence,
            timeout_ms=timeout_ms
        )

    @classmethod
    def scroll(
        cls,
        command_id: str,
        x: int,
        delta_y: int,
        confidence: float = 0.85,
        timeout_ms: int = 2000
    ) -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.SCROLL,
            target=Target.from_coordinates(x, delta_y),
            confidence=confidence,
            timeout_ms=timeout_ms
        )

    @classmethod
    def wait(
        cls,
        command_id: str,
        duration_ms: int
    ) -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.WAIT,
            confidence=1.0,
            timeout_ms=duration_ms
        )

    @classmethod
    def find(
        cls,
        command_id: str,
        target: Target,
        confidence: float = 0.8,
        timeout_ms: int = 10000,
        retry_policy: Optional[RetryPolicy] = None
    ) -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.FIND,
            target=target,
            confidence=confidence,
            timeout_ms=timeout_ms,
            retry_policy=retry_policy
        )

    @classmethod
    def done(cls, command_id: str = "cmd_done") -> "Command":
        return cls(
            command_id=command_id,
            action=ActionType.DONE,
            confidence=1.0,
            timeout_ms=0
        )


class CommandBatch(BaseModel):
    """
    Top-level command batch sent to executor.
    """
    schema_version: str = "1.0.0"
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sequence_id: int = Field(ge=1)
    origin: Origin = Origin.PYTHON
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    )
    commands: List[Command]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string for transmission."""
        return self.model_dump_json(indent=2)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return self.model_dump()


# =============================================================================
# RESPONSE MODELS (C# → Python)
# =============================================================================

class CommandResult(BaseModel):
    """
    Result of a single command execution.
    """
    command_id: str
    status: ExecutionStatus
    execution_time_ms: int = Field(ge=0)


class ExecutorResponse(BaseModel):
    """
    Response from executor after processing a command batch.
    """
    schema_version: str = "1.0.0"
    session_id: str
    sequence_id: int
    status: ExecutionStatus
    results: List[CommandResult]
    failed_command_id: Optional[str] = None
    reason: Optional[FailureReason] = None
    total_execution_time_ms: int = Field(ge=0)
    timestamp_utc: str

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status == ExecutionStatus.FAILED

    @classmethod
    def from_json(cls, json_str: str) -> "ExecutorResponse":
        """Parse from JSON string."""
        import json
        data = json.loads(json_str)
        return cls(**data)
