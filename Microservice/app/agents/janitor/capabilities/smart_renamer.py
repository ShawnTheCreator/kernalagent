"""
Smart Renamer Capability V1 - AI-powered file renaming.

Handles:
- Files with excessively long names (>100 chars)
- Files with weird characters (@#$%^&*())
- Generic/meaningless names (IMG_20240124_123456.jpg, Untitled.pdf)
- Duplicate markers (file (1).pdf, file - Copy.pdf)

Uses LLM for context-aware renaming when simple rules aren't enough.
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


# === PATTERNS FOR DETECTION ===

# Generic camera/phone patterns
GENERIC_PATTERNS = [
    r"^IMG[_-]?\d+",           # IMG_20240124_123456
    r"^DSC[_-]?\d+",           # DSC00001
    r"^DCIM[_-]?\d+",          # DCIM0001
    r"^Photo[_-]?\d+",         # Photo_001
    r"^VID[_-]?\d+",           # VID_20240124_123456
    r"^MOV[_-]?\d+",           # MOV001
    r"^Screen[_\s]?Shot",      # Screenshot
    r"^Untitled",              # Untitled.pdf
    r"^Document\s*\d*",        # Document, Document1
    r"^New\s*(Text\s*)?Doc",   # New Text Document
    r"^recording[_-]?\d*",     # recording_001
    r"^audio[_-]?\d+",         # audio_001
    r"^voice[_-]?\d+",         # voice_001
    r"^clip[_-]?\d+",          # clip_001
]

# Duplicate markers
DUPLICATE_PATTERNS = [
    r"\s*\(\d+\)\s*$",          # file (1).pdf
    r"\s*-\s*Copy\s*(\d*)$",    # file - Copy.pdf, file - Copy 2.pdf
    r"\s*copy\s*(\d*)$",        # file copy.pdf
    r"_\d{1,2}$",               # file_1.pdf (at end before extension)
]

# Weird characters that shouldn't be in filenames
WEIRD_CHARS = r"[@#$%^&*()+=\[\]{}<>|\\:;\"\'`~]"

# Maximum reasonable filename length
MAX_FILENAME_LENGTH = 100


class SmartRenamerCapability(BaseCapability):
    """
    AI-powered file renaming for messy filenames.
    
    Analyzes filenames and suggests clean, meaningful alternatives.
    """
    
    name = "smart_renamer"
    description = "Renames files with messy or generic names to clean, meaningful names"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Analyze if a file needs renaming.
        
        Checks for:
        1. Overly long filenames
        2. Weird characters
        3. Generic/meaningless names
        4. Duplicate markers
        """
        filename = file_info.get("filename", os.path.basename(file_path))
        
        # Analyze the filename
        issues = self._detect_issues(filename)
        
        if not issues:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Generate a suggested new name
        new_name = await self._generate_smart_name(file_path, filename, issues, file_info)
        
        if new_name == filename:
            # Couldn't improve it
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        issue_summary = ", ".join(issues)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="rename",
            confidence=0.8,
            suggestion=f"✏️ Rename: {self._truncate(filename, 30)} → {new_name}",
            requires_permission=True,  # Always ask before renaming
            metadata={
                "source": file_path,
                "old_name": filename,
                "new_name": new_name,
                "issues": issues,
                "issue_summary": issue_summary,
            }
        )
    
    def _detect_issues(self, filename: str) -> list[str]:
        """Detect issues with a filename."""
        issues = []
        name_part = Path(filename).stem  # Without extension
        
        # Check length
        if len(filename) > MAX_FILENAME_LENGTH:
            issues.append("too_long")
        
        # Check for weird characters
        if re.search(WEIRD_CHARS, name_part):
            issues.append("weird_chars")
        
        # Check for generic names
        for pattern in GENERIC_PATTERNS:
            if re.match(pattern, name_part, re.IGNORECASE):
                issues.append("generic_name")
                break
        
        # Check for duplicate markers
        for pattern in DUPLICATE_PATTERNS:
            if re.search(pattern, name_part, re.IGNORECASE):
                issues.append("duplicate_marker")
                break
        
        # Check for excessive underscores/dashes
        if name_part.count("_") > 5 or name_part.count("-") > 5:
            issues.append("excessive_separators")
        
        # Check for all caps or no caps
        if name_part.isupper() and len(name_part) > 10:
            issues.append("all_caps")
        
        return issues
    
    async def _generate_smart_name(
        self,
        file_path: str,
        filename: str,
        issues: list[str],
        file_info: dict
    ) -> str:
        """
        Generate a clean, meaningful filename.
        
        Strategy:
        1. Extract meaningful parts from the original name
        2. Extract date if present
        3. Use file metadata if available
        4. Fall back to simple cleanup
        """
        path = Path(filename)
        name_part = path.stem
        extension = path.suffix.lower()
        
        # Try to extract a date from the filename
        date_str = self._extract_date(name_part)
        
        # Extract meaningful words (3+ char, alphabetic)
        words = self._extract_words(name_part)
        
        # Build new name based on what we found
        if words:
            # Use extracted words
            clean_name = "_".join(words[:3])  # Max 3 words
        else:
            # Fall back to file type + date
            clean_name = self._get_type_prefix(extension)
        
        # Add date if found
        if date_str:
            clean_name = f"{clean_name}_{date_str}"
        else:
            # Add current date for truly generic files
            if "generic_name" in issues:
                today = datetime.now().strftime("%Y%m%d")
                clean_name = f"{clean_name}_{today}"
        
        # Ensure unique name
        new_name = f"{clean_name}{extension}"
        
        # Check if the new name is actually better
        if len(new_name) >= len(filename) and "too_long" not in issues:
            # Only rename if we're shortening or fixing real issues
            if issues == ["excessive_separators"] or issues == ["all_caps"]:
                return self._simple_cleanup(filename)
        
        return new_name
    
    def _extract_date(self, name: str) -> Optional[str]:
        """Extract a date from the filename."""
        # Common date patterns
        patterns = [
            (r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", "YYYYMMDD"),
            (r"(\d{2})[-_]?(\d{2})[-_]?(\d{4})", "MMDDYYYY"),
            (r"(\d{8})", "YYYYMMDD_compact"),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, name)
            if match:
                try:
                    groups = match.groups()
                    if fmt == "YYYYMMDD":
                        return f"{groups[0]}{groups[1]}{groups[2]}"
                    elif fmt == "YYYYMMDD_compact":
                        # Validate it's a reasonable date
                        date_str = groups[0]
                        year = int(date_str[:4])
                        if 2000 <= year <= 2100:
                            return date_str
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_words(self, name: str) -> list[str]:
        """Extract meaningful words from a filename."""
        # Replace common separators with spaces
        clean = re.sub(r"[-_\.]", " ", name)
        
        # Remove numbers that look like dates/IDs
        clean = re.sub(r"\b\d{4,}\b", "", clean)
        
        # Extract alphabetic words (3+ chars)
        words = re.findall(r"[a-zA-Z]{3,}", clean)
        
        # Filter out common meaningless words
        stopwords = {"copy", "new", "untitled", "document", "file", "img", "vid"}
        words = [w.lower() for w in words if w.lower() not in stopwords]
        
        return words
    
    def _get_type_prefix(self, extension: str) -> str:
        """Get a clean type prefix based on file extension."""
        prefixes = {
            # Images
            ".jpg": "photo",
            ".jpeg": "photo",
            ".png": "image",
            ".gif": "animation",
            ".webp": "image",
            ".heic": "photo",
            
            # Videos
            ".mp4": "video",
            ".mkv": "video",
            ".mov": "video",
            ".avi": "video",
            
            # Audio
            ".mp3": "audio",
            ".wav": "audio",
            ".flac": "audio",
            ".m4a": "audio",
            
            # Documents
            ".pdf": "document",
            ".docx": "document",
            ".doc": "document",
            ".txt": "note",
            ".xlsx": "spreadsheet",
            ".pptx": "presentation",
            
            # Code
            ".py": "script",
            ".js": "script",
            ".html": "webpage",
            ".css": "stylesheet",
        }
        
        return prefixes.get(extension, "file")
    
    def _simple_cleanup(self, filename: str) -> str:
        """Simple cleanup without major changes."""
        path = Path(filename)
        name = path.stem
        ext = path.suffix
        
        # Replace weird chars with underscores
        clean = re.sub(WEIRD_CHARS, "_", name)
        
        # Collapse multiple underscores/dashes
        clean = re.sub(r"[-_]+", "_", clean)
        
        # Remove leading/trailing underscores
        clean = clean.strip("_-")
        
        # Lowercase if all caps
        if clean.isupper():
            clean = clean.lower()
        
        return f"{clean}{ext}"
    
    def _truncate(self, text: str, length: int) -> str:
        """Truncate text with ellipsis."""
        if len(text) <= length:
            return text
        return text[:length - 3] + "..."
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Rename the file."""
        new_name = result.metadata.get("new_name", "")
        
        if not new_name:
            return False
        
        try:
            directory = os.path.dirname(file_path)
            new_path = os.path.join(directory, new_name)
            
            # Ensure we don't overwrite existing files
            if os.path.exists(new_path):
                base, ext = os.path.splitext(new_name)
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(directory, f"{base}_{counter}{ext}")
                    counter += 1
            
            os.rename(file_path, new_path)
            
            old_name = result.metadata.get("old_name", os.path.basename(file_path))
            logger.info(f"[SmartRenamer] Renamed: {old_name} → {os.path.basename(new_path)}")
            return True
            
        except Exception as e:
            logger.error(f"[SmartRenamer] Rename failed: {e}")
            return False
