"""Person detection service.

Detection methods, tried in order of accuracy:
1. YOLOv8 (ultralytics) — most accurate, requires `pip install ultralytics` (~2GB PyTorch)
2. OpenCV DNN with lightweight model — good balance
3. OpenCV HOG with improved preprocessing — built-in, no download
"""

import os
import logging

logger = logging.getLogger(__name__)

# ============================================================
# Method 1: YOLOv8 (best accuracy, optional install)
# ============================================================
_yolo = None


def _get_yolo():
    global _yolo
    if _yolo is None:
        try:
            from ultralytics import YOLO
            _yolo = YOLO('yolov8n.pt')
            logger.info("YOLOv8 nano model loaded — high accuracy person detection")
        except ImportError:
            logger.info("ultralytics not installed; will use fallback detectors")
        except Exception as e:
            logger.warning(f"YOLO load failed: {e}")
    return _yolo


def _detect_yolo(image_path):
    model = _get_yolo()
    if model is None:
        return -1
    try:
        results = model(image_path, verbose=False, conf=0.25)
        person_count = 0
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                if int(box.cls[0]) == 0:  # COCO class 0 = person
                    person_count += 1
        logger.info(f"YOLO detected {person_count} person(s)")
        return person_count
    except Exception as e:
        logger.warning(f"YOLO detection error: {e}")
        return -1


# ============================================================
# Method 2: Improved HOG with preprocessing
# ============================================================
_hog = None


def _get_hog():
    global _hog
    if _hog is None:
        try:
            import cv2
            _hog = cv2.HOGDescriptor()
            _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            logger.info("HOG detector ready")
        except ImportError:
            logger.warning("OpenCV not available")
        except Exception as e:
            logger.warning(f"HOG init failed: {e}")
    return _hog


def _preprocess_image(img):
    """Enhance image for better detection."""
    import cv2
    import numpy as np

    # Convert to grayscale if needed
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # CLAHE — contrast limited adaptive histogram equalization
    # Greatly improves detection in shadows / uneven lighting
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Convert back to BGR for HOG (which expects 3-channel)
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

    return enhanced_bgr


def _detect_hog(image_path):
    import cv2
    import numpy as np

    hog = _get_hog()
    if hog is None:
        return -1

    img = cv2.imread(image_path)
    if img is None:
        return -1

    # Resize large images to reasonable dimensions
    h, w = img.shape[:2]
    max_dim = 1280
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    # Apply CLAHE preprocessing — significantly improves detection in uneven lighting
    processed = _preprocess_image(img)

    all_detections = []  # (x, y, w, h, weight)

    # Multi-scale detection with different parameters for thorough coverage
    configs = [
        # (image, winStride, padding, scale, hitThreshold)
        (processed, (4, 4), (16, 16), 1.02, -0.1),
        (processed, (8, 8), (8, 8),   1.05,  0.0),
        (img,       (8, 8), (8, 8),   1.05,  0.1),
    ]

    for src, stride, padding, scl, thresh in configs:
        try:
            boxes, weights = hog.detectMultiScale(
                src,
                winStride=stride,
                padding=padding,
                scale=scl,
                hitThreshold=thresh
            )
            if len(boxes) > 0:
                for box, wgt in zip(boxes, weights):
                    all_detections.append((*box.tolist(), float(wgt)))
        except Exception as e:
            logger.warning(f"HOG pass failed: {e}")

    if not all_detections:
        logger.info("HOG detected 0 persons")
        return 0

    # Simple deduplication: merge highly overlapping boxes
    dets = sorted(all_detections, key=lambda d: d[4], reverse=True)
    kept = []

    for d in dets:
        x, y, w, h, weight = d
        is_duplicate = False
        for k in kept:
            kx, ky, kw, kh, _ = k
            # IoU-based dedup
            ix = max(x, kx)
            iy = max(y, ky)
            iw = min(x + w, kx + kw) - ix
            ih = min(y + h, ky + kh) - iy
            if iw > 0 and ih > 0:
                intersection = iw * ih
                union = w * h + kw * kh - intersection
                iou = intersection / union if union > 0 else 0
                if iou > 0.5:
                    is_duplicate = True
                    # Keep the one with higher weight
                    if weight > k[4]:
                        kept.remove(k)
                        is_duplicate = False
                    break
        if not is_duplicate:
            kept.append(d)

    count = len(kept)
    logger.info(f"HOG detected {count} person(s) (raw: {len(all_detections)}, after dedup: {count})")
    return count


# ============================================================
# Main API
# ============================================================

def detect_persons(image_path):
    """
    Detect persons in an image.
    Tries YOLO first (most accurate), then improved HOG.
    Returns person count.
    """
    if not os.path.exists(image_path):
        logger.warning(f"Image not found: {image_path}")
        return 0

    # 1) Try YOLO first — most accurate
    count = _detect_yolo(image_path)
    if count >= 0:
        return count

    # 2) Fall back to improved HOG detector
    count = _detect_hog(image_path)
    if count >= 0:
        return count

    # 3) Nothing works
    logger.warning("No detection method available — returning 0")
    return 0


def get_detection_method():
    """Return the name of the active detection method."""
    if _get_yolo() is not None:
        return 'YOLOv8 (高精度)'
    if _get_hog() is not None:
        return 'HOG + CLAHE (基础精度)'
    return '不可用'
