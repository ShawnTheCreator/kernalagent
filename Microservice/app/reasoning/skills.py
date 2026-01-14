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
    "Shutdown": {
        "action": "shutdown",
        "params": [],
        "description": "Shuts down the computer"
    },
    "Restart": {
        "action": "restart",
        "params": [],
        "description": "Restarts the computer"
    },
    
    # ===== Keyboard Shortcuts =====
    "Press Key": {
        "action": "press_key",
        "params": ["key"],
        "description": "Presses a key (enter, tab, escape, space, backspace, delete)"
    },
    "Hotkey": {
        "action": "hotkey",
        "params": ["keys"],
        "description": "Presses a keyboard shortcut like ctrl+c, alt+tab, win+d"
    },
    "Copy": {
        "action": "copy",
        "params": [],
        "description": "Copies selected content (Ctrl+C)"
    },
    "Paste": {
        "action": "paste",
        "params": [],
        "description": "Pastes clipboard content (Ctrl+V)"
    },
    "Cut": {
        "action": "cut",
        "params": [],
        "description": "Cuts selected content (Ctrl+X)"
    },
    "Undo": {
        "action": "undo",
        "params": [],
        "description": "Undoes last action (Ctrl+Z)"
    },
    "Redo": {
        "action": "redo",
        "params": [],
        "description": "Redoes last action (Ctrl+Y)"
    },
    "Select All": {
        "action": "select_all",
        "params": [],
        "description": "Selects all content (Ctrl+A)"
    },
    "Save": {
        "action": "save",
        "params": [],
        "description": "Saves current document (Ctrl+S)"
    },
    "Alt Tab": {
        "action": "alt_tab",
        "params": [],
        "description": "Switches to next window (Alt+Tab)"
    },
    "Show Desktop": {
        "action": "show_desktop",
        "params": [],
        "description": "Shows the desktop (Win+D)"
    },
    
    # ===== Mouse Control =====
    "Click": {
        "action": "click",
        "params": ["x", "y"],
        "description": "Clicks at screen coordinates"
    },
    "Double Click": {
        "action": "double_click",
        "params": ["x", "y"],
        "description": "Double clicks at screen coordinates"
    },
    "Right Click": {
        "action": "right_click",
        "params": ["x", "y"],
        "description": "Right clicks at screen coordinates"
    },
    "Move Mouse": {
        "action": "move_mouse",
        "params": ["x", "y"],
        "description": "Moves mouse to screen coordinates"
    },
    "Scroll Page": {
        "action": "scroll",
        "params": ["direction", "amount"],
        "description": "Scrolls the page up or down"
    },
    
    # ===== Media Control =====
    "Play Pause": {
        "action": "media_play_pause",
        "params": [],
        "description": "Toggles play/pause for media"
    },
    "Next Track": {
        "action": "media_next",
        "params": [],
        "description": "Skips to next track"
    },
    "Previous Track": {
        "action": "media_previous",
        "params": [],
        "description": "Goes to previous track"
    },
    "Stop Media": {
        "action": "media_stop",
        "params": [],
        "description": "Stops media playback"
    },
    
    # ===== Brightness =====
    "Brightness Up": {
        "action": "brightness_up",
        "params": ["amount"],
        "description": "Increases screen brightness"
    },
    "Brightness Down": {
        "action": "brightness_down",
        "params": ["amount"],
        "description": "Decreases screen brightness"
    },
    
    # ===== Browser Commands =====
    "New Tab": {
        "action": "new_tab",
        "params": [],
        "description": "Opens a new browser tab (Ctrl+T)"
    },
    "Close Tab": {
        "action": "close_tab",
        "params": [],
        "description": "Closes current browser tab (Ctrl+W)"
    },
    "Refresh Page": {
        "action": "refresh",
        "params": [],
        "description": "Refreshes the current page (F5)"
    },
    "Go Back": {
        "action": "go_back",
        "params": [],
        "description": "Goes back in browser history (Alt+Left)"
    },
    "Go Forward": {
        "action": "go_forward",
        "params": [],
        "description": "Goes forward in browser history (Alt+Right)"
    },
    
    # ===== Other =====
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
