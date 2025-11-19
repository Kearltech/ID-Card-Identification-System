"""OCR and field extraction module for ID card processing."""

import re
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import easyocr
    _HAVE_EASYOCR = True
except ImportError:
    easyocr = None  # type: ignore
    _HAVE_EASYOCR = False

try:
    from rapidfuzz import fuzz, process
    _HAVE_RAPIDFUZZ = True
except ImportError:
    try:
        from difflib import SequenceMatcher
        _HAVE_RAPIDFUZZ = False
    except ImportError:
        SequenceMatcher = None  # type: ignore
        _HAVE_RAPIDFUZZ = False

# Import preprocessing module
try:
    from .image_preprocessor import preprocess_for_ocr, resize_for_ocr
    _HAVE_PREPROCESSOR = True
except ImportError:
    _HAVE_PREPROCESSOR = False


# Card type detection keywords (case-insensitive)
CARD_TYPE_KEYWORDS = {
    "Ghana Card": ["ECOWAS IDENTITY CARD", "NATIONAL IDENTIFICATION CARD", "GHANA CARD"],
    "Driver's License": ["DRIVER LICENCE", "DRIVER LICENSE", "LICENCE #", "LICENSE #", "DRIVING LICENCE"],
    "Passport": ["PASSPORT", "REPUBLIC OF GHANA", "PASSPORT NO"],
    "Voter ID": ["VOTER IDENTITY CARD", "ELECTORAL COMMISSION", "VOTER ID"],
    "NHIS Card": ["NATIONAL HEALTH INSURANCE", "NHIS", "HEALTH INSURANCE"],
    "SSNIT Card": ["SOCIAL SECURITY", "SSNIT", "SOCIAL SECURITY AND NATIONAL INSURANCE TRUST"],
    "Birth Certificate": ["BIRTH CERTIFICATE", "CERTIFICATE OF BIRTH"],
    "TIN Document": ["TAX IDENTIFICATION NUMBER", "TIN", "TAX ID"],
}

# Field templates for each card type
FIELD_TEMPLATES = {
    "Ghana Card": [
        "Surname", "Firstnames", "Nationality", "Sex", "Date of Birth",
        "Height", "Personal ID Number", "Document Number",
        "Place of Issuance", "Date of Issuance", "Date of Expiry"
    ],
    "Driver's License": [
        "Name", "Date of Birth", "Licence #", "License #",
        "Class of Licence", "Class of License", "Date of Issue", "Expiry Date",
        "Nationality", "Address"
    ],
    "Passport": [
        "Passport Number", "Surname", "Given Names", "Nationality",
        "Date of Birth", "Place of Birth", "Date of Issue", "Date of Expiry",
        "Authority"
    ],
    "Voter ID": [
        "Name", "Voter ID Number", "Date of Birth", "Constituency",
        "Polling Station", "Electoral Area"
    ],
    "NHIS Card": [
        "Name", "NHIS Number", "Date of Birth", "Gender", "Expiry Date"
    ],
    "SSNIT Card": [
        "Name", "SSNIT Number", "Date of Birth", "Gender", "Employer"
    ],
    "Birth Certificate": [
        "Name", "Date of Birth", "Place of Birth", "Gender",
        "Father's Name", "Mother's Name", "Registration Number"
    ],
    "TIN Document": [
        "Name", "TIN Number", "Date of Birth", "Taxpayer Type", "Registration Date"
    ],
}

# Common field label variations for fuzzy matching
FIELD_LABEL_VARIATIONS = {
    "Name": ["name", "full name", "fullname", "holder name"],
    "Surname": ["surname", "last name", "family name"],
    "Firstnames": ["first names", "firstname", "first name", "given names"],
    "Given Names": ["given names", "first names", "firstname"],
    "Date of Birth": ["date of birth", "dob", "birth date", "born", "birthday"],
    "Date of Issue": ["date of issue", "issued", "issue date"],
    "Date of Expiry": ["date of expiry", "expiry", "expiry date", "expires", "valid until"],
    "Nationality": ["nationality", "country", "citizen"],
    "Sex": ["sex", "gender"],
    "Gender": ["gender", "sex"],
    "Height": ["height"],
    "Personal ID Number": ["personal id number", "id number", "personal id", "pid"],
    "Document Number": ["document number", "doc number", "document no"],
    "Licence #": ["licence #", "license #", "licence number", "license number", "licence no", "license no"],
    "License #": ["license #", "licence #", "license number", "licence number"],
    "Class of Licence": ["class of licence", "class of license", "license class", "licence class"],
    "Passport Number": ["passport number", "passport no", "passport #"],
    "Place of Birth": ["place of birth", "birth place", "pob"],
    "Place of Issuance": ["place of issuance", "place of issue", "issued at"],
    "Date of Issuance": ["date of issuance", "date of issue", "issued on"],
    "Voter ID Number": ["voter id number", "voter id", "voter number"],
    "NHIS Number": ["nhis number", "nhis no", "nhis id"],
    "SSNIT Number": ["ssnit number", "ssnit no", "ssnit id"],
    "TIN Number": ["tin number", "tin no", "tin id", "tax id number"],
    "Address": ["address", "residence"],
    "Constituency": ["constituency"],
    "Polling Station": ["polling station", "station"],
    "Electoral Area": ["electoral area", "area"],
    "Employer": ["employer", "company"],
    "Father's Name": ["father's name", "father", "father name"],
    "Mother's Name": ["mother's name", "mother", "mother name"],
    "Registration Number": ["registration number", "reg number", "reg no"],
    "Taxpayer Type": ["taxpayer type", "type"],
    "Registration Date": ["registration date", "reg date"],
    "Authority": ["authority", "issuing authority"],
}


def _fuzzy_match(text: str, label: str, threshold: float = 0.7) -> bool:
    """Check if text matches label using fuzzy matching."""
    if _HAVE_RAPIDFUZZ:
        ratio = fuzz.ratio(text.lower(), label.lower()) / 100.0
        return ratio >= threshold
    elif SequenceMatcher is not None:
        ratio = SequenceMatcher(None, text.lower(), label.lower()).ratio()
        return ratio >= threshold
    else:
        # Simple case-insensitive matching as fallback
        return label.lower() in text.lower() or text.lower() in label.lower()


# Module-level cache for EasyOCR reader
_ocr_reader = None


def _get_ocr_reader():
    """Get or initialize EasyOCR reader (cached at module level)."""
    global _ocr_reader
    if not _HAVE_EASYOCR:
        raise ImportError("EasyOCR is not installed. Please install it with: pip install easyocr")
    
    if _ocr_reader is None:
        _ocr_reader = easyocr.Reader(['en'], gpu=False)  # type: ignore
    
    return _ocr_reader


def _extract_text_with_ocr(image_bgr, preprocess: bool = True) -> str:
    """Extract text from image using EasyOCR.
    
    Args:
        image_bgr: Input image in BGR format
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Extracted text string
    """
    if not _HAVE_EASYOCR:
        raise ImportError("EasyOCR is not installed. Please install it with: pip install easyocr")
    
    # Preprocess image for better OCR accuracy
    processed_image = image_bgr.copy()
    if preprocess and _HAVE_PREPROCESSOR:
        try:
            # Resize if too large
            processed_image = resize_for_ocr(processed_image, max_dimension=2000)
            # Apply preprocessing pipeline
            processed_image = preprocess_for_ocr(
                processed_image,
                auto_rotate=True,
                enhance_contrast_flag=True,
                correct_lighting_flag=True,
                denoise=True,
                sharpen=False
            )
        except Exception as e:
            # If preprocessing fails, use original image
            print(f"Warning: Preprocessing failed, using original image: {e}")
            processed_image = image_bgr
    
    # Get cached reader
    reader = _get_ocr_reader()
    
    # Convert BGR to RGB for EasyOCR
    image_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
    
    # Perform OCR with detailed results
    results = reader.readtext(image_rgb, detail=1)  # type: ignore
    
    # Combine all text with newlines (preserve structure)
    full_text = "\n".join([result[1] for result in results])
    return full_text


def detect_card_type(ocr_text: str) -> Tuple[str, float]:
    """Detect card type from OCR text.
    
    Returns:
        Tuple of (card_type, confidence_score)
        If no match, returns ("Unknown", 0.0)
    """
    ocr_text_upper = ocr_text.upper()
    
    best_match = "Unknown"
    best_score = 0.0
    
    for card_type, keywords in CARD_TYPE_KEYWORDS.items():
        score = 0.0
        matches = 0
        
        for keyword in keywords:
            keyword_upper = keyword.upper()
            if keyword_upper in ocr_text_upper:
                matches += 1
                # Give higher weight to exact matches
                if keyword_upper == ocr_text_upper[:len(keyword_upper)] or keyword_upper in ocr_text_upper:
                    score += 1.0
                else:
                    score += 0.5
        
        if matches > 0:
            # Normalize score by number of keywords
            normalized_score = score / len(keywords)
            if normalized_score > best_score:
                best_score = normalized_score
                best_match = card_type
    
    return best_match, best_score


def _find_field_value(ocr_text: str, field_label: str, threshold: float = 0.6) -> Optional[str]:
    """Extract field value from OCR text by finding the label and its value.
    
    Uses advanced regex patterns to find common patterns like:
    - "Field Name: Value"
    - "Field Name Value"
    - "Field Name\nValue"
    - "Field Name = Value"
    - "Field Name | Value"
    """
    lines = ocr_text.split('\n')
    
    # Get all variations for this field
    variations = FIELD_LABEL_VARIATIONS.get(field_label, [field_label])
    variations.append(field_label)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        var_lower = var.lower()
        if var_lower not in seen:
            seen.add(var_lower)
            unique_variations.append(var)
    variations = unique_variations
    
    for var in variations:
        var_lower = var.lower()
        var_escaped = re.escape(var)
        
        # Pattern 1: "Label: Value" or "Label : Value" or "Label:Value"
        patterns = [
            # Colon separator
            re.compile(
                rf'\b{var_escaped}\s*[:]\s*([^\n]+?)(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            # Equals separator
            re.compile(
                rf'\b{var_escaped}\s*[=]\s*([^\n]+?)(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            # Pipe separator
            re.compile(
                rf'\b{var_escaped}\s*[|]\s*([^\n]+?)(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
            # Space-separated (more specific)
            re.compile(
                rf'\b{var_escaped}\s+([A-Z0-9][A-Z0-9\s\-/.,]+?)(?:\n|$)',
                re.IGNORECASE | re.MULTILINE
            ),
        ]
        
        for pattern in patterns:
            match = pattern.search(ocr_text)
            if match:
                value = match.group(1).strip()
                # Clean up value (remove common OCR artifacts)
                value = re.sub(r'[|]{2,}', '', value)  # Remove multiple pipes
                value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                if value and len(value) > 1:  # Minimum length check
                    return value
        
        # Pattern 2: Find label on one line, value on next line(s)
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if _fuzzy_match(line, var, threshold) or var_lower in line_lower:
                # Check next 2 lines for value
                for offset in [1, 2]:
                    if i + offset < len(lines):
                        next_line = lines[i + offset].strip()
                        # Skip if next line looks like another label
                        if next_line and len(next_line) > 2:
                            # Check if it's not another label
                            is_label = False
                            for other_var in unique_variations:
                                if other_var != var and other_var.lower() in next_line.lower():
                                    is_label = True
                                    break
                            if not is_label:
                                return next_line
                
                # Check same line after label
                remaining = line[len(var):].strip() if len(line) > len(var) else ""
                if remaining:
                    # Remove separators
                    for sep in [':', '=', '|']:
                        if remaining.startswith(sep):
                            remaining = remaining[1:].strip()
                    if remaining and len(remaining) > 1:
                        return remaining
        
        # Pattern 3: Multi-line value extraction (for fields that span multiple lines)
        # Look for label followed by multiple lines of text
        for i, line in enumerate(lines):
            if _fuzzy_match(line, var, threshold) or var_lower in line.lower():
                # Collect next few lines as potential value
                value_lines = []
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and len(next_line) > 1:
                        # Stop if we hit another label
                        is_another_label = False
                        for other_var in unique_variations:
                            if other_var != var and other_var.lower() in next_line.lower():
                                is_another_label = True
                                break
                        if is_another_label:
                            break
                        value_lines.append(next_line)
                
                if value_lines:
                    combined_value = " ".join(value_lines).strip()
                    if len(combined_value) > 2:
                        return combined_value
    
    return None


def extract_fields(ocr_text: str, card_type: str) -> Dict[str, Optional[str]]:
    """Extract field values for a given card type.
    
    Returns:
        Dictionary mapping field names to extracted values (or None if not found)
    """
    fields = FIELD_TEMPLATES.get(card_type, [])
    extracted = {}
    
    for field in fields:
        value = _find_field_value(ocr_text, field)
        extracted[field] = value
    
    return extracted


def process_id_card(image_bgr, preprocess: bool = True) -> Dict:
    """Process ID card image: extract text, detect type, and extract fields.
    
    Args:
        image_bgr: Input image in BGR format
        preprocess: Whether to preprocess image before OCR
        
    Returns:
        Dictionary with:
        - ocr_text: Full OCR text
        - card_type: Detected card type
        - card_type_confidence: Confidence score (0-1)
        - fields: Dictionary of extracted fields
    """
    if not _HAVE_EASYOCR:
        raise ImportError("EasyOCR is not installed. Please install it with: pip install easyocr")
    
    # Extract OCR text with optional preprocessing
    ocr_text = _extract_text_with_ocr(image_bgr, preprocess=preprocess)
    
    # Detect card type
    card_type, confidence = detect_card_type(ocr_text)
    
    # Extract fields
    fields = extract_fields(ocr_text, card_type)
    
    return {
        "ocr_text": ocr_text,
        "card_type": card_type,
        "card_type_confidence": confidence,
        "fields": fields
    }

