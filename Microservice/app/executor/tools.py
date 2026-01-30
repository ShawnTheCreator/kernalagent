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
    state: Optional[str] = None


# ===== APP NAME ALIASES =====
# Maps common app names to Windows executables
APP_ALIASES: Dict[str, str] = {
    # IDEs
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "visual studio": "devenv",
    
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    
    # Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    
    # System
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    
    # Media
    "spotify": "spotify",
    "vlc": "vlc",
}


def normalize_app_name(app_name: str) -> str:
    """
    Normalize app name to Windows executable.
    
    Examples:
        "vscode" -> "code"
        "visual studio code" -> "code"
        "chrome" -> "chrome"
    """
    if not app_name:
        return app_name
    
    # Remove .exe if present for lookup
    lookup_name = app_name.lower().replace(".exe", "").strip()
    
    # Check aliases
    if lookup_name in APP_ALIASES:
        return APP_ALIASES[lookup_name]
    
    # Return original (without .exe, will be added later)
    return lookup_name


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
    
    # Wait/Delay
    "wait": {
        "wait": "wait",
    },
    
    # YouTube shortcuts
    "youtube": {
        "skip_ad": "youtube_skip_ad",
        "play": "youtube_play",
        "pause": "youtube_pause",
        "fullscreen": "youtube_fullscreen",
        "next_video": "youtube_next",
    },
    
    # UI Automation (Element-Based Actions)
    "ui_automation": {
        "click_button": "click_button",
        "click_menu": "click_menu",
        "click_element": "click_element",
        "find_and_click": "find_and_click",
        "type_in_element": "type_in_element",
        "get_ui_elements": "get_ui_elements",
    },
    
    # Skill Management (Recording & Playback)
    "skill_management": {
        "start_recording": "start_recording",
        "stop_recording": "stop_recording",
        "play_skill": "play_skill",
        "list_skills": "list_skills",
    },

    # System toggles (Quick Settings)
    "system_toggle": {
        "wifi": "toggle_quick_setting",
        "bluetooth": "toggle_quick_setting",
        "airplane_mode": "toggle_quick_setting",
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

    # System toggles: derive a stable UI label for Quick Settings
    if tool == "system_toggle":
        try:
            label_map = {
                "wifi": "Wi-Fi",
                "bluetooth": "Bluetooth",
                "airplane_mode": "Airplane mode",
            }
            executor_action["target"] = label_map.get(action, action)
        except Exception:
            executor_action["target"] = action
    
    # Map parameters
    if "target" in llm_action:
        target = llm_action["target"]
        # Normalize app names (vscode -> code, etc.)
        if tool == "app_launcher" and target:
            target = normalize_app_name(target)
            if not target.endswith(".exe"):
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

    if "state" in llm_action:
        executor_action["state"] = llm_action["state"]
    
    # UI Automation: map path parameter for click_menu
    if "path" in llm_action:
        executor_action["path"] = llm_action["path"]

    # Verification: pass through expected outcomes if provided
    if "expected" in llm_action and isinstance(llm_action.get("expected"), dict):
        executor_action["expected"] = llm_action["expected"]

    # ===== AUTO-EXPECTED DEFAULTS (hands-free accuracy) =====
    # If LLM didn't provide expected, add safe defaults for common actions.
    if "expected" not in executor_action:
        try:
            expected: Dict[str, Any] = {}

            # open_app: expect foreground title contains a stable substring
            if executor_action.get("action") == "open_app":
                tgt = (executor_action.get("target") or "").lower().strip()
                base = tgt.replace(".exe", "")
                # Keep this conservative: only a small set of known stable substrings
                stable = {
                    "chrome": "chrome",
                    "msedge": "edge",
                    "firefox": "firefox",
                    "notepad": "notepad",
                    "explorer": "file explorer",
                    "code": "visual studio code",
                    "wt": "terminal",
                    "cmd": "command prompt",
                    "powershell": "powershell",
                    "calc": "calculator",
                    "mspaint": "paint",
                }.get(base)

                if stable:
                    expected["window_title_contains"] = stable
                    expected["timeout_ms"] = 7000

            # navigate: expect domain keyword in title (best-effort)
            if executor_action.get("action") == "navigate":
                url = (executor_action.get("url") or "").strip().lower()
                # Extract host-ish token for simple expectations
                host_token = ""
                if url.startswith("http"):
                    try:
                        from urllib.parse import urlparse
                        host = urlparse(url).hostname or ""
                        host = host.replace("www.", "")
                        host_token = host.split(".")[0] if host else ""
                    except Exception:
                        host_token = ""
                else:
                    # if url is partial, just take first token
                    host_token = url.replace("www.", "").split(".")[0]

                if host_token and len(host_token) >= 3:
                    expected["window_title_contains"] = host_token
                    expected["timeout_ms"] = 8000

            # search_web: often updates title with query token; too brittle -> skip

            # type_in_element: best-effort focus verification
            if executor_action.get("action") == "type_in_element":
                tgt = (executor_action.get("target") or "").strip()
                if tgt:
                    expected["focused_element_name_contains"] = tgt
                    expected["timeout_ms"] = max(expected.get("timeout_ms", 0), 3000)

            # toggle_quick_setting: verify toggle state when desired state is provided
            if executor_action.get("action") == "toggle_quick_setting":
                tgt = (executor_action.get("target") or "").strip()
                desired = (executor_action.get("state") or "").strip().lower()
                if tgt:
                    expected["toggle_target"] = tgt
                    if desired in ("on", "off"):
                        expected["toggle_state"] = desired
                    expected["timeout_ms"] = max(expected.get("timeout_ms", 0), 7000)

            if expected:
                executor_action["expected"] = expected
        except Exception:
            pass
    
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
