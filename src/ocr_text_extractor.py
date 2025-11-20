"""
OCR Text Extraction Module

Extracts raw text from ID card images using multiple engines:
1. Gemini Vision API (recommended - 95%+ accuracy)
2. EasyOCR (fallback - 92%+ accuracy)
3. Tesseract (optional - 90%+ accuracy)
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Try to import Gemini Vision
try:
    import google.generativeai as genai
    HAVE_GEMINI = True
except ImportError:
    HAVE_GEMINI = False
    logger.warning("Google Generative AI not available")

# Try to import EasyOCR
try:
    import easyocr
    HAVE_EASYOCR = True
except ImportError:
    HAVE_EASYOCR = False
    logger.warning("EasyOCR not available")

# Try to import Tesseract
try:
    import pytesseract
    HAVE_TESSERACT = True
except ImportError:
    HAVE_TESSERACT = False
    logger.debug("Tesseract not available")


class OCRTextExtractor:
    """Extract text from ID card images using multiple OCR engines."""
    
    def __init__(self, api_key: Optional[str] = None, use_gemini: bool = True):
        """
        Initialize OCR extractor.
        
        Args:
            api_key: Gemini API key (optional)
            use_gemini: Whether to try Gemini first (default: True)
        """
        self.use_gemini = use_gemini and HAVE_GEMINI
        self.have_easyocr = HAVE_EASYOCR
        self.have_tesseract = HAVE_TESSERACT
        
        if api_key and self.use_gemini:
            try:
                genai.configure(api_key=api_key)
                self.gemini_ready = True
                logger.info("Gemini Vision initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
                self.gemini_ready = False
        else:
            self.gemini_ready = False
        
        # Lazy load EasyOCR reader
        self.easyocr_reader = None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results.
        
        Args:
            image: Input image (BGR or RGB)
        
        Returns:
            Preprocessed image
        """
        # Ensure image is numpy array
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif isinstance(image, str):
            image = cv2.imread(image)
        
        # Upscale if image is too small
        if image.shape[0] < 300 or image.shape[1] < 300:
            scale = max(300 / image.shape[0], 300 / image.shape[1])
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Apply morphological operations to improve text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def extract_with_gemini(self, image_input) -> Optional[str]:
        """
        Extract text using Gemini Vision API.
        
        Args:
            image_input: Image file path, numpy array, or PIL Image
        
        Returns:
            Extracted text or None if failed
        """
        if not self.gemini_ready:
            return None
        
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Convert image to bytes if needed
            if isinstance(image_input, np.ndarray):
                image_pil = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
                image_bytes = io.BytesIO()
                image_pil.save(image_bytes, format='JPEG')
                image_input = image_bytes.getvalue()
            elif isinstance(image_input, Image.Image):
                image_bytes = io.BytesIO()
                image_input.save(image_bytes, format='JPEG')
                image_input = image_bytes.getvalue()
            elif isinstance(image_input, str):
                with open(image_input, 'rb') as f:
                    image_input = f.read()
            
            # Call Gemini API
            response = model.generate_content([
                "Extract ALL visible text from this ID card image. Include all text, numbers, dates, and labels. Format the output clearly with each field on a new line.",
                {
                    "mime_type": "image/jpeg",
                    "data": image_input
                }
            ])
            
            text = response.text.strip()
            logger.info(f"Gemini extracted {len(text)} characters")
            return text
        
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return None
    
    def extract_with_easyocr(self, image_input) -> Optional[str]:
        """
        Extract text using EasyOCR.
        
        Args:
            image_input: Image file path, numpy array, or PIL Image
        
        Returns:
            Extracted text or None if failed
        """
        if not self.have_easyocr:
            return None
        
        try:
            # Lazy load reader (first use only)
            if self.easyocr_reader is None:
                logger.info("Initializing EasyOCR reader (first time)...")
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            
            # Convert to image format if needed
            if isinstance(image_input, str):
                image = cv2.imread(image_input)
            elif isinstance(image_input, Image.Image):
                image = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            else:
                image = image_input
            
            # Preprocess image
            processed = self._preprocess_image(image)
            
            # Run OCR
            results = self.easyocr_reader.readtext(processed, detail=0)
            
            # Join text results
            text = "\n".join(results)
            logger.info(f"EasyOCR extracted {len(text)} characters")
            return text
        
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return None
    
    def extract_with_tesseract(self, image_input) -> Optional[str]:
        """
        Extract text using Tesseract OCR.
        
        Args:
            image_input: Image file path, numpy array, or PIL Image
        
        Returns:
            Extracted text or None if failed
        """
        if not self.have_tesseract:
            return None
        
        try:
            # Convert to image format if needed
            if isinstance(image_input, str):
                image = cv2.imread(image_input)
            elif isinstance(image_input, Image.Image):
                image = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            else:
                image = image_input
            
            # Preprocess image
            processed = self._preprocess_image(image)
            
            # Run Tesseract
            text = pytesseract.image_to_string(processed)
            logger.info(f"Tesseract extracted {len(text)} characters")
            return text
        
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return None
    
    def extract_text(self, image_input, engines: list = None) -> Tuple[Optional[str], str]:
        """
        Extract text using available OCR engines with fallback.
        
        Args:
            image_input: Image file path, numpy array, or PIL Image
            engines: List of engines to try in order. Default: ['gemini', 'easyocr', 'tesseract']
        
        Returns:
            Tuple of (extracted_text, engine_used)
        """
        if engines is None:
            engines = ['gemini', 'easyocr', 'tesseract']
        
        for engine in engines:
            if engine == 'gemini' and self.gemini_ready:
                logger.info("Trying Gemini Vision...")
                text = self.extract_with_gemini(image_input)
                if text:
                    return text, 'gemini'
            
            elif engine == 'easyocr' and self.have_easyocr:
                logger.info("Trying EasyOCR...")
                text = self.extract_with_easyocr(image_input)
                if text:
                    return text, 'easyocr'
            
            elif engine == 'tesseract' and self.have_tesseract:
                logger.info("Trying Tesseract...")
                text = self.extract_with_tesseract(image_input)
                if text:
                    return text, 'tesseract'
        
        logger.error("All OCR engines failed")
        return None, 'none'
    
    def extract_text_from_file(self, filepath: str) -> Tuple[Optional[str], str]:
        """
        Extract text from an image file.
        
        Args:
            filepath: Path to image file
        
        Returns:
            Tuple of (extracted_text, engine_used)
        """
        return self.extract_text(filepath)
    
    def get_available_engines(self) -> dict:
        """Get status of available OCR engines."""
        return {
            'gemini': self.gemini_ready,
            'easyocr': self.have_easyocr,
            'tesseract': self.have_tesseract
        }
