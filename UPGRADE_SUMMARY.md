# ID Card Extractor - Upgrade Summary

## Overview
The ID extraction system has been upgraded to automatically detect card types and extract relevant fields using OCR technology.

## New Features

### 1. Automatic Card Type Detection
- Detects 8 different ID card types based on OCR text analysis:
  - Ghana Card
  - Driver's License
  - Passport
  - Voter ID
  - NHIS Card
  - SSNIT Card
  - Birth Certificate
  - TIN Document

### 2. Field Extraction
- Extracts structured data fields specific to each card type
- Uses fuzzy matching to handle OCR variations
- Returns field-value pairs in JSON format

### 3. Enhanced UI
- Displays detected card type with confidence score
- Shows extracted fields in a clean table format
- Provides download buttons for:
  - Portrait images
  - JSON data with extracted fields
  - ZIP archive of all portraits

### 4. Output Management
- Saves portraits to `outputs/portraits/` directory
- Saves JSON extraction data to `outputs/data/` directory
- Automatic timestamp-based file naming

## New Dependencies

```
easyocr          # OCR text extraction
rapidfuzz        # Fuzzy string matching
pandas           # Data table display
```

## File Structure Changes

### New Files
- `src/face_extractor/text_extractor.py` - OCR and field extraction module

### Modified Files
- `src/app.py` - Enhanced with OCR integration and new UI
- `src/face_extractor/__init__.py` - Exports new text extraction functions
- `requirements.txt` - Added new dependencies
- `.gitignore` - Added outputs directory

### New Directories
- `outputs/portraits/` - Stores extracted portrait images
- `outputs/data/` - Stores JSON extraction data

## Usage

### Installation
```bash
pip install -r requirements.txt
```

**Note:** EasyOCR will download model files on first use (~500MB). This is a one-time download.

### Running the App
```bash
streamlit run src/app.py
```

### Features in UI

1. **Sidebar Options:**
   - Face detection settings (confidence, margin, etc.)
   - OCR toggle (enable/disable OCR processing)
   - Show OCR text toggle (for debugging)

2. **Main Display:**
   - Original image preview
   - Face detection visualization
   - Card type detection result
   - Extracted fields table
   - Portrait previews
   - Download buttons

3. **Output Files:**
   - Portrait images: `outputs/portraits/portrait_YYYYMMDD_HHMMSS.jpg`
   - JSON data: `outputs/data/extraction_YYYYMMDD_HHMMSS.json`

## JSON Output Format

```json
{
  "card_type": "Driver's License",
  "card_type_confidence": 0.85,
  "fields": {
    "Name": "Emmanuel K Frimpong",
    "Date of Birth": "1987-03-24",
    "Licence #": "NAG-03102017-10785",
    "Class of Licence": "B",
    "Date of Issue": "2017-09-14",
    "Expiry Date": "2023-09-13",
    "Nationality": "Ghanaian"
  },
  "portrait_path": "outputs/portraits/portrait_20251105_223045.jpg"
}
```

## Technical Details

### OCR Engine
- Uses **EasyOCR** for text extraction
- Supports English language
- Model files cached after first download

### Card Type Detection
- Keyword-based matching (case-insensitive)
- Confidence scoring based on keyword matches
- Returns "Unknown" if no match found

### Field Extraction
- Multiple pattern matching strategies:
  - `Label: Value` format
  - `Label Value` format
  - Multi-line label-value pairs
- Fuzzy matching for label variations
- Handles OCR errors and variations

### Performance Notes
- OCR processing may take 5-15 seconds depending on image size
- EasyOCR reader is cached at module level for performance
- First run initializes OCR models (one-time delay)

## Limitations

1. **OCR Accuracy:** Depends on image quality and clarity
2. **Field Extraction:** May miss fields if OCR text is unclear
3. **Card Type Detection:** Requires recognizable keywords in OCR text
4. **Language:** Currently optimized for English text
5. **Processing Speed:** OCR adds processing time (5-15 seconds)

## Future Enhancements

- [ ] Support for multiple languages
- [ ] Batch processing mode for multiple images
- [ ] Confidence scores per extracted field
- [ ] Image preprocessing (deskewing, enhancement)
- [ ] Custom field templates
- [ ] Export to CSV/Excel
- [ ] Database integration for storing results

## Troubleshooting

### EasyOCR Installation Issues
- Ensure you have sufficient disk space (~500MB for models)
- Check internet connection for first-time model download
- If GPU available, EasyOCR will use it automatically

### OCR Not Working
- Verify EasyOCR is installed: `pip install easyocr`
- Check image quality (clear, well-lit images work best)
- Try increasing image resolution

### No Fields Extracted
- Check if card type was detected correctly
- Verify OCR text visibility (enable "Show OCR Text" option)
- Image quality may be too low for accurate OCR

## Support

For issues or questions, refer to the main README.md or project documentation.

