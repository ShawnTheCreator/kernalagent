"""
Auto Organizer V3 - Intelligent file organization with expanded scope.

Features:
- Expanded monitoring (not just Downloads/Desktop)
- Smart file routing to correct system folders
- Misplaced file detection (e.g., video in Documents → Videos)
- Auto-archive old Downloads
- Screenshot-aware organization
"""

import os
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult
from app.agents.janitor.file_categorizer import (
    categorize_file, 
    FileCategory, 
    get_destination_path,
    is_misplaced_file,
    should_archive_file,
)

logger = logging.getLogger(__name__)


class AutoOrganizerCapability(BaseCapability):
    """
    V3 Auto Organizer - Intelligently organizes files across the system.
    
    Supports:
    - Staging areas (Downloads, Desktop) → Move to correct folders
    - Monitored folders → Detect misplaced files
    - Auto-archive old Downloads
    """
    
    name = "auto_organizer"
    description = "Smart file organization with type routing and misplacement detection"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        
        # Files in staging areas always get organized
        self._staging_paths = [
            os.path.join(self._user_home, "Downloads"),
            os.path.join(self._user_home, "Desktop"),
        ]
        
        # Monitor these folders for misplaced files
        self._monitored_paths = [
            os.path.join(self._user_home, "Documents"),
            os.path.join(self._user_home, "Pictures"),
            os.path.join(self._user_home, "Videos"),
            os.path.join(self._user_home, "Music"),
        ]
        
        # Archive settings
        self._archive_after_days = 30
        self._archive_folder = os.path.join(
            self._user_home, "Downloads", "Archive"
        )
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Analyze file and determine organization action.
        
        Decision logic:
        1. If in staging area → Route to correct system folder
        2. If in monitored folder but wrong type → Flag as misplaced
        3. If old file in Downloads → Suggest archive
        """
        filename = file_info.get("filename", os.path.basename(file_path))
        
        # --- PRIORITY 1: Staging area organization ---
        is_in_staging = any(
            file_path.startswith(p) for p in self._staging_paths
        )
        
        if is_in_staging:
            return await self._analyze_staging_file(file_path, file_info)
        
        # --- PRIORITY 2: Misplaced file detection ---
        is_in_monitored = any(
            file_path.startswith(p) for p in self._monitored_paths
        )
        
        if is_in_monitored:
            return await self._analyze_misplaced_file(file_path, file_info)
        
        # File is not in a monitored location
        return CapabilityResult(
            capability=self.name,
            action_required=False,
        )
    
    async def _analyze_staging_file(
        self, 
        file_path: str, 
        file_info: dict
    ) -> CapabilityResult:
        """Analyze a file in a staging area (Downloads/Desktop)."""
        filename = file_info.get("filename", os.path.basename(file_path))
        category = categorize_file(file_path)
        
        # Don't auto-organize unknown files
        if category == FileCategory.UNKNOWN:
            # Check if it should be archived instead
            if should_archive_file(file_path, self._archive_after_days):
                return self._create_archive_result(file_path, filename)
            
            return CapabilityResult(
                capability=self.name,
                action_required=False,
                suggestion="Unknown file type, leaving in place",
            )
        
        # Get destination
        destination = get_destination_path(category, self._user_home, file_path)
        
        if not destination:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Permission requirements
        needs_permission = category in [
            FileCategory.INSTALLERS,
            FileCategory.CODE,
            FileCategory.ARCHIVES,
        ]
        
        # Create friendly descriptions
        category_icons = {
            FileCategory.IMAGES: "🖼️",
            FileCategory.VIDEOS: "🎬",
            FileCategory.AUDIO: "🎵",
            FileCategory.SCREENSHOTS: "📸",
            FileCategory.DOCUMENTS: "📄",
            FileCategory.DOCUMENTS_WORK: "💼",
            FileCategory.DOCUMENTS_PERSONAL: "🏠",
            FileCategory.CODE: "💻",
            FileCategory.INSTALLERS: "📦",
            FileCategory.ARCHIVES: "🗜️",
        }
        
        icon = category_icons.get(category, "📁")
        dest_display = self._get_display_path(destination)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="move",
            confidence=0.9,
            suggestion=f"{icon} Move {filename} → {dest_display}",
            requires_permission=needs_permission,
            metadata={
                "source": file_path,
                "destination": destination,
                "category": category.value,
                "auto_approve": not needs_permission,
                "action_subtype": "organize",
            }
        )
    
    async def _analyze_misplaced_file(
        self, 
        file_path: str, 
        file_info: dict
    ) -> CapabilityResult:
        """Analyze a file that may be in the wrong folder."""
        filename = file_info.get("filename", os.path.basename(file_path))
        
        is_misplaced, category, correct_dest = is_misplaced_file(file_path)
        
        if not is_misplaced or not correct_dest:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # File is in wrong location!
        current_folder = Path(file_path).parent.name
        dest_display = self._get_display_path(correct_dest)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="move",
            confidence=0.75,  # Lower confidence for monitored folders
            suggestion=f"⚠️ Misplaced: {filename} in {current_folder} → {dest_display}",
            requires_permission=True,  # Always ask for misplaced files
            metadata={
                "source": file_path,
                "destination": correct_dest,
                "category": category.value if category else "unknown",
                "auto_approve": False,
                "action_subtype": "fix_misplaced",
            }
        )
    
    def _create_archive_result(
        self, 
        file_path: str, 
        filename: str
    ) -> CapabilityResult:
        """Create an archive action result for old files."""
        now = datetime.now()
        archive_dest = os.path.join(
            self._archive_folder,
            now.strftime("%Y-%m")  # e.g., "2026-01"
        )
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="move",
            confidence=0.7,
            suggestion=f"📦 Archive old file: {filename} → Archive/{now.strftime('%Y-%m')}",
            requires_permission=True,
            metadata={
                "source": file_path,
                "destination": archive_dest,
                "category": "archive",
                "auto_approve": False,
                "action_subtype": "archive_old",
            }
        )
    
    def _get_display_path(self, full_path: str) -> str:
        """Convert a full path to a user-friendly display path."""
        # Replace home directory with ~
        if full_path.startswith(self._user_home):
            return "~" + full_path[len(self._user_home):]
        return full_path
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Move the file to its destination."""
        destination_dir = result.metadata.get("destination", "")
        
        if not destination_dir:
            return False
        
        try:
            # Create destination directory
            os.makedirs(destination_dir, exist_ok=True)
            
            # Generate destination path
            filename = os.path.basename(file_path)
            dest_path = os.path.join(destination_dir, filename)
            
            # Handle conflicts
            if os.path.exists(dest_path):
                dest_path = self._resolve_conflict(dest_path)
            
            # Move the file
            shutil.move(file_path, dest_path)
            
            action_subtype = result.metadata.get("action_subtype", "organize")
            logger.info(
                f"[AutoOrganizer/{action_subtype}] Moved: {file_path} → {dest_path}"
            )
            return True
            
        except Exception as e:
            logger.error(f"[AutoOrganizer] Move failed: {e}")
            return False
    
    def _resolve_conflict(self, dest_path: str) -> str:
        """Resolve filename conflicts by adding a counter."""
        base, ext = os.path.splitext(dest_path)
        counter = 1
        new_path = dest_path
        
        while os.path.exists(new_path):
            new_path = f"{base}_{counter}{ext}"
            counter += 1
        
        return new_path
    
    # === BATCH OPERATIONS ===
    
    async def scan_folder(self, folder_path: str) -> List[CapabilityResult]:
        """
        Scan an entire folder and return organization suggestions.
        
        This is used by the clean-folder API endpoint.
        """
        results = []
        
        if not os.path.isdir(folder_path):
            return results
        
        for entry in os.scandir(folder_path):
            if entry.is_file():
                file_info = {
                    "filename": entry.name,
                    "size": entry.stat().st_size,
                }
                result = await self.analyze(entry.path, file_info)
                if result.action_required:
                    results.append(result)
        
        return results
    
    async def organize_folder(
        self, 
        folder_path: str, 
        auto_approve_categories: Optional[List[str]] = None
    ) -> dict:
        """
        Organize all files in a folder.
        
        Returns summary of actions taken.
        """
        if auto_approve_categories is None:
            auto_approve_categories = ["IMAGES", "VIDEOS", "AUDIO", "SCREENSHOTS"]
        
        results = await self.scan_folder(folder_path)
        
        summary = {
            "scanned": 0,
            "moved": 0,
            "skipped": 0,
            "errors": 0,
            "actions": []
        }
        
        for result in results:
            summary["scanned"] += 1
            
            category = result.metadata.get("category", "")
            source = result.metadata.get("source", "")
            
            # Check if auto-approved
            if category in auto_approve_categories:
                success = await self.execute(source, result)
                if success:
                    summary["moved"] += 1
                    summary["actions"].append({
                        "action": "moved",
                        "file": os.path.basename(source),
                        "destination": result.metadata.get("destination"),
                    })
                else:
                    summary["errors"] += 1
            else:
                summary["skipped"] += 1
                summary["actions"].append({
                    "action": "needs_approval",
                    "file": os.path.basename(source),
                    "suggestion": result.suggestion,
                })
        
        return summary
