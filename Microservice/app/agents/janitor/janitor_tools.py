"""
Janitor Tools - Safe file operations with transaction logging.

Provides reversible file operations for the JanitorAgent.
All operations are logged for undo functionality.
"""

import os
import shutil
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    """Result of a file operation."""
    success: bool
    source_path: str
    destination_path: Optional[str] = None
    error: Optional[str] = None
    bytes_processed: int = 0
    operation_type: str = "unknown"


class FileAnalyzer:
    """Analyzes files and directories for organization."""
    
    @staticmethod
    def get_file_category(file_path: str) -> str:
        """Categorize file by extension."""
        ext = Path(file_path).suffix.lower()
        
        categories = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages'],
            'spreadsheets': ['.xls', '.xlsx', '.csv', '.ods', '.numbers'],
            'presentations': ['.ppt', '.pptx', '.odp', '.key'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'videos': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg'],
            'code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.c', '.h'],
            'executables': ['.exe', '.msi', '.dmg', '.app', '.deb', '.rpm']
        }
        
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        
        return 'other'
    
    @staticmethod
    def analyze_directory(directory: str) -> dict:
        """Analyze directory for cleanup opportunities."""
        if not os.path.exists(directory):
            return {"error": "Directory not found"}
        
        analysis = {
            "total_files": 0,
            "total_size_mb": 0,
            "categories": {},
            "duplicates": [],
            "large_files": [],
            "old_files": [],
            "empty_folders": []
        }
        
        try:
            for root, dirs, files in os.walk(directory):
                # Check for empty directories
                if not dirs and not files:
                    analysis["empty_folders"].append(root)
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not os.path.exists(file_path):
                        continue
                        
                    try:
                        stat = os.stat(file_path)
                        size_mb = stat.st_size / (1024 * 1024)
                        age_days = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                        
                        analysis["total_files"] += 1
                        analysis["total_size_mb"] += size_mb
                        
                        # Categorize
                        category = FileAnalyzer.get_file_category(file_path)
                        if category not in analysis["categories"]:
                            analysis["categories"][category] = {"count": 0, "size_mb": 0}
                        analysis["categories"][category]["count"] += 1
                        analysis["categories"][category]["size_mb"] += size_mb
                        
                        # Check for large files (>100MB)
                        if size_mb > 100:
                            analysis["large_files"].append({
                                "path": file_path,
                                "size_mb": round(size_mb, 2)
                            })
                        
                        # Check for old files (>365 days)
                        if age_days > 365:
                            analysis["old_files"].append({
                                "path": file_path,
                                "age_days": age_days
                            })
                            
                    except (OSError, IOError):
                        continue
            
        except Exception as e:
            logger.error(f"Directory analysis failed: {e}")
            analysis["error"] = str(e)
        
        return analysis


def is_protected_path(file_path: str) -> bool:
    """Check if file/folder is protected from modification."""
    protected_patterns = [
        "Program Files", "Windows", "System32", "SysWOW64",
        "ProgramData", ".git", "node_modules", "__pycache__",
        "C:\\Windows", "C:\\Program Files"
    ]
    
    abs_path = os.path.abspath(file_path)
    return any(pattern in abs_path for pattern in protected_patterns)


async def safe_move(source: str, destination: str) -> FileOperation:
    """Safely move file/folder with transaction logging."""
    from app.agents.common.transaction_manager import get_transaction_manager
    
    try:
        if not os.path.exists(source):
            return FileOperation(
                success=False,
                source_path=source,
                error="Source path does not exist"
            )
        
        if is_protected_path(source) or is_protected_path(destination):
            return FileOperation(
                success=False,
                source_path=source,
                error="Protected path - operation not allowed"
            )
        
        # Create destination directory if needed
        dest_dir = os.path.dirname(destination)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Get file size for metrics
        size = 0
        if os.path.isfile(source):
            size = os.path.getsize(source)
        else:
            # Calculate directory size
            for root, dirs, files in os.walk(source):
                for file in files:
                    try:
                        size += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        continue
        
        # Perform move
        shutil.move(source, destination)
        
        # Log transaction for undo capability
        tm = get_transaction_manager()
        tm.log_transaction(
            agent="JANITOR_AGENT",
            action_type="move",
            description=f"Moved {os.path.basename(source)} to {dest_dir}",
            details={
                "source": source,
                "destination": destination,
                "size_bytes": size
            }
        )
        
        return FileOperation(
            success=True,
            source_path=source,
            destination_path=destination,
            bytes_processed=size,
            operation_type="move"
        )
        
    except Exception as e:
        logger.error(f"Move operation failed: {e}")
        return FileOperation(
            success=False,
            source_path=source,
            destination_path=destination,
            error=str(e),
            operation_type="move"
        )


async def safe_delete(file_path: str, to_recycle: bool = True) -> FileOperation:
    """Safely delete file/folder with transaction logging."""
    from app.agents.common.transaction_manager import get_transaction_manager
    
    try:
        if not os.path.exists(file_path):
            return FileOperation(
                success=False,
                source_path=file_path,
                error="File does not exist"
            )
        
        if is_protected_path(file_path):
            return FileOperation(
                success=False,
                source_path=file_path,
                error="Protected path - deletion not allowed"
            )
        
        # Get file size for metrics
        size = 0
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
        
        if to_recycle:
            # Move to recycle bin (Windows)
            try:
                import subprocess
                cmd = f'powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(\'{file_path}\', \'OnlyErrorDialogs\', \'SendToRecycleBin\')"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Recycle bin move failed: {result.stderr}")
            except Exception as e:
                # Fallback to regular deletion
                logger.warning(f"Recycle bin failed, using regular delete: {e}")
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    shutil.rmtree(file_path)
                to_recycle = False
        else:
            # Permanent deletion
            if os.path.isfile(file_path):
                os.remove(file_path)
            else:
                shutil.rmtree(file_path)
        
        # Log transaction
        tm = get_transaction_manager()
        tm.log_transaction(
            agent="JANITOR_AGENT",
            action_type="delete",
            description=f"Deleted {os.path.basename(file_path)}",
            details={
                "path": file_path,
                "to_recycle": to_recycle,
                "size_bytes": size
            }
        )
        
        return FileOperation(
            success=True,
            source_path=file_path,
            bytes_processed=size,
            operation_type="delete"
        )
        
    except Exception as e:
        logger.error(f"Delete operation failed: {e}")
        return FileOperation(
            success=False,
            source_path=file_path,
            error=str(e),
            operation_type="delete"
        )


async def organize_by_category(directory: str, dry_run: bool = False) -> dict:
    """Organize files in directory by category."""
    if not os.path.exists(directory):
        return {"error": "Directory not found"}
    
    if is_protected_path(directory):
        return {"error": "Protected directory"}
    
    results = {
        "total_processed": 0,
        "categories_created": [],
        "files_moved": [],
        "errors": []
    }
    
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            
            if os.path.isfile(file_path):
                category = FileAnalyzer.get_file_category(file_path)
                category_dir = os.path.join(directory, category.title())
                
                if not dry_run:
                    os.makedirs(category_dir, exist_ok=True)
                    dest_path = os.path.join(category_dir, file)
                    
                    if not os.path.exists(dest_path):
                        result = await safe_move(file_path, dest_path)
                        if result.success:
                            results["files_moved"].append({
                                "file": file,
                                "category": category,
                                "size_mb": round(result.bytes_processed / (1024 * 1024), 2)
                            })
                            results["total_processed"] += 1
                            
                            if category_dir not in results["categories_created"]:
                                results["categories_created"].append(category)
                        else:
                            results["errors"].append(f"Failed to move {file}: {result.error}")
                else:
                    # Dry run - just simulate
                    results["files_moved"].append({
                        "file": file,
                        "category": category,
                        "would_move_to": category_dir
                    })
                    results["total_processed"] += 1
                    
                    if category not in results["categories_created"]:
                        results["categories_created"].append(category)
    
    except Exception as e:
        logger.error(f"Organization failed: {e}")
        results["error"] = str(e)
    
    return results


async def compress_large_files(directory: str, size_threshold_mb: int = 100) -> dict:
    """Compress large files to save space."""
    import zipfile
    
    results = {
        "files_compressed": [],
        "space_saved_mb": 0,
        "errors": []
    }
    
    if not os.path.exists(directory):
        return {"error": "Directory not found"}
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    
                    if size_mb > size_threshold_mb and not file.endswith('.zip'):
                        zip_path = file_path + '.zip'
                        
                        # Create zip file
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(file_path, os.path.basename(file_path))
                        
                        # Check compression ratio
                        compressed_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                        compression_ratio = compressed_size_mb / size_mb
                        
                        # Only keep compressed version if significant savings
                        if compression_ratio < 0.8:  # 20% or better compression
                            # Delete original and log transaction
                            result = await safe_delete(file_path, to_recycle=True)
                            if result.success:
                                space_saved = size_mb - compressed_size_mb
                                results["files_compressed"].append({
                                    "original_file": file,
                                    "compressed_file": os.path.basename(zip_path),
                                    "original_size_mb": round(size_mb, 2),
                                    "compressed_size_mb": round(compressed_size_mb, 2),
                                    "space_saved_mb": round(space_saved, 2)
                                })
                                results["space_saved_mb"] += space_saved
                        else:
                            # Remove zip if compression wasn't worth it
                            os.remove(zip_path)
                            
                except Exception as e:
                    results["errors"].append(f"Failed to compress {file}: {str(e)}")
                    
    except Exception as e:
        logger.error(f"Compression operation failed: {e}")
        results["error"] = str(e)
    
    return results


async def find_duplicates(directory: str) -> dict:
    """Find duplicate files in directory."""
    import hashlib
    
    results = {
        "duplicate_groups": [],
        "total_duplicates": 0,
        "potential_space_saved_mb": 0
    }
    
    if not os.path.exists(directory):
        return {"error": "Directory not found"}
    
    file_hashes = {}
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    # Calculate file hash
                    hasher = hashlib.md5()
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hasher.update(chunk)
                    file_hash = hasher.hexdigest()
                    
                    file_size = os.path.getsize(file_path)
                    
                    if file_hash not in file_hashes:
                        file_hashes[file_hash] = []
                    
                    file_hashes[file_hash].append({
                        "path": file_path,
                        "size_bytes": file_size
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not hash {file_path}: {e}")
        
        # Find groups with duplicates
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                # Sort by modification time (keep newest)
                files_with_mtime = []
                for file_info in files:
                    try:
                        mtime = os.path.getmtime(file_info["path"])
                        files_with_mtime.append({
                            **file_info,
                            "mtime": mtime
                        })
                    except OSError:
                        continue
                
                if len(files_with_mtime) > 1:
                    files_with_mtime.sort(key=lambda x: x["mtime"], reverse=True)
                    
                    duplicate_group = {
                        "files": files_with_mtime,
                        "keep": files_with_mtime[0]["path"],  # Keep newest
                        "duplicates": [f["path"] for f in files_with_mtime[1:]],
                        "space_wasted_mb": sum(f["size_bytes"] for f in files_with_mtime[1:]) / (1024 * 1024)
                    }
                    
                    results["duplicate_groups"].append(duplicate_group)
                    results["total_duplicates"] += len(files_with_mtime) - 1
                    results["potential_space_saved_mb"] += duplicate_group["space_wasted_mb"]
        
    except Exception as e:
        logger.error(f"Duplicate detection failed: {e}")
        results["error"] = str(e)
    
    return results


async def clean_empty_folders(directory: str) -> dict:
    """Remove empty folders recursively."""
    results = {
        "folders_removed": [],
        "total_removed": 0
    }
    
    if not os.path.exists(directory):
        return {"error": "Directory not found"}
    
    if is_protected_path(directory):
        return {"error": "Protected directory"}
    
    try:
        # Walk from bottom up to handle nested empty folders
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                
                try:
                    if os.path.isdir(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        results["folders_removed"].append(dir_path)
                        results["total_removed"] += 1
                        logger.info(f"Removed empty folder: {dir_path}")
                except OSError as e:
                    logger.warning(f"Could not remove {dir_path}: {e}")
                    
    except Exception as e:
        logger.error(f"Empty folder cleanup failed: {e}")
        results["error"] = str(e)
    
    return results