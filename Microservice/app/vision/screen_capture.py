"""
Screen Capture Module - Eyes of the Agent

Captures screenshots for vision-based recovery.
"""

import os
import base64
import tempfile
from datetime import datetime
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import PIL for screen capture
try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - screen capture disabled")


def capture_screen() -> Optional[str]:
    """
    Capture the current screen and return path to saved image.
    
    Returns:
        Path to saved screenshot, or None if capture failed
    """
    if not PIL_AVAILABLE:
        logger.error("PIL not available for screen capture")
        return None
    
    try:
        # Capture full screen
        screenshot = ImageGrab.grab()
        
        # Save to temp file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_{timestamp}.png"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        screenshot.save(filepath, "PNG")
        logger.info(f"[VISION] Screenshot saved: {filepath}")
        
        return filepath
    except Exception as e:
        logger.error(f"[VISION] Screen capture failed: {e}")
        return None


def capture_screen_base64(
    max_width: int = 1280,
    max_height: int = 720,
    use_jpeg: bool = True,
    jpeg_quality: int = 75
) -> Optional[str]:
    """
    Capture screen and return as base64 encoded string.
    
    Args:
        max_width: Maximum width after resize (default 1280 for faster API)
        max_height: Maximum height after resize (default 720)
        use_jpeg: Use JPEG instead of PNG (smaller, ~70% reduction)
        jpeg_quality: JPEG quality 0-100 (default 75, good balance)
    
    Returns:
        Base64 encoded image, or None if capture failed
    """
    if not PIL_AVAILABLE:
        logger.error("PIL not available for screen capture")
        return None
    
    try:
        import io
        
        # Capture full screen
        screenshot = ImageGrab.grab()
        original_size = screenshot.size
        
        # Resize for API efficiency
        max_size = (max_width, max_height)
        screenshot.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to base64 with optional compression
        buffer = io.BytesIO()
        
        if use_jpeg:
            # Convert RGBA to RGB for JPEG (no alpha channel)
            if screenshot.mode == 'RGBA':
                screenshot = screenshot.convert('RGB')
            screenshot.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
            img_format = "JPEG"
        else:
            screenshot.save(buffer, format="PNG", optimize=True)
            img_format = "PNG"
        
        buffer.seek(0)
        img_bytes = buffer.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        
        # Log size info
        size_kb = len(img_bytes) / 1024
        logger.info(f"[VISION] Screenshot: {original_size} → {screenshot.size}, {img_format}, {size_kb:.1f}KB")
        
        return img_base64
    except Exception as e:
        logger.error(f"[VISION] Screen capture failed: {e}")
        return None


def capture_region(x: int, y: int, width: int, height: int) -> Optional[str]:
    """
    Capture a specific region of the screen.
    
    Args:
        x: Left coordinate
        y: Top coordinate
        width: Width of region
        height: Height of region
    
    Returns:
        Base64 encoded PNG of region, or None if failed
    """
    if not PIL_AVAILABLE:
        return None
    
    try:
        import io
        
        # Capture region
        bbox = (x, y, x + width, y + height)
        screenshot = ImageGrab.grab(bbox=bbox)
        
        # Convert to base64
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"[VISION] Region capture failed: {e}")
        return None


def get_screen_size() -> Tuple[int, int]:
    """
    Get the current screen size.
    
    Returns:
        Tuple of (width, height)
    """
    if not PIL_AVAILABLE:
        return (1920, 1080)  # Default fallback
    
    try:
        screenshot = ImageGrab.grab()
        return screenshot.size
    except:
        return (1920, 1080)
