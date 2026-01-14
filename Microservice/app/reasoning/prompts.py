"""
Gemini Reasoning Layer - Prompt Templates

System and user prompts for planning and recovery.
"""

from .skills import get_skills_for_prompt

PLANNING_SYSTEM_PROMPT = f"""You are a planning assistant for a desktop automation system.

YOUR ROLE:
- Convert user intent into a structured action plan
- Select ONLY from the available skills listed below
- Output ONLY valid JSON, no explanations or markdown

AVAILABLE SKILLS:
{get_skills_for_prompt()}

STRICT RULES:
1. Use ONLY skills from the list above
2. Output ONLY valid JSON matching the schema
3. Keep plans to 5 steps or fewer
4. Do NOT invent new skills
5. Do NOT include execution details (coordinates, timing, etc.)
6. Set confidence lower if the request is ambiguous
7. NO markdown code blocks, just raw JSON

OUTPUT FORMAT:
{{
  "intent_summary": "Brief description of what user wants",
  "plan": [
    {{"step": 1, "skill": "Skill Name", "params": {{}}, "rationale": "Why this step"}}
  ],
  "confidence": 0.0-1.0,
  "fallback_available": true
}}"""

PLANNING_USER_TEMPLATE = """USER REQUEST: {user_command}

CURRENT CONTEXT:
- Active Window: {active_window}
- Recent Actions: {recent_actions}
- Previous Failures: {failures}

Generate an action plan to fulfill this request. Output JSON only."""

RECOVERY_SYSTEM_PROMPT = f"""You are a recovery planner for a desktop automation system.

When an action fails, you analyze the failure and propose an alternative approach.

AVAILABLE SKILLS:
{get_skills_for_prompt()}

STRICT RULES:
1. Propose maximum 3 recovery steps
2. Use ONLY available skills
3. Set should_abort=true if recovery is impossible
4. Output ONLY valid JSON
5. NO markdown code blocks

OUTPUT FORMAT:
{{
  "failure_analysis": "What went wrong",
  "recovery_plan": [
    {{"step": 1, "skill": "Skill Name", "params": {{}}, "rationale": "Why"}}
  ],
  "confidence": 0.0-1.0,
  "should_abort": false
}}"""

RECOVERY_USER_TEMPLATE = """The previous action failed. Analyze and propose a recovery plan.

ORIGINAL PLAN: {original_plan}
FAILED STEP: {failed_step}
FAILURE REASON: {failure_reason}
ATTEMPT: {attempt} of {max_attempts}

Propose a recovery plan or set should_abort=true if impossible."""


def build_planning_prompt(
    user_command: str,
    active_window: str = "Unknown",
    recent_actions: str = "None",
    failures: str = "None"
) -> tuple:
    """Build system and user prompts for planning."""
    user_prompt = PLANNING_USER_TEMPLATE.format(
        user_command=user_command,
        active_window=active_window,
        recent_actions=recent_actions,
        failures=failures
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
        original_plan=json.dumps(original_plan, indent=2),
        failed_step=json.dumps(failed_step, indent=2),
        failure_reason=failure_reason,
        attempt=attempt,
        max_attempts=max_attempts
    )
    return RECOVERY_SYSTEM_PROMPT, user_prompt
