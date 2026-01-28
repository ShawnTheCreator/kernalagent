"""
File Categorizer V3 - Smart file routing by type.

Separated media categories for intelligent organization:
- IMAGES → ~/Pictures/{YYYY}/{Month}/
- VIDEOS → ~/Videos/{YYYY}/{Month}/
- AUDIO → ~/Music/{Artist} or ~/Music/Unsorted/
- DOCUMENTS → ~/Documents/{Work|Personal}
- CODE → ~/Code/
- ARCHIVES → ~/Downloads/Archives/
- INSTALLERS → ~/Downloads/Software/
- SCREENSHOTS → ~/Pictures/Screenshots/{YYYY-MM}/
"""

from enum import Enum
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime
import os
import re
import logging

logger = logging.getLogger(__name__)


class FileCategory(str, Enum):
    """Enhanced file categories for smart organization."""
    # Media (separated)
    IMAGES = "IMAGES"
    VIDEOS = "VIDEOS"  
    AUDIO = "AUDIO"
    SCREENSHOTS = "SCREENSHOTS"
    
    # Documents
    DOCUMENTS_WORK = "DOCUMENTS_WORK"
    DOCUMENTS_PERSONAL = "DOCUMENTS_PERSONAL"
    DOCUMENTS = "DOCUMENTS"
    
    # Tech
    CODE = "CODE"
    INSTALLERS = "INSTALLERS"
    ARCHIVES = "ARCHIVES"

    # Creative / Other
    DESIGN = "DESIGN"
    FONTS = "FONTS"
    THREE_D = "THREE_D"
    EBOOKS = "EBOOKS"
    
    # Misc
    TRASH = "TRASH"
    UNKNOWN = "UNKNOWN"
    
    # Legacy compatibility
    MEDIA = "MEDIA"


# Extension to category mapping (V3 - separated media types)
CATEGORY_MAP: dict[str, FileCategory] = {
    # === IMAGES ===
    ".jpg": FileCategory.IMAGES,
    ".jpeg": FileCategory.IMAGES,
    ".png": FileCategory.IMAGES,
    ".gif": FileCategory.IMAGES,
    ".bmp": FileCategory.IMAGES,
    ".svg": FileCategory.IMAGES,
    ".webp": FileCategory.IMAGES,
    ".ico": FileCategory.IMAGES,
    ".heic": FileCategory.IMAGES,
    ".heif": FileCategory.IMAGES,
    ".raw": FileCategory.IMAGES,
    ".tiff": FileCategory.IMAGES,
    ".tif": FileCategory.IMAGES,
    ".jfif": FileCategory.IMAGES,
    
    # === VIDEOS ===
    ".mp4": FileCategory.VIDEOS,
    ".mkv": FileCategory.VIDEOS,
    ".avi": FileCategory.VIDEOS,
    ".mov": FileCategory.VIDEOS,
    ".wmv": FileCategory.VIDEOS,
    ".flv": FileCategory.VIDEOS,
    ".webm": FileCategory.VIDEOS,
    ".m4v": FileCategory.VIDEOS,
    ".3gp": FileCategory.VIDEOS,
    ".mpeg": FileCategory.VIDEOS,
    ".mpg": FileCategory.VIDEOS,
    
    # === AUDIO ===
    ".mp3": FileCategory.AUDIO,
    ".wav": FileCategory.AUDIO,
    ".flac": FileCategory.AUDIO,
    ".aac": FileCategory.AUDIO,
    ".ogg": FileCategory.AUDIO,
    ".m4a": FileCategory.AUDIO,
    ".wma": FileCategory.AUDIO,
    ".aiff": FileCategory.AUDIO,
    ".opus": FileCategory.AUDIO,
    
    # === DOCUMENTS ===
    ".pdf": FileCategory.DOCUMENTS,
    ".docx": FileCategory.DOCUMENTS,
    ".doc": FileCategory.DOCUMENTS,
    ".txt": FileCategory.DOCUMENTS,
    ".xlsx": FileCategory.DOCUMENTS,
    ".xls": FileCategory.DOCUMENTS,
    ".pptx": FileCategory.DOCUMENTS,
    ".ppt": FileCategory.DOCUMENTS,
    ".odt": FileCategory.DOCUMENTS,
    ".ods": FileCategory.DOCUMENTS,
    ".odp": FileCategory.DOCUMENTS,
    ".rtf": FileCategory.DOCUMENTS,
    ".md": FileCategory.DOCUMENTS,
    ".csv": FileCategory.DOCUMENTS,
    ".epub": FileCategory.DOCUMENTS,
    ".mobi": FileCategory.EBOOKS,
    ".azw": FileCategory.EBOOKS,
    ".azw3": FileCategory.EBOOKS,
    ".cbz": FileCategory.EBOOKS,
    ".cbr": FileCategory.EBOOKS,

    # === DESIGN ===
    ".psd": FileCategory.DESIGN,
    ".ai": FileCategory.DESIGN,
    ".xd": FileCategory.DESIGN,
    ".fig": FileCategory.DESIGN,
    ".sketch": FileCategory.DESIGN,
    ".indd": FileCategory.DESIGN,
    ".ase": FileCategory.DESIGN,
    ".aseprite": FileCategory.DESIGN,
    ".blend": FileCategory.THREE_D,

    # === FONTS ===
    ".ttf": FileCategory.FONTS,
    ".otf": FileCategory.FONTS,
    ".woff": FileCategory.FONTS,
    ".woff2": FileCategory.FONTS,

    # === 3D ===
    ".fbx": FileCategory.THREE_D,
    ".obj": FileCategory.THREE_D,
    ".stl": FileCategory.THREE_D,
    ".glb": FileCategory.THREE_D,
    ".gltf": FileCategory.THREE_D,
    ".3ds": FileCategory.THREE_D,
    ".dae": FileCategory.THREE_D,
    ".usd": FileCategory.THREE_D,
    ".usdz": FileCategory.THREE_D,
    
    # === CODE ===
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
    ".sass": FileCategory.CODE,
    ".less": FileCategory.CODE,
    ".json": FileCategory.CODE,
    ".yaml": FileCategory.CODE,
    ".yml": FileCategory.CODE,
    ".xml": FileCategory.CODE,
    ".sql": FileCategory.CODE,
    ".sh": FileCategory.CODE,
    ".bash": FileCategory.CODE,
    ".bat": FileCategory.CODE,
    ".ps1": FileCategory.CODE,
    ".vue": FileCategory.CODE,
    ".svelte": FileCategory.CODE,
    ".lua": FileCategory.CODE,
    ".r": FileCategory.CODE,
    ".dart": FileCategory.CODE,
    ".ipynb": FileCategory.CODE,
    ".toml": FileCategory.CODE,
    ".ini": FileCategory.CODE,
    ".cfg": FileCategory.CODE,
    ".env": FileCategory.CODE,
    
    # === ARCHIVES ===
    ".zip": FileCategory.ARCHIVES,
    ".rar": FileCategory.ARCHIVES,
    ".7z": FileCategory.ARCHIVES,
    ".tar": FileCategory.ARCHIVES,
    ".gz": FileCategory.ARCHIVES,
    ".bz2": FileCategory.ARCHIVES,
    ".xz": FileCategory.ARCHIVES,
    ".iso": FileCategory.ARCHIVES,
    ".dmg": FileCategory.ARCHIVES,  # Also an installer on Mac
    ".zst": FileCategory.ARCHIVES,
    
    # === INSTALLERS ===
    ".exe": FileCategory.INSTALLERS,
    ".msi": FileCategory.INSTALLERS,
    ".deb": FileCategory.INSTALLERS,
    ".rpm": FileCategory.INSTALLERS,
    ".appx": FileCategory.INSTALLERS,
    ".msix": FileCategory.INSTALLERS,
    ".appimage": FileCategory.INSTALLERS,
    ".apk": FileCategory.INSTALLERS,
    
    # === TRASH ===
    ".tmp": FileCategory.TRASH,
    ".temp": FileCategory.TRASH,
    ".log": FileCategory.TRASH,
    ".bak": FileCategory.TRASH,
    ".old": FileCategory.TRASH,
    ".cache": FileCategory.TRASH,
    ".crdownload": FileCategory.TRASH,
    ".part": FileCategory.TRASH,
    ".download": FileCategory.TRASH,
    ".ds_store": FileCategory.TRASH,
    ".thumbs.db": FileCategory.TRASH,
}


# Screenshot filename patterns
SCREENSHOT_PATTERNS = [
    r"^screenshot",
    r"^screen shot",
    r"^snip",
    r"^capture",
    r"^clip[_-]?\d+",
    r"^image\s*\d+",
    r"^Screen\s*Recording",
    r"^WIN_\d+",  # Windows key screenshots
    r"^\d{4}-\d{2}-\d{2}[_\s]\d{2}[._]\d{2}",  # Date-time pattern
]


def is_screenshot(filename: str) -> bool:
    """
    Detect if a file is a screenshot based on its name.
    """
    name_lower = filename.lower()
    
    # Check patterns
    for pattern in SCREENSHOT_PATTERNS:
        if re.match(pattern, name_lower, re.IGNORECASE):
            return True
    
    # Additional checks
    if "screenshot" in name_lower or "screen shot" in name_lower:
        return True
    if "snipping" in name_lower or "snip_" in name_lower:
        return True
    
    return False


def categorize_file(filepath: str) -> FileCategory:
    """
    Categorize a file by its extension and name.
    
    Args:
        filepath: Path to the file
        
    Returns:
        FileCategory for the file
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    filename = path.name
    
    # Check if it's a screenshot first (images only)
    base_category = CATEGORY_MAP.get(ext, FileCategory.UNKNOWN)
    if base_category == FileCategory.IMAGES and is_screenshot(filename):
        return FileCategory.SCREENSHOTS
    
    return base_category


def get_destination_path(
    category: FileCategory,
    user_home: Optional[str] = None,
    file_path: Optional[str] = None
) -> Optional[str]:
    """
    Get the smart destination path for a file category.
    
    V3: Uses date-based subfolders for media files.
    
    Args:
        category: The file category
        user_home: User home directory (defaults to ~)
        file_path: Optional original file path (for date detection)
        
    Returns:
        Full destination path or None if file should be deleted
    """
    if user_home is None:
        user_home = os.path.expanduser("~")
    
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%B")  # Full month name
    year_month = now.strftime("%Y-%m")
    
    # Smart destinations based on category
    destinations = {
        # Media - to system folders with date organization
        FileCategory.IMAGES: os.path.join(user_home, "Pictures", year, month),
        FileCategory.VIDEOS: os.path.join(user_home, "Videos", year, month),
        FileCategory.AUDIO: os.path.join(user_home, "Music", "Downloads"),
        FileCategory.SCREENSHOTS: os.path.join(user_home, "Pictures", "Screenshots", year_month),
        
        # Documents
        FileCategory.DOCUMENTS: os.path.join(user_home, "Documents", "Unsorted"),
        FileCategory.DOCUMENTS_WORK: os.path.join(user_home, "Documents", "Work"),
        FileCategory.DOCUMENTS_PERSONAL: os.path.join(user_home, "Documents", "Personal"),
        
        # Tech
        FileCategory.CODE: os.path.join(user_home, "Code"),
        FileCategory.INSTALLERS: os.path.join(user_home, "Downloads", "Software"),
        FileCategory.ARCHIVES: os.path.join(user_home, "Downloads", "Archives"),

        # Creative / Other
        FileCategory.DESIGN: os.path.join(user_home, "Documents", "Design"),
        FileCategory.FONTS: os.path.join(user_home, "Documents", "Fonts"),
        FileCategory.THREE_D: os.path.join(user_home, "3D Objects", year, month),
        FileCategory.EBOOKS: os.path.join(user_home, "Documents", "Books"),
        
        # Legacy
        FileCategory.MEDIA: os.path.join(user_home, "Pictures", year, month),
        
        # Trash = delete
        FileCategory.TRASH: None,
        FileCategory.UNKNOWN: None,
    }
    
    return destinations.get(category)


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
        "resume", "cv", "cover letter", "application", "tax",
        "payroll", "statement", "financial", "company", "corporate"
    ]
    
    # Keywords suggesting personal documents
    personal_keywords = [
        "receipt", "ticket", "reservation", "travel", "vacation",
        "family", "photo", "birthday", "wedding", "party",
        "recipe", "hobby", "game", "movie", "music", "shopping",
        "personal", "home", "medical", "health", "fitness"
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


def is_old_file(filepath: str, days: int = 30) -> bool:
    """Check if a file is older than threshold."""
    return get_file_age_days(filepath) > days


def is_misplaced_file(filepath: str) -> Tuple[bool, Optional[FileCategory], Optional[str]]:
    """
    Check if a file is in the wrong folder.
    
    For example: A .mp4 file in ~/Documents should be in ~/Videos.
    
    Returns:
        Tuple of (is_misplaced, correct_category, correct_destination)
    """
    path = Path(filepath)
    category = categorize_file(filepath)
    user_home = os.path.expanduser("~")
    
    # Get parent folder name
    parent = path.parent.name.lower()
    parent_path = str(path.parent).lower()
    
    # Define expected locations for categories
    expected_parents = {
        FileCategory.IMAGES: ["pictures", "photos", "images"],
        FileCategory.VIDEOS: ["videos", "movies"],
        FileCategory.AUDIO: ["music", "audio", "songs"],
        FileCategory.DOCUMENTS: ["documents", "docs"],
        FileCategory.CODE: ["code", "projects", "dev", "development"],
        FileCategory.DESIGN: ["design", "assets"],
        FileCategory.FONTS: ["fonts"],
        FileCategory.THREE_D: ["3d", "3d objects", "models"],
        FileCategory.EBOOKS: ["books", "ebooks"],
    }
    
    # Check if file is in wrong location
    expected = expected_parents.get(category, [])
    if expected and not any(exp in parent_path for exp in expected):
        # File is misplaced!
        correct_dest = get_destination_path(category, user_home, filepath)
        return (True, category, correct_dest)
    
    return (False, None, None)


def should_archive_file(filepath: str, archive_after_days: int = 30) -> bool:
    """
    Check if a file in Downloads should be archived.
    
    Files older than X days in Downloads are candidates for archiving.
    """
    path = Path(filepath)
    user_home = os.path.expanduser("~")
    downloads_path = os.path.join(user_home, "Downloads")
    
    # Only archive files directly in Downloads (not subfolders)
    if str(path.parent) != downloads_path:
        return False
    
    # Check age
    return is_old_file(filepath, archive_after_days)
