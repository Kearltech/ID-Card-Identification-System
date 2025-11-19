"""
Advanced Face Detection Module for UIVS
Uses MediaPipe for robust, real-time face detection with multiple fallback strategies.
"""

import cv2
import numpy as np
import logging
from typing import Optional, List, Tuple, Dict, Any
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import MediaPipe
try:
    import mediapipe as mp
    HAVE_MEDIAPIPE = True
except ImportError:
    HAVE_MEDIAPIPE = False
    logger.warning("MediaPipe not available")


class AdvancedFaceDetector:
    """
    Detects faces using MediaPipe (primary) with Haar Cascade fallback.
    Returns face bounding boxes and keypoints.
    """

    def __init__(self, use_mediapipe: bool = True):
        """
        Initialize face detector.

        Args:
            use_mediapipe: Use MediaPipe if available, else Haar Cascade
        """
        self.use_mediapipe = use_mediapipe and HAVE_MEDIAPIPE

        if self.use_mediapipe:
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1,  # 0=short-range, 1=full-range
                min_detection_confidence=0.5
            )
            logger.info("MediaPipe face detector initialized")
        else:
            # Haar Cascade fallback
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("Using Haar Cascade fallback")

    def detect_faces(
        self,
        image_cv: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Detect faces in image.

        Args:
            image_cv: Image in BGR format (OpenCV)

        Returns:
            List of detected faces with bounding boxes and confidence:
            [
                {
                    'x': int,
                    'y': int,
                    'w': int,
                    'h': int,
                    'confidence': float (0-1),
                    'keypoints': List[Tuple[x, y]] or None,
                    'method': str ('mediapipe' or 'haar')
                }
            ]
        """
        if self.use_mediapipe:
            return self._detect_with_mediapipe(image_cv)
        else:
            return self._detect_with_haar(image_cv)

    def _detect_with_mediapipe(self, image_cv: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces using MediaPipe."""
        try:
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
            h, w, _ = image_rgb.shape

            # Run detection
            results = self.face_detector.process(image_rgb)

            faces = []
            if results.detections:
                for detection in results.detections:
                    confidence = detection.score[0]
                    bbox = detection.location_data.relative_bounding_box

                    # Convert normalized coordinates to pixel coordinates
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)

                    # Clamp to image bounds
                    x = max(0, x)
                    y = max(0, y)
                    width = min(w - x, width)
                    height = min(h - y, height)

                    # Extract keypoints if available
                    keypoints = None
                    if hasattr(detection.location_data, 'relative_keypoints'):
                        keypoints = [
                            (int(kp.x * w), int(kp.y * h))
                            for kp in detection.location_data.relative_keypoints
                        ]

                    faces.append({
                        'x': x,
                        'y': y,
                        'w': width,
                        'h': height,
                        'confidence': float(confidence),
                        'keypoints': keypoints,
                        'method': 'mediapipe'
                    })

            return sorted(faces, key=lambda f: f['confidence'], reverse=True)

        except Exception as e:
            logger.warning(f"MediaPipe detection failed: {e}. Falling back to Haar.")
            return self._detect_with_haar(image_cv)

    def _detect_with_haar(self, image_cv: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces using Haar Cascade (fallback)."""
        try:
            gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))

            detected = []
            for (x, y, w, h) in faces:
                detected.append({
                    'x': int(x),
                    'y': int(y),
                    'w': int(w),
                    'h': int(h),
                    'confidence': 0.5,  # Haar doesn't give confidence
                    'keypoints': None,
                    'method': 'haar'
                })

            return sorted(detected, key=lambda f: f['w'] * f['h'], reverse=True)

        except Exception as e:
            logger.error(f"Haar Cascade detection failed: {e}")
            return []

    def extract_face_crop(
        self,
        image_cv: np.ndarray,
        face_box: Dict[str, Any],
        margin_ratio: float = 0.2,
        target_size: Tuple[int, int] = (250, 250)
    ) -> Optional[Image.Image]:
        """
        Extract and standardize face crop.

        Args:
            image_cv: Image in BGR
            face_box: Detected face bounding box
            margin_ratio: Margin as % of face size
            target_size: Output size

        Returns:
            Standardized face as PIL Image
        """
        try:
            x, y, w, h = face_box['x'], face_box['y'], face_box['w'], face_box['h']

            # Add margin
            margin = int(margin_ratio * max(w, h))
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(image_cv.shape[1], x + w + margin)
            y2 = min(image_cv.shape[0], y + h + margin)

            # Crop
            face_crop = image_cv[y1:y2, x1:x2]

            if face_crop.size == 0:
                logger.warning("Face crop is empty")
                return None

            # Resize
            face_resized = cv2.resize(face_crop, target_size)

            # Convert to PIL
            face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
            face_pil = Image.fromarray(face_rgb)

            return face_pil

        except Exception as e:
            logger.error(f"Face extraction failed: {e}")
            return None

    def get_best_face(self, image_cv: np.ndarray) -> Optional[Image.Image]:
        """
        Detect and return the largest/best quality face.

        Args:
            image_cv: Image in BGR

        Returns:
            Standardized face as PIL Image or None
        """
        faces = self.detect_faces(image_cv)
        if not faces:
            return None

        best_face = faces[0]  # Already sorted by confidence/size
        return self.extract_face_crop(image_cv, best_face)

    def close(self):
        """Clean up resources."""
        if self.use_mediapipe and hasattr(self, 'face_detector'):
            self.face_detector.close()
