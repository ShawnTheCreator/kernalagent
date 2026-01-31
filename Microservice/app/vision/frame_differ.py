"""
Frame differ for intelligent UI change detection.
Reduces unnecessary Gemini API calls by detecting when UI is stable.
"""
import numpy as np
from PIL import Image
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class FrameDiffer:
    """
    Detects significant UI changes between consecutive frames.
    Uses perceptual hashing for fast comparison and optional embedding similarity.
    """
    
    def __init__(self, stability_threshold: float = 0.95):
        """
        Initialize frame differ.
        
        Args:
            stability_threshold: Similarity threshold above which frames are considered stable (0.0-1.0)
        """
        self.previous_hash: Optional[str] = None
        self.previous_pixels: Optional[np.ndarray] = None
        self.stability_threshold = stability_threshold
        self.frame_count = 0
        self.stable_count = 0
        self.change_count = 0
    
    def is_significant_change(self, current_frame: Image.Image) -> Tuple[bool, float]:
        """
        Check if current frame has significant changes from previous frame.
        
        Args:
            current_frame: Current screenshot as PIL Image
            
        Returns:
            Tuple of (is_significant_change, similarity_score)
            - is_significant_change: True if frame is different enough to warrant processing
            - similarity_score: 0.0 (completely different) to 1.0 (identical)
        """
        self.frame_count += 1
        
        # First frame is always significant
        if self.previous_hash is None:
            self._update_previous(current_frame)
            self.change_count += 1
            logger.info("[FRAME_DIFFER] First frame - processing")
            return True, 0.0
        
        # Fast path: perceptual hash comparison
        current_hash = self._perceptual_hash(current_frame)
        if current_hash == self.previous_hash:
            self.stable_count += 1
            logger.debug(f"[FRAME_DIFFER] Frame identical (hash match) - skipping")
            return False, 1.0
        
        # Detailed path: pixel-level similarity
        current_pixels = self._get_pixels(current_frame)
        similarity = self._calculate_similarity(current_pixels, self.previous_pixels)
        
        # Update previous frame data
        self._update_previous(current_frame, current_hash, current_pixels)
        
        # Determine if change is significant
        is_significant = similarity < self.stability_threshold
        
        if is_significant:
            self.change_count += 1
            logger.info(f"[FRAME_DIFFER] Significant change detected (similarity: {similarity:.3f})")
        else:
            self.stable_count += 1
            logger.debug(f"[FRAME_DIFFER] Frame stable (similarity: {similarity:.3f}) - skipping")
        
        return is_significant, similarity
    
    def _perceptual_hash(self, image: Image.Image) -> str:
        """
        Generate perceptual hash for fast comparison.
        Converts image to 8x8 grayscale and compares to average brightness.
        """
        # Resize to 8x8 and convert to grayscale
        small = image.resize((8, 8), Image.LANCZOS).convert('L')
        pixels = list(small.getdata())
        
        # Calculate average brightness
        avg = sum(pixels) / len(pixels)
        
        # Generate hash: 1 if pixel > average, 0 otherwise
        bits = ''.join('1' if p > avg else '0' for p in pixels)
        
        # Convert to hex hash
        return hashlib.md5(bits.encode()).hexdigest()
    
    def _get_pixels(self, image: Image.Image) -> np.ndarray:
        """
        Get normalized pixel array for similarity calculation.
        Uses 64x64 resize for balance between accuracy and speed.
        """
        # Resize to standard size for comparison
        small = image.resize((64, 64), Image.LANCZOS).convert('RGB')
        pixels = np.array(small, dtype=np.float32) / 255.0  # Normalize to 0-1
        return pixels
    
    def _calculate_similarity(self, pixels_a: np.ndarray, pixels_b: Optional[np.ndarray]) -> float:
        """
        Calculate structural similarity between two pixel arrays.
        Uses normalized mean squared error.
        """
        if pixels_b is None:
            return 0.0
        
        # Calculate MSE (Mean Squared Error)
        mse = np.mean((pixels_a - pixels_b) ** 2)
        
        # Convert MSE to similarity score (0=different, 1=identical)
        # MSE ranges from 0 (identical) to 1 (completely different)
        similarity = 1.0 - mse
        
        return max(0.0, min(1.0, similarity))
    
    def _update_previous(
        self, 
        image: Image.Image, 
        hash_val: Optional[str] = None, 
        pixels: Optional[np.ndarray] = None
    ):
        """Update stored previous frame data."""
        self.previous_hash = hash_val or self._perceptual_hash(image)
        self.previous_pixels = pixels if pixels is not None else self._get_pixels(image)
    
    def reset(self):
        """Reset frame differ state."""
        self.previous_hash = None
        self.previous_pixels = None
        logger.info("[FRAME_DIFFER] State reset")
    
    def get_stats(self) -> dict:
        """Get statistics about frame processing."""
        skip_rate = self.stable_count / self.frame_count if self.frame_count > 0 else 0
        return {
            "total_frames": self.frame_count,
            "stable_frames": self.stable_count,
            "changed_frames": self.change_count,
            "skip_rate": skip_rate,
            "api_calls_saved": self.stable_count
        }
