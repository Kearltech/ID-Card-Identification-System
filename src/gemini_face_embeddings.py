"""
Gemini Vision Face Embeddings Module for UIVS
Generates face embeddings using Google Gemini Vision API for accurate comparison.
"""

import os
import logging
import base64
import json
from typing import Optional, List, Dict, Any
from PIL import Image
import io
import numpy as np

logger = logging.getLogger(__name__)

# Try to import Gemini
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except ImportError:
    HAVE_GEMINI = False
    logger.warning("google-generativeai not available")


class GeminiFaceEmbeddings:
    """
    Generate face embeddings and compare faces using Gemini Vision API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini embeddings generator.

        Args:
            api_key: Google Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.available = False

        if not HAVE_GEMINI:
            logger.warning("Gemini not available")
            return

        key = api_key or os.getenv('GEMINI_API_KEY')
        if not key:
            logger.warning("GEMINI_API_KEY not set")
            return

        try:
            genai.configure(api_key=key)
            self.client = genai.GenerativeModel('gemini-1.5-flash-latest')
            self.available = True
            logger.info("Gemini Vision API initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")

    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def extract_face_features(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """
        Extract facial features using Gemini Vision.

        Args:
            image: PIL Image of face

        Returns:
            Dict with extracted features or None
        """
        if not self.available:
            return None

        try:
            b64_image = self.image_to_base64(image)

            prompt = """Analyze this face image and provide detailed facial features for embedding:
            1. Face shape (oval, round, square, etc.)
            2. Facial landmarks confidence (eyes, nose, mouth, jawline position)
            3. Skin tone and texture
            4. Distinctive features (scars, marks, freckles)
            5. Face alignment angle (frontal, tilted left/right)
            6. Lighting conditions
            
            Return as JSON with numeric scores (0-1) for each feature."""

            response = self.client.generate_content([
                {'mime_type': 'image/jpeg', 'data': b64_image},
                prompt
            ])

            if not response.text:
                return None

            # Parse response
            try:
                features = json.loads(response.text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    features = json.loads(json_match.group())
                else:
                    features = {'raw': response.text}

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return None

    def compare_face_features(
        self,
        features1: Dict[str, Any],
        features2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two sets of facial features.

        Args:
            features1: Features from first face
            features2: Features from second face

        Returns:
            Dict with similarity score and comparison details
        """
        if not features1 or not features2:
            return {
                'match': False,
                'similarity': 0.0,
                'details': 'Missing features'
            }

        try:
            # Extract numeric features
            values1 = self._extract_numeric_values(features1)
            values2 = self._extract_numeric_values(features2)

            if not values1 or not values2:
                return {
                    'match': False,
                    'similarity': 0.0,
                    'details': 'Could not extract numeric features'
                }

            # Calculate cosine similarity
            similarity = self._cosine_similarity(values1, values2)

            return {
                'match': similarity >= 0.75,
                'similarity': float(similarity),
                'details': f'Feature similarity: {similarity:.2%}'
            }

        except Exception as e:
            logger.error(f"Feature comparison failed: {e}")
            return {
                'match': False,
                'similarity': 0.0,
                'details': f'Error: {str(e)}'
            }

    def _extract_numeric_values(self, features: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract numeric values from features dict."""
        try:
            values = []
            for key, val in features.items():
                if isinstance(val, (int, float)):
                    values.append(float(val))
                elif isinstance(val, dict):
                    values.extend(self._extract_numeric_values(val) or [])

            return np.array(values) if values else None

        except Exception:
            return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Ensure same length
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]

            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0

    def compare_images_directly(
        self,
        image1: Image.Image,
        image2: Image.Image
    ) -> Dict[str, Any]:
        """
        Compare two face images directly using Gemini Vision.

        Args:
            image1: First face image
            image2: Second face image

        Returns:
            Comparison result with similarity score
        """
        if not self.available:
            return {
                'match': False,
                'similarity': 0.0,
                'method': 'gemini',
                'details': 'Gemini not available'
            }

        try:
            b64_img1 = self.image_to_base64(image1)
            b64_img2 = self.image_to_base64(image2)

            prompt = """Compare these two face images on a scale of 0-100:
            - Are these the same person?
            - Provide a similarity percentage (0=different people, 100=same person)
            - List key matching/mismatching features
            
            Return as JSON: {"similarity_percent": <number>, "same_person": <boolean>, "reasoning": "<text>"}"""

            response = self.client.generate_content([
                {'mime_type': 'image/jpeg', 'data': b64_img1},
                {'mime_type': 'image/jpeg', 'data': b64_img2},
                prompt
            ])

            if not response.text:
                return {
                    'match': False,
                    'similarity': 0.0,
                    'method': 'gemini',
                    'details': 'No response from Gemini'
                }

            # Parse response
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = {}

            similarity = float(result.get('similarity_percent', 0)) / 100.0
            same_person = result.get('same_person', False)

            return {
                'match': bool(same_person) and similarity >= 0.75,
                'similarity': max(0.0, min(1.0, similarity)),
                'method': 'gemini',
                'engine_used': 'gemini-vision',
                'confidence': similarity,
                'details': result.get('reasoning', 'Gemini comparison complete'),
                'raw_response': result
            }

        except Exception as e:
            logger.error(f"Direct image comparison failed: {e}")
            return {
                'match': False,
                'similarity': 0.0,
                'method': 'gemini',
                'details': f'Error: {str(e)}'
            }
