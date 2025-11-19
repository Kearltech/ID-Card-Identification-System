"""Enhanced ID Card Extractor with User Verification and Comparison.

This Streamlit app provides:
- OCR-based text extraction from ID cards
- Automatic card type detection
- User manual input verification
- Field-by-field comparison
- Comprehensive validation summary
- Portrait extraction and storage
"""

import io
import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import streamlit as st
st.set_page_config(
    page_title="ID Card Extractor Pro",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

import cv2
import numpy as np
from PIL import Image
import piexif

from face_extractor.text_extractor import process_id_card
from face_extractor.validator import validate_all_fields
from face_extractor.data_storage import IDCardStorage
from face_extractor.detector import detect_faces, crop_regions
from face_extractor.advanced_ocr import create_ocr_engine, OCREngine
from face_extractor.postprocessing import OCRPostProcessor
from face_extractor.gemini_client import GeminiClient
from face_extractor.comparison_engine import compare_extractions
from face_extractor.user_verification import create_user_form, UserDataStore


# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "ocr_data" not in st.session_state:
    st.session_state.ocr_data = None

if "user_data" not in st.session_state:
    st.session_state.user_data = {}

if "comparison_result" not in st.session_state:
    st.session_state.comparison_result = None

if "user_store" not in st.session_state:
    st.session_state.user_store = UserDataStore()

# Post-processor and optional Gemini client (won't call external API unless enabled)
_ocr_postprocessor = OCRPostProcessor()
_gemini_client = GeminiClient()


# ==================== Utility Functions ====================

def strip_exif(pil_image: Image.Image) -> Image.Image:
    """Remove EXIF metadata from image (privacy).
    
    Args:
        pil_image: PIL Image object
        
    Returns:
        Image without EXIF data
    """
    try:
        # Remove EXIF data
        data = list(pil_image.getdata())
        image_without_exif = Image.new(pil_image.mode, pil_image.size)
        image_without_exif.putdata(data)
        logger.info("✓ EXIF data stripped for privacy")
        return image_without_exif
    except Exception as e:
        logger.warning(f"Could not strip EXIF: {e}")
        return pil_image


def validate_file_size(uploaded_file, max_size_mb: int = 10) -> Tuple[bool, str]:
    """Validate uploaded file size.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        max_size_mb: Maximum file size in MB
        
    Returns:
        Tuple of (is_valid, message)
    """
    size_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File size ({size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
    return True, ""


def load_image_to_bgr(uploaded_file, strip_metadata: bool = True) -> Optional[np.ndarray]:
    """Load uploaded image and convert to BGR format.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        strip_metadata: Whether to strip EXIF metadata
        
    Returns:
        Image in BGR format or None if failed
    """
    try:
        data = uploaded_file.read()
        pil_img = Image.open(io.BytesIO(data)).convert("RGB")
        
        # Strip EXIF for privacy
        if strip_metadata:
            pil_img = strip_exif(pil_img)
        
        rgb = np.array(pil_img)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        
        # Validate image format
        if bgr is None or bgr.size == 0:
            return None
        
        return bgr
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return None


def save_portrait(crop: np.ndarray, output_dir: str = "outputs/portraits") -> str:
    """Save portrait to disk.
    
    Args:
        crop: Cropped portrait image
        output_dir: Output directory
        
    Returns:
        Path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"portrait_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, crop)
    return filepath


# ==================== Main App ====================

def main():
    """Main application flow."""
    st.title("🆔 ID Card Extractor Pro")
    st.caption("Extract, verify, and validate ID card information with AI-powered OCR and user verification")
    
    # Tabs for different features
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Extract",
        "✍️ Verify",
        "🔍 Compare",
        "📊 Results"
    ])
    
    # ==================== TAB 1: EXTRACT ====================
    with tab1:
        st.subheader("Step 1: Upload & Extract from ID Card")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Upload Image")
            uploaded_file = st.file_uploader(
                "Upload an ID card image (JPG, PNG, WEBP)",
                type=["jpg", "jpeg", "png", "webp"],
                help="Clear, well-lit image for best results"
            )
        
        with col2:
            st.markdown("### Extraction Settings")
            ocr_engine = st.selectbox(
                "OCR Engine",
                ["hybrid", "easyocr", "paddleocr"],
                help="Hybrid uses multiple engines for better accuracy"
            )
            preprocess_enabled = st.checkbox("Enable Preprocessing", value=True)
            show_debug = st.checkbox("Show Debug Info", value=False)
        
        if uploaded_file is None:
            st.info("👆 Please upload an ID card image to get started")
            return
        
        # Validate file
        is_valid, error_msg = validate_file_size(uploaded_file, max_size_mb=10)
        if not is_valid:
            st.error(f"❌ {error_msg}")
            return
        
        # Load image
        try:
            image_bgr = load_image_to_bgr(uploaded_file, strip_metadata=True)
            if image_bgr is None:
                st.error("❌ Failed to load image. Please try another file.")
                return
        except Exception as e:
            st.error(f"❌ Error loading image: {str(e)}")
            return
        
        # Display original image
        st.markdown("### 📷 Original Image")
        col1, col2 = st.columns(2)
        with col1:
            st.image(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), caption="Uploaded ID Card")
        with col2:
            img_h, img_w = image_bgr.shape[:2]
            st.info(f"📊 Image Info:\n- Dimensions: {img_w}×{img_h}\n- Format: {uploaded_file.type}")
        
        # Extract text
        st.markdown("### 🔍 Extracting Text...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: OCR Extraction
            status_text.text("Step 1/4: Performing OCR...")
            progress_bar.progress(25)
            
            with st.spinner("Extracting text with OCR..."):
                # Use advanced OCR if selected
                if ocr_engine != "easyocr":
                    try:
                        ocr_engine_obj = create_ocr_engine(ocr_engine, use_gpu=False)
                        ocr_result = ocr_engine_obj.extract_text(image_bgr, preprocess=preprocess_enabled)
                        ocr_text = ocr_result["full_text"]
                        ocr_confidence = ocr_result.get("confidence", 0.5)
                        if show_debug:
                            st.write(f"**OCR Engine:** {ocr_result['engine']}")
                            st.write(f"**Confidence:** {ocr_confidence:.2%}")
                    except Exception as e:
                        st.warning(f"Advanced OCR failed, falling back to EasyOCR: {e}")
                        ocr_text, ocr_confidence = extract_with_easyocr(image_bgr, preprocess_enabled)
                else:
                    ocr_text, ocr_confidence = extract_with_easyocr(image_bgr, preprocess_enabled)
            
            # Step 2: Card Type Detection & Field Extraction
            status_text.text("Step 2/4: Detecting card type and extracting fields...")
            progress_bar.progress(50)

            with st.spinner("Processing extracted text..."):
                card_data = process_id_card(image_bgr, preprocess=preprocess_enabled)
                # Post-process extracted fields to improve accuracy (normalization, fuzzy corrections)
                try:
                    fields = card_data.get("fields", {}) or {}
                    cleaned = _ocr_postprocessor.process_fields(fields)
                    card_data["fields"] = cleaned
                except Exception as _e:
                    logger.warning(f"Post-processing failed: {_e}")

                # Optionally validate/augment using Gemini (if configured)
                try:
                    if _gemini_client.enabled:
                        gemini_validation = _gemini_client.validate_fields(card_data.get("fields", {}))
                        # Merge any suggested corrections (non-destructive)
                        for k, v in gemini_validation.get("corrections", {}).items():
                            if v:
                                card_data["fields"][k] = v
                except Exception as _e:
                    logger.warning(f"Gemini validation skipped/failed: {_e}")
            
            # Store in session
            st.session_state.ocr_data = card_data
            
            # Step 3: Face Detection
            status_text.text("Step 3/4: Detecting portrait...")
            progress_bar.progress(75)
            
            portrait_path = None
            with st.spinner("Extracting portrait..."):
                detections = detect_faces(image_bgr, min_confidence=0.6)
                if detections:
                    detections.sort(key=lambda d: (d[0][2] - d[0][0]) * (d[0][3] - d[0][1]), reverse=True)
                    crops = crop_regions(image_bgr, [detections[0][0]], margin_percent=10)
                    if crops:
                        portrait_path = save_portrait(crops[0])
            
            progress_bar.progress(100)
            status_text.text("✅ Extraction complete!")
            
            # Display results
            st.success("✅ Extraction completed successfully!")
            
            st.markdown("### 📋 Extracted Information")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Card Type", card_data.get("card_type", "Unknown"))
            with col2:
                st.metric("Detection Confidence", f"{card_data.get('card_type_confidence', 0):.0%}")
            with col3:
                st.metric("OCR Confidence", f"{ocr_confidence:.0%}")
            
            # Display extracted fields
            fields = card_data.get("fields", {})
            if fields:
                st.markdown("#### Extracted Fields:")
                import pandas as pd
                field_df = pd.DataFrame([
                    {"Field": k, "Value": v}
                    for k, v in fields.items() if v
                ])
                st.dataframe(field_df, use_container_width=True, hide_index=True)
            
            # Show OCR text if debug enabled
            if show_debug and ocr_text:
                with st.expander("📝 Raw OCR Text"):
                    st.text_area("OCR Output", ocr_text, height=200, disabled=True)
            
            # Display portrait if detected
            if portrait_path:
                st.markdown("#### 👤 Detected Portrait")
                portrait_img = cv2.imread(portrait_path)
                st.image(cv2.cvtColor(portrait_img, cv2.COLOR_BGR2RGB), width=150)
                st.caption(f"Saved to: {portrait_path}")
        
        except Exception as e:
            st.error(f"❌ Extraction failed: {str(e)}")
            logger.exception("Extraction error:")
    
    # ==================== TAB 2: VERIFY ====================
    with tab2:
        st.subheader("Step 2: Manual Verification & User Input")
        
        if st.session_state.ocr_data is None:
            st.info("👈 Please extract data from an ID card first (Step 1)")
            return
        
        card_type = st.session_state.ocr_data.get("card_type", "Ghana Card")
        
        st.markdown(f"### Fill in Your Details ({card_type})")
        st.info("Please verify or correct the extracted information")
        
        # Create form
        user_form = create_user_form(card_type)
        form_fields = user_form.get_form_fields()
        
        # Display form
        user_input = {}
        cols = st.columns(2)
        col_idx = 0
        
        for field_name, field_def in form_fields.items():
            col = cols[col_idx % 2]
            col_idx += 1

            with col:
                # Pre-fill with OCR data if available
                ocr_value = st.session_state.ocr_data.get("fields", {}).get(field_name, "")
                
                if field_def["type"] == "select":
                    # Make selectbox robust: if OCR value is not in predefined options,
                    # include it as the second option so it can be shown/pre-filled.
                    base_options = list(field_def.get("options", []))
                    if ocr_value and ocr_value not in base_options:
                        options = ["", ocr_value] + base_options
                        index = 1
                    else:
                        options = [""] + base_options
                        index = 0 if not ocr_value else base_options.index(ocr_value) + 1

                    user_input[field_name] = st.selectbox(
                        field_name,
                        options=options,
                        index=index,
                        key=f"select_{field_name}"
                    )
                
                elif field_def["type"] == "date":
                    date_str = st.text_input(
                        field_name,
                        value=ocr_value,
                        placeholder="YYYY-MM-DD",
                        key=f"date_{field_name}"
                    )
                    user_input[field_name] = date_str
                
                else:  # text
                    user_input[field_name] = st.text_input(
                        field_name,
                        value=ocr_value,
                        key=f"text_{field_name}"
                    )
        
        # Validate and save
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Verify & Save Input", use_container_width=True):
                is_valid, errors = user_form.validate_input(user_input)
                
                if is_valid:
                    st.session_state.user_data = {
                        user_form.normalize_field_value(k, v): v
                        for k, v in user_input.items() if v
                    }
                    st.session_state.user_store.save_user_input(
                        st.session_state.session_id,
                        st.session_state.user_data,
                        card_type
                    )
                    st.success("✅ User input validated and saved!")
                else:
                    st.error("❌ Validation errors:")
                    for field, error in errors.items():
                        st.error(f"- {error}")
        
        with col2:
            if st.button("🔄 Skip to Comparison", use_container_width=True):
                st.session_state.user_data = st.session_state.ocr_data.get("fields", {})
                st.info("Using OCR data for comparison")
    
    # ==================== TAB 3: COMPARE ====================
    with tab3:
        st.subheader("Step 3: Compare OCR vs User Input")
        
        if st.session_state.ocr_data is None:
            st.info("👈 Please extract data first (Step 1)")
            return
        
        if not st.session_state.user_data:
            st.warning("⚠️ Please verify and save user input first (Step 2)")
            return
        
        st.markdown("### Performing Field-by-Field Comparison")
        
        with st.spinner("Comparing data..."):
            ocr_fields = st.session_state.ocr_data.get("fields", {})
            
            # Compare
            comparison_result = compare_extractions(
                ocr_fields,
                st.session_state.user_data,
                threshold_valid=0.95,
                threshold_partial=0.70
            )
            
            st.session_state.comparison_result = comparison_result
        
        st.success("✅ Comparison completed!")
        
        # Display summary
        summary = comparison_result["summary"]
        
        st.markdown("### 📊 Comparison Summary")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Fields", summary["total_fields"])
        with col2:
            st.metric("Valid Matches", summary["valid_matches"], delta=f"+{summary['valid_matches']}")
        with col3:
            st.metric("Partial Matches", summary["partial_matches"])
        with col4:
            st.metric("Confidence", f"{summary['confidence_score']:.0%}")
        
        # Overall status
        status = summary["overall_status"]
        status_color = "green" if "Valid" in status else "orange" if "Partial" in status else "red"
        
        st.markdown(f"### {status}")
        
        # Weighted score
        weighted_score = summary["weighted_score"]
        progress_value = min(max(weighted_score, 0), 1)
        st.progress(progress_value, text=f"Weighted Score: {weighted_score:.0%}")
        
        # Detailed comparison results
        st.markdown("### 🔍 Detailed Field Comparison")
        
        # Group by status
        import pandas as pd
        
        detailed_results = comparison_result["detailed_results"]
        
        # Create summary table
        comparison_df = pd.DataFrame([
            {
                "Field": r["field_name"],
                "OCR Value": r["ocr_value"][:50] + "..." if len(r["ocr_value"]) > 50 else r["ocr_value"],
                "User Value": r["user_value"][:50] + "..." if len(r["user_value"]) > 50 else r["user_value"],
                "Status": r["status"],
                "Match %": f"{r['similarity_score']:.0%}"
            }
            for r in detailed_results
        ])
        
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
        
        # Show by status
        by_status = comparison_result["by_status"]
        
        if by_status.get("✅ Valid Match"):
            with st.expander(f"✅ Valid Matches ({len(by_status['✅ Valid Match'])})"):
                valid_df = pd.DataFrame(by_status["✅ Valid Match"])
                st.dataframe(valid_df[["field_name", "ocr_value", "similarity_score"]], hide_index=True)
        
        if by_status.get("⚠️ Partial Match"):
            with st.expander(f"⚠️ Partial Matches ({len(by_status['⚠️ Partial Match'])})"):
                partial_df = pd.DataFrame(by_status["⚠️ Partial Match"])
                st.dataframe(partial_df[["field_name", "ocr_value", "user_value", "similarity_score"]], hide_index=True)
        
        if by_status.get("❌ Invalid/Mismatch"):
            with st.expander(f"❌ Mismatches ({len(by_status['❌ Invalid/Mismatch'])})"):
                invalid_df = pd.DataFrame(by_status["❌ Invalid/Mismatch"])
                st.dataframe(invalid_df[["field_name", "ocr_value", "user_value", "similarity_score"]], hide_index=True)
        
        # Recommendations
        st.markdown("### 💡 Recommendations")
        recommendations = comparison_result["recommendations"]
        for rec in recommendations:
            st.info(rec)
    
    # ==================== TAB 4: RESULTS ====================
    with tab4:
        st.subheader("Step 4: Save & Review Results")
        
        if st.session_state.comparison_result is None:
            st.info("👈 Please complete comparison first (Step 3)")
            return
        
        st.success("✅ All data ready for storage")
        
        # Prepare data for storage
        result_data = {
            "session_id": st.session_state.session_id,
            "timestamp": datetime.now().isoformat(),
            "ocr_data": st.session_state.ocr_data,
            "user_data": st.session_state.user_data,
            "comparison_result": st.session_state.comparison_result
        }
        
        # Display final summary
        st.markdown("### 📋 Final Report")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Extraction Summary")
            ocr_data = st.session_state.ocr_data
            st.write(f"- **Card Type**: {ocr_data['card_type']}")
            st.write(f"- **Confidence**: {ocr_data['card_type_confidence']:.0%}")
            st.write(f"- **Fields Extracted**: {len([v for v in ocr_data['fields'].values() if v])}")
        
        with col2:
            st.markdown("#### Comparison Summary")
            summary = st.session_state.comparison_result["summary"]
            st.write(f"- **Overall Status**: {summary['overall_status']}")
            st.write(f"- **Valid Matches**: {summary['valid_matches']}")
            st.write(f"- **Confidence Score**: {summary['confidence_score']:.0%}")
            st.write(f"- **Weighted Score**: {summary['weighted_score']:.0%}")
        
        # Download buttons
        st.markdown("### 📥 Download Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            json_str = json.dumps(result_data, indent=2, ensure_ascii=False)
            st.download_button(
                "📄 Download JSON Report",
                json_str,
                f"extraction_report_{st.session_state.session_id[:8]}.json",
                "application/json",
                use_container_width=True
            )
        
        with col2:
            import csv
            import io
            
            # Prepare CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Field", "OCR Value", "User Value", "Status", "Match %"])
            
            for result in st.session_state.comparison_result["detailed_results"]:
                writer.writerow([
                    result["field_name"],
                    result["ocr_value"],
                    result["user_value"],
                    result["status"],
                    f"{result['similarity_score']:.0%}"
                ])
            
            st.download_button(
                "📊 Download CSV Report",
                csv_buffer.getvalue(),
                f"extraction_report_{st.session_state.session_id[:8]}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col3:
            if st.button("💾 Save to Database", use_container_width=True):
                try:
                    storage = IDCardStorage()
                    storage_result = storage.store_extraction(
                        st.session_state.ocr_data,
                        portrait_path=None,
                        validation_summary=st.session_state.comparison_result["summary"]
                    )
                    if storage_result["success"]:
                        st.success(f"✅ Saved! Record ID: {storage_result['record_id']}")
                    else:
                        st.error(f"❌ Storage failed: {storage_result['message']}")
                except Exception as e:
                    st.error(f"❌ Error saving to database: {str(e)}")
        
        # Full report view
        with st.expander("📖 View Full Report"):
            st.json(result_data)


def extract_with_easyocr(image_bgr, preprocess: bool = True) -> Tuple[str, float]:
    """Extract text using EasyOCR (fallback).
    
    Args:
        image_bgr: Input image in BGR format
        preprocess: Whether to preprocess
        
    Returns:
        Tuple of (text, confidence)
    """
    from face_extractor.text_extractor import _extract_text_with_ocr, _get_ocr_reader
    
    try:
        text = _extract_text_with_ocr(image_bgr, preprocess)
        # Estimate confidence
        return text, 0.75
    except Exception as e:
        logger.error(f"EasyOCR extraction failed: {e}")
        return "", 0.0


if __name__ == "__main__":
    main()
