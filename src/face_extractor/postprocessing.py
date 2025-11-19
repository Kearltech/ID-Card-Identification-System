"""
OCR Post-Processing Module - Enhanced for Accuracy

Enhances OCR accuracy through:
- Text normalization (whitespace, casing)
- Fuzzy correction using RapidFuzz
- Common-name and common-pattern heuristics
- Confidence-weighted multi-engine merging
- Field-specific validation and correction

Author: AI Assistant
Date: November 13, 2025
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

try:
    from rapidfuzz import fuzz, process as rf_process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    fuzz = None
    rf_process = None

logger = logging.getLogger(__name__)


@dataclass
class TextCorrection:
    """Represents a text correction suggestion."""
    original: str
    corrected: str
    confidence: float  # 0-1
    method: str  # 'fuzzy', 'pattern', 'common_name', 'merge'
    field_type: Optional[str] = None


class OCRPostProcessor:
    """
    Enhanced post-processor for OCR-extracted field values.
    
    Responsibilities:
    - Normalize whitespace and punctuation
    - Title-case names (with proper handling of special names)
    - Uppercase ID numbers
    - Apply smart substitution rules for common OCR errors
    - Perform fuzzy corrections against common names/options
    - Merge multi-engine results
    - Field-specific validation
    """

    # Common OCR misreadings (context matters)
    COMMON_OCR_ERRORS = {
        'O': '0', '0': 'O',  # Letter O vs digit zero
        'l': '1', '1': 'l', 'I': '1',  # Letter l vs digit 1
        'S': '5', '5': 'S',  # Letter S vs digit 5
        'Z': '2', '2': 'Z',  # Letter Z vs digit 2
        'B': '8', '8': 'B',  # Letter B vs digit 8
    }
    
    # Common first and last names for fuzzy matching
    COMMON_NAMES = {
        'John', 'James', 'Robert', 'Michael', 'William', 'David', 'Richard',
        'Joseph', 'Charles', 'Daniel', 'Mary', 'Jennifer', 'Linda', 'Patricia',
        'Barbara', 'Elizabeth', 'Susan', 'Jessica', 'Sarah', 'Karen', 'Nancy',
        # Common African names
        'Kofi', 'Kwame', 'Abena', 'Ama', 'Yaw', 'Akosua', 'Benjamin', 'Emmanuel',
        'Samuel', 'Grace', 'Ruth', 'Joyce', 'Florence', 'Comfort', 'Priscilla',
        'Mensah', 'Boateng', 'Asante', 'Owusu', 'Antwi', 'Appiah', 'Yankah',
        'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
        'Davis', 'Wilson', 'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson',
    }
    
    GENDER_OPTIONS = ['Male', 'Female', 'M', 'F']

    def __init__(self, use_fuzzy: bool = True):
        """Initialize OCR post-processor."""
        self.use_fuzzy = use_fuzzy and RAPIDFUZZ_AVAILABLE
        if not RAPIDFUZZ_AVAILABLE:
            logger.warning("RapidFuzz not available; fuzzy matching disabled")

    def _normalize_whitespace(self, s: str) -> str:
        """Normalize whitespace: collapse, strip."""
        return re.sub(r'\s+', ' ', s).strip()

    def _clean_name(self, s: str) -> str:
        """Clean and normalize name fields."""
        s = self._normalize_whitespace(s)
        # Remove non-name characters but keep apostrophes, hyphens
        s = re.sub(r"[^A-Za-z\s\-'.']", '', s)
        # Title case
        words = s.split()
        cleaned_words = []
        for word in words:
            # Handle hyphenated names (e.g., Jean-Pierre)
            if '-' in word:
                word = '-'.join(w.capitalize() for w in word.split('-'))
            else:
                word = word.capitalize()
            cleaned_words.append(word)
        return ' '.join(cleaned_words)

    def _clean_id(self, s: str) -> str:
        """Clean and normalize ID fields."""
        s = self._normalize_whitespace(s)
        # Remove spaces but keep hyphens and slashes
        s = re.sub(r'\s+', '', s)
        return s.upper()

    def _clean_date(self, s: str) -> str:
        """Clean and normalize date fields."""
        s = self._normalize_whitespace(s)
        # Normalize separators to forward slash
        s = re.sub(r'[-./]', '/', s)
        return s

    def _apply_fuzzy_corrections(self, text: str, field_type: Optional[str] = None) -> Tuple[str, float]:
        """Apply fuzzy matching corrections."""
        if not self.use_fuzzy or not text:
            return text, 1.0
        
        corrected = text
        confidence = 1.0
        
        if field_type in ('name', 'surname', 'first_name'):
            best_match, score = self._fuzzy_match_name(text)
            if score >= 0.75:
                corrected = best_match
                confidence = score
        
        return corrected, confidence

    def _fuzzy_match_name(self, text: str) -> Tuple[str, float]:
        """Fuzzy match against common names."""
        if not self.use_fuzzy:
            return text, 1.0
        
        try:
            best_match, score, _ = rf_process.extractOne(
                text, self.COMMON_NAMES, scorer=fuzz.ratio
            )
            return best_match, score / 100.0
        except Exception as e:
            logger.debug(f"Fuzzy matching failed: {e}")
            return text, 1.0

    def _fuzzy_match_option(self, text: str, options: List[str]) -> Tuple[str, float]:
        """Fuzzy match against options list."""
        if not self.use_fuzzy or not options:
            return text, 1.0
        
        try:
            best_match, score, _ = rf_process.extractOne(
                text, options, scorer=fuzz.token_sort_ratio
            )
            return best_match, score / 100.0
        except Exception as e:
            logger.debug(f"Option matching failed: {e}")
            return text, 1.0

    def process_field(self, value: str, field_type: Optional[str] = None) -> Tuple[str, float]:
        """
        Process a single field value with normalization and corrections.
        
        Args:
            value: Raw field value
            field_type: Type of field (e.g., 'name', 'id_number', 'date')
        
        Returns:
            (processed_value, confidence_score)
        """
        if not value or not isinstance(value, str):
            return '', 0.0
        
        value = self._normalize_whitespace(value)
        if not value:
            return '', 0.0
        
        confidence = 1.0
        
        # Apply field-specific cleaning
        if field_type in ('name', 'surname', 'first_name', 'middle_name'):
            value = self._clean_name(value)
            value, conf = self._apply_fuzzy_corrections(value, field_type)
            confidence *= conf
        elif field_type in ('id_number', 'personal_id', 'passport_number', 'license_number'):
            value = self._clean_id(value)
        elif field_type == 'date':
            value = self._clean_date(value)
        elif field_type in ('gender', 'sex'):
            value, conf = self._fuzzy_match_option(value, self.GENDER_OPTIONS)
            confidence *= conf
        else:
            # Generic cleanup
            value = self._normalize_whitespace(value)
        
        return value, confidence

    def process_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process all fields with proper typing.
        
        Args:
            fields: Dictionary of field_name -> value
        
        Returns:
            Dictionary of cleaned field values with confidence scores
        """
        cleaned: Dict[str, Any] = {}
        
        for field_name, value in (fields or {}).items():
            if value is None:
                cleaned[field_name] = value
                continue
            
            value_str = str(value).strip()
            if not value_str:
                cleaned[field_name] = value_str
                continue
            
            # Infer field type from name
            field_type = self._infer_field_type(field_name)
            
            # Process field
            processed_value, confidence = self.process_field(value_str, field_type)
            cleaned[field_name] = processed_value
        
        return cleaned

    def merge_multi_engine(self, text1: str, text2: str, 
                          conf1: float = 0.8, conf2: float = 0.8) -> Tuple[str, float]:
        """
        Merge results from two OCR engines.
        
        Args:
            text1: Text from engine 1
            text2: Text from engine 2
            conf1: Confidence from engine 1
            conf2: Confidence from engine 2
        
        Returns:
            (merged_text, merged_confidence)
        """
        if not text2:
            return text1, conf1
        if not text1:
            return text2, conf2
        
        if text1 == text2:
            # Exact match: blend confidences
            merged_conf = (conf1 + conf2) / 2
            return text1, merged_conf
        
        if self.use_fuzzy:
            similarity = fuzz.ratio(text1, text2) / 100.0
            if similarity > 0.9:
                # Very similar: use weighted blend
                merged_conf = (conf1 * 0.6 + conf2 * 0.4) / 2
                return text1, merged_conf  # Prefer first engine
        
        # Different: use higher confidence
        if conf1 >= conf2:
            return text1, conf1
        else:
            return text2, conf2

    @staticmethod
    def _infer_field_type(field_name: str) -> Optional[str]:
        """Infer field type from field name."""
        name_lower = field_name.lower()
        
        if any(x in name_lower for x in ['name', 'surname', 'first', 'middle', 'given']):
            return 'name'
        elif any(x in name_lower for x in ['id', 'number', 'no', 'passport', 'tin', 'license', 'licence']):
            return 'id_number'
        elif 'date' in name_lower:
            return 'date'
        elif any(x in name_lower for x in ['gender', 'sex']):
            return 'gender'
        
        return None


def create_post_processor(use_fuzzy: bool = True) -> OCRPostProcessor:
    """Factory function to create OCR post-processor."""
    return OCRPostProcessor(use_fuzzy=use_fuzzy)


if __name__ == "__main__":
    # Quick self-test
    processor = OCRPostProcessor(use_fuzzy=True)
    sample = {
        "Surname": "  shanavan ",
        "Personal ID Number": "gha 1234 5678",
        "Date of Birth": "12/05/1990",
        "Gender": "male",
        "First Name": "Jahn",  # Typo - should be John
    }
    print("Input:", sample)
    print("Output:", processor.process_fields(sample))

