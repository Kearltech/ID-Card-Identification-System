"""
Face Comparison Module for UIVS
Compares face embeddings from uploaded portrait and ID card photo.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict, Any
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Try to import face recognition libraries
try:
    import face_recognition
    HAVE_FACE_RECOGNITION = True
except ImportError:
    HAVE_FACE_RECOGNITION = False
    logger.warning("face_recognition not available")

try:
    from deepface import DeepFace
    HAVE_DEEPFACE = True
except ImportError:
    HAVE_DEEPFACE = False
    logger.warning("DeepFace not available")


class FaceComparator:
    """Compare faces from two images."""
    
    def __init__(self, engine: str = "auto"):
        """
        Initialize face comparator.
        
        Args:
            engine: "face_recognition", "deepface", or "auto"
        """
        self.engine = engine
        self.face_distance_threshold = 0.6  # Threshold for face_recognition
        self.similarity_threshold = 0.55  # Threshold for DeepFace
    
    def compare_faces(
        self,
        portrait_image: Image.Image,
        id_card_portrait: Image.Image,
        return_details: bool = True
    ) -> Dict[str, Any]:
        """
        Compare two face images.
        
        Args:
            portrait_image: User-uploaded portrait (PIL Image)
            id_card_portrait: Face extracted from ID card (PIL Image)
            return_details: Return detailed match information
        
        Returns:
            Dict with:
            - match: bool (True if faces match)
            - similarity_score: float (0-1)
            - distance: float (for face_recognition)
            - engine_used: str
            - confidence: float
            - details: str (description)
        """
        
        result = {
            "match": False,
            "similarity_score": 0.0,
            "distance": None,
            "engine_used": None,
            "confidence": 0.0,
            "details": ""
        }
        
        # Try face_recognition first
        if HAVE_FACE_RECOGNITION and (self.engine == "face_recognition" or self.engine == "auto"):
            try:
                result = self._compare_with_face_recognition(portrait_image, id_card_portrait)
                if result["engine_used"]:
                    return result
            except Exception as e:
                logger.warning(f"face_recognition failed: {e}")
        
        # Try DeepFace
        if HAVE_DEEPFACE and (self.engine == "deepface" or self.engine == "auto"):
            try:
                result = self._compare_with_deepface(portrait_image, id_card_portrait)
                if result["engine_used"]:
                    return result
            except Exception as e:
                logger.warning(f"DeepFace failed: {e}")
        
        # Fallback: Simple pixel-based similarity
        result = self._compare_with_pixel_similarity(portrait_image, id_card_portrait)
        return result
    
    def _compare_with_face_recognition(
        self,
        portrait_image: Image.Image,
        id_card_portrait: Image.Image
    ) -> Dict[str, Any]:
        """Compare using face_recognition library."""
        
        # Convert PIL to numpy arrays
        portrait_array = np.array(portrait_image)
        id_card_array = np.array(id_card_portrait)
        
        try:
            # Encode faces
            portrait_encoding = face_recognition.face_encodings(portrait_array)
            id_card_encoding = face_recognition.face_encodings(id_card_array)
            
            if len(portrait_encoding) == 0 or len(id_card_encoding) == 0:
                return {
                    "match": False,
                    "similarity_score": 0.0,
                    "distance": 1.0,
                    "engine_used": None,
                    "confidence": 0.0,
                    "details": "Could not detect face in one or both images"
                }
            
            # Compare
            distance = face_recognition.face_distance(
                [portrait_encoding[0]],
                id_card_encoding[0]
            )[0]
            
            similarity = 1 - distance  # Convert distance to similarity
            match = similarity >= self.similarity_threshold
            
            return {
                "match": match,
                "similarity_score": float(similarity),
                "distance": float(distance),
                "engine_used": "face_recognition",
                "confidence": float(similarity),
                "details": f"Distance: {distance:.4f}, Similarity: {similarity:.2%}"
            }
        
        except Exception as e:
            logger.error(f"face_recognition comparison failed: {e}")
            return {
                "match": False,
                "similarity_score": 0.0,
                "distance": None,
                "engine_used": None,
                "confidence": 0.0,
                "details": f"Error: {str(e)}"
            }
    
    def _compare_with_deepface(
        self,
        portrait_image: Image.Image,
        id_card_portrait: Image.Image
    ) -> Dict[str, Any]:
        """Compare using DeepFace library."""
        
        # Save to temporary files (DeepFace prefers file paths)
        import tempfile
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f1:
                portrait_image.save(f1.name)
                portrait_path = f1.name
            
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f2:
                id_card_portrait.save(f2.name)
                id_card_path = f2.name
            
            # Compare
            result = DeepFace.verify(
                portrait_path,
                id_card_path,
                model_name="VGG-Face",  # or "Facenet512" for higher accuracy
                enforce_detection=False,
                silent=True
            )
            
            distance = result['distance']
            match = result['verified']
            
            # Normalize distance to similarity (0-1)
            similarity = 1 - (distance / 100)
            
            import os
            os.unlink(portrait_path)
            os.unlink(id_card_path)
            
            return {
                "match": bool(match),
                "similarity_score": float(max(0, min(1, similarity))),
                "distance": float(distance),
                "engine_used": "deepface",
                "confidence": float(max(0, min(1, similarity))),
                "details": f"DeepFace verified: {match}, Distance: {distance:.4f}"
            }
        
        except Exception as e:
            logger.error(f"DeepFace comparison failed: {e}")
            return {
                "match": False,
                "similarity_score": 0.0,
                "distance": None,
                "engine_used": None,
                "confidence": 0.0,
                "details": f"Error: {str(e)}"
            }
    
    def _compare_with_pixel_similarity(
        self,
        portrait_image: Image.Image,
        id_card_portrait: Image.Image
    ) -> Dict[str, Any]:
        """Simple pixel-based similarity comparison (fallback)."""
        
        try:
            # Resize both to same size
            size = (128, 128)
            p1 = portrait_image.resize(size)
            p2 = id_card_portrait.resize(size)
            
            # Convert to grayscale numpy arrays
            p1_gray = np.array(p1.convert('L'))
            p2_gray = np.array(p2.convert('L'))
            
            # Calculate MSE (mean squared error)
            mse = np.mean((p1_gray.astype(float) - p2_gray.astype(float)) ** 2)
            
            # Convert MSE to similarity (0-1)
            max_mse = 255 ** 2
            similarity = 1 - (mse / max_mse)
            
            match = similarity >= self.similarity_threshold
            
            return {
                "match": match,
                "similarity_score": float(similarity),
                "distance": None,
                "engine_used": "pixel_similarity",
                "confidence": float(similarity),
                "details": f"Pixel-based similarity: {similarity:.2%} (fallback method)"
            }
        
        except Exception as e:
            logger.error(f"Pixel similarity comparison failed: {e}")
            return {
                "match": False,
                "similarity_score": 0.0,
                "distance": None,
                "engine_used": None,
                "confidence": 0.0,
                "details": f"Error: {str(e)}"
            }


def extract_and_standardize_face(
    image_bgr: np.ndarray,
    target_size: Tuple[int, int] = (200, 200)
) -> Optional[Image.Image]:
    """
    Extract face from image and standardize it.
    
    Args:
        image_bgr: Image in BGR format (OpenCV)
        target_size: Target face size
    
    Returns:
        Standardized face as PIL Image or None if no face found
    """
    
    import cv2
    
    # Load cascade classifier
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)
    
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) == 0:
        logger.warning("No face detected in image")
        return None
    
    # Get largest face
    (x, y, w, h) = max(faces, key=lambda f: f[2] * f[3])
    
    # Add margin
    margin = int(0.2 * max(w, h))
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(image_bgr.shape[1] - x, w + 2 * margin)
    h = min(image_bgr.shape[0] - y, h + 2 * margin)
    
    # Crop face
    face_crop = image_bgr[y:y+h, x:x+w]
    
    # Resize to target size
    face_resized = cv2.resize(face_crop, target_size)
    
    # Convert to PIL Image
    face_rgb = cv2.cvtColor(face_resized, cv2.COLOR_BGR2RGB)
    face_pil = Image.fromarray(face_rgb)
    
    return face_pil
