"""
Main Streamlit app for ID Card Text & Portrait Extraction

Usage:
    streamlit run app.py

This app allows uploading an ID card image, extracts portrait using OpenCV,
performs OCR via Gemini API (or EasyOCR fallback), displays structured fields,
allows manual verification, compares fields, and stores records.
"""
import os
import io
import json
import logging
from datetime import datetime
from typing import Dict, Any

import streamlit as st
from PIL import Image

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure src package is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in os.sys.path:
    os.sys.path.insert(0, CURRENT_DIR)

from src.detector import detect_and_crop
from src.ocr_gemini import GeminiOCRClient
from src.validator import compare_records
from src.storage import Storage

# Initialize clients
_gemini = GeminiOCRClient()
_storage = Storage(db_path=os.path.join(CURRENT_DIR, "outputs", "id_cards.db"))

# Create outputs directories
os.makedirs(os.path.join(CURRENT_DIR, "outputs", "portraits"), exist_ok=True)

st.set_page_config(page_title="ID Card Extractor", layout="wide")
st.title("ID Card Text & Portrait Extraction")

# Sidebar
with st.sidebar:
    st.markdown("## Configuration")
    use_gemini = st.checkbox("Use Gemini API (if configured)", value=not _gemini.dry_run and _gemini.enabled)
    show_raw = st.checkbox("Show raw OCR text", value=False)

# Upload
uploaded = st.file_uploader("Upload ID card image (JPG, PNG, WEBP)", type=["jpg","jpeg","png","webp"])

if uploaded is None:
    st.info("Upload an ID card image to begin.")
    st.stop()

try:
    image = Image.open(uploaded).convert("RGB")
except Exception as e:
    st.error(f"Failed to open image: {e}")
    st.stop()

st.image(image, caption="Uploaded image", use_column_width=True)

# Detect & crop portrait
with st.spinner("Detecting portrait photo..."):
    try:
        portrait_img, face_box = detect_and_crop(image)
        if portrait_img is None:
            st.warning("No face detected on the card. Portrait will be blank.")
            portrait_path = None
        else:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            portrait_path = os.path.join(CURRENT_DIR, "outputs", "portraits", f"portrait_{ts}.jpg")
            portrait_img.save(portrait_path)
            st.success("Portrait extracted and saved.")
            st.image(portrait_img, caption="Extracted portrait", width=200)
    except Exception as e:
        st.error(f"Portrait extraction failed: {e}")
        portrait_path = None

# OCR / Gemini
with st.spinner("Running OCR and extracting structured fields..."):
    try:
        # If user checked use_gemini and gemini is enabled, allow network mode
        if use_gemini and _gemini.enabled and not _gemini.dry_run:
            result = _gemini.extract_structured(uploaded.getvalue())
        else:
            # Dry-run or Gemini disabled: use local EasyOCR fallback
            result = _gemini.extract_structured(uploaded.getvalue())

        raw_text = result.get("raw_text")
        structured = result.get("fields", {})
        card_type = result.get("card_type", "Unknown")

        if show_raw:
            st.subheader("Raw OCR Text")
            st.text_area("Raw text", value=raw_text or "", height=200)

        st.subheader("Extracted Fields")
        if not structured:
            st.warning("No structured fields were detected.")
        else:
            st.table(structured)

    except Exception as e:
        st.error(f"OCR extraction failed: {e}")
        st.stop()

# Manual verification form
st.subheader("Manual Verification")
with st.form("verify_form"):
    cols = st.columns(2)
    user_input: Dict[str, Any] = {}
    # Pre-fill common fields
    defaults = {
        "Surname": structured.get("surname") or "",
        "Firstnames": structured.get("firstnames") or "",
        "Previous Names": structured.get("previous_names") or "",
        "Date of Birth": structured.get("date_of_birth") or "",
        "Sex": structured.get("sex") or "",
        "Nationality": structured.get("nationality") or "",
        "Document Number": structured.get("document_number") or "",
        "Date of Issue": structured.get("date_of_issue") or "",
        "Date of Expiry": structured.get("date_of_expiry") or "",
        "Place of Issue": structured.get("place_of_issue") or "",
        "Height": structured.get("height") or "",
    }

    i = 0
    for field, val in defaults.items():
        col = cols[i % 2]
        with col:
            user_input[field] = st.text_input(field, value=val)
        i += 1

    submitted = st.form_submit_button("Compare & Save")

if submitted:
    # Compare
    comparison = compare_records(structured, user_input)

    st.subheader("Comparison Results")
    # Display comparison with green/red markers
    for key, res in comparison.items():
        left = res.get("extracted")
        right = res.get("user")
        match = res.get("match")
        color = "#d4edda" if match else "#f8d7da"
        emoji = "✅" if match else "❌"
        st.markdown(f"**{key}**: {emoji}")
        cols = st.columns([1, 3])
        cols[0].markdown("**Extracted**")
        cols[0].write(left)
        cols[1].markdown("**User**")
        cols[1].write(right)

    # Save if majority matches (simple rule) or always save
    try:
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "card_type": card_type,
            "fields": json.dumps(structured),
            "user_input": json.dumps(user_input),
            "portrait_path": portrait_path,
        }
        _storage.save_record(record)
        st.success("Record saved.")
    except Exception as e:
        st.error(f"Failed to save record: {e}")

st.info("All done. You can find saved portraits in outputs/portraits and records in outputs/id_cards.db")
