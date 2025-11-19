"""Configuration management for the ID card extraction system.

This module provides centralized configuration handling from environment variables
and sensible defaults.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DIRECTORIES
# ============================================================================
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Create directories
OUTPUTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)

logger = logging.getLogger(__name__)
logger.info(f"✓ Logging configured at {LOG_LEVEL} level")

# ============================================================================
# OCR SETTINGS
# ============================================================================
OCR_ENGINE = os.getenv("OCR_ENGINE", "hybrid").lower()
if OCR_ENGINE not in ["easyocr", "paddleocr", "hybrid"]:
    logger.warning(f"Invalid OCR engine: {OCR_ENGINE}, falling back to 'hybrid'")
    OCR_ENGINE = "hybrid"

USE_GPU = os.getenv("USE_GPU", "false").lower() in ["true", "1", "yes"]
OCR_CACHE_DIR = os.getenv("OCR_CACHE_DIR", str(CACHE_DIR / "ocr"))
OCR_PREPROCESS = os.getenv("OCR_PREPROCESS", "true").lower() in ["true", "1", "yes"]

os.makedirs(OCR_CACHE_DIR, exist_ok=True)

logger.info(f"✓ OCR configured: engine={OCR_ENGINE}, gpu={USE_GPU}, preprocess={OCR_PREPROCESS}")

# ============================================================================
# STORAGE SETTINGS
# ============================================================================
DB_PATH = os.getenv("DB_PATH", str(OUTPUTS_DIR / "id_cards.db"))
CSV_PATH = os.getenv("CSV_PATH", str(OUTPUTS_DIR / "id_cards.csv"))
PORTRAIT_DIR = os.getenv("PORTRAIT_DIR", str(OUTPUTS_DIR / "portraits"))
DATA_DIR = os.getenv("DATA_DIR", str(OUTPUTS_DIR / "data"))

# Create storage directories
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(PORTRAIT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logger.info(f"✓ Storage configured: db={DB_PATH}, csv={CSV_PATH}")

# ============================================================================
# FILE UPLOAD SETTINGS
# ============================================================================
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_FORMATS = tuple(
    fmt.strip().lower() 
    for fmt in os.getenv("ALLOWED_FORMATS", "jpg,jpeg,png,webp").split(",")
)

STRIP_EXIF = os.getenv("STRIP_EXIF", "true").lower() in ["true", "1", "yes"]

logger.info(f"✓ File upload configured: max_size={MAX_FILE_SIZE_MB}MB, formats={ALLOWED_FORMATS}")

# ============================================================================
# FACE DETECTION SETTINGS
# ============================================================================
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.6"))
CROP_MARGIN_PERCENT = int(os.getenv("CROP_MARGIN_PERCENT", "10"))
MAX_FACES = int(os.getenv("MAX_FACES", "10"))

# Validate ranges
MIN_CONFIDENCE = max(0.0, min(1.0, MIN_CONFIDENCE))
CROP_MARGIN_PERCENT = max(0, min(40, CROP_MARGIN_PERCENT))
MAX_FACES = max(1, MAX_FACES)

logger.info(f"✓ Face detection configured: confidence={MIN_CONFIDENCE}, margin={CROP_MARGIN_PERCENT}%")

# ============================================================================
# COMPARISON SETTINGS
# ============================================================================
THRESHOLD_VALID = float(os.getenv("THRESHOLD_VALID", "0.95"))
THRESHOLD_PARTIAL = float(os.getenv("THRESHOLD_PARTIAL", "0.70"))

# Validate thresholds
THRESHOLD_VALID = max(0.0, min(1.0, THRESHOLD_VALID))
THRESHOLD_PARTIAL = max(0.0, min(1.0, THRESHOLD_PARTIAL))

logger.info(f"✓ Comparison configured: valid_threshold={THRESHOLD_VALID}, partial_threshold={THRESHOLD_PARTIAL}")

# ============================================================================
# DEVELOPMENT SETTINGS
# ============================================================================
DEBUG = os.getenv("DEBUG", "false").lower() in ["true", "1", "yes"]
SHOW_OCR_TEXT = os.getenv("SHOW_OCR_TEXT", "false").lower() in ["true", "1", "yes"]
SHOW_DEBUG_METRICS = os.getenv("SHOW_DEBUG_METRICS", "false").lower() in ["true", "1", "yes"]

if DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.info("✓ Debug mode enabled")

# ============================================================================
# FIELD IMPORTANCE WEIGHTS (for comparison scoring)
# ============================================================================
FIELD_IMPORTANCE = {
    "Surname": 0.15,
    "Firstnames": 0.15,
    "Name": 0.15,
    "Date of Birth": 0.15,
    "Personal ID Number": 0.20,
    "Passport Number": 0.20,
    "Licence #": 0.20,
    "License #": 0.20,
    "Document Number": 0.15,
    "Nationality": 0.10,
    "Sex": 0.08,
    "Gender": 0.08,
    "Expiry Date": 0.10,
    "Date of Expiry": 0.10,
    "Height": 0.05,
}

# ============================================================================
# CARD TYPE KEYWORDS
# ============================================================================
CARD_TYPE_KEYWORDS = {
    "Ghana Card": ["ECOWAS IDENTITY CARD", "NATIONAL IDENTIFICATION CARD", "GHANA CARD"],
    "Driver's License": ["DRIVER LICENCE", "DRIVER LICENSE", "LICENCE #", "LICENSE #"],
    "Passport": ["PASSPORT", "REPUBLIC OF GHANA", "PASSPORT NO"],
    "Voter ID": ["VOTER IDENTITY CARD", "ELECTORAL COMMISSION", "VOTER ID"],
    "NHIS Card": ["NATIONAL HEALTH INSURANCE", "NHIS", "HEALTH INSURANCE"],
    "SSNIT Card": ["SOCIAL SECURITY", "SSNIT"],
    "Birth Certificate": ["BIRTH CERTIFICATE", "CERTIFICATE OF BIRTH"],
    "TIN Document": ["TAX IDENTIFICATION NUMBER", "TIN"],
}

# ============================================================================
# VALIDATION PATTERNS
# ============================================================================
VALIDATION_PATTERNS = {
    "ghana_card_id": r"^GHA-\d{9}-\d$",
    "date": r"^\d{4}-\d{2}-\d{2}$",
    "name": r"^[A-Za-z\s\-']+$",
    "phone": r"^\+?[\d\s\-\(\)]{7,15}$",
}

# ============================================================================
# SUPPORTED CARD TYPES
# ============================================================================
SUPPORTED_CARD_TYPES = [
    "Ghana Card",
    "Driver's License",
    "Passport",
    "Voter ID",
    "NHIS Card",
    "SSNIT Card",
    "Birth Certificate",
    "TIN Document",
]

# ============================================================================
# API CONFIGURATION (for future REST API)
# ============================================================================
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# ============================================================================
# OPTIONAL LLM VALIDATION (Gemini)
# ============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_ENDPOINT = os.getenv("GEMINI_ENDPOINT", "https://api.example.com/v1/gemini")
# When GEMINI_DRY_RUN is true we won't perform network calls; useful for local dev
GEMINI_DRY_RUN = os.getenv("GEMINI_DRY_RUN", "true").lower() in ["1", "true", "yes"]

logger.info(f"✓ Gemini config: enabled={'yes' if GEMINI_API_KEY else 'no'}, dry_run={GEMINI_DRY_RUN}")

# ============================================================================
# SUMMARY
# ============================================================================
def print_config_summary():
    """Print configuration summary."""
    logger.info("=" * 80)
    logger.info("CONFIGURATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"OCR Engine: {OCR_ENGINE}")
    logger.info(f"GPU Support: {USE_GPU}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Max File Size: {MAX_FILE_SIZE_MB}MB")
    logger.info(f"Debug Mode: {DEBUG}")
    logger.info("=" * 80)


if __name__ == "__main__":
    print_config_summary()
