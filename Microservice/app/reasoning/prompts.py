"""
Gemini Reasoning Layer - Prompt Templates

System and user prompts for planning and recovery.
Includes explicit examples to guide Gemini to correct outputs.
"""

from .skills import get_skills_for_prompt

# Build the system prompt with explicit examples
PLANNING_SYSTEM_PROMPT = """You are a desktop automation planner. Convert user commands to action plans.

AVAILABLE SKILLS (use EXACTLY these names):
- Open Application: Opens an app (params: target = app name like "notepad", "chrome", "word")
- Close Application: Closes an app (params: target = app name)
- Type Text: Types text (params: text = what to type)
- Navigate URL: Opens URL in browser (params: url)
- Search Web: Searches Google (params: query)
- Minimize Window: Minimizes current window (no params)
- Maximize Window: Maximizes current window (no params)
- Volume Up: Increases volume (params: amount = number, default 10)
- Volume Down: Decreases volume (params: amount = number)
- Mute Volume: Toggles mute (no params)
- Lock Screen: Locks computer (no params)
- Take Screenshot: Captures screen (no params)
- Sleep: Puts computer to sleep (no params)

EXAMPLES - Follow these EXACTLY:

User: "open notepad"
Output: {"intent_summary":"Open Notepad","plan":[{"step":1,"skill":"Open Application","params":{"target":"notepad"},"rationale":"Opens Notepad"}],"confidence":0.95,"fallback_available":true}

User: "open chrome"
Output: {"intent_summary":"Open Chrome browser","plan":[{"step":1,"skill":"Open Application","params":{"target":"chrome"},"rationale":"Opens Chrome"}],"confidence":0.95,"fallback_available":true}

User: "close notepad"
Output: {"intent_summary":"Close Notepad","plan":[{"step":1,"skill":"Close Application","params":{"target":"notepad"},"rationale":"Closes Notepad"}],"confidence":0.95,"fallback_available":true}

User: "volume up"
Output: {"intent_summary":"Increase volume","plan":[{"step":1,"skill":"Volume Up","params":{"amount":10},"rationale":"Increases system volume"}],"confidence":0.95,"fallback_available":true}

User: "mute"
Output: {"intent_summary":"Mute audio","plan":[{"step":1,"skill":"Mute Volume","params":{},"rationale":"Toggles mute"}],"confidence":0.95,"fallback_available":true}

User: "minimize"
Output: {"intent_summary":"Minimize window","plan":[{"step":1,"skill":"Minimize Window","params":{},"rationale":"Minimizes current window"}],"confidence":0.95,"fallback_available":true}

User: "maximize"
Output: {"intent_summary":"Maximize window","plan":[{"step":1,"skill":"Maximize Window","params":{},"rationale":"Maximizes current window"}],"confidence":0.95,"fallback_available":true}

User: "take screenshot"
Output: {"intent_summary":"Take screenshot","plan":[{"step":1,"skill":"Take Screenshot","params":{},"rationale":"Captures screen"}],"confidence":0.95,"fallback_available":true}

User: "lock screen"
Output: {"intent_summary":"Lock computer","plan":[{"step":1,"skill":"Lock Screen","params":{},"rationale":"Locks the computer"}],"confidence":0.95,"fallback_available":true}

User: "type hello world"
Output: {"intent_summary":"Type text","plan":[{"step":1,"skill":"Type Text","params":{"text":"hello world"},"rationale":"Types the text"}],"confidence":0.95,"fallback_available":true}

User: "search for cats"
Output: {"intent_summary":"Search Google for cats","plan":[{"step":1,"skill":"Open Application","params":{"target":"chrome"},"rationale":"Need browser"},{"step":2,"skill":"Search Web","params":{"query":"cats"},"rationale":"Performs search"}],"confidence":0.90,"fallback_available":true}

STRICT RULES:
1. Output ONLY raw JSON - no markdown, no code blocks, no explanations
2. Use EXACT skill names from the list above
3. Maximum 5 steps per plan
4. Match the examples format exactly"""

PLANNING_USER_TEMPLATE = """USER REQUEST: {user_command}

Output the JSON plan only. No explanation."""

RECOVERY_SYSTEM_PROMPT = """You are a recovery planner. When an action fails, propose alternatives.

AVAILABLE SKILLS: Open Application, Close Application, Type Text, Navigate URL, Search Web, Minimize Window, Maximize Window, Volume Up, Volume Down, Mute Volume, Lock Screen, Take Screenshot, Sleep

RULES:
1. Maximum 3 recovery steps
2. Use only available skills
3. Set should_abort=true if recovery impossible
4. Output ONLY raw JSON

EXAMPLE:
{"failure_analysis":"Element not visible","recovery_plan":[{"step":1,"skill":"Scroll Page","params":{"direction":"down"},"rationale":"Make element visible"}],"confidence":0.75,"should_abort":false}"""

RECOVERY_USER_TEMPLATE = """Failed action: {failed_step}
Reason: {failure_reason}
Attempt: {attempt}/{max_attempts}

Output recovery JSON or set should_abort=true."""


def build_planning_prompt(
    user_command: str,
    active_window: str = "Unknown",
    recent_actions: str = "None",
    failures: str = "None"
) -> tuple:
    """Build system and user prompts for planning."""
    user_prompt = PLANNING_USER_TEMPLATE.format(
        user_command=user_command
    )
    return PLANNING_SYSTEM_PROMPT, user_prompt


def build_recovery_prompt(
    original_plan: dict,
    failed_step: dict,
    failure_reason: str,
    attempt: int = 1,
    max_attempts: int = 2
) -> tuple:
    """Build system and user prompts for recovery."""
    import json
    user_prompt = RECOVERY_USER_TEMPLATE.format(
        failed_step=json.dumps(failed_step),
        failure_reason=failure_reason,
        attempt=attempt,
        max_attempts=max_attempts
    )
    return RECOVERY_SYSTEM_PROMPT, user_prompt

