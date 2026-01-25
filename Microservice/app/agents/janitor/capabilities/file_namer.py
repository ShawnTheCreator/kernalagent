"""
File Namer Capability - Intelligently rename poorly named files.

Detects:
- Untitled documents
- Download (1), Download (2) patterns
- Generic names like "document.pdf"
- Files that could use better organization

Uses LLM to suggest meaningful names based on:
- File content preview
- Creation date
- Context
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


# Patterns that indicate poor naming
POOR_NAME_PATTERNS = [
    r'^untitled',
    r'^document\s*\(\d+\)',
    r'^download\s*\(\d+\)',
    r'^new\s+(document|file|text)',
    r'^copy\s+of',
    r'^\d{8,}$',  # Just numbers (timestamps)
    r'^file\s*\(\d+\)',
    r'^img_\d+',
    r'^screenshot\s*\d*',
    r'^dsc_\d+',
    r'^photo_\d+',
]


class FileNamerCapability(BaseCapability):
    """Renames poorly named files with intelligent suggestions."""
    
    name = "file_namer"
    description = "Suggests better names for untitled or generic files"
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Check if file needs renaming.
        
        Returns suggestion if filename matches poor naming patterns.
        """
        filename = file_info.get("filename", "")
        extension = file_info.get("extension", "")
        size_bytes = file_info.get("size_bytes", 0)
        
        # Get name without extension
        name_only = Path(filename).stem
        
        # Check for poor naming patterns
        is_poorly_named = False
        reason = ""
        
        for pattern in POOR_NAME_PATTERNS:
            if re.match(pattern, name_only, re.IGNORECASE):
                is_poorly_named = True
                reason = f"Matches pattern: {pattern}"
                break
        
        # Also check for very short generic names
        if len(name_only) <= 2:
            is_poorly_named = True
            reason = "Name too short"
        
        if not is_poorly_named:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Generate suggested name
        suggested_name = await self._suggest_name(file_path, file_info)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="rename",
            confidence=0.75,
            suggestion=f"📝 Rename '{filename}' → '{suggested_name}'",
            requires_permission=True,
            metadata={
                "original_name": filename,
                "suggested_name": suggested_name,
                "reason": reason,
            }
        )
    
    async def _suggest_name(self, file_path: str, file_info: dict) -> str:
        """
        Generate a suggested filename.
        
        Uses context like:
        - Date
        - File type
        - LLM analysis (if available)
        """
        extension = file_info.get("extension", "")
        
        # Get creation date
        try:
            stat = os.stat(file_path)
            date = datetime.fromtimestamp(stat.st_ctime)
            date_str = date.strftime("%Y%m%d")
        except:
            date_str = datetime.now().strftime("%Y%m%d")
        
        # Determine category-based prefix
        category_prefixes = {
            ".pdf": "Document",
            ".doc": "Document",
            ".docx": "Document",
            ".xls": "Spreadsheet",
            ".xlsx": "Spreadsheet",
            ".ppt": "Presentation",
            ".pptx": "Presentation",
            ".jpg": "Photo",
            ".jpeg": "Photo",
            ".png": "Image",
            ".gif": "Image",
            ".mp4": "Video",
            ".mov": "Video",
            ".mp3": "Audio",
            ".wav": "Audio",
            ".zip": "Archive",
            ".rar": "Archive",
            ".exe": "Installer",
            ".msi": "Installer",
        }
        
        prefix = category_prefixes.get(extension.lower(), "File")
        
        # Try to use LLM for smarter naming
        try:
            suggested = await self._llm_suggest_name(file_path, file_info)
            if suggested:
                return f"{suggested}{extension}"
        except:
            pass
        
        # Fallback: Category_Date format
        return f"{prefix}_{date_str}{extension}"
    
    async def _llm_suggest_name(self, file_path: str, file_info: dict) -> str:
        """Use LLM to suggest a meaningful name."""
        # TODO: Implement LLM-based naming
        # Could read first page of PDF, analyze image content, etc.
        return ""
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Rename the file."""
        suggested_name = result.metadata.get("suggested_name", "")
        
        if not suggested_name:
            return False
        
        try:
            directory = os.path.dirname(file_path)
            new_path = os.path.join(directory, suggested_name)
            
            # Handle conflicts
            if os.path.exists(new_path):
                base, ext = os.path.splitext(suggested_name)
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(directory, f"{base}_{counter}{ext}")
                    counter += 1
            
            os.rename(file_path, new_path)
            logger.info(f"[FileNamer] Renamed: {file_path} → {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"[FileNamer] Rename failed: {e}")
            return False
