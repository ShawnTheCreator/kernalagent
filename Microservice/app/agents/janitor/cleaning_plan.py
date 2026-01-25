"""
Cleaning Plan - JSON manifest for user approval before execution.

All destructive actions (move, delete) require user approval via this manifest.
The plan shows what will happen and estimated impact before any changes.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class CleaningAction(BaseModel):
    """A single action in the cleaning plan."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: Literal["MOVE", "DELETE", "ARCHIVE"]
    source: str  # Full path to source file
    destination: Optional[str] = None  # Full path to destination (for MOVE)
    reason: str  # Why this action is proposed
    category: str  # File category (INSTALLERS, DOCUMENTS, etc.)
    size_bytes: int = 0
    age_days: int = 0
    reversible: bool = True
    
    def to_summary(self) -> str:
        """Human-readable summary of this action."""
        size_mb = self.size_bytes / (1024 * 1024)
        if self.action == "DELETE":
            return f"🗑️ Delete {self.source} ({size_mb:.1f} MB) - {self.reason}"
        elif self.action == "MOVE":
            return f"📁 Move to {self.destination} ({size_mb:.1f} MB)"
        elif self.action == "ARCHIVE":
            return f"📦 Archive {self.source} ({size_mb:.1f} MB)"
        return f"{self.action}: {self.source}"


class CleaningPlan(BaseModel):
    """Complete cleaning plan for user approval."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent: str = "JANITOR_AGENT"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # Plan expires if not approved
    
    # Actions grouped by type
    actions: list[CleaningAction] = Field(default_factory=list)
    
    # Summary stats
    total_files: int = 0
    total_size_bytes: int = 0
    space_recoverable_bytes: int = 0
    
    # Approval state
    requires_approval: bool = True
    approved: bool = False
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    # Execution state
    executed: bool = False
    executed_at: Optional[datetime] = None
    
    def add_action(self, action: CleaningAction) -> None:
        """Add an action to the plan."""
        self.actions.append(action)
        self.total_files += 1
        self.total_size_bytes += action.size_bytes
        if action.action == "DELETE":
            self.space_recoverable_bytes += action.size_bytes
    
    def get_actions_by_type(self, action_type: str) -> list[CleaningAction]:
        """Get all actions of a specific type."""
        return [a for a in self.actions if a.action == action_type]
    
    def get_moves(self) -> list[CleaningAction]:
        """Get all MOVE actions."""
        return self.get_actions_by_type("MOVE")
    
    def get_deletes(self) -> list[CleaningAction]:
        """Get all DELETE actions."""
        return self.get_actions_by_type("DELETE")
    
    def approve(self, approved_by: str = "user") -> None:
        """Mark plan as approved."""
        self.approved = True
        self.approved_at = datetime.utcnow()
        self.approved_by = approved_by
    
    def to_summary(self) -> str:
        """Human-readable summary of the plan."""
        size_mb = self.total_size_bytes / (1024 * 1024)
        recoverable_mb = self.space_recoverable_bytes / (1024 * 1024)
        
        moves = len(self.get_moves())
        deletes = len(self.get_deletes())
        
        lines = [
            f"🧹 Cleaning Plan ({self.plan_id[:8]})",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 {self.total_files} files ({size_mb:.1f} MB total)",
            f"📁 {moves} files to organize",
            f"🗑️ {deletes} files to delete ({recoverable_mb:.1f} MB recoverable)",
            "",
        ]
        
        if moves > 0:
            lines.append("📁 Files to organize:")
            for action in self.get_moves()[:5]:
                lines.append(f"   • {action.source.split('/')[-1]} → {action.category}")
            if moves > 5:
                lines.append(f"   ... and {moves - 5} more")
            lines.append("")
        
        if deletes > 0:
            lines.append("🗑️ Files to delete:")
            for action in self.get_deletes()[:5]:
                lines.append(f"   • {action.source.split('/')[-1]} ({action.reason})")
            if deletes > 5:
                lines.append(f"   ... and {deletes - 5} more")
        
        return "\n".join(lines)
    
    def to_json_manifest(self) -> dict:
        """Export as JSON manifest for frontend/API."""
        return {
            "plan_id": self.plan_id,
            "agent": self.agent,
            "created_at": self.created_at.isoformat(),
            "summary": {
                "total_files": self.total_files,
                "total_size_mb": round(self.total_size_bytes / (1024 * 1024), 2),
                "space_recoverable_mb": round(self.space_recoverable_bytes / (1024 * 1024), 2),
                "moves": len(self.get_moves()),
                "deletes": len(self.get_deletes()),
            },
            "actions": [a.model_dump() for a in self.actions],
            "requires_approval": self.requires_approval,
            "approved": self.approved,
        }
