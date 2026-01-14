"""
Intent Analyzer - LLM-First Architecture Core

This module replaces if-else parsing with structured LLM intent extraction.
Uses Gemini as primary, Groq (Llama 3) as fallback.

Architecture:
    User Input → Intent Analyzer → Structured Plan (JSON) → Tool Executor
"""

import os
import json
from typing import Dict, Any, Optional, List
from google import genai

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

7. browser
   - action: "navigate" | "search" | "new_tab" | "close_tab" | "refresh" | "back" | "forward"
   - url: URL (for navigate)
   - query: search terms (for search)

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
"""

# ===== THE CORE PROMPT =====
INTENT_ANALYZER_PROMPT = f"""You are an intelligent desktop automation brain.

Your job is to convert natural language commands into structured action plans.

{AVAILABLE_TOOLS}

## Rules:
1. ALWAYS output valid JSON only - no explanations, no markdown
2. Understand implicit intent (e.g., "make it quieter" = volume down)
3. Handle multi-step commands (e.g., "open chrome and go to youtube")
4. Infer missing details from context
5. Use confidence score (0.0 to 1.0) to indicate certainty

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
    }}
  ]
}}

## Examples:

Input: "open notepad"
{{
  "intent": "single_action",
  "confidence": 0.98,
  "reasoning": "Clear request to open notepad application",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "notepad.exe"}}
  ]
}}

Input: "open chrome and search for cats"
{{
  "intent": "multi_step",
  "confidence": 0.95,
  "reasoning": "Opens browser then performs search",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "chrome.exe"}},
    {{"tool": "browser", "action": "search", "query": "cats"}}
  ]
}}

Input: "reduce the brightness"
{{
  "intent": "single_action",
  "confidence": 0.97,
  "reasoning": "User wants to decrease screen brightness",
  "actions": [
    {{"tool": "brightness_control", "action": "down", "amount": 10}}
  ]
}}

Input: "make it louder"
{{
  "intent": "single_action",
  "confidence": 0.95,
  "reasoning": "Increase volume",
  "actions": [
    {{"tool": "volume_control", "action": "up", "amount": 10}}
  ]
}}

Input: "type hello world"
{{
  "intent": "single_action",
  "confidence": 0.99,
  "reasoning": "Type the specified text",
  "actions": [
    {{"tool": "text_input", "action": "type", "content": "hello world"}}
  ]
}}

Input: "open notepad and type hello"
{{
  "intent": "multi_step",
  "confidence": 0.98,
  "reasoning": "Opens notepad then types hello",
  "actions": [
    {{"tool": "app_launcher", "action": "open", "target": "notepad.exe"}},
    {{"tool": "text_input", "action": "type", "content": "hello"}}
  ]
}}

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
                print("[INTENT] Gemini client initialized")
            except Exception as e:
                print(f"[INTENT] Gemini init failed: {e}")
        
        # Groq (Fallback)
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
                print("[INTENT] Groq client initialized")
            except Exception as e:
                print(f"[INTENT] Groq init failed: {e}")
    
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
        # Build prompt with context if available
        prompt = INTENT_ANALYZER_PROMPT
        
        if context:
            prompt += f"\n\nContext:\n"
            if context.get("last_action"):
                prompt += f"- Last action: {context['last_action']}\n"
            if context.get("active_app"):
                prompt += f"- Active app: {context['active_app']}\n"
        
        prompt += f"\nUser command: \"{command}\""
        
        # Try Gemini first
        result = await self._call_gemini(prompt)
        
        # Fallback to Groq if Gemini fails
        if not result and self.groq_client:
            print("[INTENT] Gemini failed, trying Groq...")
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
                print(f"[INTENT] Gemini response: {response.text[:200]}...")
                return response.text.strip()
            
            return None
            
        except Exception as e:
            print(f"[INTENT] Gemini error: {e}")
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
                print(f"[INTENT] Groq response: {result[:200]}...")
                return result
            
            return None
            
        except Exception as e:
            print(f"[INTENT] Groq error: {e}")
            return None
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        if not response:
            return None
        
        text = response.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            result = json.loads(text)
            
            # Validate required fields
            if "actions" in result and isinstance(result["actions"], list):
                return result
            
            return None
            
        except json.JSONDecodeError as e:
            print(f"[INTENT] JSON parse error: {e}")
            print(f"[INTENT] Raw: {text[:200]}")
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
