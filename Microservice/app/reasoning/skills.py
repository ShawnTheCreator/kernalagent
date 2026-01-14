"""
Gemini Reasoning Layer - Skills Registry

Defines the closed set of skills that Gemini can reference.
Any skill not in this registry will be rejected.
"""

from typing import Dict, List, Any

# Registered skills that Gemini can use
REGISTERED_SKILLS: Dict[str, Dict[str, Any]] = {
    # ===== App Control =====
    "Open Application": {
        "action": "open_app",
        "params": ["target"],
        "description": "Opens an application by name"
    },
    "Close Application": {
        "action": "close_app", 
        "params": ["target"],
        "description": "Closes an application by name"
    },
    
    # ===== Text Input =====
    "Type Text": {
        "action": "type_text",
        "params": ["text"],
        "description": "Types text into the focused application"
    },
    "Press Key": {
        "action": "press_key",
        "params": ["key"],
        "description": "Presses a keyboard key (enter, tab, escape, etc.)"
    },
    
    # ===== Navigation =====
    "Navigate URL": {
        "action": "navigate",
        "params": ["url"],
        "description": "Navigates to a URL in the browser"
    },
    "Search Web": {
        "action": "search_web",
        "params": ["query"],
        "description": "Searches Google for a query"
    },
    
    # ===== Window Management =====
    "Minimize Window": {
        "action": "minimize_window",
        "params": [],
        "description": "Minimizes the current window"
    },
    "Maximize Window": {
        "action": "maximize_window",
        "params": [],
        "description": "Maximizes the current window"
    },
    "Restore Window": {
        "action": "restore_window",
        "params": [],
        "description": "Restores a minimized/maximized window"
    },
    
    # ===== Volume Control =====
    "Volume Up": {
        "action": "volume_up",
        "params": ["amount"],
        "description": "Increases system volume"
    },
    "Volume Down": {
        "action": "volume_down",
        "params": ["amount"],
        "description": "Decreases system volume"
    },
    "Mute Volume": {
        "action": "volume_mute",
        "params": [],
        "description": "Toggles system mute"
    },
    
    # ===== System Commands =====
    "Lock Screen": {
        "action": "lock_screen",
        "params": [],
        "description": "Locks the computer"
    },
    "Take Screenshot": {
        "action": "screenshot",
        "params": [],
        "description": "Captures a screenshot"
    },
    "Sleep": {
        "action": "sleep",
        "params": [],
        "description": "Puts computer to sleep"
    },
    
    # ===== UI Interaction =====
    "Click Element": {
        "action": "click",
        "params": ["target"],
        "description": "Clicks on a UI element by label"
    },
    "Scroll Page": {
        "action": "scroll",
        "params": ["direction", "amount"],
        "description": "Scrolls the page up or down"
    },
    "Wait": {
        "action": "wait",
        "params": ["seconds"],
        "description": "Waits before the next action"
    },
}


def get_skill_names() -> List[str]:
    """Get list of all registered skill names."""
    return list(REGISTERED_SKILLS.keys())


def is_valid_skill(skill_name: str) -> bool:
    """Check if a skill name is registered."""
    return skill_name in REGISTERED_SKILLS


def get_skill_action(skill_name: str) -> str:
    """Get the action type for a skill."""
    skill = REGISTERED_SKILLS.get(skill_name)
    return skill["action"] if skill else None


def get_skills_for_prompt() -> str:
    """Generate skill descriptions for Gemini prompt."""
    lines = []
    for name, info in REGISTERED_SKILLS.items():
        params = info["params"]
        param_str = f" (params: {', '.join(params)})" if params else ""
        lines.append(f"- {name}: {info['description']}{param_str}")
    return "\n".join(lines)
