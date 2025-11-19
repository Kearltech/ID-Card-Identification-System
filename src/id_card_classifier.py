"""
ID Card Type Classifier for UIVS
Classifies ID card type using keyword detection and AI classification.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, Dict, List
from PIL import Image

logger = logging.getLogger(__name__)

# Try to import Gemini or other ML libraries
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except ImportError:
    HAVE_GEMINI = False
    logger.warning("Gemini API not available")

try:
    import easyocr
    HAVE_EASYOCR = True
except ImportError:
    HAVE_EASYOCR = False
    logger.warning("EasyOCR not available")


# Card type patterns and keywords
CARD_TYPE_KEYWORDS = {
    "Ghana Card": [
        "ECOWAS IDENTITY CARD",
        "NATIONAL IDENTIFICATION CARD",
        "GHANA CARD",
        "ECOWAS",
        "GHANA"
    ],
    "Passport": [
        "PASSPORT",
        "REPUBLIC OF GHANA",
        "PASSPORT NO",
        "PASSPORT NUMBER"
    ],
    "Voter ID": [
        "VOTER IDENTITY",
        "ELECTORAL COMMISSION",
        "VOTER ID",
        "VOTING"
    ],
    "Driver's License": [
        "DRIVER LICENSE",
        "DRIVER LICENCE",
        "DRIVING LICENCE",
        "LICENSE CLASS",
        "LICENCE #"
    ]
}


class IDCardClassifier:
    """Classify ID card type."""
    
    def __init__(self, engine: str = "keyword", gemini_api_key: Optional[str] = None):
        """
        Initialize classifier.
        
        Args:
            engine: "keyword", "ocr", "gemini", or "hybrid"
            gemini_api_key: API key for Gemini (if using Gemini)
        """
        self.engine = engine
        self.ocr_reader = None
        
        if engine in ["ocr", "hybrid"] and HAVE_EASYOCR:
            self.ocr_reader = easyocr.Reader(['en'])
        
        if engine == "gemini" and gemini_api_key:
            genai.configure(api_key=gemini_api_key)
    
    def classify(
        self,
        image: Image.Image,
        user_selected_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Classify ID card type.
        
        Args:
            image: ID card image (PIL Image)
            user_selected_type: Type user selected (for comparison)
        
        Returns:
            Dict with:
            - card_type: Detected card type
            - confidence: Confidence score (0-1)
            - matches_user_selection: bool
            - method: str (how it was classified)
            - details: str (explanation)
            - all_confidences: dict (all card types and their scores)
        """
        
        result = {
            "card_type": "Unknown",
            "confidence": 0.0,
            "matches_user_selection": False,
            "method": None,
            "details": "",
            "all_confidences": {}
        }
        
        # Try different methods
        if self.engine == "keyword" or self.engine == "hybrid":
            result = self._classify_by_keywords(image)
            if result["confidence"] > 0.5:
                result["method"] = "keyword_detection"
                if user_selected_type:
                    result["matches_user_selection"] = (result["card_type"] == user_selected_type)
                return result
        
        if self.engine in ["ocr", "hybrid"] and self.ocr_reader:
            ocr_result = self._classify_by_ocr(image)
            if ocr_result["confidence"] > result["confidence"]:
                result = ocr_result
                result["method"] = "ocr_text_detection"
                if user_selected_type:
                    result["matches_user_selection"] = (result["card_type"] == user_selected_type)
                return result
        
        if self.engine == "gemini" and HAVE_GEMINI:
            gemini_result = self._classify_by_gemini(image)
            if gemini_result["confidence"] > result["confidence"]:
                result = gemini_result
                result["method"] = "gemini_vision"
                if user_selected_type:
                    result["matches_user_selection"] = (result["card_type"] == user_selected_type)
                return result
        
        # Default result
        if user_selected_type:
            result["card_type"] = user_selected_type
            result["confidence"] = 0.5
            result["method"] = "user_selection"
            result["details"] = "Using user-selected card type (no AI classification)"
            result["matches_user_selection"] = True
        
        return result
    
    def _classify_by_keywords(self, image: Image.Image) -> Dict[str, any]:
        """Classify by detecting keywords in image."""
        
        scores = {}
        
        try:
            # Convert to grayscale and use OCR on small regions
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            # Try to detect text regions
            if HAVE_EASYOCR and self.ocr_reader:
                results = self.ocr_reader.readtext(img_cv)
                detected_text = " ".join([text[1] for text in results])
            else:
                detected_text = ""
            
            detected_text_upper = detected_text.upper()
            
            # Score each card type
            for card_type, keywords in CARD_TYPE_KEYWORDS.items():
                matches = sum(1 for kw in keywords if kw.upper() in detected_text_upper)
                confidence = min(1.0, matches / len(keywords)) if keywords else 0.0
                scores[card_type] = confidence
            
            # Find best match
            if scores:
                best_type = max(scores, key=scores.get)
                best_confidence = scores[best_type]
                
                return {
                    "card_type": best_type,
                    "confidence": best_confidence,
                    "matches_user_selection": False,
                    "method": "keyword_detection",
                    "details": f"Keywords detected: {best_confidence:.0%}",
                    "all_confidences": scores
                }
        
        except Exception as e:
            logger.error(f"Keyword classification failed: {e}")
        
        return {
            "card_type": "Unknown",
            "confidence": 0.0,
            "matches_user_selection": False,
            "method": None,
            "details": "Could not classify",
            "all_confidences": {}
        }
    
    def _classify_by_ocr(self, image: Image.Image) -> Dict[str, any]:
        """Classify by OCR text extraction."""
        
        if not HAVE_EASYOCR or not self.ocr_reader:
            return {
                "card_type": "Unknown",
                "confidence": 0.0,
                "matches_user_selection": False,
                "method": None,
                "details": "OCR not available",
                "all_confidences": {}
            }
        
        try:
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            results = self.ocr_reader.readtext(img_cv)
            
            detected_text = " ".join([text[1] for text in results])
            detected_text_upper = detected_text.upper()
            
            scores = {}
            for card_type, keywords in CARD_TYPE_KEYWORDS.items():
                matches = sum(1 for kw in keywords if kw.upper() in detected_text_upper)
                confidence = min(1.0, matches / len(keywords)) if keywords else 0.0
                scores[card_type] = confidence
            
            if scores:
                best_type = max(scores, key=scores.get)
                best_confidence = scores[best_type]
                
                return {
                    "card_type": best_type,
                    "confidence": best_confidence,
                    "matches_user_selection": False,
                    "method": "ocr",
                    "details": f"OCR confidence: {best_confidence:.0%}",
                    "all_confidences": scores
                }
        
        except Exception as e:
            logger.error(f"OCR classification failed: {e}")
        
        return {
            "card_type": "Unknown",
            "confidence": 0.0,
            "matches_user_selection": False,
            "method": None,
            "details": "OCR classification failed",
            "all_confidences": {}
        }
    
    def _classify_by_gemini(self, image: Image.Image) -> Dict[str, any]:
        """Classify using Gemini Vision API."""
        
        if not HAVE_GEMINI:
            return {
                "card_type": "Unknown",
                "confidence": 0.0,
                "matches_user_selection": False,
                "method": None,
                "details": "Gemini not available",
                "all_confidences": {}
            }
        
        try:
            # Convert image to bytes
            import io
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Call Gemini Vision
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """
            Analyze this ID card image and determine its type.
            Respond with ONLY one of these formats:
            
            Card Type: [Ghana Card | Passport | Voter ID | Driver's License]
            Confidence: [0.0-1.0]
            Reasoning: [brief explanation]
            """
            
            response = model.generate_content([
                prompt,
                genai.upload_file(path=None, mime_type="image/png")  # Use PIL image
            ])
            
            response_text = response.text
            
            # Parse response
            card_type = "Unknown"
            confidence = 0.0
            
            for line in response_text.split('\n'):
                if "Card Type:" in line:
                    for ct in CARD_TYPE_KEYWORDS.keys():
                        if ct.upper() in line.upper():
                            card_type = ct
                            break
                elif "Confidence:" in line:
                    try:
                        confidence = float(line.split(':')[1].strip())
                    except:
                        pass
            
            return {
                "card_type": card_type,
                "confidence": confidence,
                "matches_user_selection": False,
                "method": "gemini_vision",
                "details": f"Gemini classification: {response_text[:100]}...",
                "all_confidences": {}
            }
        
        except Exception as e:
            logger.error(f"Gemini classification failed: {e}")
        
        return {
            "card_type": "Unknown",
            "confidence": 0.0,
            "matches_user_selection": False,
            "method": None,
            "details": f"Gemini error: {str(e)}",
            "all_confidences": {}
        }
