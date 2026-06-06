"""Person detection service.

Uses a layered fallback strategy:
1. OpenCV HOG descriptor (built-in pedestrian detector, no model download)
2. YOLOv8 (if ultralytics is installed)
3. Heuristic fallback: returns 0 with a clear log message
"""

import os
import logging

logger = logging.getLogger(__name__)

# ---- HOG detector (built into OpenCV) ----
_hog = None


def _get_hog():
    """Initialize OpenCV HOG descriptor for pedestrian detection."""
    global _hog
    if _hog is None:
        try:
            import cv2
            _hog = cv2.HOGDescriptor()
            _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            logger.info("HOG pedestrian detector initialized (OpenCV built-in)")
        except ImportError:
            logger.warning("OpenCV not available — person detection will return 0")
        except Exception as e:
            logger.warning(f"Failed to initialize HOG detector: {e}")
    return _hog


def _detect_hog(image_path):
    """Detect persons using OpenCV HOG descriptor. Returns person count."""
    hog = _get_hog()
    if hog is None:
        return -1  # Signal that this method failed

    import cv2
    img = cv2.imread(image_path)
    if img is None:
        return -1

    # Resize large images for performance
    h, w = img.shape[:2]
    max_dim = 1024
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    # Detect pedestrians
    boxes, weights = hog.detectMultiScale(
        img,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05,
        hitThreshold=0.0
    )

    count = len(boxes)
    logger.info(f"HOG detected {count} person(s) in {image_path}")
    return count


# ---- YOLO detector (optional, if ultralytics is installed) ----
_yolo = None


def _get_yolo():
    """Initialize YOLO model (lazy, optional)."""
    global _yolo
    if _yolo is None:
        try:
            from ultralytics import YOLO
            _yolo = YOLO('yolov8n.pt')
            logger.info("YOLOv8 nano model loaded")
        except ImportError:
            logger.info("ultralytics not installed — using HOG detector only")
        except Exception as e:
            logger.warning(f"Failed to load YOLO model: {e}")
    return _yolo


def _detect_yolo(image_path):
    """Detect persons using YOLOv8. Returns person count or -1 on failure."""
    model = _get_yolo()
    if model is None:
        return -1

    try:
        results = model(image_path, verbose=False)
        person_count = 0
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id == 0:  # COCO class 0 = person
                    person_count += 1
        logger.info(f"YOLO detected {person_count} person(s) in {image_path}")
        return person_count
    except Exception as e:
        logger.warning(f"YOLO detection failed: {e}")
        return -1


# ---- Main API ----

def detect_persons(image_path):
    """
    Detect persons in an image.
    Returns the count of detected persons.
    Falls back gracefully if no detection method is available.
    """
    if not os.path.exists(image_path):
        logger.warning(f"Image not found: {image_path}")
        return 0

    # Try YOLO first (more accurate), then HOG, then return 0
    # Actually, prefer HOG first since it doesn't need model download
    count = _detect_hog(image_path)
    if count >= 0:
        return count

    # Fall back to YOLO if HOG failed and ultralytics is installed
    count = _detect_yolo(image_path)
    if count >= 0:
        return count

    # Neither method available
    logger.warning("No person detection method available — returning 0")
    return 0
