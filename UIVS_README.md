# 🆔 Universal ID Verification System (UIVS)

A complete AI-powered identity verification system combining face matching, ID card OCR analysis, and secure database storage.

## 🎯 System Purpose

UIVS verifies user identity by:

1. **Face Comparison** - Compares user-uploaded passport photo with face extracted from ID card
2. **ID Card Analysis** - Detects and classifies the type of ID card presented
3. **Text Extraction** - Uses AI OCR to extract ID information (name, ID number, DOB, etc.)
4. **Cross-validation** - Ensures ID number entered matches extracted ID number
5. **Secure Storage** - Stores verification records in structured databases by ID type

## 🧭 User Workflow

### Step 1: Upload Passport Photo
- User uploads a clear headshot (passport-style photo)
- Used for face comparison with ID card photo

### Step 2: Select ID Type
- User chooses ID type from:
  - 🇬🇭 Ghana Card (National ID / ECOWAS)
  - 🛂 Passport
  - 🗳️ Voter ID
  - 🚗 Driver's License

### Step 3: Enter ID Number & Upload ID Card
- User enters ID number manually
- Uploads ID card image (photo or scan)

### Step 4: System Processing
The system performs four major tasks:

#### ❶ ID Card Classification
- Analyzes uploaded image
- Confirms card type using AI classification
- Warns if mismatch detected (fraud detection)

#### ❷ Text Extraction (OCR)
- Extracts name, DOB, nationality, ID number, etc.
- Uses AI OCR (Gemini Vision or EasyOCR)
- Validates field formats

#### ❸ Face Extraction
- Detects face on card using MediaPipe/OpenCV
- Crops and standardizes face
- Resizes to match uploaded portrait

#### ❹ Face Comparison
- Compares face embeddings
- Computes similarity score
- Threshold: ≥55% similarity = match

### Step 5: Verification Results
- Shows all three validation checks
- 🟢 **Identity Verified** - All checks pass
- 🔴 **Identity Invalid** - Any check fails

---

## ✅ Validation Logic

The system checks **three things**:

| Check | Details |
|-------|---------|
| **Card Type Match** | AI detected type matches user selection |
| **ID Number Match** | Entered ID matches OCR extracted ID |
| **Face Match** | Portrait similarity ≥ 55% |

**Result:**
- ✅ All 3 match → **🟢 VERIFIED**
- ❌ Any mismatch → **🔴 INVALID / FRAUD SUSPECTED**

---

## 🗄 Database Architecture

Each ID type has its own table with relevant fields:

### Table: `national_id`
```sql
id (PK)
timestamp
surname
firstname
nationality
sex
date_of_birth
id_number (UNIQUE)
card_number
issue_date
expiry_date
height
extracted_portrait (BLOB)
uploaded_portrait (BLOB)
face_match_score
card_type_match
id_number_match
validation_result
verification_status
confidence_score
notes
```

### Table: `passport`
```sql
id (PK)
timestamp
surname
given_names
nationality
passport_number (UNIQUE)
date_of_birth
issue_date
expiry_date
place_of_birth
mrz_data
extracted_portrait (BLOB)
uploaded_portrait (BLOB)
face_match_score
validation_result
verification_status
```

### Table: `voters_id`
```sql
id (PK)
timestamp
voter_id_number (UNIQUE)
name
date_of_birth
nationality
constituency
polling_station
electoral_area
extracted_portrait (BLOB)
uploaded_portrait (BLOB)
face_match_score
validation_result
verification_status
```

### Table: `drivers_license`
```sql
id (PK)
timestamp
license_number (UNIQUE)
name
date_of_birth
nationality
license_class
issue_date
expiry_date
address
extracted_portrait (BLOB)
uploaded_portrait (BLOB)
face_match_score
validation_result
verification_status
```

### Table: `verification_audit`
```sql
id (PK)
id_type
user_id
action
result
timestamp
details
```

---

## 🧩 ML Components

### 1. ID Card Type Classifier
**Purpose:** Detect card type automatically

**Methods:**
- Keyword detection (first pass)
- OCR text matching
- Gemini multimodal classification

**Supported Types:**
- Ghana Card
- Passport
- Voter ID
- Driver's License

### 2. OCR (Text Extraction)
**Primary:** Gemini Vision API
**Backup:** EasyOCR, Tesseract

**Extracts:**
- Name (surname, first names)
- Date of birth
- Nationality
- Sex/Gender
- Document number
- ID number
- Issue & expiry dates
- ID-specific fields

### 3. Face Detection
**Methods:**
- MediaPipe Face Detection (preferred)
- OpenCV Haar Cascade (fallback)

**Output:**
- Standardized face crop (200x200)
- Ready for comparison

### 4. Face Matching
**Engines:**
- face_recognition (dlib)
- DeepFace (VGG-Face, Facenet512)
- Pixel-based fallback

**Output:**
- Similarity score (0-1)
- Match decision

---

## 🎨 User Interface

Built with **Streamlit** - intuitive, step-by-step workflow

### Main Features:
- ✅ Multi-step form wizard
- ✅ Real-time image preview
- ✅ Status indicators (✅❌⚠️)
- ✅ Side-by-side face comparison
- ✅ Detailed verification report
- ✅ Download JSON report
- ✅ Admin statistics dashboard

---

## 🚀 Getting Started

### Installation

```bash
# Clone repository
git clone https://github.com/Kearltech/ID-Card-Identification-System.git
cd ID-Card-Identification-System

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run uivs_app.py
```

Then open: `http://localhost:8501`

### Configuration

Set environment variables (optional):

```bash
export GEMINI_API_KEY="your-api-key"  # For Gemini Vision
export OCR_ENGINE="hybrid"             # Options: easyocr, paddleocr, hybrid
export USE_GPU=true                    # Enable GPU acceleration
export MIN_FACE_CONFIDENCE=0.6         # Face detection threshold
export FACE_SIMILARITY_THRESHOLD=0.55  # Face match threshold (0-1)
```

---

## 📋 Requirements

### Core Dependencies
```
streamlit>=1.28.0
opencv-python-headless>=4.8.1
numpy>=1.23.0
Pillow>=10.0.0
pandas>=2.0.0
```

### OCR/Detection
```
easyocr>=1.7.0
mediapipe>=0.10.0
face_recognition>=1.3.0
deepface>=0.0.75  # Optional
google-generativeai>=0.1.0  # Optional (Gemini)
```

### Database
```
sqlite3  # Built-in
```

See `requirements.txt` for complete list.

---

## 🔐 Security & Privacy

✅ **Image Handling**
- All images processed in memory
- Optional auto-delete after verification
- BLOB storage in database

✅ **Data Protection**
- SQLite encryption (optional)
- Sensitive data encrypted at rest
- Audit trail of all verifications

✅ **User Privacy**
- No data shared externally
- Local processing by default
- Gemini API optional (offline mode available)

---

## 🧪 Testing

Run test suite:

```bash
pytest tests/test_suite.py -v
```

Test coverage includes:
- Face detection accuracy
- OCR field extraction
- Data validation
- Card type classification
- Face comparison logic
- Database operations

---

## 📊 Admin Panel

Access via Step 6 in app:

**Features:**
- Verification statistics by ID type
- Total verified/failed counts
- 24-hour verification metrics
- Database info and status

---

## 🔥 Future Extensions

- ✔️ **Liveness Detection** - Video selfie verification
- ✔️ **Batch Processing** - Verify multiple IDs
- ✔️ **API Endpoint** - REST API integration
- ✔️ **Fraud Detection** - Detect forged cards
- ✔️ **Additional ID Types** - NHIS, SSNIT, TIN, etc.
- ✔️ **Export Audit Logs** - CSV/JSON export
- ✔️ **Mobile App** - React Native frontend

---

## 🐛 Troubleshooting

### Face not detected
- Use clearer image with good lighting
- Ensure portrait is frontal and clear
- Try lowering confidence threshold

### OCR text not extracted
- Check image quality and contrast
- Try different OCR engine (Gemini vs EasyOCR)
- Ensure ID card text is legible

### Face comparison fails
- Try different face recognition engine
- Ensure both faces are visible
- Check image resolution and lighting

### Database errors
- Verify write permissions to outputs directory
- Check disk space
- Ensure SQLite not corrupted

---

## 📞 Support

For issues or questions:
- Check `PROJECT_ANALYSIS.md` for detailed architecture
- Review `ENHANCEMENT_GUIDE.md` for extending the system
- See test files for usage examples

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- MediaPipe for face detection
- Gemini API for OCR
- Streamlit for web framework
- OpenCV for image processing

---

**Status:** ✅ Production Ready  
**Last Updated:** November 19, 2025  
**Version:** 1.0.0
