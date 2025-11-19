import io
import json
import os
import sys
import zipfile
from datetime import datetime
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Allow running with `streamlit run src/app.py` by ensuring `src` is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Optional runtime installer note:
# If deploying to Streamlit Community Cloud, requirements.txt is sufficient and preferred.
# This block allows installing missing packages at runtime when the env var
# ALLOW_RUNTIME_INSTALL is set to 1/true. After installing, the app reruns once.
try:
    from utils.bootstrap import ensure_packages  # type: ignore
except Exception:
    # utils may not exist; skip runtime install support
    ensure_packages = None  # type: ignore

installed_runtime = False
if ensure_packages is not None:
    try:
        installed_runtime = ensure_packages(allow_runtime=True)
    except Exception:
        installed_runtime = False

import streamlit as st
# Must be the first Streamlit command in the script
st.set_page_config(page_title="ID Card Extractor", page_icon="🆔", layout="wide")
if installed_runtime:
    st.info("Installed missing packages. Rerunning once...")
    st.rerun()

import cv2
import numpy as np
from PIL import Image

from face_extractor.detector import detect_faces, crop_regions
from face_extractor.text_extractor import process_id_card


@dataclass
class FaceResult:
    bbox: Tuple[int, int, int, int]
    score: float


def load_image_to_bgr(uploaded_file) -> np.ndarray:
    """Load uploaded image and convert to BGR format."""
    data = uploaded_file.read()
    pil_img = Image.open(io.BytesIO(data)).convert("RGB")
    rgb = np.array(pil_img)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def draw_bboxes(image: np.ndarray, boxes: List[Tuple[int, int, int, int]], main_index: int) -> np.ndarray:
    """Draw bounding boxes on image."""
    vis = image.copy()
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        color = (0, 255, 0) if i == main_index else (255, 200, 0)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        label = "main" if i == main_index else "face"
        cv2.putText(vis, label, (x1, max(y1 - 5, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return vis


def to_download_bytes(img: np.ndarray, ext: str = ".jpg") -> bytes:
    """Convert image to bytes for download."""
    ok, buf = cv2.imencode(ext, img)
    return buf.tobytes() if ok else b""


def save_portrait(crop: np.ndarray, output_dir: str = "outputs/portraits") -> str:
    """Save portrait to disk and return file path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"portrait_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, crop)
    return filepath


def save_extraction_data(data: dict, output_dir: str = "outputs/data") -> str:
    """Save extraction data as JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"extraction_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def main():
    st.title("🆔 ID Card Extractor")
    st.caption("Extract portrait photos and structured data from ID card images using OCR and face detection.")

    with st.sidebar:
        st.header("⚙️ Options")
        
        # Face detection options
        st.subheader("Face Detection")
        conf = st.slider("Min confidence", 0.1, 0.99, 0.6, 0.01)
        margin = st.slider("Crop margin (%)", 0, 40, 10, 1)
        mode = st.radio("Return", ["Largest only", "All faces"], index=0)
        max_faces = st.number_input("Max faces (when 'All faces')", min_value=1, max_value=10, value=5, step=1)
        
        st.markdown("---")
        
        # OCR options
        st.subheader("OCR Settings")
        enable_ocr = st.checkbox("Enable OCR & Field Extraction", value=True)
        show_ocr_text = st.checkbox("Show OCR Text", value=False)
        
        st.markdown("---")
        st.markdown("💡 **Tip:** If background faces are detected, capture a tighter photo of the ID.")

    uploaded = st.file_uploader("Upload an ID card image", type=["jpg", "jpeg", "png", "webp"])
    if not uploaded:
        st.info("👆 Please upload an ID card image to get started.")
        st.stop()

    # Load image
    try:
        image_bgr = load_image_to_bgr(uploaded)
    except Exception as e:
        st.error(f"❌ Failed to load image: {str(e)}")
        st.stop()

    # Display original image
    st.subheader("📷 Original Image")
    st.image(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), caption="Uploaded ID Card", use_container_width=True)

    # OCR and field extraction
    card_data = None
    if enable_ocr:
        with st.spinner("🔍 Extracting text and detecting card type..."):
            try:
                card_data = process_id_card(image_bgr)
            except ImportError as e:
                st.warning(f"⚠️ OCR not available: {str(e)}")
                st.info("💡 Install EasyOCR: `pip install easyocr`")
                card_data = None
            except Exception as e:
                st.error(f"❌ OCR processing failed: {str(e)}")
                card_data = None

    # Face detection
    with st.spinner("👤 Detecting faces..."):
        detections = detect_faces(image_bgr, min_confidence=conf)

    if len(detections) == 0:
        st.warning("⚠️ No faces detected. Try lowering the confidence or using a clearer image.")
        if card_data:
            # Still show OCR results even if no face detected
            st.markdown("---")
            display_card_info(card_data, show_ocr_text)
        st.stop()

    # Sort by area (descending) and keep up to max_faces
    detections.sort(key=lambda d: (d[0][2] - d[0][0]) * (d[0][3] - d[0][1]), reverse=True)
    if mode == "Largest only":
        detections = detections[:1]
    else:
        detections = detections[:max_faces]

    boxes = [d[0] for d in detections]
    main_idx = 0  # after sorting, first is largest
    vis = draw_bboxes(image_bgr, boxes, main_idx)
    
    st.subheader("👤 Face Detections")
    st.image(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), caption="Detected Faces", use_container_width=True)

    # Crop faces
    crops = crop_regions(image_bgr, boxes, margin_percent=margin)
    if len(crops) == 0:
        st.error("❌ Failed to crop faces.")
        if card_data:
            st.markdown("---")
            display_card_info(card_data, show_ocr_text)
        st.stop()

    # Display card information if OCR was enabled
    if card_data:
        st.markdown("---")
        display_card_info(card_data, show_ocr_text)

    # Display cropped portraits
    st.subheader("🖼️ Cropped Portraits")
    cols = st.columns(min(3, len(crops)))
    zip_buffer = io.BytesIO()
    
    # Save main portrait
    main_portrait_path = None
    if len(crops) > 0:
        main_portrait_path = save_portrait(crops[0])
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, crop in enumerate(crops):
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            cols[i % len(cols)].image(rgb, caption=f"Portrait {i+1}")
            # Add to ZIP
            zf.writestr(f"portrait_{i+1}.jpg", to_download_bytes(crop))
            
            # Save individual portraits
            save_portrait(crop)

    # Download buttons
    st.markdown("---")
    st.subheader("📥 Downloads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if len(crops) > 0:
            main_bytes = to_download_bytes(crops[0])
            st.download_button(
                "📷 Download Main Portrait",
                data=main_bytes,
                file_name="portrait_main.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
    
    with col2:
        zip_buffer.seek(0)
        st.download_button(
            "📦 Download All Portraits (ZIP)",
            data=zip_buffer,
            file_name="portraits.zip",
            mime="application/zip",
            use_container_width=True
        )
    
    with col3:
        if card_data and main_portrait_path:
            # Prepare JSON data
            json_data = {
                "card_type": card_data["card_type"],
                "card_type_confidence": round(card_data["card_type_confidence"], 2),
                "fields": {k: v for k, v in card_data["fields"].items() if v is not None},
                "portrait_path": main_portrait_path
            }
            
            # Save JSON file
            json_path = save_extraction_data(json_data)
            
            # Download button
            json_bytes = json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')
            st.download_button(
                "📄 Download JSON Data",
                data=json_bytes,
                file_name="extraction_data.json",
                mime="application/json",
                use_container_width=True
            )


def display_card_info(card_data: dict, show_ocr_text: bool = False):
    """Display card type and extracted fields."""
    st.subheader("📋 Extracted Information")
    
    # Card type
    card_type = card_data["card_type"]
    confidence = card_data["card_type_confidence"]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Card Type", card_type)
    with col2:
        st.metric("Detection Confidence", f"{confidence:.0%}")
    
    if card_type == "Unknown":
        st.warning("⚠️ Could not automatically detect card type. Please verify manually.")
    
    # Extracted fields
    fields = card_data.get("fields", {})
    non_empty_fields = {k: v for k, v in fields.items() if v is not None and str(v).strip()}
    
    if non_empty_fields:
        st.markdown("#### Extracted Fields")
        
        # Create table
        import pandas as pd
        df = pd.DataFrame([
            {"Field": field, "Value": value}
            for field, value in non_empty_fields.items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show extraction statistics
        total_fields = len(fields)
        extracted_count = len(non_empty_fields)
        extraction_rate = (extracted_count / total_fields * 100) if total_fields > 0 else 0
        st.caption(f"📊 Extracted {extracted_count} out of {total_fields} fields ({extraction_rate:.1f}%)")
    else:
        st.info("ℹ️ No fields could be extracted. This may be due to image quality or card type mismatch.")
    
    # Show OCR text if requested
    if show_ocr_text:
        st.markdown("---")
        st.subheader("📝 OCR Text")
        ocr_text = card_data.get("ocr_text", "")
        if ocr_text:
            st.text_area("Raw OCR Output", ocr_text, height=200, disabled=True)
        else:
            st.info("No OCR text available.")


if __name__ == "__main__":
    main()
