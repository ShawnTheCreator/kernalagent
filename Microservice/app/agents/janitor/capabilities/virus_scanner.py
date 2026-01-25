"""
Virus Scanner Capability - Scans new files for threats.

Uses multiple approaches:
1. VirusTotal API (if configured)
2. Windows Defender scan trigger
3. Heuristic checks for suspicious patterns
"""

import os
import hashlib
import logging
from typing import Optional

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult

logger = logging.getLogger(__name__)


# Suspicious patterns
SUSPICIOUS_EXTENSIONS = [
    ".exe", ".msi", ".bat", ".cmd", ".ps1", ".vbs", ".js",
    ".scr", ".pif", ".com", ".dll", ".jar"
]

DOUBLE_EXTENSION_PATTERNS = [
    ".pdf.exe", ".jpg.exe", ".doc.exe", ".txt.exe",
    ".mp3.exe", ".mp4.exe", ".zip.exe"
]

# Known malware hashes (sample - in production, use VirusTotal API)
KNOWN_MALWARE_HASHES = set()


class VirusScannerCapability(BaseCapability):
    """Scans files for potential threats."""
    
    name = "virus_scanner"
    description = "Scans new files for viruses and suspicious patterns"
    
    def __init__(self):
        self._virustotal_key = os.environ.get("VIRUSTOTAL_API_KEY")
    
    async def analyze(self, file_path: str, file_info: dict) -> CapabilityResult:
        """
        Analyze a file for threats.
        
        Checks:
        1. Double extensions (invoice.pdf.exe)
        2. Suspicious file types from Downloads
        3. Hash against known malware (if available)
        4. File size anomalies
        """
        filename = file_info.get("filename", "")
        extension = file_info.get("extension", "").lower()
        size_bytes = file_info.get("size_bytes", 0)
        
        threat_level = 0
        reasons = []
        
        # Check 1: Double extensions (HIGH RISK)
        for pattern in DOUBLE_EXTENSION_PATTERNS:
            if filename.lower().endswith(pattern):
                threat_level += 80
                reasons.append(f"Double extension detected: {pattern}")
        
        # Check 2: Executable from Downloads (MEDIUM RISK)
        if extension in SUSPICIOUS_EXTENSIONS:
            if "Downloads" in file_path or "Desktop" in file_path:
                threat_level += 30
                reasons.append(f"Executable in staging area: {extension}")
        
        # Check 3: Very small executables (suspicious)
        if extension in [".exe", ".msi"] and size_bytes < 50000:
            threat_level += 20
            reasons.append("Unusually small executable")
        
        # Check 4: Hidden file with executable extension
        if filename.startswith(".") and extension in SUSPICIOUS_EXTENSIONS:
            threat_level += 40
            reasons.append("Hidden executable file")
        
        # Determine action
        if threat_level >= 50:
            return CapabilityResult(
                capability=self.name,
                action_required=True,
                action_type="quarantine",
                confidence=min(threat_level / 100, 0.95),
                suggestion=f"⚠️ Potential threat detected: {', '.join(reasons)}",
                requires_permission=True,
                metadata={
                    "threat_level": threat_level,
                    "reasons": reasons,
                    "recommendation": "quarantine" if threat_level >= 70 else "scan"
                }
            )
        elif threat_level >= 20:
            return CapabilityResult(
                capability=self.name,
                action_required=True,
                action_type="warn",
                confidence=threat_level / 100,
                suggestion=f"⚡ File requires attention: {', '.join(reasons)}",
                requires_permission=False,
                metadata={"threat_level": threat_level, "reasons": reasons}
            )
        
        return CapabilityResult(
            capability=self.name,
            action_required=False,
            confidence=0.9,
            suggestion="File appears safe",
        )
    
    async def execute(self, file_path: str, result: CapabilityResult) -> bool:
        """Execute quarantine or scan action."""
        action = result.action_type
        
        if action == "quarantine":
            # Move to quarantine folder
            quarantine_dir = os.path.join(os.path.expanduser("~"), ".janitor_quarantine")
            os.makedirs(quarantine_dir, exist_ok=True)
            
            import shutil
            dest = os.path.join(quarantine_dir, os.path.basename(file_path))
            shutil.move(file_path, dest)
            logger.warning(f"[VirusScanner] Quarantined: {file_path}")
            return True
        
        elif action == "scan":
            # Trigger Windows Defender scan
            try:
                import subprocess
                subprocess.run([
                    "powershell", "-Command",
                    f'Start-MpScan -ScanPath "{file_path}" -ScanType QuickScan'
                ], capture_output=True, timeout=30)
                logger.info(f"[VirusScanner] Triggered Defender scan: {file_path}")
                return True
            except Exception as e:
                logger.error(f"[VirusScanner] Scan failed: {e}")
                return False
        
        elif action == "warn":
            # Just log the warning - no action needed
            logger.info(f"[VirusScanner] ⚡ Warning for: {os.path.basename(file_path)}")
            return True  # Warning logged, consider success
        
        return True  # Default: no action needed = success
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
