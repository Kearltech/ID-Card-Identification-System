"""User verification module for manual data input and validation.

This module provides:
- User input form handling
- Field validation for each ID card type
- User input persistence
- Comparison with OCR results
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)


class UserInputForm:
    """User input form with validation for different ID card types."""
    
    # Field definitions for each card type
    CARD_TYPE_FIELDS = {
        "Ghana Card": {
            "Surname": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Firstnames": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Date of Birth": {"required": True, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Nationality": {"required": False, "type": "text", "pattern": r"^[A-Za-z\s]+$"},
            "Sex": {"required": False, "type": "select", "options": ["Male", "Female"]},
            "Height": {"required": False, "type": "text", "pattern": r"^\d+\s*(cm|ft|in)?$"},
            "Personal ID Number": {"required": True, "type": "text", "pattern": r"^GHA-\d{9}-\d$"},
            "Document Number": {"required": False, "type": "text"},
        },
        "Driver's License": {
            "Name": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Date of Birth": {"required": True, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Licence #": {"required": True, "type": "text"},
            "License #": {"required": True, "type": "text"},
            "Class of Licence": {"required": False, "type": "text"},
            "Date of Issue": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Expiry Date": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Nationality": {"required": False, "type": "text"},
        },
        "Passport": {
            "Surname": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Given Names": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Date of Birth": {"required": True, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Passport Number": {"required": True, "type": "text"},
            "Nationality": {"required": False, "type": "text"},
            "Date of Issue": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Date of Expiry": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        },
        "Voter ID": {
            "Name": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "Voter ID Number": {"required": True, "type": "text"},
            "Date of Birth": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Constituency": {"required": False, "type": "text"},
            "Polling Station": {"required": False, "type": "text"},
        },
        "NHIS Card": {
            "Name": {"required": True, "type": "text", "pattern": r"^[A-Za-z\s\-']+$"},
            "NHIS Number": {"required": True, "type": "text"},
            "Date of Birth": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            "Gender": {"required": False, "type": "select", "options": ["Male", "Female"]},
            "Expiry Date": {"required": False, "type": "date", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        },
    }
    
    def __init__(self, card_type: str = "Ghana Card"):
        """Initialize user input form.
        
        Args:
            card_type: Type of ID card
        """
        self.card_type = card_type
        self.fields = self.CARD_TYPE_FIELDS.get(card_type, {})
        self.validation_errors = {}
    
    def get_form_fields(self) -> Dict:
        """Get form fields for current card type.
        
        Returns:
            Dictionary of field definitions
        """
        return self.fields.copy()
    
    def validate_field(self, field_name: str, value: str) -> Tuple[bool, Optional[str]]:
        """Validate a single field value.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if field_name not in self.fields:
            return False, f"Unknown field: {field_name}"
        
        field_def = self.fields[field_name]
        
        # Check required
        if field_def.get("required", False) and not value:
            return False, f"{field_name} is required"
        
        if not value:
            return True, None
        
        # Get field type
        field_type = field_def.get("type", "text")
        
        # Validate by type
        if field_type == "text":
            pattern = field_def.get("pattern")
            if pattern and not re.match(pattern, value):
                return False, f"{field_name} format is invalid"
        
        elif field_type == "date":
            if not self._is_valid_date(value):
                return False, f"{field_name} must be a valid date (YYYY-MM-DD)"
        
        elif field_type == "select":
            options = field_def.get("options", [])
            if value not in options:
                return False, f"{field_name} must be one of: {', '.join(options)}"
        
        return True, None
    
    def validate_input(self, user_data: Dict[str, str]) -> Tuple[bool, Dict[str, str]]:
        """Validate all user input.
        
        Args:
            user_data: Dictionary of user-provided field values
            
        Returns:
            Tuple of (is_valid, error_dict)
        """
        errors = {}
        
        for field_name, value in user_data.items():
            is_valid, error_message = self.validate_field(field_name, value)
            if not is_valid:
                errors[field_name] = error_message
        
        # Check for required fields
        for field_name, field_def in self.fields.items():
            if field_def.get("required", False):
                if field_name not in user_data or not user_data[field_name]:
                    errors[field_name] = f"{field_name} is required"
        
        self.validation_errors = errors
        logger.info(f"User input validation: {len(errors)} errors found")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Check if string is a valid date.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if valid date
        """
        # Check format YYYY-MM-DD
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def normalize_field_value(field_name: str, value: str) -> str:
        """Normalize field value for consistent storage.
        
        Args:
            field_name: Name of the field
            value: Value to normalize
            
        Returns:
            Normalized value
        """
        if not value:
            return ""
        
        value = value.strip()
        
        # Name fields: Title case
        if field_name in ["Surname", "Firstnames", "Given Names", "Name"]:
            value = value.title()
        
        # ID fields: UPPERCASE
        elif field_name in ["Personal ID Number", "Licence #", "License #", "NHIS Number", 
                           "SSNIT Number", "TIN Number", "Passport Number"]:
            value = value.upper()
        
        # Gender/Sex fields: capitalize
        elif field_name in ["Sex", "Gender"]:
            value = value.capitalize()
        
        # Nationality: title case
        elif field_name == "Nationality":
            value = value.title()
        
        return value


class UserDataStore:
    """Store and retrieve user-provided data."""
    
    def __init__(self):
        """Initialize user data store."""
        self.data = {}
        self.timestamps = {}
    
    def save_user_input(self, session_id: str, user_data: Dict[str, str],
                       card_type: str) -> bool:
        """Save user input data.
        
        Args:
            session_id: Unique session identifier
            user_data: Dictionary of user-provided field values
            card_type: Type of ID card
            
        Returns:
            Success status
        """
        try:
            self.data[session_id] = {
                "card_type": card_type,
                "fields": user_data,
                "timestamp": datetime.now().isoformat()
            }
            self.timestamps[session_id] = datetime.now()
            logger.info(f"User input saved for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user input: {e}")
            return False
    
    def get_user_input(self, session_id: str) -> Optional[Dict]:
        """Get saved user input data.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            User data dictionary or None
        """
        return self.data.get(session_id)
    
    def clear_user_input(self, session_id: str) -> bool:
        """Clear user input for session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Success status
        """
        if session_id in self.data:
            del self.data[session_id]
            del self.timestamps[session_id]
            logger.info(f"User input cleared for session {session_id}")
            return True
        return False


def create_user_form(card_type: str) -> UserInputForm:
    """Factory function to create user input form.
    
    Args:
        card_type: Type of ID card
        
    Returns:
        UserInputForm instance
    """
    return UserInputForm(card_type)
