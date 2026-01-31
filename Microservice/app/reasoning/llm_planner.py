"""
LLM-First Planner - Unified Planning Pipeline

Replaces if-else logic with:
    Intent Analyzer → Tool Registry → Context Memory → Executor Steps

This is the main entry point for the new architecture.
"""

import os
import re
import logging
import sys
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

# Setup logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Feature flag for gradual rollout
USE_LLM_FIRST = os.getenv("USE_LLM_FIRST", "true").lower() == "true"


def preprocess_command(command: str) -> str:
    """
    Preprocess command to help LLM parse correctly.
    Converts 'type X and Y' → 'type X. Then Y'
    """
    if " and " not in command.lower():
        return command

    original = command

    # Pattern: "type X and [verb]" → "type X. Then [verb]"
    command = re.sub(
        r'\btype\s+([^a]+?)\s+and\s+(press|click|save|open)',
        r'type \1. Then \2',
        command,
        flags=re.IGNORECASE
    )

    if command != original:
        logger.info(f"[PREPROCESSOR] '{original}' → '{command}'")

    return command


def _try_build_entertainment_steps(
    command: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower().strip()

    media_only_map = {
        "pause": "media_play_pause",
        "play": "media_play_pause",
        "play pause": "media_play_pause",
        "play/pause": "media_play_pause",
        "resume": "media_play_pause",
        "next": "media_next",
        "next song": "media_next",
        "next track": "media_next",
        "previous": "media_previous",
        "previous song": "media_previous",
        "previous track": "media_previous",
        "stop": "media_stop",
        "stop music": "media_stop",
    }
    if lower in media_only_map:
        return [{"action": media_only_map[lower]}]

    is_spotify = "spotify" in lower
    is_yt_music = any(k in lower for k in ["yt music", "youtube music", "youtubemusic", "music.youtube", "music youtube"])
    is_yt = "youtube" in lower or "yt " in (lower + " ")

    if not lower.startswith("play "):
        return None

    if not (is_spotify or is_yt_music or is_yt):
        return None

    query = re.sub(r"^play\s+", "", cmd, flags=re.IGNORECASE).strip()

    query = re.sub(r"\b(on|in|from)\s+(youtube\s+music|yt\s+music|youtube|spotify)\b", "", query, flags=re.IGNORECASE).strip()
    query = re.sub(r"\b(youtube\s+music|yt\s+music|youtube|spotify)\b", "", query, flags=re.IGNORECASE).strip()
    query = query.strip(" -–—:")

    if not query:
        return None

    if is_spotify:
        search_url = f"https://open.spotify.com/search/{quote_plus(query)}"
        click_target = "first result"
    else:
        search_url = f"https://music.youtube.com/search?q={quote_plus(query)}"
        click_target = "first song" if ("song" in lower or "music" in lower or is_yt_music) else "first result"

    pref = ((context or {}).get("preferences") or {}).get("default_browser")
    browser = "chrome"
    if pref in ("edge", "msedge"):
        browser = "msedge"
    elif pref in ("chrome", "firefox"):
        browser = pref

    return [
        {"action": "open_app", "target": f"{browser}.exe"},
        {"action": "navigate", "url": search_url},
        {"action": "wait", "ms": 2200},
        {
            "action": "click_element",
            "target": click_target,
            "requires_vision_targeting": True,
        },
        {"action": "wait", "ms": 1200},
    ]


def _try_build_form_fill_steps(command: str) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower()
    if not any(term in lower for term in ["fill", "form", "apply", "submit"]):
        return None

    # Extract field/value pairs like "name John" or "email john@x.com"
    pairs: List[Dict[str, str]] = []
    pattern = r"\b(?P<label>name|email|phone|mobile|address|city|state|zip|postal|company|website|username|password)\s+(?P<value>[^,;\n]+)"
    for match in re.finditer(pattern, cmd, flags=re.IGNORECASE):
        label = (match.group("label") or "").strip()
        value = (match.group("value") or "").strip()
        if label and value:
            pairs.append({"label": label, "value": value})

    if not pairs:
        return None

    steps: List[Dict[str, Any]] = []
    for pair in pairs:
        label = pair["label"].title()
        steps.extend([
            {
                "action": "click_element",
                "target": label,
                "requires_vision_targeting": True,
            },
            {"action": "wait", "ms": 300},
            {"action": "type_text", "content": pair["value"]},
            {"action": "wait", "ms": 200},
        ])

    if "submit" in lower:
        steps.append({
            "action": "click_element",
            "target": "Submit",
            "requires_vision_targeting": True,
        })

    return steps


def _try_build_browser_settings_steps(
    command: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower().strip()
    if "settings" not in lower:
        return None

    browser = None
    if any(term in lower for term in ["chrome", "google chrome", "chrome browser"]):
        browser = "chrome"
    elif any(term in lower for term in ["edge", "microsoft edge", "msedge"]):
        browser = "msedge"
    elif "browser" in lower:
        pref = ((context or {}).get("preferences") or {}).get("default_browser")
        if pref in ("chrome", "edge", "msedge", "firefox"):
            browser = "msedge" if pref == "edge" else pref

    if not browser:
        return None

    focused = ((context or {}).get("focused_process") or "").lower()
    active_app = ((context or {}).get("active_app") or "").lower()
    has_browser_focus = browser in focused or browser in active_app

    steps: List[Dict[str, Any]] = []
    if not has_browser_focus:
        steps.append({"action": "open_app", "target": f"{browser}.exe"})
        steps.append({"action": "wait", "ms": 700})

    steps.extend([
        {"action": "hotkey", "content": "ctrl+l"},
        {"action": "type_text", "content": f"{browser}://settings"},
        {"action": "press_key", "content": "enter"},
        {"action": "wait", "ms": 1500},
    ])

    return steps


def _should_skip_cache(command: str) -> bool:
    cmd = (command or "").lower()
    if not cmd:
        return False

    if any(term in cmd for term in ["whatsapp", "telegram", "discord", "slack"]):
        return True

    if "email" in cmd or "mail" in cmd:
        return True

    if "login" in cmd or "sign in" in cmd:
        return True

    return False


def _extract_message_parts(command: str) -> Optional[Dict[str, str]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower()
    if not any(term in lower for term in ["send", "message", "text", "dm"]):
        return None

    patterns = [
        r"\b(?:send|message|text|dm)\s+(?P<body>.+?)\s+to\s+(?P<recipient>.+)$",
        r"\b(?:send|message|text|dm)\s+(?P<recipient>.+?)\s+(?:saying|message|text)\s+(?P<body>.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, cmd, flags=re.IGNORECASE)
        if match:
            recipient = (match.group("recipient") or "").strip()
            body = (match.group("body") or "").strip()
            if recipient and body:
                return {"recipient": recipient, "body": body}

    return None


def _try_build_messaging_steps(command: str) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower()
    platform = None
    for name in ["whatsapp", "telegram", "discord", "slack"]:
        if name in lower:
            platform = name
            break

    if not platform:
        return None

    parts = _extract_message_parts(cmd)
    if not parts:
        return None

    tokens = re.findall(r"[a-z0-9]+", lower)
    has_app_pair = "app" in tokens and any(p in tokens for p in ["whatsapp", "telegram", "discord", "slack"])
    prefer_desktop = "desktop" in tokens or "application" in tokens or has_app_pair

    config = {
        "whatsapp": {
            "exe": "whatsapp.exe",
            "fallback": "https://web.whatsapp.com",
            "search": None,
        },
        "telegram": {
            "exe": "telegram.exe",
            "fallback": "https://web.telegram.org",
            "search": "ctrl+f",
        },
        "discord": {
            "exe": "discord.exe",
            "fallback": "https://discord.com/app",
            "search": "ctrl+k",
        },
        "slack": {
            "exe": "slack.exe",
            "fallback": "https://app.slack.com/client",
            "search": "ctrl+k",
        },
    }

    cfg = config.get(platform)
    if not cfg:
        return None

    steps: List[Dict[str, Any]] = []

    if prefer_desktop:
        steps.extend([
            {
                "action": "open_app",
                "target": cfg["exe"],
                "fallback_url": cfg["fallback"],
            },
            {"action": "wait", "ms": 2000},
        ])
    else:
        steps.extend([
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": cfg["fallback"]},
            {"action": "wait", "ms": 2200},
        ])

    if cfg.get("search"):
        steps.append({"action": "hotkey", "content": cfg["search"]})
    else:
        steps.append({
            "action": "click_element",
            "target": "Search",
            "requires_vision_targeting": True,
        })

    steps.extend([
        {"action": "type_text", "content": parts["recipient"]},
        {"action": "press_key", "content": "enter"},
        {"action": "wait", "ms": 700},
        {"action": "type_text", "content": parts["body"]},
        {"action": "press_key", "content": "enter"},
    ])

    return steps


def _try_build_email_steps(command: str) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower()
    if "email" not in lower and "mail" not in lower:
        return None

    if not any(term in lower for term in ["send", "compose", "draft"]):
        return None

    to_match = re.search(r"\bto\s+(.+?)(?:\s+subject\b|\s+body\b|$)", cmd, flags=re.IGNORECASE)
    subject_match = re.search(r"\bsubject\s+(.+?)(?:\s+body\b|$)", cmd, flags=re.IGNORECASE)
    body_match = re.search(r"\bbody\s+(.+)$", cmd, flags=re.IGNORECASE)

    recipient = (to_match.group(1).strip() if to_match else "")
    subject = (subject_match.group(1).strip() if subject_match else "")
    body = (body_match.group(1).strip() if body_match else "")

    if not recipient or not body:
        return None

    uses_outlook = "outlook" in lower
    uses_gmail = "gmail" in lower

    steps: List[Dict[str, Any]] = []

    if uses_outlook:
        steps.extend([
            {
                "action": "open_app",
                "target": "outlook.exe",
                "fallback_url": "https://outlook.office.com/mail/",
            },
            {"action": "wait", "ms": 2000},
            {"action": "hotkey", "content": "ctrl+n"},
            {"action": "wait", "ms": 700},
            {"action": "type_text", "content": recipient},
            {"action": "press_key", "content": "tab"},
            {"action": "type_text", "content": subject},
            {"action": "press_key", "content": "tab"},
            {"action": "press_key", "content": "tab"},
            {"action": "type_text", "content": body},
            {"action": "hotkey", "content": "ctrl+enter"},
        ])
    else:
        gmail_url = "https://mail.google.com/" if uses_gmail or "mail" in lower else "https://mail.google.com/"
        steps.extend([
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": gmail_url},
            {"action": "wait", "ms": 2200},
            {
                "action": "click_element",
                "target": "Compose",
                "requires_vision_targeting": True,
            },
            {"action": "wait", "ms": 600},
            {"action": "type_text", "content": recipient},
            {"action": "press_key", "content": "tab"},
            {"action": "type_text", "content": subject},
            {"action": "press_key", "content": "tab"},
            {"action": "type_text", "content": body},
            {"action": "hotkey", "content": "ctrl+enter"},
        ])

    return steps


def _try_build_login_steps(command: str) -> Optional[List[Dict[str, Any]]]:
    cmd = (command or "").strip()
    if not cmd:
        return None

    lower = cmd.lower()
    if "login" not in lower and "sign in" not in lower:
        return None

    platform = None
    for name in ["whatsapp", "telegram", "discord", "slack", "outlook", "gmail", "email"]:
        if name in lower:
            platform = "email" if name in ("email", "gmail", "outlook") else name
            break

    if not platform:
        return None

    try:
        from app.core.user_credentials import load_user_credentials
    except Exception:
        return None

    credentials = load_user_credentials()
    creds = credentials.get(platform)
    if not creds:
        return None

    login_targets = {
        "whatsapp": ("whatsapp.exe", "https://web.whatsapp.com"),
        "telegram": ("telegram.exe", "https://web.telegram.org"),
        "discord": ("discord.exe", "https://discord.com/login"),
        "slack": ("slack.exe", "https://slack.com/signin"),
        "email": ("outlook.exe", "https://outlook.office.com/mail/"),
    }

    tokens = re.findall(r"[a-z0-9]+", lower)
    has_app_pair = "app" in tokens and any(
        p in tokens for p in ["whatsapp", "telegram", "discord", "slack", "outlook", "gmail", "email"]
    )
    prefer_desktop = "desktop" in tokens or "application" in tokens or has_app_pair
    exe, fallback = login_targets.get(platform, ("chrome.exe", ""))

    steps: List[Dict[str, Any]] = []
    if prefer_desktop:
        steps.extend([
            {"action": "open_app", "target": exe, "fallback_url": fallback},
            {"action": "wait", "ms": 2000},
        ])
    else:
        steps.extend([
            {"action": "open_app", "target": "chrome.exe"},
            {"action": "navigate", "url": fallback},
            {"action": "wait", "ms": 2200},
        ])

    steps.extend([
        {"action": "click_element", "target": "Email", "requires_vision_targeting": True},
        {"action": "type_text", "content": creds.get("email", "")},
        {"action": "press_key", "content": "tab"},
        {"action": "type_text", "content": creds.get("password", "")},
        {"action": "press_key", "content": "enter"},
    ])

    return steps


async def plan_command(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Main planning function - LLM-first with intelligent fallbacks.
    
    Pipeline:
    0. Preprocess command (fix 'type X and Y')
    1. Check for contextual commands ("do that again")
    1.5. Check for agent match (NEW - Janitor, etc.)
    2. Check plan cache (skip LLM if cached)
    3. Analyze intent with LLM (Gemini → Groq)
    4. Convert to executor steps
    5. Cache successful plan
    6. Update context
    
    Args:
        command: User's natural language command
        session_id: Session ID for context
    
    Returns:
        List of executor-ready action dicts
    """
    from app.reasoning.intent_analyzer import analyze_command
    from app.executor.tools import convert_plan_to_executor_steps
    from app.memory.context import (
        get_context_for_llm,
        is_contextual_command,
        resolve_contextual_command,
        update_session,
    )
    from app.core.plan_cache import get_plan_cache
    
    logger.info(f"[PLANNER] ========== PROCESSING COMMAND ==========")
    logger.info(f"[PLANNER] Command: '{command}'")
    logger.info(f"[PLANNER] Session: {session_id}")
    
    # ===== Step 0: Preprocess Command =====
    command = preprocess_command(command)

    context = get_context_for_llm(session_id)

    try:
        entertainment = _try_build_entertainment_steps(command, context)
        if entertainment:
            logger.info(f"[PLANNER] Using deterministic entertainment plan ({len(entertainment)} steps)")
            update_session(session_id, command, entertainment[0])
            return entertainment
    except Exception as e:
        logger.warning(f"[PLANNER] Entertainment planner failed: {e}, continuing with LLM...")

    try:
        browser_settings = _try_build_browser_settings_steps(command, context)
        if browser_settings:
            logger.info(f"[PLANNER] Using browser settings shortcut ({len(browser_settings)} steps)")
            update_session(session_id, command, browser_settings[0])
            return browser_settings
    except Exception as e:
        logger.warning(f"[PLANNER] Browser settings shortcut failed: {e}, continuing with LLM...")

    try:
        login_steps = _try_build_login_steps(command)
        if login_steps:
            logger.info(f"[PLANNER] Using deterministic login plan ({len(login_steps)} steps)")
            update_session(session_id, command, login_steps[0])
            return login_steps
    except Exception as e:
        logger.warning(f"[PLANNER] Login planner failed: {e}, continuing with LLM...")

    try:
        messaging_steps = _try_build_messaging_steps(command)
        if messaging_steps:
            logger.info(f"[PLANNER] Using deterministic messaging plan ({len(messaging_steps)} steps)")
            update_session(session_id, command, messaging_steps[0])
            return messaging_steps
    except Exception as e:
        logger.warning(f"[PLANNER] Messaging planner failed: {e}, continuing with LLM...")

    try:
        email_steps = _try_build_email_steps(command)
        if email_steps:
            logger.info(f"[PLANNER] Using deterministic email plan ({len(email_steps)} steps)")
            update_session(session_id, command, email_steps[0])
            return email_steps
    except Exception as e:
        logger.warning(f"[PLANNER] Email planner failed: {e}, continuing with LLM...")

    try:
        form_steps = _try_build_form_fill_steps(command)
        if form_steps:
            logger.info(f"[PLANNER] Using deterministic form fill plan ({len(form_steps)} steps)")
            update_session(session_id, command, form_steps[0])
            return form_steps
    except Exception as e:
        logger.warning(f"[PLANNER] Form fill planner failed: {e}, continuing with LLM...")
    
    # ===== Step 1: Check Contextual Commands =====
    if is_contextual_command(command):
        resolved = resolve_contextual_command(command, session_id)
        if resolved:
            logger.info(f"[PLANNER] Resolved contextual command: {resolved}")
            # Update context and return
            update_session(session_id, command, resolved)
            return [resolved]
    
    # ===== Step 1.5: Check for Agent Match (NEW) =====
    try:
        from app.agents.agent_planner import should_route_to_agent, get_agent_for_intent
        
        agent_name = await should_route_to_agent(command)
        if agent_name:
            logger.info(f"[PLANNER] 🤖 Agent matched: {agent_name}")
            agent = await get_agent_for_intent(command)
            
            if agent:
                logger.info(f"[PLANNER] Delegating to {agent.name}...")
                
                # Run agent's analyze -> plan lifecycle
                context = {"intent": command, "session_id": session_id}
                analysis = await agent.analyze(context)
                plan = await agent.plan(analysis)

                # Always return a single meta-step when an agent matches.
                # IMPORTANT: even if the agent produces 0 executable actions, the agent may
                # still have produced useful findings (e.g., a health report). We must not
                # fall through into UI automation planning.
                summary = None
                try:
                    findings = getattr(analysis, "findings", {}) or {}
                    health_report = findings.get("health_report", {})
                    
                    # Generate detailed, intent-specific summary
                    if isinstance(health_report, dict):
                        # Extract detailed metrics
                        cpu_info = health_report.get("cpu", {})
                        memory_info = health_report.get("memory", {})
                        temp_info = health_report.get("temperature", {})
                        disk_info = health_report.get("disk", {})
                        network_info = health_report.get("network", {})
                        
                        # Build detailed summary based on intent
                        intent_lower = command.lower()
                        
                        if "metrics" in intent_lower or "real-time" in intent_lower:
                            # Real-time metrics format
                            cpu_pct = cpu_info.get("percent_total", 0)
                            mem_pct = ((memory_info.get("virtual", {})).get("percent_used", 0))
                            temp = temp_info.get("max_temp", "N/A")
                            
                            # Get disk usage from new structure
                            disk_usage = 0
                            if disk_info and disk_info.get("usage"):
                                c_drive = disk_info["usage"].get("c", {})
                                disk_usage = c_drive.get("percent_used", 0)
                            
                            # Get network rates from new structure
                            net_sent = network_info.get("bytes_sent_per_sec", 0)
                            net_recv = network_info.get("bytes_recv_per_sec", 0)
                            
                            summary = (
                                f"📊 Real-time System Metrics:\n"
                                f"• CPU: {cpu_pct}% (cores: {cpu_info.get('cores', 'N/A')})\n"
                                f"• RAM: {mem_pct}% (used: {memory_info.get('virtual', {}).get('used_gb', 'N/A')}GB / {memory_info.get('virtual', {}).get('total_gb', 'N/A')}GB)\n"
                                f"• Temperature: {temp}°C\n"
                                f"• Disk C: {disk_usage}% used\n"
                                f"• Network: ↑{net_sent/1024:.1f}KB/s ↓{net_recv/1024:.1f}KB/s"
                            )
                        elif "temperature" in intent_lower or "thermal" in intent_lower:
                            # Temperature-focused summary
                            temps = temp_info.get("sensors", {})
                            temp_list = [f"{name}: {t}°C" for name, t in temps.items() if isinstance(t, (int, float))]
                            summary = (
                                f"🌡️ Thermal Status:\n"
                                f"• Max Temperature: {temp_info.get('max_temp', 'N/A')}°C\n"
                                f"• Sensors: {', '.join(temp_list) if temp_list else 'N/A'}\n"
                                f"• Fan Status: {temp_info.get('fan_status', 'N/A')}"
                            )
                        elif "cpu" in intent_lower:
                            # CPU-focused summary
                            summary = (
                                f"⚡ CPU Performance:\n"
                                f"• Total Usage: {cpu_info.get('percent_total', 0)}%\n"
                                f"• Cores: {cpu_info.get('cores', 'N/A')}\n"
                                f"• Frequency: {cpu_info.get('frequency', 'N/A')} GHz\n"
                                f"• Load Average: {cpu_info.get('load_average', 'N/A')}"
                            )
                        elif "memory" in intent_lower or "ram" in intent_lower:
                            # Memory-focused summary
                            virt_mem = memory_info.get("virtual", {})
                            phys_mem = memory_info.get("physical", {})
                            summary = (
                                f"💾 Memory Usage:\n"
                                f"• Virtual: {virt_mem.get('percent_used', 0)}% ({virt_mem.get('used_gb', 'N/A')}GB / {virt_mem.get('total_gb', 'N/A')}GB)\n"
                                f"• Physical: {phys_mem.get('percent_used', 0)}% ({phys_mem.get('used_gb', 'N/A')}GB / {phys_mem.get('total_gb', 'N/A')}GB)\n"
                                f"• Available: {virt_mem.get('available_gb', 'N/A')}GB"
                            )
                        elif "disk" in intent_lower or "storage" in intent_lower:
                            # Disk-focused summary
                            disk_lines = []
                            if disk_info and disk_info.get("usage"):
                                for drive, info in disk_info["usage"].items():
                                    disk_lines.append(f"• {drive.upper()}: {info.get('percent_used', 0)}% ({info.get('used_gb', 'N/A')}GB / {info.get('total_gb', 'N/A')}GB)")
                            summary = f"💿 Disk Usage:\n" + "\n".join(disk_lines) if disk_lines else "💿 Disk information unavailable"
                        elif "network" in intent_lower:
                            # Network-focused summary
                            summary = (
                                f"🌐 Network Activity:\n"
                                f"• Upload: {network_info.get('bytes_sent_per_sec', 0):.1f}KB/s\n"
                                f"• Download: {network_info.get('bytes_recv_per_sec', 0):.1f}KB/s\n"
                                f"• Total Sent: {network_info.get('bytes_sent_total', 0):.1f}MB\n"
                                f"• Total Received: {network_info.get('bytes_recv_total', 0):.1f}MB"
                            )
                        else:
                            # Default comprehensive summary
                            cpu_pct = cpu_info.get("percent_total", 0)
                            mem_pct = ((memory_info.get("virtual", {})).get("percent_used", 0))
                            temp = temp_info.get("max_temp", "N/A")
                            
                            # Get disk usage from new structure
                            disk_usage = 0
                            if disk_info and disk_info.get("usage"):
                                c_drive = disk_info["usage"].get("c", {})
                                disk_usage = c_drive.get("percent_used", 0)
                            
                            # Get network rates from new structure
                            net_sent = network_info.get("bytes_sent_per_sec", 0)
                            net_recv = network_info.get("bytes_recv_per_sec", 0)
                            
                            summary = (
                                f"🖥️ System Health Report:\n"
                                f"• CPU: {cpu_pct}% | RAM: {mem_pct}% | Temp: {temp}°C\n"
                                f"• Disk: {disk_usage}% used\n"
                                f"• Network: ↑{net_sent/1024:.1f}KB/s ↓{net_recv/1024:.1f}KB/s"
                            )
                    else:
                        # Fallback to simple format
                        summary = f"{agent.name}: {len(plan.actions)} actions ready"
                        
                except Exception as e:
                    logger.warning(f"[PLANNER] Failed to generate detailed summary: {e}")
                    summary = f"{agent.name}: system analysis complete"

                # Return a non-executable step so the Desktop app can surface the result
                # without attempting UI automation / recovery.
                step = {
                    "action": "conversation",
                    "content": summary or f"{agent.name}: plan ready ({len(plan.actions)} actions)",
                }

                logger.info(f"[PLANNER] Agent plan ready with {len(plan.actions)} actions")
                return [step]
                    
    except Exception as e:
        logger.warning(f"[PLANNER] Agent routing failed: {e}, continuing with LLM...")
    
    # ===== Step 2: Check Plan Cache =====
    cache = get_plan_cache()
    if _should_skip_cache(command):
        cache.invalidate(command)
        cached_plan = None
    else:
        cached_plan = cache.get(command)
    if cached_plan:
        logger.info(f"[PLANNER] CACHE HIT! Skipping LLM call")
        logger.info(f"[PLANNER] Returning {len(cached_plan)} cached steps")
        return cached_plan
    
    # ===== Step 3: Analyze Intent with LLM =====
    logger.info(f"[PLANNER] Cache miss - calling LLM to analyze intent...")
    plan = await analyze_command(command, context)
    
    
    logger.info(f"[PLANNER] LLM Response: intent={plan.get('intent')}, confidence={plan.get('confidence')}")
    logger.info(f"[PLANNER] LLM reasoning: {plan.get('reasoning', 'N/A')}")
    
    # Check confidence threshold
    if plan.get("confidence", 0) < 0.5:
        logger.warning(f"[PLANNER] Low confidence ({plan.get('confidence')}), plan may be unreliable")
    
    # Check for actions - if we have actions, USE THEM even if intent is "unclear"
    actions = plan.get("actions", [])
    logger.info(f"[PLANNER] LLM returned {len(actions)} actions")
    for i, action in enumerate(actions):
        logger.info(f"[PLANNER]   Action {i+1}: {action}")
    
    if not actions:
        logger.warning(f"[PLANNER] LLM returned no actions, returning empty plan")
        return []
    
    # ===== Step 5: Convert to Executor Steps =====
    executor_steps = convert_plan_to_executor_steps(plan)
    
    logger.info(f"[PLANNER] Generated {len(executor_steps)} executor steps:")
    for i, step in enumerate(executor_steps):
        logger.info(f"[PLANNER]   Step {i+1}: {step.get('action')} | {step}")
    
    # ===== Step 6: Cache Successful Plan =====
    if executor_steps and len(executor_steps) > 0 and not _should_skip_cache(command):
        cache.put(command, executor_steps)
    
    # ===== Step 7: Update Context =====
    if executor_steps:
        # Update with first action for context tracking
        update_session(session_id, command, executor_steps[0])
    
    logger.info(f"[PLANNER] ========== DONE ==========")
    return executor_steps


def mark_ambiguous_targets(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Mark steps that have ambiguous targets requiring vision-based resolution.
    
    Examples of ambiguous: "any video", "first result", "a button"  
    Examples of specific: "Save", "File > Open", "Submit"
    
    Args:
        steps: List of executor steps
        
    Returns:
        Same steps with 'requires_vision_targeting' flag added where needed
    """
    from app.agent.verification_strategy import is_ambiguous_target
    
    # Actions that ALWAYS need vision (inherently ambiguous)
    ALWAYS_VISION_ACTIONS = ["click_element", "find_and_click", "vision_guided"]
    
    # Actions that MAY need vision if target is ambiguous or no coords
    VISION_CANDIDATE_ACTIONS = ["click", "double_click", "right_click"]
    
    for step in steps:
        # Check target and content fields for ambiguity
        target = step.get("target", "") or ""
        content = step.get("content", "") or ""
        action = step.get("action", "")
        
        # click_element and find_and_click ALWAYS need vision
        # They are inherently meant for "find something and click it"
        if action in ALWAYS_VISION_ACTIONS:
            step["requires_vision_targeting"] = True
            logger.info(f"[PLANNER] Vision required (always): {action} → '{target}'")
            continue
        
        # For standard clicks, check if target is ambiguous
        if action in VISION_CANDIDATE_ACTIONS:
            if is_ambiguous_target(target) or is_ambiguous_target(content):
                step["requires_vision_targeting"] = True
                logger.info(f"[PLANNER] Vision required (ambiguous target): {action} → '{target or content}'")
                continue
            
            # If a click has no coordinates, it needs vision
            has_coords = step.get("x") is not None and step.get("y") is not None
            if not has_coords and target:
                step["requires_vision_targeting"] = True
                logger.info(f"[PLANNER] Vision required (no coords): {action} → '{target}'")
    
    return steps


async def plan_command_with_fallback(
    command: str,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Plan command with LLM. Returns vision-guided plan if LLM fails.
    
    NO DETERMINISTIC FALLBACK - removed to prevent bad multi-step parsing.
    Instead, returns a vision-guided plan that will use screen analysis.
    """
    logger.info(f"[PLANNER] plan_command_with_fallback called for: {command}")
    logger.info(f"[PLANNER] USE_LLM_FIRST={USE_LLM_FIRST}")
    
    # Try LLM-first planning (Gemini → Groq)
    if USE_LLM_FIRST:
        try:
            logger.info("[PLANNER] Calling plan_command...")
            steps = await plan_command(command, session_id)
            logger.info(f"[PLANNER] plan_command returned {len(steps)} steps")
            
            if steps:
                # Mark any steps with ambiguous targets for vision resolution
                steps = mark_ambiguous_targets(steps)
                return steps
                
            logger.warning(f"[PLANNER] LLM returned empty plan")
        except Exception as e:
            logger.error(f"[PLANNER] LLM planning error: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.warning("[PLANNER] USE_LLM_FIRST is False!")
    
    # ============================================================
    # NO DETERMINISTIC FALLBACK - Return vision-guided plan instead
    # ============================================================
    logger.warning(f"[PLANNER] LLM failed, returning vision-guided plan")
    
    # Return a special step that tells executor to use vision
    return [{
        "action": "vision_guided",
        "goal": command,
        "requires_vision_targeting": True,
        "reason": "LLM planning failed, using vision-guided execution"
    }]
