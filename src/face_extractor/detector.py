from typing import List, Tuple, Optional
import os

import cv2
import numpy as np

# Try to import mediapipe; fall back to OpenCV Haar cascades if unavailable.
try:
    import mediapipe as mp  # type: ignore
    _HAVE_MEDIAPIPE = True
except Exception:
    mp = None  # type: ignore
    _HAVE_MEDIAPIPE = False

# Try to load DNN face detector
_DNN_NET = None
_DNN_INPUT_SIZE = (300, 300)
_DNN_CONFIDENCE_THRESHOLD = 0.7


def _clip_box(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> Tuple[int, int, int, int]:
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w - 1))
    y2 = max(0, min(y2, h - 1))
    if x2 <= x1:
        x2 = min(w - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(h - 1, y1 + 1)
    return x1, y1, x2, y2


def _load_dnn_face_detector():
    """Load OpenCV DNN face detector model."""
    global _DNN_NET
    
    if _DNN_NET is not None:
        return _DNN_NET
    
    # Try to load DNN model files
    prototxt_path = None
    model_path = None
    
    # Common paths for DNN models
    possible_paths = [
        ("models/opencv_face_detector.pbtxt", "models/opencv_face_detector_uint8.pb"),
        ("face_detector/deploy.prototxt", "face_detector/res10_300x300_ssd_iter_140000.caffemodel"),
    ]
    
    for prototxt, model in possible_paths:
        if os.path.exists(prototxt) and os.path.exists(model):
            prototxt_path = prototxt
            model_path = model
            break
    
    if prototxt_path and model_path:
        try:
            _DNN_NET = cv2.dnn.readNetFromTensorflow(model_path, prototxt_path) if prototxt_path.endswith('.pbtxt') else cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
            return _DNN_NET
        except Exception:
            pass
    
    return None


def detect_faces(image_bgr: np.ndarray, min_confidence: float = 0.6, use_dnn: bool = False) -> List[Tuple[Tuple[int, int, int, int], float]]:
    """Detect faces using MediaPipe (preferred), DNN, or OpenCV Haar cascade.

    Args:
        image_bgr: Input image in BGR format
        min_confidence: Minimum confidence threshold for detection
        use_dnn: Whether to prefer DNN over Haar cascade (if MediaPipe unavailable)

    Returns a list of tuples: ((x1, y1, x2, y2), score)
    Coordinates are absolute pixels in the input image space.
    """
    h, w = image_bgr.shape[:2]

    # Preferred: MediaPipe
    if _HAVE_MEDIAPIPE:
        mp_fd = mp.solutions.face_detection
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        with mp_fd.FaceDetection(model_selection=1, min_detection_confidence=min_confidence) as fd:
            results = fd.process(image_rgb)
        detections: List[Tuple[Tuple[int, int, int, int], float]] = []
        if results.detections:
            for det in results.detections:
                rel = det.location_data.relative_bounding_box
                x1 = int(rel.xmin * w)
                y1 = int(rel.ymin * h)
                x2 = int((rel.xmin + rel.width) * w)
                y2 = int((rel.ymin + rel.height) * h)
                x1, y1, x2, y2 = _clip_box(x1, y1, x2, y2, w, h)
                score = det.score[0] if det.score else 0.0
                if score >= min_confidence:
                    detections.append(((x1, y1, x2, y2), float(score)))
        return detections

    # Option 2: DNN face detector (if available and requested)
    if use_dnn:
        dnn_net = _load_dnn_face_detector()
        if dnn_net is not None:
            blob = cv2.dnn.blobFromImage(image_bgr, 1.0, _DNN_INPUT_SIZE, [104, 117, 123], swapRB=False, crop=False)
            dnn_net.setInput(blob)
            detections_dnn = dnn_net.forward()
            
            detections: List[Tuple[Tuple[int, int, int, int], float]] = []
            for i in range(detections_dnn.shape[2]):
                confidence = float(detections_dnn[0, 0, i, 2])
                if confidence >= min_confidence:
                    x1 = int(detections_dnn[0, 0, i, 3] * w)
                    y1 = int(detections_dnn[0, 0, i, 4] * h)
                    x2 = int(detections_dnn[0, 0, i, 5] * w)
                    y2 = int(detections_dnn[0, 0, i, 6] * h)
                    x1, y1, x2, y2 = _clip_box(x1, y1, x2, y2, w, h)
                    detections.append(((x1, y1, x2, y2), confidence))
        return detections

    # Fallback: Haar cascade (no confidence scores)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    # Enhance contrast for better detection
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        return []
    
    # Use adaptive parameters based on image size
    min_size = max(30, min(w, h) // 20)
    rects = face_cascade.detectMultiScale(
        gray, 
        scaleFactor=1.1, 
        minNeighbors=5, 
        minSize=(min_size, min_size),
        flags=cv2.CASCADE_SCALE_IMAGE
    )
    dets: List[Tuple[Tuple[int, int, int, int], float]] = []
    for (x, y, bw, bh) in rects:
        x1, y1, x2, y2 = _clip_box(int(x), int(y), int(x + bw), int(y + bh), w, h)
        # Estimate confidence based on face size relative to image
        face_area = bw * bh
        image_area = w * h
        estimated_confidence = min(1.0, face_area / (image_area * 0.1))  # Assume good if >10% of image
        if estimated_confidence >= min_confidence:
            dets.append(((x1, y1, x2, y2), estimated_confidence))
    return dets


def crop_regions(image_bgr: np.ndarray, boxes: List[Tuple[int, int, int, int]], margin_percent: int = 10) -> List[np.ndarray]:
    h, w = image_bgr.shape[:2]
    margin_percent = max(0, margin_percent)
    crops: List[np.ndarray] = []
    for (x1, y1, x2, y2) in boxes:
        bw, bh = x2 - x1, y2 - y1
        mx = int(bw * margin_percent / 100)
        my = int(bh * margin_percent / 100)
        cx1, cy1, cx2, cy2 = _clip_box(x1 - mx, y1 - my, x2 + mx, y2 + my, w, h)
        crop = image_bgr[cy1:cy2, cx1:cx2]
        if crop.size > 0:
            crops.append(crop)
    return crops
