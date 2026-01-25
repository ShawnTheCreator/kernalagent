"""
Agent Intelligence Module

Provides intelligent decision-making for the Kernal Agent.
"""
from .decision_engine import (
    decide_next_action,
    get_decision_for_gemini,
    select_best_skill,
    calculate_intent_similarity
)

from .failure_detector import (
    detect_failure,
    should_retry,
    log_failure_event,
    calculate_adjusted_confidence
)

__all__ = [
    'decide_next_action',
    'get_decision_for_gemini',
    'select_best_skill',
    'calculate_intent_similarity',
    'detect_failure',
    'should_retry',
    'log_failure_event',
    'calculate_adjusted_confidence'
]
