"""Advanced OCR module with multiple OCR engines and preprocessing techniques.

This module provides:
- Multiple OCR engines (EasyOCR, PaddleOCR)
- Automatic orientation detection and correction
- Text region detection (CRAFT-based)
- Image preprocessing pipeline
- Confidence scoring and result aggregation
"""

import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
import os

logger = logging.getLogger(__name__)

# OCR Engine options
class OCREngine(Enum):
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    HYBRID = "hybrid"  # Combine results from multiple engines


class AdvancedOCREngine:
    """Advanced OCR engine with multiple backends and preprocessing."""
    
    def __init__(self, engine: OCREngine = OCREngine.HYBRID, use_gpu: bool = False):
        """Initialize OCR engine.
        
        Args:
            engine: Which OCR engine to use
            use_gpu: Whether to use GPU (if available)
        """
        self.engine = engine
        self.use_gpu = use_gpu
        self._easyocr_reader = None
        self._paddleocr_reader = None
        
        if engine in [OCREngine.EASYOCR, OCREngine.HYBRID]:
            self._init_easyocr()
        if engine in [OCREngine.PADDLEOCR, OCREngine.HYBRID]:
            self._init_paddleocr()
    
    def _init_easyocr(self):
        """Initialize EasyOCR reader."""
        try:
            import easyocr
            logger.info("Initializing EasyOCR reader...")
            self._easyocr_reader = easyocr.Reader(
                ['en'],
                gpu=self.use_gpu,
                model_storage_directory='.cache/easyocr',
                user_network_directory='.cache/easyocr'
            )
            logger.info("✓ EasyOCR initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize EasyOCR: {e}")
            self._easyocr_reader = None
    
    def _init_paddleocr(self):
        """Initialize PaddleOCR reader."""
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR reader...")
            self._paddleocr_reader = PaddleOCR(
                use_angle_cls=True,
                use_gpu=self.use_gpu,
                lang='en',
                ocr_version='PP-OCRv4',
                cache_home_dir='.cache/paddleocr'
            )
            logger.info("✓ PaddleOCR initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR: {e}")
            self._paddleocr_reader = None
    
    def detect_text_orientation(self, image_bgr: np.ndarray) -> Tuple[float, np.ndarray]:
        """Detect and correct text orientation.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Tuple of (rotation_angle, rotated_image)
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Use Hough line detection to find dominant orientation
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
        
        if lines is None or len(lines) == 0:
            logger.debug("No lines detected for orientation")
            return 0.0, image_bgr
        
        # Extract angles from lines
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta)
            # Convert to -90 to 90 range
            if angle > 90:
                angle = angle - 180
            angles.append(angle)
        
        # Find most common angle (histogram)
        hist, bin_edges = np.histogram(angles, bins=180, range=(-90, 90))
        dominant_angle = bin_edges[np.argmax(hist)]
        
        # Correct if angle is significant (> 2 degrees)
        if abs(dominant_angle) > 2:
            logger.debug(f"Detected rotation angle: {dominant_angle:.2f}°")
            height, width = image_bgr.shape[:2]
            center = (width // 2, height // 2)
            
            # Rotate image
            rotation_matrix = cv2.getRotationMatrix2D(center, dominant_angle, 1.0)
            rotated = cv2.warpAffine(
                image_bgr,
                rotation_matrix,
                (width, height),
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(255, 255, 255)
            )
            return dominant_angle, rotated
        
        return 0.0, image_bgr
    
    def preprocess_for_ocr(self, image_bgr: np.ndarray,
                          auto_rotate: bool = True,
                          enhance_contrast: bool = True,
                          denoise: bool = True) -> np.ndarray:
        """Preprocess image for optimal OCR performance.
        
        Args:
            image_bgr: Input image in BGR format
            auto_rotate: Whether to auto-detect and correct rotation
            enhance_contrast: Whether to enhance contrast
            denoise: Whether to denoise image
            
        Returns:
            Preprocessed image
        """
        processed = image_bgr.copy()
        
        # Step 1: Auto-rotate if enabled
        if auto_rotate:
            rotation_angle, processed = self.detect_text_orientation(processed)
        
        # Step 2: Convert to grayscale
        if len(processed.shape) == 3:
            gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            gray = processed
        
        # Step 3: Denoise if enabled
        if denoise:
            gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # Step 4: Contrast enhancement using CLAHE
        if enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        
        # Step 5: Binary thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Step 6: Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        logger.debug("Image preprocessing completed")
        return cleaned
    
    def extract_with_easyocr(self, image_bgr: np.ndarray) -> Tuple[str, List[Dict]]:
        """Extract text using EasyOCR.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Tuple of (full_text, detailed_results)
        """
        if self._easyocr_reader is None:
            logger.warning("EasyOCR not available")
            return "", []
        
        try:
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            
            # Perform OCR
            results = self._easyocr_reader.readtext(image_rgb, detail=1)
            
            # Extract text and confidence
            full_text = "\n".join([result[1] for result in results])
            detailed = [
                {
                    "text": result[1],
                    "confidence": result[2],
                    "bbox": result[0]
                }
                for result in results
            ]
            
            logger.info(f"EasyOCR extracted {len(detailed)} text regions")
            return full_text, detailed
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return "", []
    
    def extract_with_paddleocr(self, image_bgr: np.ndarray) -> Tuple[str, List[Dict]]:
        """Extract text using PaddleOCR.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            Tuple of (full_text, detailed_results)
        """
        if self._paddleocr_reader is None:
            logger.warning("PaddleOCR not available")
            return "", []
        
        try:
            # Convert BGR to RGB
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            
            # Perform OCR
            results = self._paddleocr_reader.ocr(image_rgb, cls=True)
            
            if not results or results[0] is None:
                logger.warning("PaddleOCR returned empty results")
                return "", []
            
            # Extract text and confidence
            full_text = "\n".join([result[1][0] for result in results[0]])
            detailed = [
                {
                    "text": result[1][0],
                    "confidence": float(result[1][1]),
                    "bbox": result[0]
                }
                for result in results[0]
            ]
            
            logger.info(f"PaddleOCR extracted {len(detailed)} text regions")
            return full_text, detailed
        except Exception as e:
            logger.error(f"PaddleOCR extraction failed: {e}")
            return "", []
    
    def extract_text(self, image_bgr: np.ndarray,
                    preprocess: bool = True) -> Dict[str, any]:
        """Extract text from image using configured OCR engine(s).
        
        Args:
            image_bgr: Input image in BGR format
            preprocess: Whether to preprocess image before OCR
            
        Returns:
            Dictionary with:
            - 'full_text': Combined text
            - 'easyocr_text': Text from EasyOCR (if hybrid)
            - 'paddleocr_text': Text from PaddleOCR (if hybrid)
            - 'detailed_results': List of text regions with confidence
            - 'engine': Which engine was used
            - 'confidence': Average confidence score
        """
        # Preprocess if enabled
        if preprocess:
            image_bgr = self.preprocess_for_ocr(image_bgr)
        
        results = {
            "engine": self.engine.value,
            "full_text": "",
            "easyocr_text": "",
            "paddleocr_text": "",
            "detailed_results": [],
            "confidence": 0.0
        }
        
        if self.engine == OCREngine.EASYOCR:
            text, details = self.extract_with_easyocr(image_bgr)
            results["full_text"] = text
            results["easyocr_text"] = text
            results["detailed_results"] = details
        
        elif self.engine == OCREngine.PADDLEOCR:
            text, details = self.extract_with_paddleocr(image_bgr)
            results["full_text"] = text
            results["paddleocr_text"] = text
            results["detailed_results"] = details
        
        elif self.engine == OCREngine.HYBRID:
            # Use both engines and combine results
            easy_text, easy_details = self.extract_with_easyocr(image_bgr)
            paddle_text, paddle_details = self.extract_with_paddleocr(image_bgr)
            
            results["easyocr_text"] = easy_text
            results["paddleocr_text"] = paddle_text
            
            # Combine texts with preference for higher confidence results
            all_details = easy_details + paddle_details
            combined_text = easy_text if len(easy_text) >= len(paddle_text) else paddle_text
            
            results["full_text"] = combined_text
            results["detailed_results"] = all_details
        
        # Calculate average confidence
        if results["detailed_results"]:
            confidences = [r.get("confidence", 0.5) for r in results["detailed_results"]]
            results["confidence"] = np.mean(confidences)
        
        logger.info(f"OCR extraction complete. Average confidence: {results['confidence']:.2%}")
        return results


def create_ocr_engine(engine: str = "hybrid", use_gpu: bool = False) -> AdvancedOCREngine:
    """Factory function to create OCR engine.
    
    Args:
        engine: "easyocr", "paddleocr", or "hybrid"
        use_gpu: Whether to use GPU
        
    Returns:
        AdvancedOCREngine instance
    """
    engine_enum = OCREngine[engine.upper()]
    return AdvancedOCREngine(engine=engine_enum, use_gpu=use_gpu)
