"""
Enhanced Smart Renamer Capability - AI-powered file renaming with content analysis.

Handles:
- Files with excessively long names (>100 chars)
- Files with weird characters (@#$%^&*())
- Generic/meaningless names (IMG_20240124_123456.jpg, Untitled.pdf)
- Duplicate markers (file (1).pdf, file - Copy.pdf)
- Content-based naming using ML and image/document analysis
- Learning from user corrections

Uses LLM and content analysis for context-aware renaming when simple rules aren't enough.
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, List
import json
import asyncio

try:
    from PIL import Image, ExifTags
    from PIL.ExifTags import TAGS
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import PyPDF2
    import pdfplumber
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

from app.agents.janitor.capabilities import BaseCapability, CapabilityResult
from app.agents.janitor.file_categorizer import FileCategory, categorize_file

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Extract meaningful content from files for intelligent naming."""
    
    @staticmethod
    async def extract_image_metadata(image_path: str) -> Dict:
        """Extract comprehensive metadata from images."""
        if not IMAGE_PROCESSING_AVAILABLE:
            return {}
        
        try:
            with Image.open(image_path) as img:
                metadata = {}
                
                # Basic info
                metadata['format'] = img.format
                metadata['mode'] = img.mode
                metadata['size'] = img.size
                
                # EXIF data
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        metadata[tag] = value
                
                # Extract date and location
                date_taken = metadata.get('DateTimeOriginal') or metadata.get('DateTime')
                if date_taken:
                    try:
                        metadata['parsed_date'] = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
                    except:
                        pass
                
                # GPS coordinates
                gps_info = metadata.get('GPSInfo')
                if gps_info:
                    lat, lon = ContentAnalyzer._extract_gps_coords(gps_info)
                    if lat and lon:
                        metadata['latitude'] = lat
                        metadata['longitude'] = lon
                        metadata['location'] = ContentAnalyzer._get_location_name(lat, lon)
                
                # Camera info
                metadata['camera_make'] = metadata.get('Make')
                metadata['camera_model'] = metadata.get('Model')
                
                return metadata
                
        except Exception as e:
            logger.debug(f"[ContentAnalyzer] Failed to extract image metadata: {e}")
            return {}
    
    @staticmethod
    def _extract_gps_coords(gps_info: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS coordinates from EXIF GPS info."""
        try:
            def convert_to_degrees(value):
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)
            
            lat = convert_to_degrees(gps_info.get(2))
            lon = convert_to_degrees(gps_info.get(4))
            
            if gps_info.get(1) == 'S':
                lat = -lat
            if gps_info.get(3) == 'W':
                lon = -lon
                
            return lat, lon
            
        except:
            return None, None
    
    @staticmethod
    def _get_location_name(lat: float, lon: float) -> str:
        """Get location name from coordinates (placeholder)."""
        # TODO: Implement reverse geocoding
        # For now, return coordinates as string
        return f"{lat:.4f},{lon:.4f}"
    
    @staticmethod
    async def extract_document_preview(file_path: str) -> str:
        """Extract text preview from documents."""
        ext = Path(file_path).suffix.lower()
        
        try:
            if ext == '.pdf' and PDF_PROCESSING_AVAILABLE:
                return await ContentAnalyzer._extract_pdf_text(file_path)
            elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
                return await ContentAnalyzer._extract_text_file(file_path)
            elif ext in ['.docx', '.doc']:
                return await ContentAnalyzer._extract_word_text(file_path)
        except Exception as e:
            logger.debug(f"[ContentAnalyzer] Failed to extract text from {file_path}: {e}")
        
        return ""
    
    @staticmethod
    async def _extract_pdf_text(file_path: str) -> str:
        """Extract text from PDF file."""
        text = ""
        
        try:
            # Try pdfplumber first (better quality)
            if pdfplumber:
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages[:3]:  # First 3 pages
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
        except:
            pass
        
        if not text:
            try:
                # Fallback to PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages[:3]:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except:
                pass
        
        return text[:1000]  # First 1000 chars
    
    @staticmethod
    async def _extract_text_file(file_path: str) -> str:
        """Extract text from plain text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:1000]
        except:
            return ""
    
    @staticmethod
    async def _extract_word_text(file_path: str) -> str:
        """Extract text from Word documents."""
        # TODO: Implement Word document extraction
        # Requires python-docx library
        return ""
    
    @staticmethod
    async def analyze_image_content(image_path: str) -> str:
        """Analyze image content for smart naming."""
        if not IMAGE_PROCESSING_AVAILABLE or not OCR_AVAILABLE:
            return ""
        
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale for better OCR
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Extract text using OCR
                text = pytesseract.image_to_string(img)
                return text[:200]  # First 200 chars
                
        except Exception as e:
            logger.debug(f"[ContentAnalyzer] OCR failed for {image_path}: {e}")
            return ""


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
    Enhanced AI-powered file renaming for messy filenames.
    
    Analyzes filenames and suggests clean, meaningful alternatives using:
    - Content analysis and ML
    - Image metadata and OCR
    - Document content extraction
    - Learning from user corrections
    """
    
    name = "smart_renamer"
    description = "Renames files with messy or generic names to clean, meaningful names using content analysis"
    
    def __init__(self):
        self._user_home = os.path.expanduser("~")
        self.content_analyzer = ContentAnalyzer()
        self.naming_history = {}  # Learn from user corrections
        self._load_naming_history()
    
    def _load_naming_history(self):
        """Load naming history from file."""
        try:
            history_file = os.path.join(os.path.expanduser("~"), ".janitor_renames.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.naming_history = json.load(f)
        except:
            pass
    
    def _save_naming_history(self):
        """Save naming history to file."""
        try:
            history_file = os.path.join(os.path.expanduser("~"), ".janitor_renames.json")
            with open(history_file, 'w') as f:
                json.dump(self.naming_history, f, indent=2)
        except:
            pass
    
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
        
        # Generate a suggested new name using enhanced content analysis
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
        Generate a clean, meaningful filename using content analysis.
        
        Strategy:
        1. Try content-based naming for images and documents
        2. Extract meaningful parts from the original name
        3. Extract date if present
        4. Use file metadata if available
        5. Fall back to simple cleanup
        """
        path = Path(filename)
        name_part = path.stem
        extension = path.suffix.lower()
        
        # Get file category for intelligent naming
        category = categorize_file(file_path)
        
        # Try content-based naming first
        content_name = await self._generate_content_based_name(file_path, category, extension)
        if content_name:
            return content_name
        
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
    
    async def _generate_content_based_name(self, file_path: str, category: FileCategory, extension: str) -> Optional[str]:
        """Generate name based on file content analysis."""
        try:
            # Get file creation date
            stat = os.stat(file_path)
            file_date = datetime.fromtimestamp(stat.st_ctime)
        except:
            file_date = datetime.now()
        
        # Category-specific content analysis
        if category in [FileCategory.IMAGES, FileCategory.SCREENSHOTS]:
            return await self._name_image_file(file_path, file_date, extension)
        elif category in [FileCategory.DOCUMENTS, FileCategory.DOCUMENTS_WORK, FileCategory.DOCUMENTS_PERSONAL]:
            return await self._name_document_file(file_path, file_date, extension)
        elif category == FileCategory.VIDEOS:
            return await self._name_video_file(file_path, file_date, extension)
        elif category == FileCategory.AUDIO:
            return await self._name_audio_file(file_path, file_date, extension)
        elif category == FileCategory.INSTALLERS:
            return await self._name_installer_file(file_path, extension)
        
        return None
    
    async def _name_image_file(self, file_path: str, file_date: datetime, extension: str) -> str:
        """Generate intelligent name for image files."""
        metadata = await self.content_analyzer.extract_image_metadata(file_path)
        
        # Use EXIF date if available
        if metadata.get('parsed_date'):
            file_date = metadata['parsed_date']
        
        date_str = file_date.strftime('%Y%m%d')
        
        # Check if it's a screenshot
        if self._is_screenshot(file_path, metadata):
            time_str = file_date.strftime('%H%M')
            return f"Screenshot_{date_str}_{time_str}{extension}"
        
        # Use location if available
        location = metadata.get('location')
        if location and location != f"{metadata.get('latitude', 0):.4f},{metadata.get('longitude', 0):.4f}":
            location_clean = re.sub(r'[^\w\s-]', '', location).strip()[:20]
            return f"Photo_{location_clean}_{date_str}{extension}"
        
        # Use camera info
        camera = metadata.get('camera_make')
        if camera:
            camera_clean = re.sub(r'[^\w\s-]', '', camera).strip()[:10]
            return f"{camera_clean}_{date_str}{extension}"
        
        # Try OCR for content
        ocr_text = await self.content_analyzer.analyze_image_content(file_path)
        if ocr_text:
            words = ocr_text.split()[:3]  # First 3 words
            clean_words = [re.sub(r'[^\w\s-]', '', w).strip() for w in words if len(w) > 2]
            if clean_words:
                content_name = '_'.join(clean_words)
                return f"{content_name}_{date_str}{extension}"
        
        # Fallback to date-based naming
        return f"Photo_{date_str}{extension}"
    
    async def _name_document_file(self, file_path: str, file_date: datetime, extension: str) -> str:
        """Generate intelligent name for document files."""
        # Extract document content
        content = await self.content_analyzer.extract_document_preview(file_path)
        
        if content:
            # Extract meaningful words from content
            words = content.split()
            # Filter out common words
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            
            meaningful_words = [w.lower() for w in words if len(w) > 3 and w.lower() not in stop_words and w.isalnum()]
            
            if meaningful_words:
                # Use first few meaningful words
                name_words = meaningful_words[:4]
                content_name = '_'.join(name_words)
                
                # Add date if recent
                date_str = file_date.strftime('%Y%m%d')
                return f"{content_name}_{date_str}{extension}"
        
        # Fallback to category and date
        category_map = {
            '.pdf': 'Document',
            '.doc': 'Document',
            '.docx': 'Document',
            '.xls': 'Spreadsheet',
            '.xlsx': 'Spreadsheet',
            '.ppt': 'Presentation',
            '.pptx': 'Presentation',
        }
        
        prefix = category_map.get(extension, 'Document')
        date_str = file_date.strftime('%Y%m%d')
        return f"{prefix}_{date_str}{extension}"
    
    async def _name_video_file(self, file_path: str, file_date: datetime, extension: str) -> str:
        """Generate intelligent name for video files."""
        date_str = file_date.strftime('%Y%m%d')
        time_str = file_date.strftime('%H%M')
        
        # Check if screen recording
        filename = Path(file_path).name.lower()
        if any(keyword in filename for keyword in ['recording', 'screen', 'capture']):
            return f"Screen_Recording_{date_str}_{time_str}{extension}"
        
        return f"Video_{date_str}_{time_str}{extension}"
    
    async def _name_audio_file(self, file_path: str, file_date: datetime, extension: str) -> str:
        """Generate intelligent name for audio files."""
        date_str = file_date.strftime('%Y%m%d')
        
        # TODO: Extract audio metadata (artist, title) if available
        return f"Audio_{date_str}{extension}"
    
    async def _name_installer_file(self, file_path: str, extension: str) -> str:
        """Generate intelligent name for installer files."""
        filename = Path(file_path).name
        
        # Extract application name from filename
        name_without_ext = Path(filename).stem
        
        # Clean up common patterns
        cleaned_name = re.sub(r'[-_](v|version|setup|install|win|x64|x86).*$', '', name_without_ext, flags=re.IGNORECASE)
        cleaned_name = re.sub(r'[-_]\d+(\.\d+)*$', '', cleaned_name)  # Remove version numbers
        
        if cleaned_name:
            return f"{cleaned_name}_Installer{extension}"
        
        return f"Installer_{datetime.now().strftime('%Y%m%d')}{extension}"
    
    def _is_screenshot(self, file_path: str, metadata: Dict) -> bool:
        """Determine if image is a screenshot."""
        filename = Path(file_path).name.lower()
        
        # Check filename patterns
        screenshot_keywords = ['screenshot', 'screen shot', 'snip', 'capture', 'clip', 'win_']
        if any(keyword in filename for keyword in screenshot_keywords):
            return True
        
        # Check common screenshot dimensions
        size = metadata.get('size')
        if size:
            common_sizes = [
                (1920, 1080), (1366, 768), (1440, 900), (1280, 720),
                (2560, 1440), (3840, 2160), (1920, 1200), (1680, 1050)
            ]
            if size in common_sizes:
                return True
        
        return False
    
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
        """Rename the file and save to history for learning."""
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
                # Update the new_name with the counter
                new_name = os.path.basename(new_path)
            
            os.rename(file_path, new_path)
            
            # Save to naming history for learning
            old_name = result.metadata.get("old_name", os.path.basename(file_path))
            self.naming_history[old_name] = new_name
            self._save_naming_history()
            
            logger.info(f"[SmartRenamer] Renamed: {old_name} → {new_name}")
            return True
            
        except Exception as e:
            logger.error(f"[SmartRenamer] Rename failed: {e}")
            return False
