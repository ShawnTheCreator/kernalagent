"""
OpenCV-based UI element detection and OCR utilities.
Falls back to Gemini if OpenCV/EasyOCR can't find the target.
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
        logger.info("[OPENCV] Initializing EasyOCR reader...")
        _reader = easyocr.Reader(['en'], gpu=False)
        logger.info("[OPENCV] EasyOCR initialized")
    return _reader


def base64_to_cv2(image_b64: str) -> Optional[np.ndarray]:
    """Convert base64 image to OpenCV format."""
    try:
        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.error(f"[OPENCV] Failed to decode base64 image: {e}")
        return None


def detect_buttons(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect button-like elements using enhanced contours and shape analysis."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 100)  # More lenient thresholds

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    buttons = []
    
    logger.info(f"[OPENCV] Found {len(contours)} total contours")

    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)

        # More lenient heuristics for buttons
        if w < 20 or h < 15 or area < 200:  # Reduced minimums
            continue
        if w > image.shape[1] * 0.9 or h > image.shape[0] * 0.4:  # Increased maximums
            continue
        aspect = w / h
        if aspect < 0.2 or aspect > 8:  # Wider aspect ratio range
            continue

        # Shape analysis
        perimeter = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.03 * perimeter, True)  # More lenient approximation
        solidity = float(area) / cv2.contourArea(cv2.convexHull(cnt))
        
        # Determine button type based on shape
        button_type = "button"
        if len(approx) == 4:
            button_type = "rectangular_button"
        elif len(approx) > 8:
            button_type = "rounded_button"
        
        # Color analysis for state detection
        roi = image[y:y+h, x:x+w]
        avg_color = np.mean(roi, axis=(0, 1))
        is_enabled = _is_element_enabled(roi)

        logger.info(f"[OPENCV] Button {len(buttons)+1}: pos=({x+w//2},{y+h//2}) size=({w}x{h}) area={area} type={button_type}")

        buttons.append({
            "x": x + w // 2,
            "y": y + h // 2,
            "width": w,
            "height": h,
            "bounds": (x, y, x + w, y + h),
            "confidence": min(1.0, area / 5000),  # Reduced area threshold
            "type": button_type,
            "shape": {
                "vertices": len(approx),
                "solidity": solidity,
                "aspect_ratio": aspect
            },
            "color": {
                "avg_bgr": avg_color.tolist(),
                "is_enabled": bool(is_enabled),
                "has_focus": bool(_has_element_focus(roi)) if hasattr(roi, 'shape') else False
            }
        })

    logger.info(f"[OPENCV] Detected {len(buttons)} buttons")
    
    # If no buttons found, try to detect any rectangular UI elements
    if len(buttons) == 0:
        logger.info("[OPENCV] No buttons found, trying fallback UI element detection")
        buttons = _detect_ui_elements_fallback(image)
    
    return sorted(buttons, key=lambda b: b["confidence"], reverse=True)


def _detect_ui_elements_fallback(image: np.ndarray) -> List[Dict[str, Any]]:
    """Fallback detection for any rectangular UI elements when no buttons are found."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Use adaptive threshold for better detection
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    elements = []
    
    logger.info(f"[OPENCV] Fallback: Found {len(contours)} contours")
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        
        # Very lenient criteria for fallback
        if w < 15 or h < 10 or area < 100:
            continue
        if w > image.shape[1] * 0.95 or h > image.shape[0] * 0.5:
            continue
            
        elements.append({
            "x": x + w // 2,
            "y": y + h // 2,
            "width": w,
            "height": h,
            "bounds": (x, y, x + w, y + h),
            "confidence": min(1.0, area / 3000),
            "type": "ui_element",
            "shape": {
                "vertices": 4,  # Assume rectangular
                "aspect_ratio": w / h
            },
            "color": {
                "avg_bgr": np.mean(image[y:y+h, x:x+w], axis=(0, 1)).tolist(),
                "is_enabled": True
            }
        })
        
        if len(elements) >= 10:  # Limit to top 10 elements
            break
    
    logger.info(f"[OPENCV] Fallback detected {len(elements)} UI elements")
    return elements


def detect_text_boxes(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect text input boxes using enhanced morphological operations."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    # Horizontal and vertical kernels to detect text boxes
    kernel_horiz = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    kernel_vert = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 25))

    horiz = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_horiz, iterations=2)
    vert = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_vert, iterations=2)

    mask = cv2.addWeighted(horiz, 0.5, vert, 0.5, 0.0)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)

        # Enhanced heuristics for text boxes
        if w < 60 or h < 20 or area < 800:
            continue
        if w > image.shape[1] * 0.9 or h > image.shape[0] * 0.4:
            continue
        aspect = w / h
        if aspect < 1.5 or aspect > 8:
            continue

        # Color analysis for text boxes
        roi = image[y:y+h, x:x+w]
        avg_color = np.mean(roi, axis=(0, 1))
        is_enabled = _is_element_enabled(roi)
        
        # Check if box has focus (brighter borders)
        has_focus = _has_element_focus(roi)

        boxes.append({
            "x": x + w // 2,
            "y": y + h // 2,
            "width": w,
            "height": h,
            "bounds": (x, y, x + w, y + h),
            "confidence": min(1.0, area / 15000),
            "type": "text_box",
            "color": {
                "avg_bgr": avg_color.tolist(),
                "is_enabled": is_enabled,
                "has_focus": has_focus
            }
        })

    return sorted(boxes, key=lambda b: b["confidence"], reverse=True)


def extract_text(image: np.ndarray, region: Optional[Tuple[int, int, int, int]] = None) -> List[str]:
    """Extract text using EasyOCR, optionally within a bounding box."""
    try:
        reader = get_ocr_reader()
        if region:
            x, y, x2, y2 = region
            cropped = image[y:y2, x:x2]
        else:
            cropped = image

        # Convert to RGB for EasyOCR
        rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        results = reader.readtext(rgb, detail=0, paragraph=False)
        return [text.strip() for text in results if text.strip()]
    except Exception as e:
        logger.error(f"[OPENCV] OCR failed: {e}")
        return []


def find_element_by_label(
    image: np.ndarray,
    label: str,
    element_type: str = "any"
) -> Optional[Dict[str, Any]]:
    """Find a UI element by its visible label using OCR + detection."""
    label_lower = label.lower()
    text_results = extract_text(image)

    # Find all elements
    buttons = detect_buttons(image) if element_type in ("any", "button") else []
    boxes = detect_text_boxes(image) if element_type in ("any", "text_box") else []
    all_elements = buttons + boxes

    # Try to match label to nearby text
    for element in all_elements:
        x, y, w, h = element["bounds"]
        expanded_region = (max(0, x - 100), max(0, y - 30), min(image.shape[1], x + w + 100), min(image.shape[0], y + h + 30))
        nearby_text = extract_text(image, expanded_region)

        for text in nearby_text:
            if label_lower in text.lower() or text.lower() in label_lower:
                element["label"] = text
                element["match_score"] = _match_score(label_lower, text.lower())
                return element

    # Fallback: try to match any text on screen
    for text in text_results:
        if label_lower in text.lower() or text.lower() in label_lower:
            # Find nearest element to this text
            return _find_nearest_element_to_text(image, text, all_elements)

    return None


def _match_score(query: str, candidate: str) -> float:
    """Simple fuzzy match score."""
    if query == candidate:
        return 1.0
    if query in candidate or candidate in query:
        return 0.8
    # Simple word overlap
    q_words = set(query.split())
    c_words = set(candidate.split())
    if q_words & c_words:
        return 0.6
    return 0.0


def _find_nearest_element_to_text(image: np.ndarray, text: str, elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the UI element closest to the given text location."""
    try:
        reader = get_ocr_reader()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = reader.readtext(rgb, detail=1, paragraph=False)

        # Find bounding box for our text
        text_bbox = None
        for (bbox, detected_text, _) in results:
            if detected_text.strip() == text:
                text_bbox = bbox
                break

        if not text_bbox:
            return None

        # Get center of text bbox
        tx = int(np.mean([p[0] for p in text_bbox]))
        ty = int(np.mean([p[1] for p in text_bbox]))

        # Find nearest element
        best = None
        best_dist = float('inf')
        for elem in elements:
            ex, ey = elem["x"], elem["y"]
            dist = ((ex - tx) ** 2 + (ey - ty) ** 2) ** 0.5
            if dist < best_dist and dist < 150:  # Max 150px away
                best_dist = dist
                best = elem
                best["label"] = text
                best["match_score"] = 0.7

        return best
    except Exception as e:
        logger.error(f"[OPENCV] Failed to find nearest element: {e}")
        return None


def find_click_target_opencv(
    image_b64: str,
    target_description: str,
    element_type: str = "any"
) -> Optional[Dict[str, Any]]:
    """Try to find a clickable target using OpenCV + OCR."""
    img = base64_to_cv2(image_b64)
    if img is None:
        return None

    # Normalize target
    target = target_description.lower().strip()

    # Try direct label matching
    element = find_element_by_label(img, target, element_type)
    if element:
        logger.info(f"[OPENCV] Found '{target}' via OpenCV at ({element['x']}, {element['y']})")
        return {
            "x": element["x"],
            "y": element["y"],
            "confidence": element.get("confidence", 0.7) * element.get("match_score", 0.7),
            "element": element.get("label", target),
            "method": "opencv"
        }

    # Try keyword matching for common elements
    keywords = {
        "submit": ["submit", "send", "continue", "next", "ok", "confirm"],
        "cancel": ["cancel", "close", "back", "exit"],
        "login": ["login", "sign in", "signin"],
        "search": ["search", "find", "go"],
    }

    for key, synonyms in keywords.items():
        if key in target or any(s in target for s in synonyms):
            element = find_element_by_label(img, key, "button")
            if element:
                logger.info(f"[OPENCV] Found keyword match '{key}' for '{target}' at ({element['x']}, {element['y']})")
                return {
                    "x": element["x"],
                    "y": element["y"],
                    "confidence": element.get("confidence", 0.6),
                    "element": key,
                    "method": "opencv_keyword"
                }

    logger.info(f"[OPENCV] Could not find '{target}' with OpenCV, will fall back to Gemini")
    return None


def _is_element_enabled(roi: np.ndarray) -> bool:
    """Determine if a UI element is enabled based on color analysis."""
    # Convert to HSV for better color analysis
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # Calculate brightness and saturation
    brightness = np.mean(hsv[:, :, 2])  # V channel
    saturation = np.mean(hsv[:, :, 1])  # S channel
    
    # Grayed out elements typically have low saturation
    return saturation > 30 and brightness > 50


def _has_element_focus(roi: np.ndarray) -> bool:
    """Determine if an element has focus based on border brightness."""
    if roi.shape[0] < 10 or roi.shape[1] < 10:
        return False
    
    # Sample border pixels
    border_pixels = [
        roi[0, :],      # Top edge
        roi[-1, :],     # Bottom edge
        roi[:, 0],      # Left edge
        roi[:, -1]      # Right edge
    ]
    
    # Calculate average border brightness
    border_brightness = np.mean([np.mean(border) for border in border_pixels])
    inner_brightness = np.mean(roi[2:-2, 2:-2])  # Inner area
    
    # Focused elements typically have brighter borders
    return border_brightness > inner_brightness + 20


def match_template_advanced(image: np.ndarray, template: np.ndarray,
                           threshold: float = 0.8,
                           scale_invariance: bool = True,
                           rotation_invariance: bool = False) -> List[Dict[str, Any]]:
    """
    Advanced template matching with scale and optional rotation invariance.
    
    Returns:
        List of match results with coordinates, confidence, and transformation info
    """
    matches = []
    
    if scale_invariance:
        # Try multiple scales
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]
        for scale in scales:
            scaled_template = cv2.resize(template, None, fx=scale, fy=scale)
            if scaled_template.shape[0] > image.shape[0] or scaled_template.shape[1] > image.shape[1]:
                continue
                
            result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            
            for pt in zip(*locations[::-1]):
                matches.append({
                    "x": int(pt[0] + scaled_template.shape[1] // 2),
                    "y": int(pt[1] + scaled_template.shape[0] // 2),
                    "confidence": float(result[pt[1], pt[0]]),
                    "scale": scale,
                    "width": scaled_template.shape[1],
                    "height": scaled_template.shape[0]
                })
    else:
        # Standard template matching
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        for pt in zip(*locations[::-1]):
            matches.append({
                "x": int(pt[0] + template.shape[1] // 2),
                "y": int(pt[1] + template.shape[0] // 2),
                "confidence": float(result[pt[1], pt[0]]),
                "scale": 1.0,
                "width": template.shape[1],
                "height": template.shape[0]
            })
    
    # Remove duplicates (non-maximum suppression)
    matches = _non_maximum_suppression(matches, 0.3)
    
    return sorted(matches, key=lambda m: m["confidence"], reverse=True)


def _non_maximum_suppression(matches: List[Dict[str, Any]], iou_threshold: float) -> List[Dict[str, Any]]:
    """Remove overlapping matches using non-maximum suppression."""
    if not matches:
        return []
    
    # Sort by confidence
    matches.sort(key=lambda m: m["confidence"], reverse=True)
    
    keep = []
    while matches:
        # Keep the highest confidence match
        current = matches.pop(0)
        keep.append(current)
        
        # Remove overlapping matches
        remaining = []
        for match in matches:
            iou = _calculate_iou(current, match)
            if iou < iou_threshold:
                remaining.append(match)
        matches = remaining
    
    return keep


def _calculate_iou(match1: Dict[str, Any], match2: Dict[str, Any]) -> float:
    """Calculate Intersection over Union for two matches."""
    x1 = max(match1["x"] - match1["width"] // 2, match2["x"] - match2["width"] // 2)
    y1 = max(match1["y"] - match1["height"] // 2, match2["y"] - match2["height"] // 2)
    x2 = min(match1["x"] + match1["width"] // 2, match2["x"] + match2["width"] // 2)
    y2 = min(match1["y"] + match1["height"] // 2, match2["y"] + match2["height"] // 2)
    
    if x2 <= x1 or y2 <= y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = match1["width"] * match1["height"]
    area2 = match2["width"] * match2["height"]
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def detect_contours_advanced(image: np.ndarray, 
                            min_area: int = 500,
                            max_area_ratio: float = 0.3) -> List[Dict[str, Any]]:
    """
    Advanced contour detection for UI elements with shape classification.
    
    Returns:
        List of detected contours with detailed shape analysis
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Use adaptive thresholding for better lighting invariance
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 11, 2)
    
    # Find contours
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    elements = []
    max_area = image.shape[0] * image.shape[1] * max_area_ratio
    
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        
        # Basic properties
        x, y, w, h = cv2.boundingRect(cnt)
        perimeter = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
        
        # Shape analysis
        aspect_ratio = float(w) / h
        extent = float(area) / (w * h)
        solidity = float(area) / cv2.contourArea(cv2.convexHull(cnt))
        
        # Classify shape
        shape_type = _classify_shape(approx, aspect_ratio, solidity, extent)
        
        # Color analysis
        roi = image[y:y+h, x:x+w]
        avg_color = np.mean(roi, axis=(0, 1))
        is_enabled = _is_element_enabled(roi)
        
        # Check if it's a child element (has parent in hierarchy)
        has_parent = hierarchy[0][i][3] != -1
        
        elements.append({
            "x": x + w // 2,
            "y": y + h // 2,
            "width": w,
            "height": h,
            "bounds": (x, y, x + w, y + h),
            "area": int(area),
            "confidence": min(1.0, area / 5000),
            "type": shape_type,
            "shape": {
                "vertices": len(approx),
                "aspect_ratio": aspect_ratio,
                "extent": extent,
                "solidity": solidity,
                "perimeter": int(perimeter)
            },
            "color": {
                "avg_bgr": avg_color.tolist(),
                "is_enabled": bool(is_enabled),
                "has_focus": bool(_has_element_focus(roi)) if hasattr(roi, 'shape') else False
            },
            "hierarchy": {
                "has_parent": has_parent,
                "parent_idx": int(hierarchy[0][i][3]) if has_parent else None
            }
        })
    
    return sorted(elements, key=lambda e: e["confidence"], reverse=True)


def _classify_shape(approx: np.ndarray, aspect_ratio: float, solidity: float, extent: float) -> str:
    """Classify UI element shape based on geometric properties."""
    vertices = len(approx)
    
    # Basic geometric shapes
    if vertices == 3:
        return "triangle"
    elif vertices == 4:
        if 0.95 < aspect_ratio < 1.05:
            return "square"
        else:
            return "rectangle"
    elif vertices > 8:
        if solidity > 0.9:
            return "circle"
        else:
            return "rounded"
    
    # UI-specific shapes based on aspect ratio and extent
    if aspect_ratio > 3:
        return "horizontal_bar"
    elif aspect_ratio < 0.3:
        return "vertical_bar"
    elif extent > 0.8:
        return "filled_button"
    elif solidity < 0.7:
        return "hollow_element"
    else:
        return "irregular"


def detect_color_changes(image_before: np.ndarray, image_after: np.ndarray,
                         region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
    """
    Detect color changes between two images for state verification.
    
    Returns:
        Dictionary with change metrics and significant regions
    """
    if region:
        x, y, x2, y2 = region
        img1 = image_before[y:y2, x:x2]
        img2 = image_after[y:y2, x:x2]
    else:
        img1 = image_before
        img2 = image_after
    
    # Calculate color differences
    diff = cv2.absdiff(img1, img2)
    avg_diff = np.mean(diff)
    max_diff = np.max(diff)
    
    # Find regions with significant changes
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)[1]
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    significant_regions = []
    for cnt in contours:
        if cv2.contourArea(cnt) > 100:  # Ignore small changes
            x, y, w, h = cv2.boundingRect(cnt)
            significant_regions.append({
                "x": int(x + (region[0] if region else 0)),
                "y": int(y + (region[1] if region else 0)),
                "width": w,
                "height": h,
                "area": int(cv2.contourArea(cnt)),
                "avg_change": float(np.mean(diff[y:y+h, x:x+w]))
            })
    
    return {
        "avg_color_difference": float(avg_diff),
        "max_color_difference": float(max_diff),
        "significant_change": avg_diff > 15,
        "changed_regions": significant_regions,
        "change_percentage": float(np.sum(gray_diff > 30) / gray_diff.size * 100)
    }


def analyze_ui_comprehensive(image_b64: str, 
                           target_description: Optional[str] = None) -> Dict[str, Any]:
    """
    Comprehensive UI analysis using all OpenCV capabilities.
    
    This is the main integration function that combines:
    - Button detection with shape analysis
    - Text box detection with focus detection
    - Advanced contour detection
    - Template matching (if template provided)
    - Color analysis for state detection
    - OCR text extraction
    
    Returns:
        Comprehensive analysis results with all detected elements
    """
    img = base64_to_cv2(image_b64)
    if img is None:
        return {"error": "Failed to load image"}
    
    results = {
        "image_size": {"width": img.shape[1], "height": img.shape[0]},
        "buttons": detect_buttons(img),
        "text_boxes": detect_text_boxes(img),
        "contours": detect_contours_advanced(img),
        "text_elements": extract_text(img),
        "analysis_timestamp": str(np.datetime64('now'))
    }
    
    # If target specified, try to find it using all methods
    if target_description:
        target = target_description.lower().strip()
        
        # Try existing element finding
        element = find_element_by_label(img, target)
        if element:
            results["target_found"] = {
                "method": "label_matching",
                "element": element,
                "confidence": element.get("match_score", 0.7)
            }
        else:
            # Try keyword matching
            keywords = {
                "submit": ["submit", "send", "continue", "next", "ok", "confirm"],
                "cancel": ["cancel", "close", "back", "exit"],
                "login": ["login", "sign in", "signin"],
                "search": ["search", "find", "go"],
            }
            
            found_keyword = None
            for key, synonyms in keywords:
                if key in target or any(s in target for s in synonyms):
                    found_keyword = key
                    break
            
            if found_keyword:
                element = find_element_by_label(img, found_keyword, "button")
                if element:
                    results["target_found"] = {
                        "method": "keyword_matching",
                        "element": element,
                        "confidence": element.get("confidence", 0.6),
                        "keyword": found_keyword
                    }
    
    # Add summary statistics
    results["summary"] = {
        "total_elements": len(results["buttons"]) + len(results["text_boxes"]) + len(results["contours"]),
        "interactive_elements": len(results["buttons"]) + len(results["text_boxes"]),
        "enabled_elements": sum(1 for b in results["buttons"] if b["color"]["is_enabled"]) +
                           sum(1 for t in results["text_boxes"] if t["color"]["is_enabled"]),
        "focused_elements": sum(1 for t in results["text_boxes"] if t["color"]["has_focus"])
    }
    
    logger.info(f"[OPENCV] Comprehensive analysis complete: {results['summary']['total_elements']} elements found")
    return results
