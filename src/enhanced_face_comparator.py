"""
Enhanced Face Comparator for UIVS
Integrates MediaPipe detection + Gemini embeddings with fallback to existing engines.
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple, Dict, Any
from PIL import Image

logger = logging.getLogger(__name__)

# Import detection and embedding modules
try:
    from advanced_face_detector import AdvancedFaceDetector
    HAVE_ADVANCED_DETECTOR = True
except ImportError:
    HAVE_ADVANCED_DETECTOR = False
    logger.warning("AdvancedFaceDetector not available")

try:
    from gemini_face_embeddings import GeminiFaceEmbeddings
    HAVE_GEMINI_EMBEDDINGS = True
except ImportError:
    HAVE_GEMINI_EMBEDDINGS = False
    logger.warning("GeminiFaceEmbeddings not available")

# Import legacy comparator for fallback
try:
    from face_comparator import FaceComparator
    HAVE_LEGACY_COMPARATOR = True
except ImportError:
    HAVE_LEGACY_COMPARATOR = False


class EnhancedFaceComparator:
    """
    Enhanced face comparison using:
    1. MediaPipe for robust face detection
    2. Gemini Vision for semantic feature comparison
    3. Fallback to dlib/DeepFace/pixel-based methods
    """

    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize enhanced comparator.

        Args:
            gemini_api_key: Google Gemini API key
        """
        # Initialize detectors and comparators
        self.detector = None
        self.gemini_embeddings = None
        self.legacy_comparator = None

        if HAVE_ADVANCED_DETECTOR:
            self.detector = AdvancedFaceDetector(use_mediapipe=True)
            logger.info("MediaPipe face detector initialized")

        if HAVE_GEMINI_EMBEDDINGS:
            self.gemini_embeddings = GeminiFaceEmbeddings(api_key=gemini_api_key)
            logger.info("Gemini embeddings initialized")

        if HAVE_LEGACY_COMPARATOR:
            self.legacy_comparator = FaceComparator(engine="auto")
            logger.info("Legacy comparator initialized as fallback")

        # Thresholds
        self.gemini_threshold = 0.75
        self.legacy_threshold = 0.55

    def compare_faces(
        self,
        portrait_image: Image.Image,
        id_card_portrait: Image.Image
    ) -> Dict[str, Any]:
        """
        Compare two face images using multi-tier approach.

        Args:
            portrait_image: User-uploaded portrait (PIL Image)
            id_card_portrait: Face extracted from ID card (PIL Image)

        Returns:
            Dict with match decision and confidence
        """

        result = {
            "match": False,
            "similarity_score": 0.0,
            "engine_used": None,
            "confidence": 0.0,
            "details": "",
            "method_chain": []
        }

        # Tier 1: Gemini Vision direct comparison
        if self.gemini_embeddings and self.gemini_embeddings.available:
            try:
                logger.info("Attempting Gemini Vision comparison...")
                gemini_result = self.gemini_embeddings.compare_images_directly(
                    portrait_image,
                    id_card_portrait
                )

                result['method_chain'].append('gemini_vision')

                if gemini_result.get('match'):
                    result.update({
                        'match': True,
                        'similarity_score': gemini_result.get('similarity', 0.0),
                        'engine_used': 'gemini_vision',
                        'confidence': gemini_result.get('confidence', 0.0),
                        'details': gemini_result.get('details', 'Gemini match'),
                        'raw_response': gemini_result.get('raw_response')
                    })
                    logger.info(f"✓ Gemini match detected: {result['similarity_score']:.2%}")
                    return result

            except Exception as e:
                logger.warning(f"Gemini comparison failed: {e}")

        # Tier 2: Gemini feature extraction + comparison
        if self.gemini_embeddings and self.gemini_embeddings.available:
            try:
                logger.info("Attempting Gemini feature extraction...")
                features1 = self.gemini_embeddings.extract_face_features(portrait_image)
                features2 = self.gemini_embeddings.extract_face_features(id_card_portrait)

                if features1 and features2:
                    feature_result = self.gemini_embeddings.compare_face_features(
                        features1,
                        features2
                    )

                    result['method_chain'].append('gemini_features')

                    if feature_result.get('match'):
                        result.update({
                            'match': True,
                            'similarity_score': feature_result.get('similarity', 0.0),
                            'engine_used': 'gemini_features',
                            'confidence': feature_result.get('similarity', 0.0),
                            'details': feature_result.get('details', '')
                        })
                        logger.info(f"✓ Gemini features match: {result['similarity_score']:.2%}")
                        return result

            except Exception as e:
                logger.warning(f"Gemini feature extraction failed: {e}")

        # Tier 3: Legacy comparator (face_recognition, DeepFace, pixel-based)
        if self.legacy_comparator:
            try:
                logger.info("Attempting legacy comparator...")
                legacy_result = self.legacy_comparator.compare_faces(
                    portrait_image,
                    id_card_portrait
                )

                result['method_chain'].append(legacy_result.get('engine_used', 'unknown'))

                if legacy_result.get('match'):
                    result.update({
                        'match': True,
                        'similarity_score': legacy_result.get('similarity_score', 0.0),
                        'engine_used': legacy_result.get('engine_used'),
                        'confidence': legacy_result.get('confidence', 0.0),
                        'details': legacy_result.get('details', '')
                    })
                    logger.info(f"✓ Legacy match detected: {result['similarity_score']:.2%}")
                    return result

            except Exception as e:
                logger.warning(f"Legacy comparison failed: {e}")

        # No match across all tiers
        result['details'] = 'No match detected across all comparison methods'
        logger.warning("✗ No face match detected")
        return result

    def detect_and_compare(
        self,
        portrait_cv: np.ndarray,
        id_card_cv: np.ndarray
    ) -> Dict[str, Any]:
        """
        Detect faces and compare them end-to-end.

        Args:
            portrait_cv: Portrait in BGR (OpenCV format)
            id_card_cv: ID card in BGR (OpenCV format)

        Returns:
            Comparison result with detection and matching info
        """

        result = {
            'portrait_face_detected': False,
            'card_face_detected': False,
            'match': False,
            'comparison_result': None,
            'details': ''
        }

        # Detect faces
        if self.detector:
            try:
                portrait_face = self.detector.get_best_face(portrait_cv)
                id_card_face = self.detector.get_best_face(id_card_cv)

                if portrait_face:
                    result['portrait_face_detected'] = True
                if id_card_face:
                    result['card_face_detected'] = True

                if portrait_face and id_card_face:
                    comparison = self.compare_faces(portrait_face, id_card_face)
                    result['comparison_result'] = comparison
                    result['match'] = comparison.get('match', False)
                    result['details'] = comparison.get('details', '')

            except Exception as e:
                logger.error(f"End-to-end comparison failed: {e}")
                result['details'] = f'Error: {str(e)}'

        return result

    def close(self):
        """Clean up resources."""
        if self.detector:
            self.detector.close()
