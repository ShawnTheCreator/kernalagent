"""
Executor module for Kernal Agent.

Provides the command schema and generator for Python → C# communication.
"""
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

__all__ = [
    # Enums
    "ActionType",
    "TargetType",
    "Origin",
    "ExecutionStatus",
    "FailureReason",
    # Models
    "Target",
    "RetryPolicy",
    "Command",
    "CommandBatch",
    "CommandResult",
    "ExecutorResponse",
    # Generators
    "CommandGenerator",
    "ResponseHandler"
]
