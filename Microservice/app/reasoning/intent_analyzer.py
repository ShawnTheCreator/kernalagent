"""
Intent Analyzer - LLM-First Architecture Core

This module replaces if-else parsing with structured LLM intent extraction.
Uses Gemini as primary, Groq (Llama 3) as fallback.

Architecture:
    User Input → Intent Analyzer → Structured Plan (JSON) → Tool Executor
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from google import genai

# Setup logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ===== LLM CONFIGURATION =====
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ===== TOOL DEFINITIONS (What LLM can plan) =====
AVAILABLE_TOOLS = """
Available tools and their parameters:

1. app_launcher
   - action: "open" | "close"
   - target: application name (e.g., "notepad.exe", "chrome.exe", "vscode")

2. text_input
   - action: "type"
   - content: text to type

3. keyboard
   - action: "hotkey" | "press"
   - keys: key combination (e.g., "ctrl+c", "enter", "alt+tab")

4. media_control
   - action: "play_pause" | "next" | "previous" | "stop"

5. volume_control
   - action: "up" | "down" | "mute"
   - amount: number (1-100, optional)

6. brightness_control
   - action: "up" | "down"
   - amount: number (1-100, optional)

7. SPECIALIZED AGENTS (for complex tasks):
   - RECOVERY_AGENT: Undo/restore operations
     - Keywords: "undo", "recover", "restore", "bring back", "oops"
     - Examples: "undo last action", "recover deleted file", "restore changes"
     - When detected, set intent: "agent_task" and target: "RECOVERY_AGENT"

IMPORTANT: If command matches agent keywords, use agent_task instead of generic tools!

7. browser
   - action: "navigate" | "search" | "new_tab" | "close_tab" | "refresh" | "back" | "forward"
   - url: URL (for navigate) - for YouTube use "https://youtube.com"
   - query: search terms (for search)

8. window_control
8. system
   - action: "screenshot" | "lock" | "sleep" | "shutdown" | "restart"

9. window_control
   - action: "minimize" | "maximize" | "restore" | "alt_tab" | "show_desktop"

10. clipboard
    - action: "copy" | "paste" | "cut"

11. file_ops
    - action: "save" | "undo" | "redo" | "select_all"

12. mouse
    - action: "click" | "double_click" | "right_click" | "scroll" | "move"
    - x: x coordinate (for click/move)
    - y: y coordinate (for click/move)
    - direction: "up" | "down" (for scroll)

13. virtual_desktop
    - action: "switch_left" | "switch_right" | "new" | "close" | "task_view"

14. wait
    - action: "wait"
    - duration: seconds to wait (default 2)
    - Use this between actions that need time (page load, video start, etc.)

15. youtube (shortcut for common YouTube actions)
    - action: "skip_ad" | "play" | "pause" | "fullscreen" | "next_video"
    - skip_ad: presses Tab then Enter to skip
    - play/pause: presses Space or K key
    - fullscreen: presses F key

16. ui_automation (PREFERRED for clicking UI elements!)
    - action: "click_button" | "click_menu" | "click_element" | "type_in_element"
    - target: button/element name (e.g., "Save", "Cancel", "OK", "Submit")
    - path: menu path for click_menu (e.g., "File > Save As", "Edit > Preferences")
    - content: text to type (for type_in_element)
    
    IMPORTANT: Prefer ui_automation over mouse clicks when clicking named buttons!
    Examples:
    - "click the Save button" → ui_automation, action: click_button, target: "Save"
    - "click File menu then Save As" → ui_automation, action: click_menu, path: "File > Save As"
    - "click OK" → ui_automation, action: click_button, target: "OK"

17. skill_management (Record and replay workflows!)
    - action: "start_recording" | "stop_recording" | "play_skill" | "list_skills"
    - target: skill name (for start_recording and play_skill)
    
    Examples:
    - "learn how I do this" → skill_management, action: start_recording, target: "my_workflow"
    - "stop learning" → skill_management, action: stop_recording
    - "do the login thing" → skill_management, action: play_skill, target: "login"
    - "what skills do I have" → skill_management, action: list_skills

18. system_toggle (Hands-free system toggles)
    - action: "wifi" | "bluetooth" | "airplane_mode"
    - state: "on" | "off"
    IMPORTANT: Use this for "turn on/off wifi", "enable bluetooth", "airplane mode on".
    This should be executed via Quick Settings UI automation on Windows.
"""

# ===== THE CORE PROMPT =====
INTENT_ANALYZER_PROMPT = f"""You are an intelligent desktop automation brain.

Your job is to convert natural language commands into structured action plans.

{AVAILABLE_TOOLS}

## Rules:
1. ALWAYS output valid JSON only - no explanations, no markdown
2. Output a single JSON object with no trailing text
3. Do not include raw newlines inside string values
4. Understand implicit intent (e.g., "make it quieter" = volume down)
5. Handle multi-step commands (e.g., "open chrome and go to youtube")
6. Infer missing details from context
7. Use confidence score (0.0 to 1.0) to indicate certainty
8. CRITICAL: For AMBIGUOUS VISUAL TARGETS like "any video", "first result", "a thumbnail", 
   "the video", etc. - use ui_automation with action="click_element" and target=description.
   DO NOT use tab+enter for these - keyboard navigation won't work for visual content!
   Examples:
   - "click on any video" → ui_automation, action: click_element, target: "any video"
   - "click the first video" → ui_automation, action: click_element, target: "first video"
   - "click on a search result" → ui_automation, action: click_element, target: "first search result"

## CRITICAL: SPELLING & TYPO CORRECTION
Users may have spelling mistakes, typos, or voice recognition errors. You MUST:
1. Auto-correct common typos and interpret the intended meaning
2. Common misspellings to recognize:
   - "ant", "nad", "adn", "anf" → "and" (the separator word)
   - "notpad", "notepadd", "notepd" → "notepad"
   - "chorme", "crome", "gogle chrome", "googel" → "chrome"
   - "youtoube", "utube", "youtub" → "youtube"
   - "tipe", "tyep", "typee" → "type"
   - "opne", "oepn", "oen" → "open"
   - "clsoe", "closee", "colse" → "close"
   - "volum", "volumee" → "volume"
   - "helo", "heloo", "hellow" → "hello"
   - Names like "buhle", "john", "sarah" should be preserved exactly (proper nouns)
3. Focus on INTENT, not exact spelling
4. If a word looks like a typo of a known action/app, correct it
5. Preserve proper nouns and user-specified text content exactly as-is

## CONTEXT-AWARE RULES (for relative commands):
- "this" = current active app/window
- "it" = selection if available, else last action target, else current app
- "that" = last action target or selection
- "bigger" in browser/editor = zoom in/font size up; in media = volume up; else = maximize
- "smaller" = opposite of bigger
- "save this" = save in current app (Ctrl+S)
- "close this" = close current window
- "do that again" = repeat last action

## Output Format:
{{
  "intent": "single_action" | "multi_step" | "unclear",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "actions": [
    {{
      "tool": "tool_name",
      "action": "action_type",
      ...other params
      "expected": {{
        "window_title_contains": "string (optional)",
        "window_title_not_contains": "string (optional)",
        "element_present": "element name to be findable via UI automation (optional)",
        "element_not_present": "element name that should disappear (optional)",
        "textbox_value_contains": "expected text substring after typing (optional)",
        "focused_element_name_contains": "name/label of the focused control after click/focus (optional)",
        "toggle_target": "toggle name/label for quick settings (optional)",
        "toggle_state": "on|off expected final toggle state (optional)",
        "timeout_ms": 4000
      }}
    }}
  ]
}}

## VERIFICATION (CRITICAL FOR HANDS-FREE ACCURACY)
- For every action, include an `expected` object whenever possible.
- Prefer simple, checkable expectations.
  Examples:
  - app_launcher/open chrome.exe -> expected.window_title_contains: "chrome"
  - ui_automation/click_button Save -> expected.element_present: "Save" (or element_not_present if it disappears)
  - text_input/type "hello" -> expected.textbox_value_contains: "hello"
  - ui_automation/type_in_element "Search" -> expected.focused_element_name_contains: "search" and expected.textbox_value_contains: "..." (when possible)
- If you cannot safely predict an expectation, omit `expected`.

## CRITICAL PARSING RULES:
1. The word "and" is a SEPARATOR between actions
2. For "type X and Y", the content is ONLY "X" (everything before "and")
3. Split the command by "and" first, then process each part separately

## Examples:

Input: "type hello and press enter"
WRONG: {{"tool": "text_input", "content": "hello and press enter"}}
CORRECT:
{{
  "intent": "multi_step",
  "actions": [
    {{"tool": "text_input", "action": "type", "content": "hello"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}}
  ]
}}

Input: "open notepad and type Hello World and press ctrl+s"
WRONG: {{"tool": "text_input", "content": "Hello World and press ctrl+s"}}
CORRECT:
{{
  "intent": "multi_step",
  "confidence": 0.98,
  "reasoning": "Open notepad → type 'Hello World' → save with Ctrl+S",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "notepad.exe"}},
    {{"tool": "text_input", "action": "type", "content": "Hello World"}},
    {{"tool": "keyboard", "action": "hotkey", "keys": "ctrl+s"}}
  ]
}}

Input: "type test.txt and press enter"
CORRECT:
{{
  "intent": "multi_step",
  "actions": [
    {{"tool": "text_input", "action": "type", "content": "test.txt"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}}
  ]
}}

Input: "open notepad and type Hello World and press ctrl+s and type test.txt and press enter"
WRONG: {{"tool": "text_input", "content": "Hello World and press ctrl+s and type test.txt and press enter"}}
CORRECT:
{{
  "intent": "multi_step",
  "confidence": 0.96,
  "reasoning": "5 steps: open → type text → save → type filename → confirm",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "notepad.exe"}},
    {{"tool": "text_input", "action": "type", "content": "Hello World"}},
    {{"tool": "keyboard", "action": "hotkey", "keys": "ctrl+s"}},
    {{"tool": "text_input", "action": "type", "content": "test.txt"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}}
  ]
}}

Input: "open chrome and search for cats"
{{
  "intent": "multi_step",
  "confidence": 0.95,
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "chrome.exe"}},
    {{"tool": "browser", "action": "search", "query": "cats"}}
  ]
}}

Input: "open chrome go to youtube and search for trailers"
{{
  "intent": "multi_step",
  "confidence": 0.97,
  "reasoning": "Open browser, navigate to YouTube, then search",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "chrome.exe"}},
    {{"tool": "browser", "action": "navigate", "url": "https://youtube.com"}},
    {{"tool": "text_input", "action": "type", "content": "trailers"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}}
  ]
}}

Input: "open youtube search for movie trailers and play the first one"
{{
  "intent": "multi_step",
  "confidence": 0.95,
  "reasoning": "Open YouTube, search, click first result",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "chrome.exe"}},
    {{"tool": "browser", "action": "navigate", "url": "https://youtube.com"}},
    {{"tool": "text_input", "action": "type", "content": "movie trailers"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}},
    {{"tool": "keyboard", "action": "press", "keys": "tab"}},
    {{"tool": "keyboard", "action": "press", "keys": "enter"}}
  ]
}}

Input: "skip ad" or "skip this ad"
{{
  "intent": "single_action",
  "confidence": 0.99,
  "reasoning": "Press Tab to focus skip button then Enter",
  "actions": [
    {{"tool": "keyboard", "action": "hotkey", "keys": "tab+enter"}}
  ]
}}

REMEMBER: 
1. Split by "and" or "then" to find multiple actions
2. For YouTube/browser: navigate first, then search, then interact
3. Tab+Enter is common for clicking buttons without mouse

Now analyze this command:
"""


class IntentAnalyzer:
    """
    LLM-powered intent analyzer that converts natural language to structured plans.
    No if-else logic - pure LLM understanding.
    """
    
    def __init__(self):
        self.gemini_client = None
        self.groq_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize LLM clients."""
        # Gemini (Primary)
        if GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client()
                logger.info("[INTENT] Gemini client initialized")
            except Exception as e:
                logger.error(f"[INTENT] Gemini init failed: {e}")
        
        # Groq (Fallback)
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
                logger.info("[INTENT] Groq client initialized")
            except Exception as e:
                logger.error(f"[INTENT] Groq init failed: {e}")
    
    def _normalize_typos(self, command: str) -> str:
        """
        Normalize common typos and spelling mistakes in commands.
        This preprocesses the command before sending to LLM.
        """
        import re
        
        # Dictionary of common typos -> corrections
        # Format: typo_pattern: correct_word
        typo_corrections = {
            # "and" variants (critical separator)
            r'\bant\b': 'and',
            r'\badn\b': 'and',
            r'\bnad\b': 'and',
            r'\banf\b': 'and',
            r'\band\s+and\b': 'and',  # double "and"
            
            # "open" variants
            r'\bopne\b': 'open',
            r'\boepn\b': 'open',
            r'\boen\b': 'open',
            r'\bopem\b': 'open',
            
            # "close" variants
            r'\bclsoe\b': 'close',
            r'\bcloase\b': 'close',
            r'\bcolse\b': 'close',
            
            # "type" variants
            r'\btipe\b': 'type',
            r'\btyep\b': 'type',
            r'\btpye\b': 'type',
            r'\btyoe\b': 'type',
            
            # App names
            r'\bnotpad\b': 'notepad',
            r'\bnotepadd\b': 'notepad',
            r'\bnotepd\b': 'notepad',
            r'\bchorme\b': 'chrome',
            r'\bcrome\b': 'chrome',
            r'\bgoolge\b': 'google',
            r'\bgoogel\b': 'google',
            r'\bgogle\b': 'google',
            r'\byoutube\b': 'youtube',
            r'\byoutueb\b': 'youtube',
            r'\byoutub\b': 'youtube',
            r'\butube\b': 'youtube',
            r'\bfirefxo\b': 'firefox',
            r'\bfirefoc\b': 'firefox',
            
            # Common words
            r'\bsercah\b': 'search',
            r'\bsaerch\b': 'search',
            r'\bserach\b': 'search',
            r'\bbrowsr\b': 'browser',
            r'\bbrwoser\b': 'browser',
            r'\bvoluem\b': 'volume',
            r'\bvolum\b': 'volume',
            r'\bpreess\b': 'press',
            r'\bperss\b': 'press',
            r'\benteer\b': 'enter',
            r'\bentr\b': 'enter',
        }
        
        normalized = command.lower()
        
        for typo_pattern, correction in typo_corrections.items():
            normalized = re.sub(typo_pattern, correction, normalized, flags=re.IGNORECASE)
        
        return normalized

    
    async def analyze(
        self, 
        command: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user command and return structured action plan.
        
        Args:
            command: Natural language command
            context: Optional context (last action, active app, etc.)
        
        Returns:
            Structured plan with intent, confidence, and actions
        """
        # Preprocess command to fix common typos
        normalized_command = self._normalize_typos(command)
        if normalized_command != command:
            logger.info(f"[INTENT] Typo correction: '{command}' → '{normalized_command}'")
        
        # Build prompt with context if available
        prompt = INTENT_ANALYZER_PROMPT
        
        if context:
            prompt += f"\n\nContext:\n"
            if context.get("last_action"):
                prompt += f"- Last action: {context['last_action']}\n"
            if context.get("active_app"):
                prompt += f"- Active app: {context['active_app']}\n"
        
        prompt += f'\nUser command: "{normalized_command}"'
        
        # Try Gemini first
        result = await self._call_gemini(prompt)
        
        # Fallback to Groq if Gemini fails
        if not result and self.groq_client:
            logger.warning("[INTENT] Gemini failed, trying Groq...")
            result = await self._call_groq(prompt)
        
        # Parse and validate result
        if result:
            plan = self._parse_response(result)
            if plan:
                return plan
        
        # Ultimate fallback - return unclear intent
        return {
            "intent": "unclear",
            "confidence": 0.0,
            "reasoning": "Could not parse command",
            "actions": []
        }
    
    async def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Gemini API."""
        if not self.gemini_client:
            return None
        
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 1024,
                }
            )
            
            if response and response.text:
                logger.info(f"[INTENT] Gemini response received ({len(response.text)} chars)")
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"[INTENT] Gemini error: {e}")
            return None
    
    async def _call_groq(self, prompt: str) -> Optional[str]:
        """Call Groq API (Llama 3)."""
        if not self.groq_client:
            return None
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
            )
            
            if response and response.choices:
                result = response.choices[0].message.content
                logger.info(f"[INTENT] Groq response received ({len(result)} chars)")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"[INTENT] Groq error: {e}")
            return None
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        if not response:
            return None
        
        text = response.strip()

        def _strip_code_fences(value: str) -> str:
            stripped = value.strip()
            if stripped.startswith("```json"):
                stripped = stripped[7:]
            elif stripped.startswith("```"):
                stripped = stripped[3:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            return stripped.strip()

        def _parse_json(value: str) -> Optional[Dict[str, Any]]:
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None
            if "actions" in parsed and isinstance(parsed["actions"], list):
                return parsed
            return None

        text = _strip_code_fences(text)

        parsed = _parse_json(text)
        if parsed:
            return parsed

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            recovered = text[start:end + 1].strip()
            parsed = _parse_json(recovered)
            if parsed:
                logger.warning("[INTENT] Recovered JSON substring from LLM response")
                return parsed

        logger.error("[INTENT] JSON parse error: failed to parse response")
        logger.error(f"[INTENT] Raw: {text[:200]}")
        return None


# Singleton instance
_analyzer: Optional[IntentAnalyzer] = None

def get_intent_analyzer() -> IntentAnalyzer:
    """Get or create the Intent Analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = IntentAnalyzer()
    return _analyzer


async def analyze_command(
    command: str, 
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze a command.
    
    Usage:
        plan = await analyze_command("open chrome and play music")
        for action in plan["actions"]:
            execute(action)
    """
    analyzer = get_intent_analyzer()
    return await analyzer.analyze(command, context)
