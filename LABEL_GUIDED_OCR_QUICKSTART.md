# Label-Guided OCR Quick Start Guide

**Get started in 5 minutes** with the label-guided OCR system for ID card field extraction.

---

## Installation

### 1. Prerequisites
```bash
# Python 3.13+
python --version

# Navigate to project directory
cd Id_card_image_extracted-main
```

### 2. Dependencies (already installed)
```bash
pip list | grep -E "easyocr|opencv|pillow|google-generative"
```

All required packages are already in `requirements.txt`.

---

## Quick Start: 3 Steps

### Step 1: Import the Pipeline

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline

# Initialize
pipeline = LabelGuidedOCRPipeline(gemini_api_key=None)
```

### Step 2: Process an ID Card

```python
# Process image
result = pipeline.process_id_card("path/to/ghana_card.jpg", "ghana_card")

# Check if successful
if result['status'] == 'success':
    print(f"✓ Extracted {result['steps']['field_parsing']['fields_found']} fields")
else:
    print(f"✗ Error: {result['error']}")
```

### Step 3: View Extracted Fields

```python
# Display results
print(pipeline.get_summary(result))

# Or access individual fields
for field_name, value in result['extracted_fields'].items():
    if value:
        print(f"{field_name}: {value}")
```

---

## Complete Example: End-to-End Verification

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline
from src.ocr_database import OCRResultsDatabase

# Initialize
pipeline = LabelGuidedOCRPipeline()
db = OCRResultsDatabase()

# 1. Process ID card
card_result = pipeline.process_id_card("ghana_card.jpg", "ghana_card")

if card_result['status'] != 'success':
    print(f"Failed: {card_result['error']}")
    exit()

# 2. User provides data (from form)
user_data = {
    "Surname": "Oppong",
    "Firstnames": "Morrison",
    "Date of Birth": "15/03/1990",
    "Sex": "M",
    "ID Number": "GHA-724693385-3"
}

# 3. Compare user vs card
comparison = pipeline.validate_user_input(
    user_data,
    card_result['extracted_fields'],
    "ghana_card",
    similarity_threshold=0.85
)

# 4. Check result
if comparison['overall_match']:
    print("✓ VERIFICATION PASSED - User data matches card")
else:
    print("✗ VERIFICATION FAILED - Mismatches detected")
    for field, mismatch in comparison['comparison']['mismatches'].items():
        print(f"  {field}: {mismatch['user_value']} vs {mismatch['extracted_value']}")

# 5. Store results
extraction_id = db.store_extraction(card_result)
db.store_user_comparison(extraction_id, comparison)
db.store_type_specific_result(extraction_id, card_result['extracted_fields'], "ghana_card")

print(f"\nStored in database: extraction_id={extraction_id}")
```

---

## Common Use Cases

### Use Case 1: Extract Fields Only

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline

pipeline = LabelGuidedOCRPipeline()
result = pipeline.process_id_card("id.jpg", "ghana_card")

# Get extracted fields as dict
fields = result['extracted_fields']
print(f"Name: {fields['Surname']} {fields['Firstnames']}")
print(f"DOB: {fields['Date of Birth']}")
print(f"ID: {fields['ID Number']}")
```

### Use Case 2: Validate Against User Input

```python
from src.ocr_field_parser import FieldValidator

validator = FieldValidator()

user_input = {
    "Surname": "Smith",
    "Firstnames": "John",
    "Date of Birth": "01/01/1990"
}

extracted = {
    "Surname": "SMITH",
    "Firstnames": "JOHN",
    "Date of Birth": "01/01/1990"
}

comparison = validator.compare_fields(user_input, extracted, similarity_threshold=0.85)

print(f"Confidence: {comparison['overall_confidence']:.1%}")
print(f"Matches: {len(comparison['matches'])}")
print(f"Mismatches: {len(comparison['mismatches'])}")
```

### Use Case 3: Database Lookup

```python
from src.ocr_database import OCRResultsDatabase

db = OCRResultsDatabase()

# Search by ID number
result = db.search_by_id_number("GHA-724693385-3", "ghana_card")

if result:
    print(f"Found: {result['surname']} {result['firstnames']}")
    print(f"Verified: {result['verified']}")
else:
    print("Not found")
```

### Use Case 4: Batch Processing

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline
from src.ocr_database import OCRResultsDatabase
import os

pipeline = LabelGuidedOCRPipeline()
db = OCRResultsDatabase()

# Process all images in directory
image_dir = "id_images/"
for filename in os.listdir(image_dir):
    if filename.endswith((".jpg", ".png")):
        filepath = os.path.join(image_dir, filename)
        
        # Process
        result = pipeline.process_id_card(filepath, "ghana_card")
        
        if result['status'] == 'success':
            # Store
            extraction_id = db.store_extraction(result)
            db.store_type_specific_result(extraction_id, result['extracted_fields'], "ghana_card")
            print(f"✓ {filename} - ID: {extraction_id}")
        else:
            print(f"✗ {filename} - Failed: {result['error']}")
```

---

## Supported ID Types

```python
# Ghana Card
result = pipeline.process_id_card("card.jpg", "ghana_card")

# Passport
result = pipeline.process_id_card("passport.jpg", "passport")

# Voter ID
result = pipeline.process_id_card("voter_id.jpg", "voters_id")

# Driver's License
result = pipeline.process_id_card("license.jpg", "drivers_license")
```

---

## Working with Results

### JSON Export

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline
import json

pipeline = LabelGuidedOCRPipeline()
result = pipeline.process_id_card("card.jpg", "ghana_card")

# Export as JSON
json_str = pipeline.export_to_json(result)

# Save to file
with open("result.json", "w") as f:
    f.write(json_str)

# Or parse as dict
data = json.loads(json_str)
print(data['extracted_fields'])
```

### Human-Readable Summary

```python
pipeline = LabelGuidedOCRPipeline()
result = pipeline.process_id_card("card.jpg", "ghana_card")

# Print summary
print(pipeline.get_summary(result))

# Output:
# ==================================================
# OCR PIPELINE SUMMARY
# ==================================================
# ID Type: ghana_card
# Status: success
#
# ID Card Processing:
#   - Engine: easyocr
#   - Fields extracted: 7/13
#   - Valid: True
# ==================================================
```

---

## Configuration

### Use Gemini Vision (Better Accuracy)

```python
from src.ocr_pipeline import LabelGuidedOCRPipeline

# Initialize with Gemini API key
pipeline = LabelGuidedOCRPipeline(gemini_api_key="YOUR_API_KEY")

# Now Gemini will be tried first (95%+ accuracy)
result = pipeline.process_id_card("card.jpg", "ghana_card")
```

### Adjust Similarity Threshold

```python
# Strict matching (high security)
comparison = pipeline.validate_user_input(
    user_data,
    extracted_fields,
    "ghana_card",
    similarity_threshold=0.95  # Only exact matches
)

# Lenient matching (user-friendly)
comparison = pipeline.validate_user_input(
    user_data,
    extracted_fields,
    "ghana_card",
    similarity_threshold=0.75  # Allow variations
)
```

---

## Troubleshooting

### Problem: "No text detected"

```
Error: "OCR extraction failed - no text detected"
```

**Solutions:**
- Ensure image is clear and well-lit
- Check that ID card fills most of frame
- Try with different image format
- Use Gemini Vision for better accuracy

### Problem: "Missing required fields"

```
missing_required: ["Surname", "Date of Birth"]
```

**Solutions:**
- Verify all required fields are on ID card
- Check image quality
- Try with different OCR engine
- Check field schema for ID type

### Problem: "User mismatch detected"

```
overall_match: false
mismatches: {"Surname": {"user_value": "Smith", "extracted_value": "SMYTH"}}
```

**Solutions:**
- Check for typos in user input
- Verify OCR accuracy
- Lower similarity threshold if intentional
- Manual review recommended

---

## Performance Tips

### For Better Accuracy

1. **Use High-Quality Images**
   - Good lighting
   - High resolution
   - Clear focus
   - Minimal glare

2. **Use Gemini Vision**
   - Best accuracy (95%+)
   - Requires API key
   - Slightly slower

3. **Validate All Fields**
   - Check data types
   - Verify required fields
   - Cross-reference dates

### For Better Speed

1. **Use EasyOCR**
   - Good accuracy (92%+)
   - Faster than Gemini
   - No API required

2. **Cache Results**
   - Database lookups faster
   - Avoid re-processing
   - Use extraction_id

3. **Batch Processing**
   - Process multiple at once
   - Share OCR model
   - Parallel processing

---

## Database Operations

### Store Results

```python
from src.ocr_database import OCRResultsDatabase

db = OCRResultsDatabase()

# Store extraction
extraction_id = db.store_extraction(result)

# Store validation
validation_id = db.store_validation(extraction_id, validation)

# Store comparison
comparison_id = db.store_user_comparison(extraction_id, comparison)

# Store type-specific
db.store_type_specific_result(extraction_id, fields, "ghana_card")
```

### Query Results

```python
# Get by extraction ID
result = db.get_extraction_by_id(extraction_id)

# Search by ID number
result = db.search_by_id_number("GHA-724693385-3", "ghana_card")

# Get statistics
stats = db.get_statistics()
print(f"Total extractions: {stats['extractions_by_type']}")
print(f"Valid: {stats['validations']['valid']}")
```

---

## Integration with Streamlit

```python
import streamlit as st
from src.ocr_pipeline import LabelGuidedOCRPipeline

st.title("ID Card Verification")

# File upload
uploaded_file = st.file_uploader("Upload ID Card", type=["jpg", "png", "jpeg"])
id_type = st.selectbox("ID Type", ["ghana_card", "passport", "voters_id", "drivers_license"])

if uploaded_file:
    # Process
    pipeline = LabelGuidedOCRPipeline()
    result = pipeline.process_id_card(uploaded_file, id_type)
    
    if result['status'] == 'success':
        st.success(f"Extracted {result['steps']['field_parsing']['fields_found']} fields")
        
        # Show fields
        cols = st.columns(2)
        for i, (field, value) in enumerate(result['extracted_fields'].items()):
            if value:
                with cols[i % 2]:
                    st.write(f"**{field}:** {value}")
    else:
        st.error(f"Failed: {result['error']}")
```

---

## Next Steps

1. **Run Examples**
   ```bash
   python examples/label_guided_ocr_example.py
   ```

2. **Read Full Documentation**
   ```bash
   less LABEL_GUIDED_OCR.md
   ```

3. **Test with Your Data**
   - Upload real ID cards
   - Verify accuracy
   - Adjust thresholds

4. **Integrate with UI**
   - Add to Streamlit app
   - Connect to database
   - Build verification flow

5. **Deploy to Production**
   - Set up monitoring
   - Configure backups
   - Scale database

---

## API Reference

### LabelGuidedOCRPipeline

```python
# Initialize
pipeline = LabelGuidedOCRPipeline(gemini_api_key=None)

# Methods
pipeline.process_id_card(image, id_type) → Dict
pipeline.validate_user_input(user_input, extracted, id_type, threshold) → Dict
pipeline.full_verification_pipeline(image, id_type, user_input) → Dict
pipeline.export_to_json(result) → str
pipeline.get_summary(result) → str
pipeline.get_available_ocr_engines() → Dict
```

### OCRResultsDatabase

```python
# Initialize
db = OCRResultsDatabase(db_path)

# Methods
db.store_extraction(result) → int
db.store_validation(extraction_id, validation) → int
db.store_user_comparison(extraction_id, comparison) → int
db.store_type_specific_result(extraction_id, fields, id_type) → bool
db.get_extraction_by_id(extraction_id) → Dict
db.search_by_id_number(id_number, id_type) → Dict
db.get_statistics() → Dict
```

---

## Support

- **Documentation:** `LABEL_GUIDED_OCR.md`
- **Examples:** `examples/label_guided_ocr_example.py`
- **Issues:** GitHub Issues
- **Questions:** GitHub Discussions

---

**Version:** 1.0.0  
**Last Updated:** November 2025  
**Status:** ✅ Production Ready
