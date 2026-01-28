"""
Transaction Manager - Logs reversible actions and handles rollback.

Persists transactions to a JSON log to allow "undo" functionality across sessions.
"""

import os
import json
import logging
import shutil
from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel

from app.agents.janitor.janitor_tools import safe_move, safe_delete, is_protected_path

logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    """Record of a reversible action."""
    id: str
    agent: str
    action_type: str  # "move", "delete", "rename"
    timestamp: datetime
    description: str
    details: dict  # Checkpoint data needed for rollback
    reverted: bool = False


class TransactionManager:
    """
    Manages action logs and rollback logic.
    """
    
    def __init__(self, storage_path: str = "transactions.json"):
        self._storage_path = storage_path
        self._transactions: List[Transaction] = []
        self._load()
    
    def log_transaction(
        self,
        agent: str,
        action_type: str,
        description: str,
        details: dict
    ) -> str:
        """
        Log a new transaction.
        
        Args:
            agent: Name of agent performing action
            action_type: Type of action ("move", "delete", etc.)
            description: Human readable description
            details: Data needed to reverse the action
            
        Returns:
            Transaction ID
        """
        tx = Transaction(
            id=f"tx_{int(datetime.now().timestamp())}_{len(self._transactions)}",
            agent=agent,
            action_type=action_type,
            timestamp=datetime.now(),
            description=description,
            details=details,
        )
        
        self._transactions.append(tx)
        self._save()
        logger.info(f"[TransactionManager] Logged: {description}")
        
        # v2: Log to Episodic Memory (Timeline)
        try:
            # We don't have user_id here easily, so we'll use "default_user" for now
            # In a multi-user system, we'd need to pass context down
            import asyncio
            from app.db.memory_bridge import log_event
            
            # Fire and forget (don't await in sync method)
            asyncio.create_task(log_event(
                user_id="default_user",
                event_type="action_tool",
                content=description,
                metadata={
                    "agent": agent,
                    "action_type": action_type,
                    "transaction_id": tx.id
                }
            ))
        except Exception as e:
            logger.warning(f"[TransactionManager] Failed to log to timeline: {e}")
            
        return tx.id
    
    async def rollback(self, transaction_id: str) -> bool:
        """
        Rollback a specific transaction.
        """
        tx = next((t for t in self._transactions if t.id == transaction_id), None)
        if not tx:
            logger.error(f"[TransactionManager] Transaction {transaction_id} not found")
            return False
            
        if tx.reverted:
            logger.warning(f"[TransactionManager] Transaction {transaction_id} already reverted")
            return False
            
        success = False
        
        try:
            if tx.action_type == "move":
                success = await self._rollback_move(tx.details)
            elif tx.action_type == "delete":
                success = await self._rollback_delete(tx.details)
            elif tx.action_type == "rename":
                success = await self._rollback_rename(tx.details)
            
            if success:
                tx.reverted = True
                self._save()
                logger.info(f"[TransactionManager] Rolled back: {tx.description}")
                
        except Exception as e:
            logger.error(f"[TransactionManager] Rollback failed: {e}")
            
        return success
    
    async def undo_last(self, count: int = 1) -> List[str]:
        """
        Undo the last N transactions.
        
        Returns list of descriptions of undone actions.
        """
        undone = []
        
        # Get active transactions (not reverted), newest first
        active = [t for t in reversed(self._transactions) if not t.reverted]
        
        for i in range(min(count, len(active))):
            tx = active[i]
            if await self.rollback(tx.id):
                undone.append(tx.description)
        
        return undone
    
    async def _rollback_move(self, details: dict) -> bool:
        """Reverse a move (Move Dest -> Source)."""
        src = details.get("source")
        dst = details.get("destination")
        
        if not os.path.exists(dst):
            logger.error(f"Cannot undo move: Destination {dst} missing")
            return False
            
        # Move back
        res = await safe_move(dst, src)
        return res.success
    
    async def _rollback_rename(self, details: dict) -> bool:
        """Reverse a rename (Rename New -> Old)."""
        return await self._rollback_move(details)

    async def _rollback_delete(self, details: dict) -> bool:
        """Reverse a delete (RESTORE from Recycle Bin)."""
        original_path = details.get("path")
        is_recycle = details.get("to_recycle", True)
        
        if not is_recycle:
            logger.error(f"Cannot undo permanent delete: {original_path}")
            return False
            
        # Try to restore using winshell/powershell
        # This is tricky autonomously. 
        # For now, simplistic approach if we used a mock trash folder
        
        # Check if we logged a trash path (fallback method)
        trash_path = details.get("trash_path")
        if trash_path and os.path.exists(trash_path):
             res = await safe_move(trash_path, original_path)
             return res.success
             
        # If it went to real recycle bin, we need specialized restore logic
        # For MVP, we'll try PowerShell restore based on filename
        try:
            filename = os.path.basename(original_path)
            cmd = f'$obj = (New-Object -ComObject Shell.Application).NameSpace(0xa).Items() | Where-Object {{$_.Name -eq "{filename}"}}; if ($obj) {{ $obj.InvokeVerb("restore"); return "True" }}'
            
            import subprocess
            res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            
            if "True" in res.stdout:
                return True
                
        except Exception as e:
            logger.error(f"Recycle bin restore error: {e}")
            
        return False

    def _load(self):
        if os.path.exists(self._storage_path):
            try:
                with open(self._storage_path, "r") as f:
                    data = json.load(f)
                    self._transactions = [Transaction(**t) for t in data]
            except Exception:
                self._transactions = []

    def _save(self):
        try:
            with open(self._storage_path, "w") as f:
                json.dump([t.model_dump() for t in self._transactions], f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transactions: {e}")

# Singleton
_tm = None

def get_transaction_manager() -> TransactionManager:
    global _tm
    if not _tm:
        _tm = TransactionManager()
    return _tm
