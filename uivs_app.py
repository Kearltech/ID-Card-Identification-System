"""
Universal ID Verification System (UIVS) - Main Streamlit Application
A complete ID verification pipeline combining face matching, OCR, and database storage.
"""

import streamlit as st
import os
import sys
import io
import json
import logging
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Any
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import custom modules
try:
    from src.uivs_database import UIVSDatabase
    from src.face_comparator import FaceComparator, extract_and_standardize_face
    from src.id_card_classifier import IDCardClassifier
    from src.face_extractor.detector import detect_faces, crop_regions
    from src.face_extractor.text_extractor import process_id_card
except Exception as e:
    logger.error(f"Import error: {e}")
    st.error(f"Failed to import modules: {e}")
    st.stop()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="🆔 Universal ID Verification System",
    page_icon="🆔",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header { text-align: center; }
    .success-box { background-color: #d4edda; padding: 20px; border-radius: 5px; border-left: 4px solid #28a745; }
    .error-box { background-color: #f8d7da; padding: 20px; border-radius: 5px; border-left: 4px solid #dc3545; }
    .warning-box { background-color: #fff3cd; padding: 20px; border-radius: 5px; border-left: 4px solid #ffc107; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZE SESSION STATE
# ============================================================================

if "current_step" not in st.session_state:
    st.session_state.current_step = 1

if "portrait_image" not in st.session_state:
    st.session_state.portrait_image = None

if "id_type" not in st.session_state:
    st.session_state.id_type = None

if "id_number" not in st.session_state:
    st.session_state.id_number = ""

if "id_card_image" not in st.session_state:
    st.session_state.id_card_image = None

if "verification_result" not in st.session_state:
    st.session_state.verification_result = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_database():
    """Load UIVS database."""
    db_path = os.path.join(CURRENT_DIR, "outputs", "uivs_verification.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return UIVSDatabase(db_path)

def image_to_bytes(image: Image.Image) -> bytes:
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()

def process_verification(
    portrait_image: Image.Image,
    id_card_image: Image.Image,
    id_type: str,
    id_number: str,
    user_entered_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform complete verification process.
    """
    
    logger.info(f"Starting verification process for {id_type}")
    verification_result = {
        "status": "UNKNOWN",
        "card_type_match": False,
        "id_number_match": False,
        "face_match": False,
        "overall_match": False,
        "confidence_score": 0.0,
        "details": {},
        "warnings": [],
        "errors": []
    }
    
    # Step 1: Classify ID Card Type
    st.info("🔍 Step 1: Analyzing ID card type...")
    classifier = IDCardClassifier(engine="hybrid")
    classification = classifier.classify(id_card_image, id_type)
    
    verification_result["details"]["classification"] = classification
    verification_result["card_type_match"] = classification["matches_user_selection"]
    
    if not verification_result["card_type_match"]:
        verification_result["warnings"].append(
            f"⚠️ Card type mismatch! Expected {id_type}, but detected {classification['card_type']} "
            f"(confidence: {classification['confidence']:.0%})"
        )
    
    # Step 2: Extract Text from ID Card
    st.info("🔤 Step 2: Extracting text from ID card...")
    try:
        id_card_cv = cv2.cvtColor(np.array(id_card_image), cv2.COLOR_RGB2BGR)
        ocr_result = process_id_card(id_card_cv)
        
        verification_result["details"]["ocr_result"] = ocr_result
        
        # Extract ID number from OCR
        extracted_id_number = ocr_result.get("fields", {}).get("id_number") or \
                             ocr_result.get("fields", {}).get("document_number") or \
                             ocr_result.get("fields", {}).get("passport_number")
        
        if extracted_id_number:
            verification_result["id_number_match"] = (
                str(extracted_id_number).strip().upper() == str(id_number).strip().upper()
            )
        
        if not verification_result["id_number_match"]:
            verification_result["warnings"].append(
                f"⚠️ ID number mismatch! Entered: {id_number}, Extracted: {extracted_id_number}"
            )
    
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        verification_result["errors"].append(f"OCR extraction failed: {str(e)}")
        verification_result["details"]["ocr_result"] = None
    
    # Step 3: Extract Face from ID Card
    st.info("👤 Step 3: Extracting face from ID card...")
    try:
        id_card_cv = cv2.cvtColor(np.array(id_card_image), cv2.COLOR_RGB2BGR)
        id_card_face = extract_and_standardize_face(id_card_cv)
        
        if id_card_face is None:
            verification_result["errors"].append("Could not detect face on ID card")
        else:
            verification_result["details"]["id_card_face"] = id_card_face
    
    except Exception as e:
        logger.error(f"Face extraction failed: {e}")
        verification_result["errors"].append(f"Face extraction failed: {str(e)}")
    
    # Step 4: Compare Faces
    st.info("🔄 Step 4: Comparing faces...")
    if "id_card_face" in verification_result["details"] and id_card_face:
        try:
            comparator = FaceComparator(engine="auto")
            face_comparison = comparator.compare_faces(portrait_image, id_card_face)
            
            verification_result["details"]["face_comparison"] = face_comparison
            verification_result["face_match"] = face_comparison["match"]
            verification_result["confidence_score"] = face_comparison["similarity_score"]
            
            if not verification_result["face_match"]:
                verification_result["warnings"].append(
                    f"⚠️ Face mismatch! Similarity: {face_comparison['similarity_score']:.0%} "
                    f"(Threshold: 55%)"
                )
        
        except Exception as e:
            logger.error(f"Face comparison failed: {e}")
            verification_result["errors"].append(f"Face comparison failed: {str(e)}")
    
    # Determine overall verification status
    if len(verification_result["errors"]) > 0:
        verification_result["status"] = "ERROR"
    elif verification_result["card_type_match"] and \
         verification_result["id_number_match"] and \
         verification_result["face_match"]:
        verification_result["status"] = "VERIFIED"
        verification_result["overall_match"] = True
    else:
        verification_result["status"] = "FAILED"
    
    return verification_result

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main app logic."""
    
    st.markdown("<h1 class='main-header'>🆔 Universal ID Verification System</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>AI-powered identity verification using face matching and OCR</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📋 Navigation")
        
        step = st.radio(
            "Select Step:",
            [
                "1️⃣ Instructions",
                "2️⃣ Upload Portrait",
                "3️⃣ Select ID Type",
                "4️⃣ Verify Identity",
                "5️⃣ View Results",
                "6️⃣ Admin Panel"
            ],
            index=st.session_state.current_step - 1
        )
        
        st.session_state.current_step = int(step[0])
        
        st.markdown("---")
        
        # Status indicator
        st.subheader("📊 Verification Status")
        if st.session_state.verification_result:
            result = st.session_state.verification_result
            
            if result["status"] == "VERIFIED":
                st.success(f"✅ {result['status']}")
            elif result["status"] == "FAILED":
                st.error(f"❌ {result['status']}")
            else:
                st.warning(f"⚠️ {result['status']}")
            
            st.metric("Confidence", f"{result.get('confidence_score', 0):.0%}")
    
    # ========================================================================
    # STEP 1: Instructions
    # ========================================================================
    if st.session_state.current_step == 1:
        st.header("📖 How UIVS Works")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Verification Process")
            st.write("""
            The Universal ID Verification System (UIVS) verifies your identity through:
            
            1. **Face Comparison** - Compares your passport photo with the face on your ID
            2. **Card Analysis** - Confirms the type of ID you're presenting
            3. **Text Extraction** - Uses AI to read ID information
            4. **Validation** - Checks all information matches
            """)
        
        with col2:
            st.subheader("✅ What We Check")
            st.write("""
            - ✔️ **ID Type Match** - Card type matches what you selected
            - ✔️ **ID Number Match** - ID number matches what you entered
            - ✔️ **Face Match** - Your face matches the ID photo
            
            **All three must match for verification to succeed.**
            """)
        
        st.subheader("🔒 Security & Privacy")
        st.write("""
        - All images processed securely
        - Data encrypted in database
        - Option to delete images after verification
        - Audit trail of all verifications
        """)
        
        st.subheader("📋 Supported ID Types")
        col1, col2, col3, col4 = st.columns(4)
        col1.info("🇬🇭 Ghana Card")
        col2.info("🛂 Passport")
        col3.info("🗳️ Voter ID")
        col4.info("🚗 Driver's License")
        
        if st.button("➡️ Continue to Step 2", key="step1_continue"):
            st.session_state.current_step = 2
            st.rerun()
    
    # ========================================================================
    # STEP 2: Upload Portrait
    # ========================================================================
    elif st.session_state.current_step == 2:
        st.header("📸 Step 2: Upload Passport Photo")
        
        st.write("Upload a clear headshot photo (like a passport photo) for face comparison.")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_portrait = st.file_uploader(
                "Upload portrait/passport photo",
                type=["jpg", "jpeg", "png", "webp"]
            )
            
            if uploaded_portrait:
                portrait_image = Image.open(uploaded_portrait).convert("RGB")
                st.session_state.portrait_image = portrait_image
                
                st.image(portrait_image, caption="Your portrait photo", use_column_width=True)
                
                st.success("✅ Portrait uploaded successfully!")
                
                if st.button("➡️ Continue to Step 3"):
                    st.session_state.current_step = 3
                    st.rerun()
        
        with col2:
            st.info("📝 Tips:\n- Good lighting\n- Clear face\n- Passport style")
    
    # ========================================================================
    # STEP 3: Select ID Type
    # ========================================================================
    elif st.session_state.current_step == 3:
        st.header("🆔 Step 3: Select ID Type")
        
        if not st.session_state.portrait_image:
            st.warning("⚠️ Please upload a portrait photo first (Step 2)")
            if st.button("⬅️ Back to Step 2"):
                st.session_state.current_step = 2
                st.rerun()
        else:
            st.write("Choose the type of ID you'll be verifying:")
            
            id_options = [
                ("🇬🇭 Ghana Card (National ID)", "Ghana Card"),
                ("🛂 Passport", "Passport"),
                ("🗳️ Voter ID", "Voter ID"),
                ("🚗 Driver's License", "Driver's License")
            ]
            
            selected_id = st.radio("ID Type:", [opt[0] for opt in id_options])
            st.session_state.id_type = next(opt[1] for opt in id_options if opt[0] == selected_id)
            
            st.info(f"Selected: {st.session_state.id_type}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("➡️ Continue to Step 4"):
                    st.session_state.current_step = 4
                    st.rerun()
            
            with col2:
                if st.button("⬅️ Back to Step 2"):
                    st.session_state.current_step = 2
                    st.rerun()
    
    # ========================================================================
    # STEP 4: Verify Identity
    # ========================================================================
    elif st.session_state.current_step == 4:
        st.header("🔐 Step 4: Verify Identity")
        
        if not st.session_state.portrait_image or not st.session_state.id_type:
            st.warning("⚠️ Please complete Steps 2 and 3 first")
            if st.button("⬅️ Back"):
                st.session_state.current_step = 2
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📝 Enter Information")
                
                id_number = st.text_input(
                    f"{st.session_state.id_type} Number:",
                    placeholder="Enter ID number"
                )
                st.session_state.id_number = id_number
            
            with col2:
                st.subheader("📷 Upload ID Card")
                
                uploaded_card = st.file_uploader(
                    "Upload ID card image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="id_card_upload"
                )
                
                if uploaded_card:
                    id_card_image = Image.open(uploaded_card).convert("RGB")
                    st.session_state.id_card_image = id_card_image
                    
                    st.image(id_card_image, caption="ID Card", use_column_width=True)
                    st.success("✅ ID card uploaded")
            
            st.markdown("---")
            
            if st.session_state.id_card_image and id_number:
                if st.button("🚀 Start Verification", use_container_width=True):
                    with st.spinner("🔄 Verifying identity..."):
                        # Create dummy user data for now
                        user_data = {
                            "id_type": st.session_state.id_type,
                            "id_number": id_number
                        }
                        
                        result = process_verification(
                            st.session_state.portrait_image,
                            st.session_state.id_card_image,
                            st.session_state.id_type,
                            id_number,
                            user_data
                        )
                        
                        st.session_state.verification_result = result
                        st.session_state.current_step = 5
                        st.rerun()
            else:
                st.warning("⚠️ Please enter ID number and upload card image")
            
            if st.button("⬅️ Back to Step 3"):
                st.session_state.current_step = 3
                st.rerun()
    
    # ========================================================================
    # STEP 5: View Results
    # ========================================================================
    elif st.session_state.current_step == 5:
        st.header("📊 Verification Results")
        
        if not st.session_state.verification_result:
            st.warning("⚠️ No verification result available")
            if st.button("⬅️ Back to Step 4"):
                st.session_state.current_step = 4
                st.rerun()
        else:
            result = st.session_state.verification_result
            
            # Overall status
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if result["status"] == "VERIFIED":
                    st.markdown('<div class="success-box"><h3>✅ VERIFIED</h3></div>', unsafe_allow_html=True)
                elif result["status"] == "FAILED":
                    st.markdown('<div class="error-box"><h3>❌ FAILED</h3></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="warning-box"><h3>⚠️ ERROR</h3></div>', unsafe_allow_html=True)
            
            with col2:
                st.metric("Card Type Match", "✅" if result["card_type_match"] else "❌")
            
            with col3:
                st.metric("ID Number Match", "✅" if result["id_number_match"] else "❌")
            
            with col4:
                st.metric("Face Match", "✅" if result["face_match"] else "❌")
            
            st.markdown("---")
            
            # Detailed results
            st.subheader("🔍 Detailed Verification Report")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Classification")
                if "classification" in result["details"]:
                    clf = result["details"]["classification"]
                    st.write(f"**Detected Type:** {clf['card_type']}")
                    st.write(f"**Confidence:** {clf['confidence']:.0%}")
                    st.write(f"**Method:** {clf['method']}")
            
            with col2:
                st.subheader("Face Comparison")
                if "face_comparison" in result["details"]:
                    face = result["details"]["face_comparison"]
                    st.write(f"**Similarity:** {face['similarity_score']:.0%}")
                    st.write(f"**Engine:** {face['engine_used']}")
                    st.write(f"**Match:** {'✅ Yes' if face['match'] else '❌ No'}")
            
            # Show warnings/errors
            if result["warnings"]:
                st.warning("⚠️ **Warnings**")
                for warning in result["warnings"]:
                    st.write(f"- {warning}")
            
            if result["errors"]:
                st.error("❌ **Errors**")
                for error in result["errors"]:
                    st.write(f"- {error}")
            
            # Image comparison
            st.subheader("👤 Face Comparison")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.image(st.session_state.portrait_image, caption="Your Portrait", use_column_width=True)
            
            with col2:
                st.write("**vs**")
            
            with col3:
                if "id_card_face" in result["details"]:
                    st.image(result["details"]["id_card_face"], caption="ID Card Face", use_column_width=True)
            
            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Save Verification"):
                    db = load_database()
                    
                    # Prepare data for database
                    db_data = {
                        "id_number": st.session_state.id_number,
                        "face_match_score": result.get("confidence_score", 0),
                        "card_type_match": result["card_type_match"],
                        "id_number_match": result["id_number_match"],
                        "validation_result": result["status"],
                        "verification_status": "VERIFIED" if result["status"] == "VERIFIED" else "FAILED",
                        "confidence_score": result.get("confidence_score", 0),
                        "extracted_portrait": image_to_bytes(result["details"].get("id_card_face") or Image.new("RGB", (1, 1))),
                        "uploaded_portrait": image_to_bytes(st.session_state.portrait_image),
                        "notes": json.dumps(result["details"])
                    }
                    
                    # Save based on ID type
                    if st.session_state.id_type == "Ghana Card":
                        db.save_national_id(db_data)
                    elif st.session_state.id_type == "Passport":
                        db.save_passport(db_data)
                    elif st.session_state.id_type == "Voter ID":
                        db.save_voters_id(db_data)
                    elif st.session_state.id_type == "Driver's License":
                        db.save_drivers_license(db_data)
                    
                    st.success("✅ Verification saved to database")
            
            with col2:
                if st.button("🔄 New Verification"):
                    # Reset session state
                    st.session_state.clear()
                    st.rerun()
            
            with col3:
                if st.button("📥 Download Report"):
                    report_json = json.dumps(result, indent=2, default=str)
                    st.download_button(
                        label="Download JSON Report",
                        data=report_json,
                        file_name=f"verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
    
    # ========================================================================
    # STEP 6: Admin Panel
    # ========================================================================
    elif st.session_state.current_step == 6:
        st.header("🔧 Admin Panel")
        
        db = load_database()
        
        st.subheader("📊 Verification Statistics")
        
        stats = db.get_verification_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("National ID (Verified)", stats.get("national_id_verified", 0))
        
        with col2:
            st.metric("Passport (Verified)", stats.get("passport_verified", 0))
        
        with col3:
            st.metric("Voter ID (Verified)", stats.get("voters_id_verified", 0))
        
        with col4:
            st.metric("Driver License (Verified)", stats.get("drivers_license_verified", 0))
        
        st.markdown("---")
        
        st.subheader("📋 Database Info")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.info(f"National ID\nTotal: {stats.get('national_id_total', 0)}")
        
        with col2:
            st.info(f"Passport\nTotal: {stats.get('passport_total', 0)}")
        
        with col3:
            st.info(f"Voter ID\nTotal: {stats.get('voters_id_total', 0)}")
        
        with col4:
            st.info(f"Driver License\nTotal: {stats.get('drivers_license_total', 0)}")
        
        st.info(f"**Verifications in 24h:** {stats.get('verifications_24h', 0)}")

if __name__ == "__main__":
    main()
