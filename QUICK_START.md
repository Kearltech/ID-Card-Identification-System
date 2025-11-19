# Quick Start Guide - Improved ID Card Extraction System

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Optional: Install MediaPipe for Better Face Detection**:
   ```bash
   pip install mediapipe
   ```

## Usage

### Option 1: Streamlit Web App (Recommended)

```bash
streamlit run src/app.py
```

Then:
1. Open the URL shown in the terminal (usually `http://localhost:8501`)
2. Upload an ID card image
3. View extracted fields, validation results, and download portraits

### Option 2: Command Line Script

```bash
# Process an ID card image
python example_usage.py path/to/id_card.jpg

# Query database
python example_usage.py --query

# Query by card type
python example_usage.py --query --card-type "Ghana Card"
```

### Option 3: Python API

```python
import cv2
from face_extractor.text_extractor import process_id_card
from face_extractor.validator import validate_all_fields
from face_extractor.data_storage import IDCardStorage
from face_extractor.detector import detect_faces, crop_regions

# Load image
image = cv2.imread("id_card.jpg")

# Extract text and fields
card_data = process_id_card(image, preprocess=True)

# Validate fields
validation_results = validate_all_fields(
    card_data["fields"],
    card_data["card_type"]
)

# Detect and crop portrait
detections = detect_faces(image, min_confidence=0.6)
if detections:
    boxes = [detections[0][0]]  # Get largest face
    crops = crop_regions(image, boxes, margin_percent=10)
    cv2.imwrite("portrait.jpg", crops[0])

# Store in database
storage = IDCardStorage()
storage.store_extraction(
    card_data,
    portrait_path="portrait.jpg",
    validation_summary=validation_results
)
```

## Key Features

### 1. Enhanced OCR
- Automatic rotation detection and correction
- Lighting and contrast correction
- Noise reduction
- Better accuracy on poor quality images

### 2. Advanced Field Extraction
- Multiple regex patterns for different field formats
- Fuzzy matching for OCR errors
- Multi-line value extraction
- Support for 8+ card types

### 3. Data Validation
- Date format validation and normalization
- Name validation and cleaning
- ID number format validation
- Nationality, gender, height validation

### 4. Structured Storage
- SQLite database for structured queries
- CSV export for easy analysis
- Query functions for filtering and statistics

### 5. Improved Face Detection
- Multiple detection methods (MediaPipe/DNN/Haar)
- Confidence scoring
- Better preprocessing for low-quality images

## Output Files

After processing, you'll find:

- `outputs/portraits/portrait_YYYYMMDD_HHMMSS.jpg` - Cropped portrait images
- `outputs/data/extraction_YYYYMMDD_HHMMSS.json` - Extracted data in JSON format
- `outputs/id_cards.db` - SQLite database with all extractions
- `outputs/id_cards.csv` - CSV export of all extractions

## Supported Card Types

- Ghana Card
- Driver's License
- Passport
- Voter ID
- NHIS Card
- SSNIT Card
- Birth Certificate
- TIN Document

## Example Output

```json
{
  "card_type": "Ghana Card",
  "card_type_confidence": 0.85,
  "fields": {
    "Surname": "Doe",
    "Firstnames": "John",
    "Date of Birth": "1990-12-25",
    "Nationality": "Ghanaian",
    "Sex": "Male",
    "Personal ID Number": "GHA-123456789-0"
  },
  "validated_fields": {
    "Surname": "Doe",
    "Firstnames": "John",
    "Date of Birth": "1990-12-25",
    "Nationality": "Ghanaian",
    "Sex": "Male",
    "Personal ID Number": "GHA-123456789-0"
  },
  "portrait_path": "outputs/portraits/portrait_20241106_133031.jpg"
}
```

## Troubleshooting

### OCR Not Working
- Ensure EasyOCR is installed: `pip install easyocr`
- Check image quality (should be clear and well-lit)
- Try different preprocessing options

### No Faces Detected
- Lower the confidence threshold in the sidebar
- Ensure portrait is clearly visible
- Try a clearer image

### Validation Failures
- Check field formats match expected patterns
- Review validation errors in the output
- Some fields may require manual correction

## Next Steps

1. Review `IMPROVEMENTS.md` for detailed documentation
2. Check `example_usage.py` for more examples
3. Explore the database using SQL queries
4. Integrate with your RAG system for semantic search

## Support

For issues or questions:
1. Check the `IMPROVEMENTS.md` documentation
2. Review the example usage script
3. Check the code comments for detailed explanations

