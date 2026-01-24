"""
Janitor Capabilities - Modular plugins for autonomous file handling.

Each capability is a self-contained module that can:
- Analyze files
- Propose actions
- Execute with user permission

This makes the Janitor extensible and upgradable.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CapabilityResult(BaseModel):
    """Result from a capability analysis."""
    capability: str
    action_required: bool = False
    action_type: Optional[str] = None  # "move", "rename", "delete", "install", "scan"
    confidence: float = 0.0
    suggestion: Optional[str] = None
    requires_permission: bool = True
    metadata: dict = {}


class BaseCapability(ABC):
    """Base class for Janitor capabilities."""
    
    name: str = "base"
    description: str = "Base capability"
    
    @abstractmethod
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Analyze a file and determine what action to take.
        
        Args:
            file_path: Full path to the file
            file_info: Dict with filename, extension, size_bytes, etc.
            
        Returns:
            CapabilityResult with proposed action
        """
        pass
    
    @abstractmethod
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """
        Execute the proposed action.
        
        Args:
            file_path: Full path to the file
            result: The analysis result to execute
            
        Returns:
            True if successful
        """
        pass


# ============================================================================
# CAPABILITY REGISTRY
# ============================================================================

_capabilities: dict[str, BaseCapability] = {}


def register_capability(capability: BaseCapability) -> None:
    """Register a capability."""
    _capabilities[capability.name] = capability
    logger.info(f"[Janitor] Registered capability: {capability.name}")


def get_capability(name: str) -> Optional[BaseCapability]:
    """Get a capability by name."""
    return _capabilities.get(name)


def get_all_capabilities() -> list[BaseCapability]:
    """Get all registered capabilities."""
    return list(_capabilities.values())


async def run_capabilities(file_path: str, file_info: dict) -> list[CapabilityResult]:
    """
    Run all capabilities on a file.
    
    Returns list of results that require action.
    """
    results = []
    
    for capability in _capabilities.values():
        try:
            result = await capability.analyze(file_path, file_info)
            if result.action_required:
                results.append(result)
        except Exception as e:
            logger.error(f"[Janitor] Capability {capability.name} failed: {e}")
    
    return results
