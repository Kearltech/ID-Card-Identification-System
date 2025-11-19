"""
OpenCV face detection and portrait cropping utilities.

Functions:
- detect_and_crop(pil_image) -> (portrait_pil_image or None, bbox or None)

Uses Haar cascades (included in OpenCV) and will select the largest detected face
when multiple faces are found.
"""
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image
import io


def detect_and_crop(pil_image: Image.Image) -> Tuple[Optional[Image.Image], Optional[Tuple[int,int,int,int]]]:
    """Detect faces in a PIL image and return the largest face crop as PIL Image.

    Returns (portrait_image, bbox) where bbox is (x, y, w, h). If no face found,
    returns (None, None).
    """
    # Convert PIL to OpenCV BGR
    img = np.array(pil_image.convert('RGB'))
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Use Haar cascade from OpenCV data
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    # adjust scaleFactor/minNeighbors for robustness
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30,30))

    if faces is None or len(faces) == 0:
        return None, None

    # Select largest face by area
    largest = max(faces, key=lambda rect: rect[2]*rect[3])
    x, y, w, h = largest

    # Add small margin
    margin = int(0.15 * max(w,h))
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(img_bgr.shape[1], x + w + margin)
    y2 = min(img_bgr.shape[0], y + h + margin)

    crop = img_bgr[y1:y2, x1:x2]
    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    pil_crop = Image.fromarray(crop_rgb)
    return pil_crop, (x1, y1, x2-x1, y2-y1)
