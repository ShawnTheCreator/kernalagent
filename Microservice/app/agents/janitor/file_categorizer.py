"""
File Categorizer - Determines file category based on extension and LLM analysis.

Categories:
- INSTALLERS: .exe, .msi, .dmg
- DOCUMENTS: .pdf, .docx, .txt (sub-categorized as WORK/PERSONAL via LLM)
- MEDIA: .jpg, .png, .mp4
- CODE: .py, .js, .cpp
- ARCHIVES: .zip, .rar, .7z
- TRASH: .tmp, .log, .bak
"""

from enum import Enum
from typing import Optional
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class FileCategory(str, Enum):
    """File category for organization."""
    INSTALLERS = "INSTALLERS"
    DOCUMENTS_WORK = "DOCUMENTS_WORK"
    DOCUMENTS_PERSONAL = "DOCUMENTS_PERSONAL"
    DOCUMENTS = "DOCUMENTS"  # Uncategorized doc
    MEDIA = "MEDIA"
    CODE = "CODE"
    ARCHIVES = "ARCHIVES"
    TRASH = "TRASH"
    UNKNOWN = "UNKNOWN"


# Extension to category mapping
CATEGORY_MAP: dict[str, FileCategory] = {
    # Installers
    ".exe": FileCategory.INSTALLERS,
    ".msi": FileCategory.INSTALLERS,
    ".dmg": FileCategory.INSTALLERS,
    ".deb": FileCategory.INSTALLERS,
    ".rpm": FileCategory.INSTALLERS,
    ".appx": FileCategory.INSTALLERS,
    ".msix": FileCategory.INSTALLERS,
    
    # Documents
    ".pdf": FileCategory.DOCUMENTS,
    ".docx": FileCategory.DOCUMENTS,
    ".doc": FileCategory.DOCUMENTS,
    ".txt": FileCategory.DOCUMENTS,
    ".xlsx": FileCategory.DOCUMENTS,
    ".xls": FileCategory.DOCUMENTS,
    ".pptx": FileCategory.DOCUMENTS,
    ".ppt": FileCategory.DOCUMENTS,
    ".odt": FileCategory.DOCUMENTS,
    ".rtf": FileCategory.DOCUMENTS,
    ".md": FileCategory.DOCUMENTS,
    
    # Media - Images
    ".jpg": FileCategory.MEDIA,
    ".jpeg": FileCategory.MEDIA,
    ".png": FileCategory.MEDIA,
    ".gif": FileCategory.MEDIA,
    ".bmp": FileCategory.MEDIA,
    ".svg": FileCategory.MEDIA,
    ".webp": FileCategory.MEDIA,
    ".ico": FileCategory.MEDIA,
    ".heic": FileCategory.MEDIA,
    
    # Media - Video
    ".mp4": FileCategory.MEDIA,
    ".mkv": FileCategory.MEDIA,
    ".avi": FileCategory.MEDIA,
    ".mov": FileCategory.MEDIA,
    ".wmv": FileCategory.MEDIA,
    ".flv": FileCategory.MEDIA,
    ".webm": FileCategory.MEDIA,
    
    # Media - Audio
    ".mp3": FileCategory.MEDIA,
    ".wav": FileCategory.MEDIA,
    ".flac": FileCategory.MEDIA,
    ".aac": FileCategory.MEDIA,
    ".ogg": FileCategory.MEDIA,
    ".m4a": FileCategory.MEDIA,
    
    # Code
    ".py": FileCategory.CODE,
    ".js": FileCategory.CODE,
    ".ts": FileCategory.CODE,
    ".jsx": FileCategory.CODE,
    ".tsx": FileCategory.CODE,
    ".cpp": FileCategory.CODE,
    ".c": FileCategory.CODE,
    ".h": FileCategory.CODE,
    ".hpp": FileCategory.CODE,
    ".java": FileCategory.CODE,
    ".go": FileCategory.CODE,
    ".rs": FileCategory.CODE,
    ".cs": FileCategory.CODE,
    ".rb": FileCategory.CODE,
    ".php": FileCategory.CODE,
    ".swift": FileCategory.CODE,
    ".kt": FileCategory.CODE,
    ".scala": FileCategory.CODE,
    ".html": FileCategory.CODE,
    ".css": FileCategory.CODE,
    ".scss": FileCategory.CODE,
    ".json": FileCategory.CODE,
    ".yaml": FileCategory.CODE,
    ".yml": FileCategory.CODE,
    ".xml": FileCategory.CODE,
    ".sql": FileCategory.CODE,
    ".sh": FileCategory.CODE,
    ".bat": FileCategory.CODE,
    ".ps1": FileCategory.CODE,
    
    # Archives
    ".zip": FileCategory.ARCHIVES,
    ".rar": FileCategory.ARCHIVES,
    ".7z": FileCategory.ARCHIVES,
    ".tar": FileCategory.ARCHIVES,
    ".gz": FileCategory.ARCHIVES,
    ".bz2": FileCategory.ARCHIVES,
    ".xz": FileCategory.ARCHIVES,
    ".iso": FileCategory.ARCHIVES,
    
    # Trash
    ".tmp": FileCategory.TRASH,
    ".temp": FileCategory.TRASH,
    ".log": FileCategory.TRASH,
    ".bak": FileCategory.TRASH,
    ".old": FileCategory.TRASH,
    ".cache": FileCategory.TRASH,
    ".crdownload": FileCategory.TRASH,  # Chrome partial downloads
    ".part": FileCategory.TRASH,  # Firefox partial downloads
}


# Destination folders for each category
DESTINATIONS: dict[FileCategory, str] = {
    FileCategory.INSTALLERS: "Software/Installers",
    FileCategory.DOCUMENTS_WORK: "Documents/Work",
    FileCategory.DOCUMENTS_PERSONAL: "Documents/Personal",
    FileCategory.DOCUMENTS: "Documents/Unsorted",
    FileCategory.MEDIA: "Pictures/Sorted/{date}",
    FileCategory.CODE: "Projects/Misc",
    FileCategory.ARCHIVES: "Archives",
    FileCategory.TRASH: None,  # Delete these
}


def categorize_file(filepath: str) -> FileCategory:
    """
    Categorize a file by its extension.
    
    Args:
        filepath: Path to the file
        
    Returns:
        FileCategory for the file
    """
    ext = Path(filepath).suffix.lower()
    return CATEGORY_MAP.get(ext, FileCategory.UNKNOWN)


def get_destination_path(
    category: FileCategory,
    user_home: Optional[str] = None
) -> Optional[str]:
    """
    Get the destination path for a file category.
    
    Args:
        category: The file category
        user_home: User home directory (defaults to ~)
        
    Returns:
        Full destination path or None if file should be deleted
    """
    base_dest = DESTINATIONS.get(category)
    if base_dest is None:
        return None  # File should be deleted
    
    if user_home is None:
        user_home = os.path.expanduser("~")
    
    # Handle date placeholder
    if "{date}" in base_dest:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m")
        base_dest = base_dest.replace("{date}", date_str)
    
    return os.path.join(user_home, base_dest)


async def llm_categorize_document(
    filename: str,
    content_preview: Optional[str] = None
) -> FileCategory:
    """
    Use LLM to determine if a document is WORK or PERSONAL.
    
    Args:
        filename: The document filename
        content_preview: Optional first few lines of content
        
    Returns:
        DOCUMENTS_WORK or DOCUMENTS_PERSONAL
    """
    # Keywords suggesting work documents
    work_keywords = [
        "invoice", "contract", "proposal", "report", "meeting",
        "budget", "project", "client", "quarterly", "annual",
        "presentation", "agenda", "memo", "policy", "procedure",
        "resume", "cv", "cover letter", "application"
    ]
    
    # Keywords suggesting personal documents
    personal_keywords = [
        "receipt", "ticket", "reservation", "travel", "vacation",
        "family", "photo", "birthday", "wedding", "party",
        "recipe", "hobby", "game", "movie", "music"
    ]
    
    filename_lower = filename.lower()
    
    # Simple keyword matching (fast path before LLM)
    work_score = sum(1 for kw in work_keywords if kw in filename_lower)
    personal_score = sum(1 for kw in personal_keywords if kw in filename_lower)
    
    if work_score > personal_score:
        return FileCategory.DOCUMENTS_WORK
    elif personal_score > work_score:
        return FileCategory.DOCUMENTS_PERSONAL
    
    # TODO: Call LLM for ambiguous cases
    # For now, default to uncategorized
    logger.debug(f"Could not categorize document: {filename}")
    return FileCategory.DOCUMENTS


def get_file_age_days(filepath: str) -> int:
    """Get file age in days since last modification."""
    import time
    try:
        stat = os.stat(filepath)
        age_seconds = time.time() - stat.st_mtime
        return int(age_seconds / 86400)
    except OSError:
        return 0


def is_old_installer(filepath: str, days: int = 30) -> bool:
    """Check if an installer is older than threshold."""
    category = categorize_file(filepath)
    if category != FileCategory.INSTALLERS:
        return False
    return get_file_age_days(filepath) > days
