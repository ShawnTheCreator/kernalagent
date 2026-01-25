"""
Janitor Tools - Safe file system operations.

All operations:
- Check if files are in use before moving/deleting
- Create directories as needed
- Send deletions to Recycle Bin (not permanent delete)
- Never touch system folders
"""

import os
import shutil
import logging
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger(__name__)


# Folders that should NEVER be touched
PROTECTED_FOLDERS = [
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "System32",
    "$Recycle.Bin",
    "Recovery",
    "AppData\\Local\\Microsoft",
    "AppData\\Roaming\\Microsoft",
]


class FileInfo(BaseModel):
    """Information about a file."""
    path: str
    name: str
    extension: str
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    is_hidden: bool = False
    is_readonly: bool = False
    

class MoveResult(BaseModel):
    """Result of a move operation."""
    success: bool
    source: str
    destination: str
    error: Optional[str] = None


class DeleteResult(BaseModel):
    """Result of a delete operation."""
    success: bool
    path: str
    to_recycle: bool = True
    error: Optional[str] = None


def is_protected_path(path: str) -> bool:
    """Check if a path is in a protected system folder."""
    path = os.path.normpath(path)
    parts = path.split(os.sep)
    
    for protected in PROTECTED_FOLDERS:
        # Check against full path components to avoid substring matching
        # e.g. "Recovery" should match "C:\Recovery" but not "C:\RecoveryTest"
        for part in parts:
            if part.lower() == protected.lower():
                return True
                
        # Also check strict start for full paths like "AppData\Local"
        if "\\" in protected:
             if protected.lower() in path.lower():
                 return True
                 
    return False


def is_file_in_use(path: str) -> bool:
    """
    Check if a file is currently in use by another process.
    
    On Windows, tries to open the file exclusively.
    """
    if not os.path.exists(path):
        return False
    
    try:
        # Try to open file exclusively
        with open(path, 'r+b') as f:
            pass
        return False
    except (IOError, OSError, PermissionError):
        return True


async def get_file_info(path: str) -> Optional[FileInfo]:
    """
    Get detailed information about a file.
    
    Args:
        path: Full path to the file
        
    Returns:
        FileInfo or None if file doesn't exist
    """
    if not os.path.exists(path):
        return None
    
    try:
        stat = os.stat(path)
        p = Path(path)
        
        return FileInfo(
            path=path,
            name=p.name,
            extension=p.suffix.lower(),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            accessed_at=datetime.fromtimestamp(stat.st_atime),
            is_hidden=p.name.startswith('.') or bool(stat.st_file_attributes & 2) if hasattr(stat, 'st_file_attributes') else False,
            is_readonly=not os.access(path, os.W_OK),
        )
    except Exception as e:
        logger.error(f"Error getting file info for {path}: {e}")
        return None


async def safe_move(src: str, dst: str) -> MoveResult:
    """
    Safely move a file to a new location.
    
    - Creates destination directory if needed
    - Checks if file is in use
    - Checks for protected paths
    
    Args:
        src: Source file path
        dst: Destination file path
        
    Returns:
        MoveResult with success status
    """
    # Validate paths
    if is_protected_path(src):
        return MoveResult(
            success=False,
            source=src,
            destination=dst,
            error="Source is in a protected folder"
        )
    
    if not os.path.exists(src):
        return MoveResult(
            success=False,
            source=src,
            destination=dst,
            error="Source file does not exist"
        )
    
    if is_file_in_use(src):
        return MoveResult(
            success=False,
            source=src,
            destination=dst,
            error="File is in use by another process"
        )
    
    try:
        # Create destination directory
        dst_dir = os.path.dirname(dst)
        os.makedirs(dst_dir, exist_ok=True)
        
        # Handle filename conflicts
        final_dst = dst
        if os.path.exists(dst):
            base, ext = os.path.splitext(dst)
            counter = 1
            while os.path.exists(final_dst):
                final_dst = f"{base}_{counter}{ext}"
                counter += 1
        
        # Move the file
        shutil.move(src, final_dst)
        logger.info(f"Moved: {src} → {final_dst}")
        
        # Log transaction
        try:
            from app.agents.common.transaction_manager import get_transaction_manager
            tm = get_transaction_manager()
            tm.log_transaction(
                agent="Janitor",
                action_type="move",
                description=f"Moved {os.path.basename(src)}",
                details={"source": src, "destination": final_dst}
            )
        except Exception as e:
            logger.warning(f"Failed to log transaction: {e}")
        
        return MoveResult(
            success=True,
            source=src,
            destination=final_dst
        )
        
    except Exception as e:
        logger.error(f"Error moving {src}: {e}")
        return MoveResult(
            success=False,
            source=src,
            destination=dst,
            error=str(e)
        )


async def safe_delete(path: str, to_recycle: bool = True) -> DeleteResult:
    """
    Safely delete a file.
    
    By default, moves to Recycle Bin instead of permanent delete.
    
    Args:
        path: Path to file to delete
        to_recycle: If True, move to Recycle Bin
        
    Returns:
        DeleteResult with success status
    """
    if is_protected_path(path):
        return DeleteResult(
            success=False,
            path=path,
            to_recycle=to_recycle,
            error="File is in a protected folder"
        )
    
    if not os.path.exists(path):
        return DeleteResult(
            success=False,
            path=path,
            to_recycle=to_recycle,
            error="File does not exist"
        )
    
    if is_file_in_use(path):
        return DeleteResult(
            success=False,
            path=path,
            to_recycle=to_recycle,
            error="File is in use by another process"
        )
    
    try:
        if to_recycle:
            # Use send2trash for Recycle Bin (cross-platform)
            try:
                from send2trash import send2trash
                send2trash(path)
            except ImportError:
                # Fallback: move to a "trash" folder
                trash_dir = os.path.join(os.path.expanduser("~"), ".janitor_trash")
                os.makedirs(trash_dir, exist_ok=True)
                trash_path = os.path.join(trash_dir, os.path.basename(path))
                shutil.move(path, trash_path)
                logger.warning(f"send2trash not installed, moved to {trash_dir}")
        else:
            os.remove(path)
        
        logger.info(f"Deleted: {path} (recycle={to_recycle})")
        
        # Log transaction
        try:
            from app.agents.common.transaction_manager import get_transaction_manager
            tm = get_transaction_manager()
            tm.log_transaction(
                agent="Janitor",
                action_type="delete",
                description=f"Deleted {os.path.basename(path)}",
                details={
                    "path": path, 
                    "to_recycle": to_recycle,
                    "trash_path": trash_path if not to_recycle and 'trash_path' in locals() else None
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log transaction: {e}")

        return DeleteResult(
            success=True,
            path=path,
            to_recycle=to_recycle
        )
        
    except Exception as e:
        logger.error(f"Error deleting {path}: {e}")
        return DeleteResult(
            success=False,
            path=path,
            to_recycle=to_recycle,
            error=str(e)
        )


def get_temp_folders() -> list[str]:
    """Get system and user temp folders."""
    folders = []
    
    # User temp
    user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if user_temp and os.path.exists(user_temp):
        folders.append(user_temp)
    
    # System temp (Windows)
    if os.name == 'nt':
        system_temp = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
        if os.path.exists(system_temp):
            folders.append(system_temp)
    
    return folders


async def get_folder_size(path: str) -> int:
    """Get total size of a folder in bytes."""
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


async def get_folder_file_count(path: str) -> int:
    """Get total number of files in a folder."""
    count = 0
    try:
        for _, _, filenames in os.walk(path):
            count += len(filenames)
    except (OSError, PermissionError):
        pass
    return count


async def scan_folder(
    path: str,
    extensions: Optional[list[str]] = None,
    min_age_days: int = 0,
    max_size_mb: Optional[float] = None,
    min_size_mb: Optional[float] = None,
) -> list[FileInfo]:
    """
    Scan a folder and return file info based on filters.
    
    Args:
        path: Folder path to scan
        extensions: Only include these extensions (e.g., [".tmp", ".log"])
        min_age_days: Only include files older than this
        max_size_mb: Only include files smaller than this
        min_size_mb: Only include files larger than this
        
    Returns:
        List of FileInfo matching the criteria
    """
    results = []
    
    if not os.path.exists(path):
        return results
    
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            if not os.path.isfile(item_path):
                continue
            
            info = await get_file_info(item_path)
            if info is None:
                continue
            
            # Apply filters
            if extensions:
                if info.extension not in extensions:
                    continue
            
            if min_age_days > 0:
                age = (datetime.now() - info.modified_at).days
                if age < min_age_days:
                    continue
            
            if max_size_mb is not None:
                if info.size_bytes > max_size_mb * 1024 * 1024:
                    continue
            
            if min_size_mb is not None:
                if info.size_bytes < min_size_mb * 1024 * 1024:
                    continue
            
            results.append(info)
            
    except (OSError, PermissionError) as e:
        logger.warning(f"Error scanning {path}: {e}")
    
    return results


async def find_large_files(
    path: str,
    min_size_mb: float = 500,
    max_depth: int = 10
) -> list[FileInfo]:
    """
    Find large files in deep subdirectories.
    
    Args:
        path: Root path to search
        min_size_mb: Minimum file size in MB
        max_depth: Maximum directory depth to search
        
    Returns:
        List of large files found
    """
    results = []
    min_bytes = min_size_mb * 1024 * 1024
    
    def scan_recursive(current_path: str, depth: int):
        if depth > max_depth:
            return
        
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                
                if is_protected_path(item_path):
                    continue
                
                if os.path.isfile(item_path):
                    try:
                        size = os.path.getsize(item_path)
                        if size >= min_bytes:
                            # Add to results (synchronously for now)
                            info = FileInfo(
                                path=item_path,
                                name=os.path.basename(item_path),
                                extension=Path(item_path).suffix.lower(),
                                size_bytes=size,
                                created_at=datetime.now(),
                                modified_at=datetime.now(),
                                accessed_at=datetime.now(),
                            )
                            results.append(info)
                    except (OSError, PermissionError):
                        pass
                        
                elif os.path.isdir(item_path):
                    scan_recursive(item_path, depth + 1)
                    
        except (OSError, PermissionError):
            pass
    
    scan_recursive(path, 0)
    return results
