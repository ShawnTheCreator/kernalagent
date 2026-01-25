"""
Installer Handler Capability - Detects software installers and manages them.

Features:
- Detect .exe/.msi installer patterns
- Prompt user to install or delete
- Track installed software
- Clean up old installers after successful install
"""

import os
import re
import logging
from datetime import datetime, timedelta

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


# Patterns that indicate installer files
INSTALLER_PATTERNS = [
    r'setup',
    r'install',
    r'installer',
    r'_setup',
    r'-setup',
    r'\.setup\.',
    r'update',
    r'patch',
]

# Known software vendors
KNOWN_VENDORS = [
    "microsoft", "google", "adobe", "oracle", "nvidia", 
    "amd", "intel", "discord", "spotify", "zoom",
    "vlc", "7zip", "winrar", "notepad++", "vscode",
]


class InstallerHandlerCapability(BaseCapability):
    """Handles software installers - prompts to install or delete."""
    
    name = "installer_handler"
    description = "Detects software installers and offers to install or clean up"
    
    def __init__(self):
        self._software_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Software")
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Check if file is an installer and what to do with it.
        """
        filename = file_info.get("filename", "").lower()
        extension = file_info.get("extension", "").lower()
        size_bytes = file_info.get("size_bytes", 0)
        
        # Only check executables
        if extension not in [".exe", ".msi"]:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Check if it looks like an installer
        is_installer = False
        software_name = ""
        
        # Pattern matching
        for pattern in INSTALLER_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                is_installer = True
                break
        
        # Check for known vendors
        for vendor in KNOWN_VENDORS:
            if vendor in filename:
                is_installer = True
                software_name = vendor.title()
                break
        
        # Size heuristic (installers are usually > 1MB)
        if extension in [".exe", ".msi"] and size_bytes > 1_000_000:
            is_installer = True
        
        if not is_installer:
            return CapabilityResult(
                capability=self.name,
                action_required=False,
            )
        
        # Extract software name from filename
        if not software_name:
            software_name = self._extract_software_name(filename)
        
        return CapabilityResult(
            capability=self.name,
            action_required=True,
            action_type="install_prompt",
            confidence=0.8,
            suggestion=f"💿 New installer detected: {software_name}. Install now?",
            requires_permission=True,
            metadata={
                "software_name": software_name,
                "file_path": file_path,
                "size_mb": round(size_bytes / (1024 * 1024), 1),
                "options": ["install", "move_to_software", "delete"],
            }
        )
    
    def _extract_software_name(self, filename: str) -> str:
        """Extract software name from installer filename."""
        # Remove extension
        name = os.path.splitext(filename)[0]
        
        # Remove common patterns
        remove_patterns = [
            r'_setup$', r'-setup$', r'\.setup$',
            r'_installer$', r'-installer$',
            r'_install$', r'-install$',
            r'_x64$', r'_x86$', r'_64bit$', r'_32bit$',
            r'_win64$', r'_win32$',
            r'\(x64\)$', r'\(x86\)$',
            r'_v?\d+[\.\d]*$',  # Version numbers
        ]
        
        for pattern in remove_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        # Clean up
        name = name.replace('_', ' ').replace('-', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name.title() or "Unknown Software"
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Handle the installer based on user choice."""
        action = result.metadata.get("user_choice", "move_to_software")
        
        if action == "install":
            # Launch the installer
            try:
                import subprocess
                subprocess.Popen([file_path], shell=True)
                logger.info(f"[InstallerHandler] Launched installer: {file_path}")
                return True
            except Exception as e:
                logger.error(f"[InstallerHandler] Launch failed: {e}")
                return False
        
        elif action == "move_to_software":
            # Move to Software folder
            try:
                os.makedirs(self._software_dir, exist_ok=True)
                dest = os.path.join(self._software_dir, os.path.basename(file_path))
                
                import shutil
                shutil.move(file_path, dest)
                logger.info(f"[InstallerHandler] Moved to Software: {dest}")
                return True
            except Exception as e:
                logger.error(f"[InstallerHandler] Move failed: {e}")
                return False
        
        elif action == "delete":
            # Delete the installer
            try:
                os.remove(file_path)
                logger.info(f"[InstallerHandler] Deleted: {file_path}")
                return True
            except Exception as e:
                logger.error(f"[InstallerHandler] Delete failed: {e}")
                return False
        
        return False
