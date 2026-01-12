"""
Agent Short-Term Memory (STM) Module

Implements session-scoped memory for the agent to track:
- Recent actions and skills
- Vision signals
- Failure counts

This memory is:
- Session-only (no persistence)
- Deterministic (no ML)
- Explainable (full state visibility)

Used by the decision engine to:
- Detect infinite loops
- Adjust confidence after failures
- Prefer recently successful skills
"""
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    """
    Short-term memory container for a single agent session.
    
    Tracks recent actions, signals, and failures to enable
    stateful decision-making without neural networks.
    """
    
    # Last action taken
    last_action: Optional[str] = None
    
    # Last skill used
    last_skill: Optional[str] = None
    
    # Last vision signal observed
    last_signal: Optional[str] = None
    
    # History of action types (for pattern detection)
    action_history: List[str] = field(default_factory=list)
    
    # Count of consecutive failures
    failure_count: int = 0
    
    # Maximum history to keep
    MAX_HISTORY: int = 10
    
    def record_action(
        self, 
        action_type: str, 
        skill_name: Optional[str], 
        signal: str
    ) -> None:
        """
        Record an action execution.
        
        Args:
            action_type: The type of action performed (CLICK, TYPE, etc.)
            skill_name: Name of the skill used (if any)
            signal: The vision signal at time of action
        """
        self.last_action = action_type
        self.last_skill = skill_name
        self.last_signal = signal
        
        # Append to history (with size limit)
        self.action_history.append(action_type)
        if len(self.action_history) > self.MAX_HISTORY:
            self.action_history = self.action_history[-self.MAX_HISTORY:]
    
    def record_failure(self) -> None:
        """
        Record a failure event.
        Increments the consecutive failure counter.
        """
        self.failure_count += 1
    
    def record_success(self) -> None:
        """
        Record a success event.
        Resets the consecutive failure counter.
        """
        self.failure_count = 0
    
    def reset(self) -> None:
        """
        Reset all memory state.
        Called at session start or on new intent.
        """
        self.last_action = None
        self.last_skill = None
        self.last_signal = None
        self.action_history = []
        self.failure_count = 0
    
    def is_loop_detected(self, proposed_action: str, current_signal: str) -> bool:
        """
        Check if we're in a potential infinite loop.
        
        A loop is detected when:
        - Same action is proposed as last action
        - Same vision signal (no state change)
        
        Args:
            proposed_action: The action about to be taken
            current_signal: The current vision signal
            
        Returns:
            True if loop detected, False otherwise
        """
        return (
            self.last_action == proposed_action 
            and self.last_signal == current_signal
        )
    
    def get_confidence_modifier(self) -> float:
        """
        Calculate confidence modifier based on failure history.
        
        Returns:
            Multiplier for confidence (0.8 if 2+ failures, 1.0 otherwise)
        """
        if self.failure_count >= 2:
            return 0.8
        return 1.0
    
    def get_skill_boost(self, skill_name: Optional[str]) -> float:
        """
        Calculate confidence boost for skill reuse.
        
        If the same skill was used recently with no failures,
        we give a small confidence boost.
        
        Args:
            skill_name: Name of skill being considered
            
        Returns:
            Boost value (0.0 to 0.1)
        """
        if skill_name and skill_name == self.last_skill and self.failure_count == 0:
            return 0.1
        return 0.0
    
    def get_context(self) -> dict:
        """
        Get memory context for explainability output.
        
        Returns:
            Dictionary with current memory state
        """
        return {
            "last_action": self.last_action or "None",
            "last_skill": self.last_skill or "None",
            "last_signal": self.last_signal or "None",
            "failure_count": self.failure_count,
            "action_history": self.action_history[-5:] if self.action_history else []
        }
    
    def format_for_log(self) -> str:
        """
        Format memory state for console logging.
        
        Returns:
            Formatted string for log output
        """
        return (
            f"🧠 MEMORY CONTEXT\n"
            f"   Last Action : {self.last_action or 'None'}\n"
            f"   Last Skill  : {self.last_skill or 'None'}\n"
            f"   Last Signal : {self.last_signal or 'None'}\n"
            f"   Failures    : {self.failure_count}"
        )
