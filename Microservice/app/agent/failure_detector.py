"""
Failure Detection Module

Detects action failures by comparing expected vs actual vision signals.
Logs failures to Firebase for learning and analysis.
"""
from datetime import datetime
from typing import Optional

# Expected signal mappings for different action types
EXPECTED_SIGNALS = {
    "CLICK": ["SCREEN_CHANGED", "LAYOUT_CHANGE", "MINOR_UPDATE"],
    "TYPE": ["MINOR_UPDATE", "UI_STABLE"],
    "SCROLL": ["LAYOUT_CHANGE", "MINOR_UPDATE"],
    "WAIT": ["UI_STABLE", "MINOR_UPDATE"],
    "DONE": ["UI_STABLE"]
}


def detect_failure(
    action_type: str,
    expected_signal: Optional[str],
    actual_signal: str
) -> dict:
    """
    Detect if an action failed based on vision signal comparison.
    
    Args:
        action_type: The action that was performed (CLICK, TYPE, etc.)
        expected_signal: The expected vision signal (from skill steps)
        actual_signal: The actual vision signal observed
        
    Returns:
        Dictionary with failure detection results
    """
    result = {
        "failed": False,
        "severity": "none",
        "confidence_penalty": 0.0,
        "reason": "Action completed successfully"
    }
    
    # If we have an explicit expected signal, check it
    if expected_signal:
        if actual_signal != expected_signal:
            # Check if it's a close match
            if expected_signal in ("UI_STABLE", "MINOR_UPDATE") and \
               actual_signal in ("UI_STABLE", "MINOR_UPDATE"):
                result["severity"] = "minor"
                result["confidence_penalty"] = 0.05
                result["reason"] = f"Minor deviation: expected {expected_signal}, got {actual_signal}"
            else:
                result["failed"] = True
                result["severity"] = "major"
                result["confidence_penalty"] = 0.25
                result["reason"] = f"Signal mismatch: expected {expected_signal}, got {actual_signal}"
        return result
    
    # Use action-type based expectations
    acceptable_signals = EXPECTED_SIGNALS.get(action_type, ["UI_STABLE"])
    
    if actual_signal not in acceptable_signals:
        # SCREEN_CHANGED on a WAIT action is definitely a failure
        if action_type == "WAIT" and actual_signal == "SCREEN_CHANGED":
            result["failed"] = True
            result["severity"] = "major"
            result["confidence_penalty"] = 0.3
            result["reason"] = "Screen changed during WAIT - unexpected activity"
        
        # UI_STABLE after CLICK might indicate click didn't work
        elif action_type == "CLICK" and actual_signal == "UI_STABLE":
            result["failed"] = True
            result["severity"] = "moderate"
            result["confidence_penalty"] = 0.2
            result["reason"] = "No change after CLICK - action may have missed target"
        
        else:
            result["severity"] = "minor"
            result["confidence_penalty"] = 0.1
            result["reason"] = f"Unexpected signal {actual_signal} for {action_type}"
    
    return result


def should_retry(failure_result: dict, retry_count: int) -> bool:
    """
    Determine if an action should be retried based on failure severity.
    
    Args:
        failure_result: Result from detect_failure
        retry_count: Number of retries already attempted
        
    Returns:
        True if should retry, False otherwise
    """
    max_retries = {
        "none": 0,
        "minor": 1,
        "moderate": 2,
        "major": 3
    }
    
    severity = failure_result.get("severity", "none")
    return retry_count < max_retries.get(severity, 0)


def log_failure_event(
    skill_id: Optional[str],
    action_type: str,
    failure_result: dict,
    context: dict
) -> None:
    """
    Log failure event to Firebase for analysis.
    
    Args:
        skill_id: ID of the skill being executed (if any)
        action_type: The action that failed
        failure_result: Result from detect_failure
        context: Additional context (intent, step_index, etc.)
    """
    try:
        from app.db.firebase_client import get_firestore_client
        
        db = get_firestore_client()
        failures_ref = db.collection('failure_logs')
        
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "skill_id": skill_id,
            "action_type": action_type,
            "severity": failure_result.get("severity"),
            "reason": failure_result.get("reason"),
            "confidence_penalty": failure_result.get("confidence_penalty"),
            "context": context
        }
        
        failures_ref.add(event)
        print(f"[FAILURE LOG] Logged failure: {failure_result.get('reason')}")
        
    except Exception as e:
        # Don't let logging failures break the main flow
        print(f"[FAILURE LOG] Failed to log event: {e}")


def calculate_adjusted_confidence(
    base_confidence: float,
    failure_history: list,
    current_failure: Optional[dict] = None
) -> float:
    """
    Calculate adjusted confidence based on failure history.
    
    Args:
        base_confidence: Starting confidence level
        failure_history: List of recent failure results
        current_failure: Current failure result (if any)
        
    Returns:
        Adjusted confidence value
    """
    confidence = base_confidence
    
    # Apply current failure penalty
    if current_failure and current_failure.get("failed"):
        confidence -= current_failure.get("confidence_penalty", 0.15)
    
    # Apply historical penalty (diminishing)
    for i, failure in enumerate(failure_history[-5:]):  # Last 5 failures
        if failure.get("failed"):
            # Older failures have less impact
            age_factor = 0.5 ** (len(failure_history) - i - 1)
            confidence -= failure.get("confidence_penalty", 0.1) * age_factor * 0.5
    
    # Clamp to valid range
    return max(0.1, min(0.95, confidence))
