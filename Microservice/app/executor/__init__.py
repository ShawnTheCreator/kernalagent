"""
Executor Module

Provides action execution capabilities.
Toggle MOCK_EXECUTION to switch between mock and real execution.
"""
from .mock_executor import (
    execute,
    print_agent_decision,
    print_action_plan
)

# ============================================================================
# EXECUTION MODE FLAG
# ============================================================================
# Set to True for mock execution (no C# required)
# Set to False to send actions to real C# executor
MOCK_EXECUTION = True

__all__ = [
    'execute',
    'print_agent_decision',
    'print_action_plan',
    'MOCK_EXECUTION'
]
