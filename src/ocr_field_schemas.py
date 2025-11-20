"""
Label-Guided OCR Field Schemas for ID Cards

Defines field schemas for different ID card types with label variants.
Used for structured field extraction and validation.
"""

# Complete field schemas for all supported ID card types
ID_CARD_SCHEMAS = {
    "ghana_card": {
        "Surname": ["Surname", "Nom", "SURNAME"],
        "Firstnames": ["Firstnames", "Prenoms", "First Names", "Given Names", "FIRSTNAMES"],
        "Date of Birth": ["Date of Birth", "Naissance", "DOB", "D.O.B", "DATE OF BIRTH"],
        "Sex": ["Sex", "Sexe", "Gender", "M/F", "SEX"],
        "Nationality": ["Nationality", "Nationalité", "NATIONALITY"],
        "ID Number": ["Personal ID Number", "GHA", "ID Number", "Personal ID", "ID NO"],
        "Height": ["Height", "Taille", "HEIGHT"],
        "Document Number": ["Document Number", "Numero du document", "DOCUMENT NUMBER"],
        "Date of Issuance": ["Date of Issuance", "Date d'emission", "Issued", "Issue Date", "DATE OF ISSUANCE"],
        "Date of Expiry": ["Date of Expiry", "Date d'expiration", "Expires", "Expiry Date", "DATE OF EXPIRY"],
        "Religion": ["Religion", "RELIGION"],
        "Occupation": ["Occupation", "OCCUPATION"],
        "Signature": ["Signature", "SIGNATURE"]
    },

    "passport": {
        "Surname": ["Surname", "Nom", "Last Name", "SURNAME"],
        "Given Names": ["Given Names", "Prenoms", "First Name", "Name", "GIVEN NAMES"],
        "Passport Number": ["Passport No", "Passport Number", "Document No", "No", "PASSPORT NUMBER"],
        "Nationality": ["Nationality", "Nationalité", "NATIONALITY"],
        "Sex": ["Sex", "Sexe", "Gender", "M/F", "SEX"],
        "Date of Birth": ["Date of Birth", "Naissance", "DOB", "D.O.B", "DATE OF BIRTH"],
        "Place of Birth": ["Place of Birth", "Lieu de Naissance", "PLACE OF BIRTH"],
        "Date of Issue": ["Date of Issue", "Date d'emission", "Issued", "Issue Date", "DATE OF ISSUE"],
        "Date of Expiry": ["Date of Expiry", "Date d'expiration", "Expires", "Expiry Date", "DATE OF EXPIRY"],
        "Authority": ["Authority", "Authorité", "Issued by", "AUTHORITY"],
        "MRZ": ["MRZ", "Machine Readable Zone", "MRZ Line"]
    },

    "voters_id": {
        "Full Name": ["Name", "Full Name", "Voter Name", "FULL NAME"],
        "Voter ID": ["Voter ID", "Voter No", "Voter Number", "ID Number", "VOTER ID"],
        "Sex": ["Sex", "Sexe", "Gender", "M/F", "SEX"],
        "Date of Birth": ["Date of Birth", "DOB", "D.O.B", "Naissance", "DATE OF BIRTH"],
        "Polling Station": ["Polling Station", "Station", "Voting Station", "POLLING STATION"],
        "Region": ["Region", "REGION"],
        "District": ["District", "DISTRICT"],
        "Constituency": ["Constituency", "CONSTITUENCY"],
        "Date of Issue": ["Date of Issue", "Issued", "Issue Date", "DATE OF ISSUE"],
        "Date of Expiry": ["Date of Expiry", "Expires", "Expiry Date", "DATE OF EXPIRY"]
    },

    "drivers_license": {
        "License Number": ["License No", "License Number", "Driver License No", "DL Number", "LICENSE NUMBER"],
        "Name": ["Name", "Surname", "Driver Name", "NAME"],
        "Date of Birth": ["DOB", "Date of Birth", "Date of Birth", "D.O.B", "DATE OF BIRTH"],
        "Address": ["Address", "Residence", "ADDRESS"],
        "Expiration": ["Expiry", "Expires", "Expiration Date", "Valid Until", "EXPIRATION"],
        "Class": ["Class", "Category", "License Class", "CLASS"],
        "Issue Date": ["Issue Date", "Issued", "Date of Issue", "ISSUE DATE"],
        "Sex": ["Sex", "Gender", "M/F", "SEX"],
        "Restrictions": ["Restrictions", "Endorsements", "RESTRICTIONS"]
    }
}

# Field metadata for each ID type
ID_FIELD_METADATA = {
    "ghana_card": {
        "required": ["Surname", "Firstnames", "Date of Birth", "Sex", "ID Number"],
        "optional": ["Height", "Nationality", "Religion", "Occupation", "Document Number", "Date of Issuance", "Date of Expiry"],
        "searchable": ["ID Number", "Surname", "Firstnames", "Date of Birth"]
    },
    "passport": {
        "required": ["Surname", "Given Names", "Passport Number", "Nationality", "Date of Birth"],
        "optional": ["Sex", "Place of Birth", "Date of Issue", "Date of Expiry", "Authority", "MRZ"],
        "searchable": ["Passport Number", "Surname", "Given Names", "Date of Birth"]
    },
    "voters_id": {
        "required": ["Full Name", "Voter ID", "Sex", "Date of Birth"],
        "optional": ["Polling Station", "Region", "District", "Constituency", "Date of Issue", "Date of Expiry"],
        "searchable": ["Voter ID", "Full Name", "Date of Birth"]
    },
    "drivers_license": {
        "required": ["License Number", "Name", "Date of Birth"],
        "optional": ["Address", "Expiration", "Class", "Issue Date", "Sex", "Restrictions"],
        "searchable": ["License Number", "Name", "Date of Birth"]
    }
}

# Common date formats found on ID cards
DATE_FORMATS = [
    r"\d{1,2}/\d{1,2}/\d{2,4}",  # MM/DD/YYYY or DD/MM/YYYY
    r"\d{1,2}-\d{1,2}-\d{2,4}",  # MM-DD-YYYY or DD-MM-YYYY
    r"\d{4}/\d{1,2}/\d{1,2}",    # YYYY/MM/DD
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}",  # 01 January 2020
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4}",
]

# ID number patterns by type
ID_NUMBER_PATTERNS = {
    "ghana_card": r"GHA-?\d{9}-?\d",
    "passport": r"[A-Z]{1,2}\d{6,8}",
    "voters_id": r"\d{10,12}",
    "drivers_license": r"[A-Z0-9]{5,10}"
}

# Field data types for validation
FIELD_DATA_TYPES = {
    "Surname": "text",
    "Firstnames": "text",
    "Given Names": "text",
    "Full Name": "text",
    "Date of Birth": "date",
    "Sex": "choice",  # M, F, Male, Female
    "Nationality": "text",
    "ID Number": "id_number",
    "Passport Number": "id_number",
    "Voter ID": "id_number",
    "License Number": "id_number",
    "Height": "number",
    "Document Number": "id_number",
    "Date of Issuance": "date",
    "Date of Issue": "date",
    "Date of Expiry": "date",
    "Expiration": "date",
    "Religion": "text",
    "Occupation": "text",
    "Signature": "blob",
    "Address": "text",
    "Class": "text",
    "Region": "text",
    "District": "text",
    "Constituency": "text",
    "Polling Station": "text",
    "Authority": "text",
    "Place of Birth": "text",
    "MRZ": "text",
    "Restrictions": "text"
}


def get_schema(id_type: str) -> dict:
    """
    Get the field schema for a specific ID card type.
    
    Args:
        id_type: Type of ID card (e.g., 'ghana_card', 'passport')
    
    Returns:
        Dictionary with field names and label variants
    """
    return ID_CARD_SCHEMAS.get(id_type.lower(), {})


def get_required_fields(id_type: str) -> list:
    """Get list of required fields for an ID type."""
    return ID_FIELD_METADATA.get(id_type.lower(), {}).get("required", [])


def get_optional_fields(id_type: str) -> list:
    """Get list of optional fields for an ID type."""
    return ID_FIELD_METADATA.get(id_type.lower(), {}).get("optional", [])


def get_all_fields(id_type: str) -> list:
    """Get all fields (required + optional) for an ID type."""
    required = get_required_fields(id_type)
    optional = get_optional_fields(id_type)
    return required + optional


def get_searchable_fields(id_type: str) -> list:
    """Get searchable fields for an ID type."""
    return ID_FIELD_METADATA.get(id_type.lower(), {}).get("searchable", [])


def get_field_data_type(field_name: str) -> str:
    """Get the data type for a field."""
    return FIELD_DATA_TYPES.get(field_name, "text")


def validate_field_value(field_name: str, value: any) -> tuple:
    """
    Validate a field value based on its data type.
    
    Args:
        field_name: Name of the field
        value: Value to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None or value == "":
        return True, None
    
    field_type = get_field_data_type(field_name)
    
    if field_type == "date":
        import re
        for pattern in DATE_FORMATS:
            if re.search(pattern, str(value)):
                return True, None
        return False, f"Invalid date format: {value}"
    
    elif field_type == "choice":
        valid_values = ["M", "F", "Male", "Female", "m", "f"]
        if str(value) in valid_values:
            return True, None
        return False, f"Sex must be M or F, got: {value}"
    
    elif field_type == "number":
        try:
            float(value)
            return True, None
        except (ValueError, TypeError):
            return False, f"Invalid number: {value}"
    
    elif field_type == "id_number":
        # Basic validation - at least 3 characters, alphanumeric
        if len(str(value)) >= 3 and any(c.isalnum() for c in str(value)):
            return True, None
        return False, f"Invalid ID number format: {value}"
    
    # Default: text is always valid
    return True, None


def get_display_name(id_type: str) -> str:
    """Get human-readable display name for ID type."""
    display_names = {
        "ghana_card": "Ghana Card",
        "passport": "Passport",
        "voters_id": "Voter ID",
        "drivers_license": "Driver's License"
    }
    return display_names.get(id_type.lower(), id_type)
