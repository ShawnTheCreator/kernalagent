"""
Mock Executor for Live Testing

Simulates action execution without C# backend.
Provides real-time visual feedback in terminal for demos and debugging.

Usage:
    from app.executor.mock_executor import execute
    execute(action)
"""
import time
import sys


# ANSI color codes for terminal styling
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_with_delay(text: str, delay: float = 0.02):
    """Print text character by character for live effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def execute(action: dict) -> dict:
    """
    Execute an action in mock mode.
    
    Simulates action execution with visual feedback.
    Returns execution result.
    
    Args:
        action: Action dictionary with action_type, explanation, etc.
        
    Returns:
        Execution result dictionary
    """
    action_type = action.get("action_type", "UNKNOWN")
    explanation = action.get("explanation", "No explanation")
    confidence = action.get("confidence", 0.5)
    
    result = {
        "executed": True,
        "action_type": action_type,
        "mock": True
    }
    
    # Simulate execution based on action type
    if action_type == "CLICK":
        coord = action.get("coordinate_label")
        if coord:
            print(f"{Colors.CYAN}🖱️  [MOCK EXECUTOR] Clicking element #{coord}...{Colors.ENDC}")
        else:
            print(f"{Colors.CYAN}🖱️  [MOCK EXECUTOR] Mouse click executing...{Colors.ENDC}")
        time.sleep(0.3)
        print(f"{Colors.GREEN}   ✓ Click complete{Colors.ENDC}")
        
    elif action_type == "SCROLL":
        print(f"{Colors.CYAN}📜 [MOCK EXECUTOR] Scrolling down...{Colors.ENDC}")
        for i in range(3):
            print(f"   {'▼' * (i + 1)}")
            time.sleep(0.15)
        print(f"{Colors.GREEN}   ✓ Scroll complete{Colors.ENDC}")
        
    elif action_type == "TYPE":
        text = action.get("text_payload", "sample text")
        print(f"{Colors.CYAN}⌨️  [MOCK EXECUTOR] Typing text...{Colors.ENDC}")
        print(f"   \"", end="")
        for char in text[:30]:  # Show first 30 chars
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.05)
        if len(text) > 30:
            print("...")
        else:
            print("\"")
        print(f"{Colors.GREEN}   ✓ Type complete{Colors.ENDC}")
        
    elif action_type == "WAIT":
        print(f"{Colors.YELLOW}⏳ [MOCK EXECUTOR] Waiting...{Colors.ENDC}")
        for i in range(3):
            time.sleep(0.2)
            sys.stdout.write(".")
            sys.stdout.flush()
        print()
        print(f"{Colors.GREEN}   ✓ Wait complete{Colors.ENDC}")
        
    elif action_type == "DONE":
        print(f"{Colors.GREEN}{'=' * 50}")
        print(f"✅ [MOCK EXECUTOR] TASK COMPLETED SUCCESSFULLY!")
        print(f"{'=' * 50}{Colors.ENDC}")
        result["task_complete"] = True
        
    else:
        print(f"{Colors.RED}❓ [MOCK EXECUTOR] Unknown action: {action_type}{Colors.ENDC}")
        result["executed"] = False
    
    return result


def print_agent_decision(decision: dict, user_intent: str):
    """
    Print formatted agent decision for debugging.
    
    Args:
        decision: Decision dictionary from decide_next_action
        user_intent: The user's original intent
    """
    print()
    print(f"{Colors.HEADER}{'=' * 50}")
    print(f"🧠 AGENT DECISION")
    print(f"{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.BOLD}Intent    :{Colors.ENDC} {user_intent}")
    print(f"{Colors.BOLD}Strategy  :{Colors.ENDC} {decision.get('strategy', 'UNKNOWN')}")
    print(f"{Colors.BOLD}Confidence:{Colors.ENDC} {decision.get('confidence', 0):.0%}")
    
    if decision.get('skill_name'):
        print(f"{Colors.BOLD}Skill     :{Colors.ENDC} {decision.get('skill_name')}")
    
    print(f"{Colors.BOLD}Reason    :{Colors.ENDC} {decision.get('reason', 'No reason')}")
    print()


def print_action_plan(action: dict):
    """
    Print formatted action plan before execution.
    
    Args:
        action: Action dictionary
    """
    print(f"{Colors.BLUE}{'─' * 50}")
    print(f"📋 ACTION PLAN")
    print(f"{'─' * 50}{Colors.ENDC}")
    print(f"  Action     : {action.get('action_type', 'UNKNOWN')}")
    print(f"  Confidence : {action.get('confidence', 0):.0%}")
    
    if action.get('coordinate_label'):
        print(f"  Target     : Element #{action.get('coordinate_label')}")
    if action.get('text_payload'):
        print(f"  Text       : \"{action.get('text_payload')[:50]}...\"")
    
    print(f"  Explanation: {action.get('explanation', 'None')[:60]}...")
    print()
