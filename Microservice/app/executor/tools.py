"""
Tool Registry - Maps tool names to action schemas.

This module defines all available automation tools that the Intent Analyzer can plan.
Each tool has a schema defining required/optional parameters.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


# ===== ACTION SCHEMA DEFINITIONS =====

class ActionSchema(BaseModel):
    """Base schema for an action."""
    tool: str
    action: str
    # Optional params populated by specific tools
    target: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    query: Optional[str] = None
    keys: Optional[str] = None
    amount: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    direction: Optional[str] = None


# ===== TOOL REGISTRY =====
# Maps LLM tool names to C# executor action names

TOOL_TO_ACTION_MAP: Dict[str, Dict[str, str]] = {
    # App Launcher
    "app_launcher": {
        "open": "open_app",
        "close": "close_app",
    },
    
    # Text Input
    "text_input": {
        "type": "type_text",
    },
    
    # Keyboard
    "keyboard": {
        "hotkey": "hotkey",
        "press": "press_key",
    },
    
    # Media Control
    "media_control": {
        "play_pause": "media_play_pause",
        "next": "media_next",
        "previous": "media_previous",
        "stop": "media_stop",
    },
    
    # Volume Control
    "volume_control": {
        "up": "volume_up",
        "down": "volume_down",
        "mute": "volume_mute",
    },
    
    # Brightness Control
    "brightness_control": {
        "up": "brightness_up",
        "down": "brightness_down",
    },
    
    # Browser
    "browser": {
        "navigate": "navigate",
        "search": "search_web",
        "new_tab": "new_tab",
        "close_tab": "close_tab",
        "refresh": "refresh",
        "back": "go_back",
        "forward": "go_forward",
    },
    
    # System
    "system": {
        "screenshot": "screenshot",
        "lock": "lock_screen",
        "sleep": "sleep",
        "shutdown": "shutdown",
        "restart": "restart",
    },
    
    # Window Control
    "window_control": {
        "minimize": "minimize_window",
        "maximize": "maximize_window",
        "restore": "restore_window",
        "alt_tab": "alt_tab",
        "show_desktop": "show_desktop",
    },
    
    # Clipboard
    "clipboard": {
        "copy": "copy",
        "paste": "paste",
        "cut": "cut",
    },
    
    # File Operations
    "file_ops": {
        "save": "save",
        "undo": "undo",
        "redo": "redo",
        "select_all": "select_all",
    },
    
    # Mouse
    "mouse": {
        "click": "click",
        "double_click": "double_click",
        "right_click": "right_click",
        "scroll": "scroll",
        "move": "move_mouse",
    },
    
    # Virtual Desktop
    "virtual_desktop": {
        "switch_left": "switch_desktop_left",
        "switch_right": "switch_desktop_right",
        "new": "new_desktop",
        "close": "close_desktop",
        "task_view": "task_view",
    },
}


def convert_to_executor_action(llm_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert LLM action format to C# executor format.
    
    LLM outputs: {"tool": "app_launcher", "action": "open", "target": "chrome"}
    Executor needs: {"action": "open_app", "target": "chrome.exe"}
    """
    tool = llm_action.get("tool", "")
    action = llm_action.get("action", "")
    
    # Get the mapped action name
    if tool in TOOL_TO_ACTION_MAP:
        action_name = TOOL_TO_ACTION_MAP[tool].get(action, action)
    else:
        # Unknown tool, pass through
        action_name = action
    
    # Build executor action
    executor_action = {
        "action": action_name
    }
    
    # Map parameters
    if "target" in llm_action:
        target = llm_action["target"]
        # Ensure .exe extension for app names
        if tool == "app_launcher" and target and not target.endswith(".exe"):
            target = f"{target}.exe"
        executor_action["target"] = target
    
    if "content" in llm_action:
        executor_action["content"] = llm_action["content"]
    
    if "url" in llm_action:
        executor_action["url"] = llm_action["url"]
    
    if "query" in llm_action:
        executor_action["query"] = llm_action["query"]
    
    if "keys" in llm_action:
        executor_action["content"] = llm_action["keys"]  # Map to content for hotkey
    
    if "amount" in llm_action:
        executor_action["amount"] = llm_action["amount"]
    
    if "x" in llm_action:
        executor_action["x"] = llm_action["x"]
    
    if "y" in llm_action:
        executor_action["y"] = llm_action["y"]
    
    if "direction" in llm_action:
        executor_action["target"] = llm_action["direction"]  # Map direction to target for scroll
    
    return executor_action


def convert_plan_to_executor_steps(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert full LLM plan to list of executor steps.
    
    Args:
        plan: LLM output with "actions" list
    
    Returns:
        List of executor-ready action dicts
    """
    actions = plan.get("actions", [])
    return [convert_to_executor_action(a) for a in actions]


def get_supported_tools() -> List[str]:
    """Get list of all supported tool names."""
    return list(TOOL_TO_ACTION_MAP.keys())


def get_tool_actions(tool: str) -> List[str]:
    """Get available actions for a tool."""
    if tool in TOOL_TO_ACTION_MAP:
        return list(TOOL_TO_ACTION_MAP[tool].keys())
    return []
