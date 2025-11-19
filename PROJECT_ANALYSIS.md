# ID Card Image Extraction Project - Core Functionality Analysis

## Executive Summary
This is a **Streamlit-based ID card portrait extraction and OCR system** designed to extract portrait photos and text data from various types of ID cards (Ghana Cards, Passports, Driver's Licenses, etc.) without requiring model training. The project uses MediaPipe and OpenCV for face detection combined with multiple OCR engines (EasyOCR, PaddleOCR) for text extraction.

---

## Project Architecture Overview

```
id_card_image_extracted-main/
├── app.py                          # Main Streamlit entry point
├── src/
│   ├── config.py                   # Centralized configuration management
│   ├── detector.py                 # Basic OpenCV face detection
│   ├── ocr_gemini.py              # Gemini API OCR client (optional)
│   ├── app.py, app_enhanced.py,   # Alternative app implementations
│   ├── db/
│   │   └── models.py              # Database models
│   ├── face_extractor/            # Core extraction module
│   │   ├── __init__.py            # Module exports
│   │   ├── detector.py            # Advanced face detection (MediaPipe/DNN/Haar)
│   │   ├── text_extractor.py      # OCR and field extraction
│   │   ├── advanced_ocr.py        # Multi-engine OCR backend
│   │   ├── comparison_engine.py   # Validation & comparison logic
│   │   ├── validator.py           # Field validation rules
│   │   ├── data_storage.py        # Database & CSV storage
│   │   ├── image_preprocessor.py  # Image enhancement
│   │   ├── postprocessing.py      # Result post-processing
│   │   ├── user_verification.py   # Manual verification forms
│   │   └── gemini_client.py       # Gemini API integration
│   ├── services/
│   │   ├── face_matcher.py        # Face matching utilities
│   │   └── ocr_extractor.py       # OCR wrapper
│   └── utils/
│       └── bootstrap.py           # Runtime package installation
├── tests/
│   └── test_suite.py              # Unit tests
└── requirements.txt               # Python dependencies
```

---

## Core Functionality

### 1. **Face Detection & Portrait Extraction**

#### Primary Implementation: `src/face_extractor/detector.py`

**Detection Hierarchy:**
1. **MediaPipe** (Preferred) - Fast, accurate frontal face detection
2. **DNN Face Detector** - Alternative SSD-based model
3. **OpenCV Haar Cascade** (Fallback) - Always available, no external models

```python
def detect_faces(image_bgr, min_confidence=0.6, use_dnn=False)
    # Returns list of ((x1, y1, x2, y2), confidence_score) tuples
```

**Key Features:**
- Multi-detector fallback system ensures robustness
- Confidence scoring and filtering
- Handles multiple faces in a single image
- Adaptive parameters based on image size
- CLAHE (Contrast Limited Adaptive Histogram Equalization) enhancement for Haar cascade

**Cropping:**
```python
def crop_regions(image_bgr, boxes, margin_percent=10)
    # Extracts face regions with configurable margins
    # Performs clipping to ensure coordinates stay within bounds
```

#### Secondary Implementation: `src/detector.py` (Simpler)
- Uses OpenCV Haar Cascade only
- Selects largest detected face
- Adds fixed 15% margin around detected face

---

### 2. **Optical Character Recognition (OCR)**

#### Multi-Engine Architecture: `src/face_extractor/advanced_ocr.py`

**Supported Engines:**
- **EasyOCR** - Lightweight, easy to use
- **PaddleOCR** - High accuracy, optimized for ID cards
- **Hybrid** - Combines results from multiple engines for improved accuracy

**Capabilities:**
```python
class AdvancedOCREngine:
    def detect_text_orientation(image_bgr) → (rotation_angle, rotated_image)
    def extract_text(image_bgr) → List[OCRResult]
    def aggregate_results(results_from_multiple_engines) → best_result
```

**Key Features:**
- Automatic text orientation detection and correction
- Image preprocessing (deskewing, contrast enhancement)
- Confidence scoring per detected text region
- Caching for repeated requests
- GPU acceleration support (optional)

---

### 3. **Text Field Extraction & Parsing**

#### Module: `src/face_extractor/text_extractor.py`

**Card Type Detection:**
- Identifies card type by keyword matching on OCR text
- Supported card types:
  - Ghana Card
  - Driver's License
  - Passport
  - Voter ID
  - NHIS Card
  - SSNIT Card
  - Birth Certificate
  - TIN Document

```python
def detect_card_type(raw_text: str) → (card_type: str, confidence: float)
    # Matches against CARD_TYPE_KEYWORDS dictionary
```

**Field Extraction:**
```python
def extract_fields(raw_text: str, card_type: str) → Dict[str, str]
    # Uses FIELD_TEMPLATES to identify expected fields
    # Performs fuzzy matching of field labels
    # Extracts corresponding values
```

**Fuzzy Matching for Field Labels:**
- Handles OCR errors and variations (e.g., "Licence #" vs "License #")
- Uses RapidFuzz library for string similarity scoring
- Fallback to difflib if RapidFuzz unavailable

---

### 4. **Data Validation & Verification**

#### Validator Module: `src/face_extractor/validator.py`

**Field Validation Functions:**

| Function | Purpose |
|----------|---------|
| `validate_date()` | Validates and normalizes dates (multiple format support) |
| `validate_name()` | Validates name format (letters, spaces, hyphens, apostrophes) |
| `validate_id_number()` | Validates ID/document numbers (card-type specific) |
| `validate_nationality()` | Checks against known country codes |
| `validate_phone()` | Validates phone number format |
| `validate_gender()` | Ensures gender field is M/F/Other |
| `validate_height()` | Validates height in cm or feet/inches |

#### Comparison Engine: `src/face_extractor/comparison_engine.py`

```python
class ComparisonResult:
    VALID = "✅ Valid Match"
    PARTIAL = "⚠️ Partial Match"
    INVALID = "❌ Invalid/Mismatch"
    MISSING_OCR = "⚠️ Missing in OCR"
    MISSING_USER = "⚠️ Missing in User Input"

def compare_extractions(ocr_data: Dict, user_input: Dict) → ComparisonReport
    # Field-by-field comparison
    # Similarity scoring (0.0-1.0)
    # Status determination based on configurable thresholds
    # Detailed mismatch reporting
```

**Comparison Thresholds:**
- **Valid Match**: ≥95% similarity
- **Partial Match**: 70-94% similarity
- **Invalid/Mismatch**: <70% similarity

---

### 5. **Data Storage**

#### Module: `src/face_extractor/data_storage.py`

**Dual Storage System:**

**A) SQLite Database** (`outputs/id_cards.db`)
```sql
CREATE TABLE id_cards (
    id INTEGER PRIMARY KEY,
    extraction_timestamp TEXT,
    card_type TEXT,
    card_type_confidence REAL,
    -- Extracted fields (50+ columns)
    name, surname, firstnames, date_of_birth, nationality, sex, etc.
    -- OCR confidence scores
    ocr_confidence REAL,
    -- User verification data
    user_verified BOOLEAN,
    verification_timestamp TEXT,
    -- Portrait reference
    portrait_path TEXT
)
```

**B) CSV Export** (`outputs/id_cards.csv`)
- Flattened view of database records
- Easy import into spreadsheets/analysis tools

**Storage API:**
```python
class IDCardStorage:
    def save_record(record_dict) → record_id
    def get_record(record_id) → record_dict
    def query_records(filters) → List[record_dict]
    def export_to_csv() → None
    def get_statistics() → summary_stats
```

---

### 6. **Configuration Management**

#### Module: `src/config.py`

**Environment Variable Support:**
```python
# OCR Settings
OCR_ENGINE = "hybrid"          # Options: easyocr, paddleocr, hybrid
USE_GPU = false                # Enable GPU acceleration
OCR_CACHE_DIR = ".cache/ocr"   # Cache directory

# Face Detection
MIN_CONFIDENCE = 0.6           # Detection confidence threshold
CROP_MARGIN_PERCENT = 10       # Extra pixels around face box
MAX_FACES = 10                 # Maximum faces to extract per image

# Storage
DB_PATH = "outputs/id_cards.db"
CSV_PATH = "outputs/id_cards.csv"
PORTRAIT_DIR = "outputs/portraits"

# File Upload
MAX_FILE_SIZE_MB = 10
ALLOWED_FORMATS = "jpg,jpeg,png,webp"
STRIP_EXIF = true              # Remove location/metadata

# Comparison Thresholds
THRESHOLD_VALID = 0.95         # Similarity for valid match
THRESHOLD_PARTIAL = 0.70       # Similarity for partial match

# Development
DEBUG = false
SHOW_OCR_TEXT = false
SHOW_DEBUG_METRICS = false

# Gemini API (Optional)
GEMINI_API_KEY = ""
GEMINI_DRY_RUN = true          # Disable network calls for local dev
```

---

### 7. **Streamlit Web Interface**

#### Main App: `app.py` (Root) / `src/app.py`

**User Workflow:**
1. **Upload Image** - Accept JPG/PNG/WEBP
2. **Configure Settings** (Sidebar)
   - Min confidence slider
   - Crop margin %
   - Return: largest only vs all faces
   - Use Gemini API toggle
3. **Portrait Extraction** - Displays cropped portrait
4. **OCR Processing** - Extracts text fields
5. **Manual Verification** - User reviews and corrects fields
6. **Comparison** - Shows extracted vs user input with match indicators
7. **Save Record** - Stores to database/CSV
8. **Download** - Portrait JPEG or all as ZIP

**UI Features:**
- Two-column form layout for field entry
- Color-coded comparison (green=match, red=mismatch)
- Emoji indicators (✅❌)
- Progress spinners during processing
- File download buttons

---

## Key Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `streamlit` | Web UI framework | ≥1.28.0 |
| `opencv-python-headless` | Image processing & Haar cascades | ≥4.8.1 |
| `mediapipe` | Advanced face detection | ≥0.10.0 |
| `easyocr` | OCR engine | ≥1.7.0 |
| `paddleocr` | Alternative OCR | ≥2.7.0 |
| `numpy` | Numerical computing | ≥1.23.0 |
| `Pillow` | Image format support | ≥10.0.0 |
| `rapidfuzz` | Fuzzy string matching | ≥2.0.0 |
| `pandas` | Data processing | ≥2.0.0 |
| `python-dotenv` | Environment variable loading | ≥1.0.0 |

---

## Data Flow Diagram

```
[Upload Image (JPG/PNG/WEBP)]
           ↓
[Load & Validate via PIL]
           ↓
[Face Detection]
  ├─ Try: MediaPipe
  ├─ Try: DNN Model
  └─ Fallback: Haar Cascade
           ↓
[Crop Portrait(s) with Margin]
           ↓
[Save Portrait to outputs/portraits/]
           ↓
[OCR Processing]
  ├─ Image Preprocessing (deskew, enhance)
  ├─ Run Multiple OCR Engines (parallel)
  └─ Aggregate Results
           ↓
[Extract Raw Text]
           ↓
[Card Type Detection]
  └─ Keyword matching against card type templates
           ↓
[Field Extraction & Normalization]
  ├─ Fuzzy match field labels
  ├─ Extract values
  └─ Normalize formats (dates, names, etc.)
           ↓
[Display Extracted Fields in UI]
           ↓
[User Manual Verification Form]
           ↓
[Compare Extracted vs User Input]
  ├─ Field-by-field similarity scoring
  ├─ Determine match status
  └─ Display colored comparison
           ↓
[Save to Database & CSV]
  ├─ SQLite: id_cards.db
  └─ CSV: id_cards.csv
           ↓
[Generate Downloads]
  ├─ portrait_main.jpg
  └─ portraits.zip (all faces)
```

---

## Supported Document Types

The system automatically identifies and extracts fields specific to:

1. **Ghana Card** - ECOWAS Identity Card
   - Fields: Surname, Firstnames, Personal ID Number, DOB, Nationality, Sex, Height, Expiry
   
2. **Driver's License**
   - Fields: Name, License Number, DOB, Class, Issue/Expiry dates, Nationality
   
3. **Passport**
   - Fields: Passport Number, Surname, Given Names, DOB, Nationality, Issue/Expiry dates
   
4. **Voter ID** - Electoral commission issued
   - Fields: Name, Voter ID, DOB, Constituency, Polling Station
   
5. **NHIS Card** - National Health Insurance
   - Fields: Name, NHIS Number, DOB, Gender, Expiry Date
   
6. **SSNIT Card** - Social Security
   - Fields: Name, SSNIT Number, DOB, Employer
   
7. **Birth Certificate**
   - Fields: Name, DOB, Place of Birth, Parents' names, Registration Number
   
8. **TIN Document** - Tax ID
   - Fields: Name, TIN Number, DOB, Taxpayer Type, Registration Date

---

## Error Handling & Fallbacks

| Scenario | Handling |
|----------|----------|
| No face detected | Displays warning; allows continuation with blank portrait |
| OCR fails | Falls back through engine hierarchy (PaddleOCR → EasyOCR → None) |
| Field extraction fails | Shows raw OCR text for manual review |
| Invalid dates | Normalizes to standard format or flags as invalid |
| Missing Gemini API key | Automatically disables, falls back to local OCR |
| Image too large | Resizes while maintaining aspect ratio |
| Unsupported image format | Converts to RGB using PIL |

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Face detection | 100-500ms | Depends on image size and detector |
| Portrait extraction | 50-200ms | Includes cropping and saving |
| OCR (single engine) | 2-10s | Depends on text density, image quality |
| OCR (hybrid mode) | 4-15s | Runs engines in parallel |
| Field extraction | 100-500ms | Fuzzy matching overhead minimal |
| Database save | 50-100ms | SQLite write operation |

---

## Extension Points

The project is designed for student/researcher extension:

1. **Deskewing** - Auto-straighten ID cards before face detection
2. **Custom Detectors** - Train lightweight YOLO model for portrait window
3. **Privacy** - EXIF stripping, temporary storage management
4. **Batch Mode** - Accept multiple images, export results CSV
5. **Face Matching** - Compare extracted portraits against gallery
6. **Liveness Detection** - Prevent spoofing attacks
7. **Language Support** - Add non-English card types
8. **REST API** - Expose core functions via FastAPI/Flask

---

## Known Limitations

1. **MediaPipe** - Optimized for frontal faces; struggles with tilted/angled cards
2. **Background Faces** - May detect faces in ID photos if people visible in background
3. **Low-Quality Images** - OCR accuracy drops significantly with low resolution/lighting
4. **Card Cropping** - Currently extracts full image; doesn't isolate card region
5. **Gemini Integration** - Optional, requires API key; falls back to local OCR
6. **No Face Liveness** - Cannot detect if ID photo is real or printed copy

---

## Security & Privacy Considerations

✓ **EXIF Stripping** - Removes GPS/metadata by default  
✓ **Local Processing** - All OCR runs locally (Gemini is optional)  
⚠️ **Database** - SQLite file stored locally; no encryption by default  
⚠️ **Portrait Storage** - Saved in plaintext directories  

**Recommendations for Production:**
- Enable database encryption
- Implement access controls
- Add audit logging for data access
- Implement data retention policies
- Use secure temporary file handling

---

## Testing

Test suite in `tests/test_suite.py` covers:
- Face detection accuracy
- OCR field extraction
- Data validation functions
- Card type identification
- Comparison engine logic
- Storage operations

Run with: `pytest tests/test_suite.py -v`

---

## Deployment Options

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud
- Upload to GitHub
- Connect via Streamlit Cloud dashboard
- Specify Python 3.10+ in `runtime.txt`
- Add API keys to secrets management

### Docker
- Build container with all dependencies
- Pre-download OCR models
- Mount `/outputs` volume for persistence

### REST API
- Wrap core functions in FastAPI/Flask
- Serve via Gunicorn/uWSGI
- Support batch processing endpoint

---

## Summary

This is a **production-ready baseline system** for ID card portrait extraction and OCR that:
- ✅ Works offline after installation
- ✅ Requires no model training
- ✅ Supports 8+ document types
- ✅ Provides human verification workflow
- ✅ Stores results in database/CSV
- ✅ Offers clear extension points for research

The modular architecture makes it easy to swap detectors, add OCR engines, or enhance validation logic.
