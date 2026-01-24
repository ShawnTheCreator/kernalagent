"""
Auto Organizer Capability - Automatically moves files to appropriate folders.

File Routing Rules:
- Documents → ~/Documents/{Work|Personal}
- Images → ~/Pictures/{Screenshots|Photos|Wallpapers}
- Videos → ~/Videos
- Music → ~/Music
- Code → ~/Code or ~/Projects
- Archives → ~/Downloads/Archives
- Installers → ~/Downloads/Software (ask to install)
"""

import os
import logging
from pathlib import Path
from datetime import datetime

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult
from app.agents.janitor.file_categorizer import categorize_file, FileCategory, get_destination_path

logger = logging.getLogger(__name__)


class AutoOrganizerCapability(BaseCapability):
    """Automatically organizes files into appropriate folders."""
    
    name = "auto_organizer"
    description = "Moves files to organized folders based on type"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        
        # Files in these locations trigger organization
        self._staging_paths = [
            os.path.join(self._user_home, "Downloads"),
            os.path.join(self._user_home, "Desktop"),
        ]
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Determine if file should be moved and where.
        
        Only organizes files in staging areas (Downloads/Desktop).
        """
        # Only organize files in staging areas
        is_in_staging = any(
            file_path.startswith(p) for p in self._staging_paths
        )
        
        if not is_in_staging:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Categorize the file
        category = categorize_file(file_path)
        
        # Don't auto-organize unknown files
        if category == FileCategory.UNKNOWN:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
                suggestion="Unknown file type, leaving in place",
            )
        
        # Get destination path
        destination = get_destination_path(category, self._user_home)
        
        if not destination:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Determine if we need permission
        # Auto-approve: media, documents
        # Ask first: executables, code, archives
        needs_permission = category in [
            FileCategory.INSTALLERS,
            FileCategory.CODE,
            FileCategory.ARCHIVES,
        ]
        
        filename = file_info.get("filename", os.path.basename(file_path))
        dest_folder = os.path.basename(destination)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="move",
            confidence=0.85,
            suggestion=f"📁 Move {filename} → {dest_folder}/",
            requires_permission=needs_permission,
            metadata={
                "source": file_path,
                "destination": destination,
                "category": category.value,
                "auto_approve": not needs_permission,
            }
        )
    
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
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(destination_dir, f"{base}_{counter}{ext}")
                    counter += 1
            
            # Move the file
            import shutil
            shutil.move(file_path, dest_path)
            
            logger.info(f"[AutoOrganizer] Moved: {file_path} → {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"[AutoOrganizer] Move failed: {e}")
            return False
