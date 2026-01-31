"""
OCR Helper utilities for extracting text from screenshots.
Provides both full-screen and region-based text extraction.
"""

import cv2
import numpy as np
import easyocr
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Lazy-load EasyOCR to avoid startup delay
_reader = None

def get_ocr_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        logger.info("[OCR] Initializing EasyOCR reader...")
        _reader = easyocr.Reader(['en'], gpu=False)
        logger.info("[OCR] EasyOCR initialized")
    return _reader


def base64_to_cv2(image_b64: str) -> Optional[np.ndarray]:
    """Convert base64 image to OpenCV format."""
    try:
        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"[OCR] Failed to decode base64 image: {e}")
        return None


def extract_text_from_image(
    image_b64: str,
    region: Optional[Tuple[int, int, int, int]] = None,
    detail_level: str = "low"  # "low" = text only, "high" = text + bounding boxes
) -> List[Dict[str, Any]]:
    """
    Extract text from screenshot using EasyOCR.
    
    Args:
        image_b64: Base64 encoded screenshot
        region: Optional (x, y, x2, y2) to crop before OCR
        detail_level: "low" returns just text, "high" returns text + bbox + confidence
    
    Returns:
        List of dictionaries with text, bbox, confidence (if detail_level="high")
    """
    try:
        img = base64_to_cv2(image_b64)
        if img is None:
            return []

        if region:
            x, y, x2, y2 = region
            img = img[y:y2, x:x2]

        # Convert to RGB for EasyOCR
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        reader = get_ocr_reader()

        if detail_level == "high":
            results = reader.readtext(rgb, detail=1, paragraph=False)
            extracted = []
            for (bbox, text, confidence) in results:
                if text.strip():
                    extracted.append({
                        "text": text.strip(),
                        "bbox": bbox,
                        "confidence": confidence,
                        "center": (
                            int(np.mean([p[0] for p in bbox])),
                            int(np.mean([p[1] for p in bbox]))
                        )
                    })
            return extracted
        else:
            results = reader.readtext(rgb, detail=0, paragraph=False)
            return [{"text": text.strip()} for text in results if text.strip()]

    except Exception as e:
        logger.error(f"[OCR] Extraction failed: {e}")
        return []


def find_text_elements(
    image_b64: str,
    search_terms: List[str],
    fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Find specific text elements on screen.
    
    Args:
        image_b64: Base64 encoded screenshot
        search_terms: List of strings to search for
        fuzzy: Enable fuzzy matching (contains/substring)
    
    Returns:
        List of matches with text, bbox, center, and match_score
    """
    results = extract_text_from_image(image_b64, detail_level="high")
    matches = []

    for item in results:
        text = item["text"].lower()
        for term in search_terms:
            term_lower = term.lower()
            score = 0.0

            if fuzzy:
                if term_lower in text:
                    score = 0.9
                elif text in term_lower:
                    score = 0.8
                else:
                    # Simple word overlap
                    t_words = set(term_lower.split())
                    txt_words = set(text.split())
                    if t_words & txt_words:
                        score = 0.6
            else:
                if term_lower == text:
                    score = 1.0

            if score > 0:
                match = item.copy()
                match["search_term"] = term
                match["match_score"] = score
                matches.append(match)
                break  # Only match each text item once

    return sorted(matches, key=lambda m: m["match_score"], reverse=True)


def get_form_fields(image_b64: str) -> List[Dict[str, Any]]:
    """
    Detect form fields (text boxes, buttons) using OCR + heuristics.
    
    Args:
        image_b64: Base64 encoded screenshot
    
    Returns:
        List of form fields with type, label, bbox, center
    """
    from app.vision.opencv_detector import detect_text_boxes, detect_buttons
    
    img = base64_to_cv2(image_b64)
    if img is None:
        return []

    # Get OCR text with positions
    text_elements = extract_text_from_image(image_b64, detail_level="high")
    
    # Get UI elements from OpenCV
    text_boxes = detect_text_boxes(img)
    buttons = detect_buttons(img)

    fields = []

    # Process text boxes (input fields)
    for box in text_boxes:
        # Find nearby label text
        x, y, w, h = box["bounds"]
        label = _find_nearby_label(text_elements, (x, y, w, h))
        
        fields.append({
            "type": "text_input",
            "label": label or "Text Field",
            "bbox": box["bounds"],
            "center": (box["x"], box["y"]),
            "confidence": box.get("confidence", 0.7)
        })

    # Process buttons
    for btn in buttons:
        # Find nearby label text
        x, y, w, h = btn["bounds"]
        label = _find_nearby_label(text_elements, (x, y, w, h))
        
        fields.append({
            "type": "button",
            "label": label or "Button",
            "bbox": btn["bounds"],
            "center": (btn["x"], btn["y"]),
            "confidence": btn.get("confidence", 0.7)
        })

    return fields


def _find_nearby_label(text_elements: List[Dict[str, Any]], element_bbox: Tuple[int, int, int, int]) -> Optional[str]:
    """Find the most likely label text near a UI element."""
    ex, ey, ew, eh = element_bbox
    element_center = (ex + ew // 2, ey + eh // 2)

    best_label = None
    best_score = 0.0

    for text_item in text_elements:
        text = text_item["text"]
        center = text_item["center"]
        
        # Calculate distance
        dist = ((center[0] - element_center[0]) ** 2 + (center[1] - element_center[1]) ** 2) ** 0.5
        
        # Score based on distance and text characteristics
        if dist < 100:  # Within 100px
            score = 1.0 - (dist / 100)
            
            # Boost score for common label patterns
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in ["name", "email", "password", "submit", "cancel", "login", "search"]):
                score += 0.2
            
            if score > best_score:
                best_score = score
                best_label = text

    return best_label if best_score > 0.3 else None


def read_screen_text(image_b64: str) -> str:
    """
    Extract all readable text from the screen.
    
    Args:
        image_b64: Base64 encoded screenshot
    
    Returns:
        Concatenated text from all detected elements
    """
    results = extract_text_from_image(image_b64, detail_level="low")
    return " ".join([item["text"] for item in results])
