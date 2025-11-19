"""Data validation module for ID card extracted fields.

This module provides validation functions for common ID card fields
like dates, names, ID numbers, etc.
"""

import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List


def validate_date(date_str: str, formats: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """Validate and normalize date string.
    
    Args:
        date_str: Date string to validate
        formats: List of date formats to try (default: common formats)
        
    Returns:
        Tuple of (is_valid, normalized_date_string or None)
    """
    if not date_str or not isinstance(date_str, str):
        return False, None
    
    date_str = date_str.strip()
    
    if formats is None:
        formats = [
            "%d/%m/%Y",      # 25/12/1990
            "%d-%m-%Y",      # 25-12-1990
            "%d.%m.%Y",      # 25.12.1990
            "%Y/%m/%d",      # 1990/12/25
            "%Y-%m-%d",      # 1990-12-25
            "%d %B %Y",      # 25 December 1990
            "%d %b %Y",      # 25 Dec 1990
            "%B %d, %Y",     # December 25, 1990
            "%b %d, %Y",     # Dec 25, 1990
            "%d/%m/%y",      # 25/12/90
            "%d-%m-%y",      # 25-12-90
        ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Normalize to standard format
            normalized = dt.strftime("%Y-%m-%d")
            return True, normalized
        except ValueError:
            continue
    
    # Try regex-based extraction for dates like "25 DEC 1990"
    date_patterns = [
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
        r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})',  # DD MONTH YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                if len(match.groups()) == 3:
                    parts = match.groups()
                    # Try to parse
                    if len(parts[2]) == 4:  # YYYY format
                        if len(parts[0]) <= 2:  # DD/MM/YYYY
                            dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        else:  # YYYY/MM/DD
                            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                        normalized = dt.strftime("%Y-%m-%d")
                        return True, normalized
            except (ValueError, IndexError):
                continue
    
    return False, None


def validate_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate and clean name string.
    
    Args:
        name: Name string to validate
        
    Returns:
        Tuple of (is_valid, cleaned_name or None)
    """
    if not name or not isinstance(name, str):
        return False, None
    
    # Remove extra whitespace
    cleaned = " ".join(name.split())
    
    # Check if name contains only letters, spaces, hyphens, and apostrophes
    if not re.match(r'^[A-Za-z\s\-\']+$', cleaned):
        # Try to extract name from mixed text
        name_match = re.search(r'([A-Za-z\s\-\']{2,})', cleaned)
        if name_match:
            cleaned = name_match.group(1).strip()
        else:
            return False, None
    
    # Check minimum length
    if len(cleaned) < 2:
        return False, None
    
    # Capitalize properly
    cleaned = cleaned.title()
    
    return True, cleaned


def validate_id_number(id_str: str, pattern: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate ID number format.
    
    Args:
        id_str: ID number string to validate
        pattern: Optional regex pattern for specific ID format
        
    Returns:
        Tuple of (is_valid, cleaned_id_number or None)
    """
    if not id_str or not isinstance(id_str, str):
        return False, None
    
    # Remove whitespace and common separators
    cleaned = re.sub(r'[\s\-\.]', '', id_str.upper())
    
    if pattern:
        if re.match(pattern, cleaned):
            return True, cleaned
        return False, None
    
    # Default: alphanumeric, at least 6 characters
    if re.match(r'^[A-Z0-9]{6,}$', cleaned):
        return True, cleaned
    
    return False, None


def validate_ghana_card_number(id_str: str) -> Tuple[bool, Optional[str]]:
    """Validate Ghana Card number format (GHA-XXXXXXXXX-X).
    
    Args:
        id_str: Ghana Card number string
        
    Returns:
        Tuple of (is_valid, cleaned_id_number or None)
    """
    if not id_str or not isinstance(id_str, str):
        return False, None
    
    # Remove whitespace
    cleaned = id_str.strip().upper()
    
    # Pattern: GHA-XXXXXXXXX-X (where X is alphanumeric)
    pattern = r'^GHA-?[A-Z0-9]{9}-?[A-Z0-9]$'
    if re.match(pattern, cleaned):
        # Normalize format
        cleaned = re.sub(r'[-\s]', '', cleaned)
        normalized = f"{cleaned[:3]}-{cleaned[3:12]}-{cleaned[12:]}"
        return True, normalized
    
    return False, None


def validate_license_number(id_str: str) -> Tuple[bool, Optional[str]]:
    """Validate driver's license number format.
    
    Args:
        id_str: License number string
        
    Returns:
        Tuple of (is_valid, cleaned_license_number or None)
    """
    if not id_str or not isinstance(id_str, str):
        return False, None
    
    cleaned = re.sub(r'[\s\-\.]', '', id_str.upper())
    
    # Common patterns: alphanumeric, 6-15 characters
    if re.match(r'^[A-Z0-9]{6,15}$', cleaned):
        return True, cleaned
    
    return False, None


def validate_passport_number(id_str: str) -> Tuple[bool, Optional[str]]:
    """Validate passport number format.
    
    Args:
        id_str: Passport number string
        
    Returns:
        Tuple of (is_valid, cleaned_passport_number or None)
    """
    if not id_str or not isinstance(id_str, str):
        return False, None
    
    cleaned = re.sub(r'[\s\-\.]', '', id_str.upper())
    
    # Passport numbers are typically alphanumeric, 6-12 characters
    if re.match(r'^[A-Z0-9]{6,12}$', cleaned):
        return True, cleaned
    
    return False, None


def validate_nationality(nationality: str) -> Tuple[bool, Optional[str]]:
    """Validate and normalize nationality string.
    
    Args:
        nationality: Nationality string
        
    Returns:
        Tuple of (is_valid, normalized_nationality or None)
    """
    if not nationality or not isinstance(nationality, str):
        return False, None
    
    cleaned = " ".join(nationality.split()).title()
    
    # Common nationalities
    valid_nationalities = [
        "Ghanaian", "Ghana", "Nigerian", "Nigeria", "Togolese", "Togo",
        "Ivorian", "Ivory Coast", "Burkinabe", "Burkina Faso",
        "Malian", "Mali", "Senegalese", "Senegal"
    ]
    
    # Check if it matches a known nationality
    for valid in valid_nationalities:
        if valid.lower() in cleaned.lower() or cleaned.lower() in valid.lower():
            return True, valid
    
    # If it looks like a country name (letters only, reasonable length)
    if re.match(r'^[A-Za-z\s]{3,30}$', cleaned) and len(cleaned) >= 3:
        return True, cleaned
    
    return False, None


def validate_gender(gender: str) -> Tuple[bool, Optional[str]]:
    """Validate and normalize gender/sex field.
    
    Args:
        gender: Gender string
        
    Returns:
        Tuple of (is_valid, normalized_gender or None)
    """
    if not gender or not isinstance(gender, str):
        return False, None
    
    cleaned = gender.strip().upper()
    
    # Map variations to standard values
    gender_map = {
        "M": "Male",
        "MALE": "Male",
        "F": "Female",
        "FEMALE": "Female",
        "MALE": "Male",
        "FEMALE": "Female",
    }
    
    if cleaned in gender_map:
        return True, gender_map[cleaned]
    
    # Check if it contains gender keywords
    if any(keyword in cleaned for keyword in ["MALE", "M", "MAN"]):
        return True, "Male"
    elif any(keyword in cleaned for keyword in ["FEMALE", "F", "WOMAN"]):
        return True, "Female"
    
    return False, None


def validate_height(height_str: str) -> Tuple[bool, Optional[str]]:
    """Validate height field (e.g., "175 cm", "5'10"").
    
    Args:
        height_str: Height string
        
    Returns:
        Tuple of (is_valid, normalized_height or None)
    """
    if not height_str or not isinstance(height_str, str):
        return False, None
    
    cleaned = height_str.strip().upper()
    
    # Pattern for cm: "175 cm" or "175cm"
    cm_match = re.search(r'(\d{2,3})\s*CM', cleaned)
    if cm_match:
        cm_value = int(cm_match.group(1))
        if 50 <= cm_value <= 250:  # Reasonable height range
            return True, f"{cm_value} cm"
    
    # Pattern for feet/inches: "5'10"" or "5 10"
    feet_match = re.search(r"(\d{1,2})['\s](\d{1,2})", cleaned)
    if feet_match:
        feet = int(feet_match.group(1))
        inches = int(feet_match.group(2))
        if 3 <= feet <= 8 and 0 <= inches <= 11:
            total_cm = int((feet * 30.48) + (inches * 2.54))
            return True, f"{total_cm} cm"
    
    # Just numbers (assume cm)
    num_match = re.search(r'(\d{2,3})', cleaned)
    if num_match:
        cm_value = int(num_match.group(1))
        if 50 <= cm_value <= 250:
            return True, f"{cm_value} cm"
    
    return False, None


def validate_field(field_name: str, field_value: str, card_type: str = "Unknown") -> Dict:
    """Validate a single field based on its name and card type.
    
    Args:
        field_name: Name of the field
        field_value: Value to validate
        card_type: Type of ID card
        
    Returns:
        Dictionary with validation results:
        {
            "is_valid": bool,
            "normalized_value": str or None,
            "error": str or None
        }
    """
    if not field_value or not isinstance(field_value, str):
        return {
            "is_valid": False,
            "normalized_value": None,
            "error": "Empty or invalid field value"
        }
    
    field_lower = field_name.lower()
    
    # Date fields
    if any(keyword in field_lower for keyword in ["date", "dob", "birth", "issue", "expiry", "expires"]):
        is_valid, normalized = validate_date(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid date format"
        }
    
    # Name fields
    if any(keyword in field_lower for keyword in ["name", "surname", "firstname", "given"]):
        is_valid, normalized = validate_name(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid name format"
        }
    
    # ID number fields
    if "ghana card" in card_type.lower() and "id" in field_lower:
        is_valid, normalized = validate_ghana_card_number(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid Ghana Card number format"
        }
    
    if "licence" in field_lower or "license" in field_lower:
        is_valid, normalized = validate_license_number(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid license number format"
        }
    
    if "passport" in field_lower:
        is_valid, normalized = validate_passport_number(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid passport number format"
        }
    
    if "id number" in field_lower or "number" in field_lower:
        is_valid, normalized = validate_id_number(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid ID number format"
        }
    
    # Nationality
    if "nationality" in field_lower:
        is_valid, normalized = validate_nationality(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid nationality"
        }
    
    # Gender/Sex
    if "sex" in field_lower or "gender" in field_lower:
        is_valid, normalized = validate_gender(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid gender value"
        }
    
    # Height
    if "height" in field_lower:
        is_valid, normalized = validate_height(field_value)
        return {
            "is_valid": is_valid,
            "normalized_value": normalized,
            "error": None if is_valid else "Invalid height format"
        }
    
    # Default: just clean the value
    cleaned = " ".join(field_value.split())
    return {
        "is_valid": True,
        "normalized_value": cleaned if cleaned else None,
        "error": None
    }


def validate_all_fields(fields: Dict[str, Optional[str]], card_type: str = "Unknown") -> Dict:
    """Validate all extracted fields.
    
    Args:
        fields: Dictionary of field names to values
        card_type: Type of ID card
        
    Returns:
        Dictionary with validation results:
        {
            "validated_fields": Dict[str, str],  # Only valid, normalized fields
            "invalid_fields": Dict[str, str],    # Fields with errors
            "validation_summary": Dict[str, Dict]  # Full validation details
        }
    """
    validated = {}
    invalid = {}
    summary = {}
    
    for field_name, field_value in fields.items():
        if field_value is None:
            continue
        
        result = validate_field(field_name, field_value, card_type)
        summary[field_name] = result
        
        if result["is_valid"] and result["normalized_value"]:
            validated[field_name] = result["normalized_value"]
        else:
            invalid[field_name] = result.get("error", "Validation failed")
    
    return {
        "validated_fields": validated,
        "invalid_fields": invalid,
        "validation_summary": summary
    }

