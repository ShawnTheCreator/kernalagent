"""
Janitor Agent Package - File system organization and cleanup.

The Janitor Agent eliminates "Digital Entropy" by:
- Organizing Downloads and Desktop folders
- Clearing temporary files and caches
- Finding large hidden files
- Generating cleanup plans for user approval
"""

from app.agents.janitor.janitor_agent import JanitorAgent
from app.agents.janitor.file_categorizer import (
    categorize_file,
    FileCategory,
    CATEGORY_MAP,
)
from app.agents.janitor.cleaning_plan import CleaningPlan, CleaningAction

__all__ = [
    "JanitorAgent",
    "categorize_file",
    "FileCategory",
    "CATEGORY_MAP",
    "CleaningPlan",
    "CleaningAction",
]
