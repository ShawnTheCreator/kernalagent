"""
Tiered Verification Strategy

Determines when vision is needed vs cheap checks.
Uses UIElementFinder (C#) for accessibility-based verification.

Risk Levels:
- LOW: No vision needed (process checks, UIElementFinder)
- MEDIUM: Vision only if cheap check fails
- HIGH: Always use vision (ambiguous targets)
"""

import time
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    LOW = "low"      # No vision needed
    MEDIUM = "medium"  # Vision if cheap check fails
    HIGH = "high"    # Always vision


# Action risk classifications
ACTION_RISK = {
    # LOW - Use UIElementFinder / process checks (NO VISION)
    "open_app": RiskLevel.LOW,
    "close_app": RiskLevel.LOW,
    "type_text": RiskLevel.LOW,
    "wait": RiskLevel.LOW,
    "scroll": RiskLevel.LOW,
    "press_key": RiskLevel.LOW,
    "hotkey": RiskLevel.LOW,
    "volume_up": RiskLevel.LOW,
    "volume_down": RiskLevel.LOW,
    "volume_mute": RiskLevel.LOW,
    "brightness_up": RiskLevel.LOW,
    "brightness_down": RiskLevel.LOW,
    "minimize_window": RiskLevel.LOW,
    "maximize_window": RiskLevel.LOW,
    "alt_tab": RiskLevel.LOW,
    "show_desktop": RiskLevel.LOW,
    "copy": RiskLevel.LOW,
    "paste": RiskLevel.LOW,
    "cut": RiskLevel.LOW,
    "undo": RiskLevel.LOW,
    "redo": RiskLevel.LOW,
    "save": RiskLevel.LOW,
    "select_all": RiskLevel.LOW,
    "new_tab": RiskLevel.LOW,
    "close_tab": RiskLevel.LOW,
    "refresh": RiskLevel.LOW,
    "go_back": RiskLevel.LOW,
    "go_forward": RiskLevel.LOW,
    "media_play_pause": RiskLevel.LOW,
    "media_next": RiskLevel.LOW,
    "media_previous": RiskLevel.LOW,
    "screenshot": RiskLevel.LOW,
    
    # UIElementFinder handles these (accessibility-based, no vision)
    "click_button": RiskLevel.LOW,
    "click_menu": RiskLevel.LOW,
    "type_in_element": RiskLevel.LOW,
    
    # MEDIUM - Check window/element state first, vision if fail
    "navigate": RiskLevel.MEDIUM,
    "click": RiskLevel.MEDIUM,  # If has x,y coords
    "search": RiskLevel.MEDIUM,
    
    # HIGH - Always need vision (ambiguous targets)
    "click_element": RiskLevel.HIGH,
    "find_and_click": RiskLevel.HIGH,
    "vision_guided": RiskLevel.HIGH,
    "verify_goal": RiskLevel.HIGH,
}

# Cheap verification methods (provided by C# UIElementFinder/SmartExecutor)
CHEAP_CHECKS = {
    "open_app": "check_process_exists",
    "navigate": "check_window_title_changed",
    "click_button": "check_button_exists",
    "click_menu": "check_menu_item_exists",
    "type_text": "check_focus_exists",
}

# Vision throttling to prevent API abuse
VISION_COOLDOWN = 2.0  # seconds between vision calls
_last_vision_call = 0.0


def get_risk_level(action: str) -> RiskLevel:
    """Get the risk level for an action."""
    return ACTION_RISK.get(action, RiskLevel.MEDIUM)


def should_use_vision(
    action: str, 
    cheap_check_passed: bool = True,
    requires_vision_targeting: bool = False,
    has_coordinates: bool = False
) -> bool:
    """
    Determine if vision is needed for this action.
    
    Args:
        action: The action type
        cheap_check_passed: Whether the cheap check (UIElementFinder) passed
        requires_vision_targeting: If step was marked for vision (ambiguous target)
        has_coordinates: If the step already has x,y coordinates
    
    Returns:
        True if vision should be used
    """
    # If explicitly marked for vision targeting, always use vision
    if requires_vision_targeting:
        logger.info(f"[VERIFY] {action} requires_vision_targeting=True → USE VISION")
        return True
    
    risk = get_risk_level(action)
    
    if risk == RiskLevel.LOW:
        logger.debug(f"[VERIFY] {action} is LOW risk → NO VISION")
        return False
    elif risk == RiskLevel.HIGH:
        # If we already have coordinates, might not need vision
        if has_coordinates:
            logger.debug(f"[VERIFY] {action} is HIGH risk but has coords → NO VISION")
            return False
        logger.info(f"[VERIFY] {action} is HIGH risk → USE VISION")
        return True
    else:  # MEDIUM
        if not cheap_check_passed:
            logger.info(f"[VERIFY] {action} cheap check failed → USE VISION")
            return True
        logger.debug(f"[VERIFY] {action} cheap check passed → NO VISION")
        return False


def can_call_vision() -> bool:
    """
    Check vision throttle - prevent too many API calls.
    
    Returns:
        True if vision can be called (cooldown elapsed)
    """
    global _last_vision_call
    now = time.time()
    if now - _last_vision_call >= VISION_COOLDOWN:
        _last_vision_call = now
        return True
    
    remaining = VISION_COOLDOWN - (now - _last_vision_call)
    logger.warning(f"[VERIFY] Vision throttled, {remaining:.1f}s remaining")
    return False


def get_cheap_check(action: str) -> Optional[str]:
    """Get the cheap check method name for an action."""
    return CHEAP_CHECKS.get(action)


def is_ambiguous_target(target: str) -> bool:
    """
    Check if a target description is ambiguous and needs vision.
    
    Examples of ambiguous: "any video", "first result", "a button"
    Examples of specific: "Save", "File", "Submit"
    """
    if not target:
        return False
    
    target_lower = target.lower()
    
    AMBIGUOUS_PHRASES = [
        "any", "first", "a video", "a result", "one of", 
        "something", "the video", "a button", "some", 
        "random", "next", "previous"
    ]
    
    for phrase in AMBIGUOUS_PHRASES:
        if phrase in target_lower:
            return True
    
    return False
