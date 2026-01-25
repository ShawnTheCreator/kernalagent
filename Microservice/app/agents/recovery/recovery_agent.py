"""
Recovery Agent - "The Time Traveller"

Specializes in:
1. Undoing recent actions (Reverse engineering)
2. Restoring from Recycle Bin
3. Git recovery (undo changes, reset hard)
"""

import logging
from typing import Any, Optional

from app.agents.base_agent import BaseAgent, AgentType, AnalysisResult, ActionPlan, AgentTrigger, ExecutionResult
from app.agents.common.transaction_manager import get_transaction_manager

logger = logging.getLogger(__name__)


class RecoveryAgent(BaseAgent):
    """Agent for undoing mistakes and recovering files."""
    
    def __init__(self):
        self.name = "RECOVERY_AGENT"
        self.agent_type = AgentType.ON_DEMAND
        self.specialization = "undo_restore"
        super().__init__()
        self._tm = get_transaction_manager()
    
    async def analyze(self, context: dict) -> AnalysisResult:
        """Analyze intent to determine recovery strategy."""
        intent = context.get("intent", "").lower()
        
        # Strategy detection
        if "undo" in intent or "oops" in intent or "go back" in intent:
            # Check for count "undo last 3 things"
            count = 1
            import re
            match = re.search(r'(\d+)', intent)
            if match:
                count = int(match.group(1))
            
            return AnalysisResult(
                agent_name=self.name,
                findings={"strategy": "undo_transaction", "count": count},
                recommendations=[f"Undo last {count} actions"],
                severity="info"
            )
            
        if "recycle" in intent or "trash" in intent or "bin" in intent:
             return AnalysisResult(
                agent_name=self.name,
                findings={"strategy": "recycle_bin"},
                recommendations=["Scan Recycle Bin"],
                severity="info"
            )
            
        return AnalysisResult(
            agent_name=self.name,
            findings={"strategy": "unknown"},
            severity="info"
        )

    async def plan(self, analysis: AnalysisResult) -> ActionPlan:
        """Create recovery plan."""
        strategy = analysis.findings.get("strategy")
        actions = []
        
        if strategy == "undo_transaction":
            count = analysis.findings.get("count", 1)
            actions.append({
                "tool": "undo_last_action",
                "parameters": {"count": count},
                "description": f"Undo last {count} operational changes"
            })
            
        elif strategy == "recycle_bin":
            actions.append({
                "tool": "scan_recycle_bin",
                "parameters": {},
                "description": "Scan Recycle Bin for recoverable files"
            })
            
        return ActionPlan(
            agent_name=self.name,
            actions=actions,
            estimated_impact=f"Recovering via {strategy}",
            requires_approval=True
        )

    async def execute(self, plan: ActionPlan) -> ExecutionResult:
        """Execute recovery actions."""
        results = []
        completed = 0
        failed = 0
        
        for action in plan.actions:
            tool = action.get("tool")
            try:
                if tool == "undo_last_action":
                    count = action.get("parameters", {}).get("count", 1)
                    undone = await self._tm.undo_last(count)
                    if undone:
                        results.append(f"✅ Undid: {', '.join(undone)}")
                    else:
                        results.append("⚠️ Nothing to undo found")
                    completed += 1
                        
                elif tool == "scan_recycle_bin":
                    # Implement Recycle Bin scanning
                    results.append("Recycle bin scan not implemented yet")
                    completed += 1
            except Exception as e:
                failed += 1
                results.append(f"Error executing {tool}: {e}")
                
        return ExecutionResult(
            plan_id=plan.plan_id,
            agent_name=self.name,
            status="success" if failed == 0 else "partial",
            actions_completed=completed,
            actions_failed=failed,
            metrics={"results": results}
        )

    def get_triggers(self) -> list[AgentTrigger]:
        """Return triggers for this agent."""
        return [
            AgentTrigger(
                trigger_type="user_intent",
                condition="undo, recover, restore, oops, recycle bin",
                priority=9
            )
        ]
