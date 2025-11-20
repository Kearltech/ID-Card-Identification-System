"""
Field Parsing and Matching Module

Parses OCR-extracted text and matches fields based on known label patterns.
Returns structured JSON with extracted field values.
"""

import re
import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FieldParser:
    """Parse OCR text and extract structured field data."""
    
    def __init__(self):
        """Initialize field parser."""
        # Import schemas
        from ocr_field_schemas import ID_CARD_SCHEMAS, FIELD_DATA_TYPES, get_field_data_type
        self.schemas = ID_CARD_SCHEMAS
        self.field_types = FIELD_DATA_TYPES
        self.get_field_type = get_field_data_type
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for matching.
        
        Args:
            text: Text to normalize
        
        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove special characters except alphanumeric, dash, slash, dot
        text = re.sub(r'[^\w\s\-/\.]', '', text)
        return text
    
    def clean_field_value(self, value: str) -> str:
        """
        Clean extracted field value.
        
        Args:
            value: Raw extracted value
        
        Returns:
            Cleaned value
        """
        # Strip whitespace
        value = value.strip()
        # Remove trailing punctuation
        value = re.sub(r'[.,;:\-]*$', '', value)
        return value
    
    def find_label_in_text(self, text: str, label_variants: list) -> Optional[str]:
        """
        Find a label in text (case-insensitive).
        
        Args:
            text: Text to search
            label_variants: List of label variants to match
        
        Returns:
            Matched label or None
        """
        text_lower = text.lower()
        
        for label in label_variants:
            if label.lower() in text_lower:
                return label
        
        return None
    
    def extract_value_after_label(self, text: str, label: str, context_length: int = 100) -> Optional[str]:
        """
        Extract value that comes after a label.
        
        Args:
            text: Full text to search
            label: Label to find
            context_length: Characters to look ahead after label
        
        Returns:
            Extracted value or None
        """
        pattern = rf"{re.escape(label)}\s*[:;\-]?\s*([^\n\r]+?)(?=\n|\r|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).strip()
            # Take only the first part if value is too long
            if len(value) > context_length:
                value = value[:context_length].strip()
            return self.clean_field_value(value)
        
        return None
    
    def extract_by_position(self, text: str, keywords: list) -> Optional[str]:
        """
        Extract value near position of keywords.
        
        Args:
            text: Text to search
            keywords: List of keywords to search for
        
        Returns:
            Extracted value or None
        """
        for keyword in keywords:
            # Find lines containing the keyword
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    # Extract the line content
                    parts = re.split(r'[:;\-]', line)
                    if len(parts) > 1:
                        return self.clean_field_value(parts[-1])
        
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date from text.
        
        Args:
            text: Text containing date
        
        Returns:
            Extracted date or None
        """
        # Common date patterns
        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4})',           # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{1,2}-\d{1,2}-\d{2,4})',           # MM-DD-YYYY
            r'(\d{4}/\d{1,2}/\d{1,2})',             # YYYY/MM/DD
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_sex(self, text: str) -> Optional[str]:
        """
        Extract sex/gender field.
        
        Args:
            text: Text to search
        
        Returns:
            'M' or 'F' or None
        """
        # Look for M/F patterns
        pattern = r'(?:sex|gender|m/f|sexe)\s*[:;\-]?\s*([MmFf])'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1).upper()
            if value in ['M', 'F']:
                return value
        
        # Look for Male/Female
        if re.search(r'male', text, re.IGNORECASE):
            return 'M'
        if re.search(r'female', text, re.IGNORECASE):
            return 'F'
        
        return None
    
    def extract_id_number(self, text: str, id_type: str) -> Optional[str]:
        """
        Extract ID number based on card type.
        
        Args:
            text: Text to search
            id_type: Type of ID card
        
        Returns:
            Extracted ID number or None
        """
        from ocr_field_schemas import ID_NUMBER_PATTERNS
        
        pattern = ID_NUMBER_PATTERNS.get(id_type.lower())
        if not pattern:
            return None
        
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
        
        return None
    
    def parse_fields_from_text(self, text: str, id_type: str) -> Dict[str, Any]:
        """
        Parse all fields from OCR text.
        
        Args:
            text: OCR-extracted text
            id_type: Type of ID card
        
        Returns:
            Dictionary with extracted fields
        """
        schema = self.schemas.get(id_type.lower(), {})
        if not schema:
            logger.error(f"Unknown ID type: {id_type}")
            return {}
        
        extracted = {}
        
        for field_name, label_variants in schema.items():
            value = None
            
            # Try to find field using label matching
            matched_label = self.find_label_in_text(text, label_variants)
            if matched_label:
                value = self.extract_value_after_label(text, matched_label)
            
            # Fallback: try extracting by keyword search
            if not value:
                value = self.extract_by_position(text, label_variants)
            
            # Special handling for specific field types
            if not value:
                if 'date' in field_name.lower():
                    value = self.extract_date(text)
                elif 'sex' in field_name.lower() or 'gender' in field_name.lower():
                    value = self.extract_sex(text)
                elif 'id' in field_name.lower() and ('number' in field_name.lower() or 'id' in field_name.lower()):
                    value = self.extract_id_number(text, id_type)
            
            # Store extracted value
            extracted[field_name] = value
            
            if value:
                logger.debug(f"Extracted {field_name}: {value}")
        
        return extracted
    
    def extract_to_json(self, text: str, id_type: str) -> Dict[str, Any]:
        """
        Extract fields and return as structured JSON.
        
        Args:
            text: OCR-extracted text
            id_type: Type of ID card
        
        Returns:
            JSON-compatible dictionary
        """
        fields = self.parse_fields_from_text(text, id_type)
        
        result = {
            "id_type": id_type,
            "extraction_status": "success" if fields else "failed",
            "fields_extracted": len([f for f in fields.values() if f is not None]),
            "fields": fields,
            "raw_text": text[:500] + "..." if len(text) > 500 else text,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        return result


class FieldValidator:
    """Validate and compare extracted fields with user input."""
    
    def __init__(self):
        """Initialize field validator."""
        from ocr_field_schemas import get_required_fields, get_optional_fields
        self.get_required = get_required_fields
        self.get_optional = get_optional_fields
    
    def normalize_for_comparison(self, value: str) -> str:
        """
        Normalize value for comparison.
        
        Args:
            value: Value to normalize
        
        Returns:
            Normalized value
        """
        if not value:
            return ""
        
        # Convert to lowercase
        value = str(value).lower()
        
        # Remove whitespace
        value = re.sub(r'\s+', '', value)
        
        # Remove special characters
        value = re.sub(r'[^\w]', '', value)
        
        return value
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity ratio between two strings.
        
        Args:
            str1: First string
            str2: Second string
        
        Returns:
            Similarity ratio (0-1)
        """
        if not str1 or not str2:
            return 0.0
        
        norm1 = self.normalize_for_comparison(str1)
        norm2 = self.normalize_for_comparison(str2)
        
        if norm1 == norm2:
            return 1.0
        
        matcher = SequenceMatcher(None, norm1, norm2)
        return matcher.ratio()
    
    def compare_fields(self, user_input: Dict[str, Any], extracted_fields: Dict[str, Any], 
                      similarity_threshold: float = 0.85) -> Dict[str, Any]:
        """
        Compare user input with extracted fields.
        
        Args:
            user_input: User-provided data
            extracted_fields: Fields extracted from ID
            similarity_threshold: Minimum similarity ratio to consider as match (0-1)
        
        Returns:
            Comparison results with matches, mismatches, and confidence
        """
        comparison = {
            "matches": {},
            "mismatches": {},
            "missing_on_id": {},
            "not_provided_by_user": {},
            "confidence_scores": {},
            "overall_confidence": 0.0
        }
        
        match_count = 0
        total_fields = 0
        
        # Compare user-provided fields with extracted fields
        for key, user_value in user_input.items():
            if not user_value:
                continue
            
            total_fields += 1
            extracted_value = extracted_fields.get(key)
            
            if extracted_value is None:
                comparison["missing_on_id"][key] = user_value
            else:
                similarity = self.calculate_similarity(str(user_value), str(extracted_value))
                comparison["confidence_scores"][key] = similarity
                
                if similarity >= similarity_threshold:
                    comparison["matches"][key] = {
                        "user_value": user_value,
                        "extracted_value": extracted_value,
                        "similarity": similarity
                    }
                    match_count += 1
                else:
                    comparison["mismatches"][key] = {
                        "user_value": user_value,
                        "extracted_value": extracted_value,
                        "similarity": similarity
                    }
        
        # Find fields on ID that user didn't provide
        for key, extracted_value in extracted_fields.items():
            if extracted_value and key not in user_input:
                comparison["not_provided_by_user"][key] = extracted_value
        
        # Calculate overall confidence
        if total_fields > 0:
            comparison["overall_confidence"] = (match_count / total_fields)
        
        return comparison
    
    def validate_extracted_fields(self, extracted_fields: Dict[str, Any], id_type: str) -> Dict[str, Any]:
        """
        Validate extracted fields against schema.
        
        Args:
            extracted_fields: Extracted fields dictionary
            id_type: Type of ID card
        
        Returns:
            Validation results
        """
        from ocr_field_schemas import get_field_data_type, validate_field_value
        
        validation = {
            "id_type": id_type,
            "valid_fields": {},
            "invalid_fields": {},
            "missing_required": [],
            "overall_valid": True
        }
        
        required_fields = self.get_required(id_type)
        
        # Check required fields
        for field in required_fields:
            if not extracted_fields.get(field):
                validation["missing_required"].append(field)
                validation["overall_valid"] = False
        
        # Validate each field
        for field_name, value in extracted_fields.items():
            if value is None:
                continue
            
            is_valid, error_msg = validate_field_value(field_name, value)
            
            if is_valid:
                validation["valid_fields"][field_name] = value
            else:
                validation["invalid_fields"][field_name] = {
                    "value": value,
                    "error": error_msg
                }
                validation["overall_valid"] = False
        
        return validation
