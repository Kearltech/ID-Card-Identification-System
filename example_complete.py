"""
Complete example demonstrating the ID card extraction, verification, and comparison workflow.

This script shows:
1. Extracting data from an ID card image
2. Getting user input for verification
3. Comparing OCR data with user input
4. Storing results in database
5. Generating comprehensive reports
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import cv2
import numpy as np

from face_extractor.text_extractor import process_id_card
from face_extractor.validator import validate_all_fields
from face_extractor.data_storage import IDCardStorage
from face_extractor.detector import detect_faces, crop_regions
from face_extractor.advanced_ocr import create_ocr_engine, OCREngine
from face_extractor.comparison_engine import compare_extractions
from face_extractor.user_verification import create_user_form, UserDataStore


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(text: str):
    """Print formatted section."""
    print(f"\n▶ {text}")
    print("-" * 80)


def print_result(status: str, message: str):
    """Print formatted result."""
    if "✓" in status or "Success" in status:
        print(f"  ✅ {status}: {message}")
    elif "⚠" in status or "Warning" in status:
        print(f"  ⚠️  {status}: {message}")
    else:
        print(f"  ℹ️  {message}")


def demo_basic_extraction(image_path: str):
    """Demonstrate basic OCR extraction.
    
    Args:
        image_path: Path to ID card image
    """
    print_header("DEMO 1: Basic OCR Extraction")
    
    # Load image
    print_section("Loading Image")
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        print("   Please provide a valid ID card image path")
        return None
    
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        print(f"❌ Failed to load image: {image_path}")
        return None
    
    h, w = image_bgr.shape[:2]
    print_result("✓ Loaded", f"{w}×{h} pixels from {Path(image_path).name}")
    
    # Extract text
    print_section("OCR Extraction (Standard)")
    try:
        card_data = process_id_card(image_bgr, preprocess=True)
        print_result("✓ Success", f"Card type: {card_data['card_type']}")
        print_result("✓ Confidence", f"{card_data['card_type_confidence']:.0%}")
        
        fields = card_data.get("fields", {})
        extracted_count = len([v for v in fields.values() if v])
        print_result("✓ Fields", f"Extracted {extracted_count} fields")
        
        return card_data
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return None


def demo_advanced_ocr(image_path: str):
    """Demonstrate advanced OCR with multiple engines.
    
    Args:
        image_path: Path to ID card image
    """
    print_header("DEMO 2: Advanced OCR (Hybrid Engine)")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        print(f"❌ Failed to load image")
        return
    
    print_section("Initializing Hybrid OCR Engine")
    try:
        ocr_engine = create_ocr_engine("hybrid", use_gpu=False)
        print_result("✓ Initialized", "Hybrid OCR engine (EasyOCR + PaddleOCR)")
    except Exception as e:
        print(f"⚠️  Advanced OCR not available: {e}")
        print("   Falling back to standard extraction")
        return
    
    print_section("Extracting with Advanced Preprocessing")
    try:
        result = ocr_engine.extract_text(image_bgr, preprocess=True)
        print_result("✓ Extraction", f"Engine: {result['engine']}")
        print_result("✓ Confidence", f"Average: {result['confidence']:.0%}")
        print_result("✓ Regions", f"Detected {len(result['detailed_results'])} text regions")
        
        # Show sample text
        text_preview = result["full_text"][:100]
        print_result("✓ Sample", f"First 100 chars: {text_preview}...")
    except Exception as e:
        print(f"❌ Advanced OCR failed: {e}")


def demo_user_verification(card_data: dict):
    """Demonstrate user verification workflow.
    
    Args:
        card_data: Extracted card data
    """
    print_header("DEMO 3: User Verification & Input")
    
    if not card_data:
        print("❌ No card data provided")
        return None
    
    card_type = card_data.get("card_type", "Ghana Card")
    print_section(f"Creating Verification Form for {card_type}")
    
    # Create form
    user_form = create_user_form(card_type)
    form_fields = user_form.get_form_fields()
    print_result("✓ Form", f"Created form with {len(form_fields)} fields")
    
    # Simulate user input
    print_section("Simulating User Input (Auto-filled from OCR)")
    
    user_data = {}
    ocr_fields = card_data.get("fields", {})
    
    for field_name, field_def in form_fields.items():
        # Use OCR data if available, otherwise mock
        if field_name in ocr_fields and ocr_fields[field_name]:
            value = ocr_fields[field_name]
        else:
            # Mock values for demo
            if "Date" in field_name:
                value = "1990-12-25"
            elif "Birth" in field_name:
                value = "1990-12-25"
            elif "Name" in field_name or "Surname" in field_name:
                value = "Doe"
            elif "Firstnames" in field_name:
                value = "John"
            elif "ID" in field_name or "Number" in field_name:
                value = "GHA-123456789-0"
            else:
                value = ""
        
        if value:
            user_data[field_name] = value
    
    print_result("✓ Input", f"Collected {len(user_data)} field values")
    
    # Validate
    print_section("Validating User Input")
    
    is_valid, errors = user_form.validate_input(user_data)
    if is_valid:
        print_result("✓ Valid", "All required fields are valid")
    else:
        print(f"⚠️  Validation errors ({len(errors)}):")
        for field, error in errors.items():
            print(f"   - {field}: {error}")
    
    return user_data if is_valid else None


def demo_comparison(ocr_data: dict, user_data: dict):
    """Demonstrate data comparison.
    
    Args:
        ocr_data: Extracted data from OCR
        user_data: User-provided data
    """
    print_header("DEMO 4: Field-by-Field Comparison")
    
    if not ocr_data or not user_data:
        print("❌ Missing OCR or user data")
        return None
    
    print_section("Performing Comparison")
    
    ocr_fields = ocr_data.get("fields", {})
    comparison_result = compare_extractions(ocr_fields, user_data)
    
    summary = comparison_result["summary"]
    print_result("✓ Status", summary["overall_status"])
    print_result("✓ Confidence", f"{summary['confidence_score']:.0%}")
    print_result("✓ Weighted Score", f"{summary['weighted_score']:.0%}")
    
    print_section("Detailed Results")
    print(f"  Total Fields: {summary['total_fields']}")
    print(f"  ✅ Valid Matches: {summary['valid_matches']}")
    print(f"  ⚠️  Partial Matches: {summary['partial_matches']}")
    print(f"  ❌ Mismatches: {summary['mismatches']}")
    print(f"  ⚠️  Missing (OCR): {summary['missing_ocr']}")
    print(f"  ⚠️  Missing (User): {summary['missing_user']}")
    
    print_section("Field-by-Field Analysis")
    detailed = comparison_result["detailed_results"]
    
    # Group by status
    by_status = comparison_result["by_status"]
    
    if by_status.get("✅ Valid Match"):
        print(f"\n✅ Valid Matches ({len(by_status['✅ Valid Match'])}):")
        for result in by_status["✅ Valid Match"][:3]:  # Show first 3
            print(f"   • {result['field_name']}: {result['ocr_value'][:30]}")
    
    if by_status.get("⚠️ Partial Match"):
        print(f"\n⚠️  Partial Matches ({len(by_status['⚠️ Partial Match'])}):")
        for result in by_status["⚠️ Partial Match"][:3]:
            print(f"   • {result['field_name']}: {result['similarity_score']:.0%} match")
    
    if by_status.get("❌ Invalid/Mismatch"):
        print(f"\n❌ Mismatches ({len(by_status['❌ Invalid/Mismatch'])}):")
        for result in by_status["❌ Invalid/Mismatch"][:3]:
            print(f"   • {result['field_name']}: Mismatch")
    
    print_section("Recommendations")
    recommendations = comparison_result["recommendations"]
    for rec in recommendations[:3]:  # Show first 3
        print(f"  • {rec}")
    
    return comparison_result


def demo_face_detection(image_path: str):
    """Demonstrate portrait extraction.
    
    Args:
        image_path: Path to ID card image
    """
    print_header("DEMO 5: Portrait Extraction")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        print(f"❌ Failed to load image")
        return
    
    print_section("Detecting Faces")
    
    try:
        detections = detect_faces(image_bgr, min_confidence=0.6)
        
        if len(detections) == 0:
            print("⚠️  No faces detected")
            return
        
        print_result("✓ Detected", f"{len(detections)} face(s)")
        
        # Sort by area
        detections.sort(key=lambda d: (d[0][2] - d[0][0]) * (d[0][3] - d[0][1]), reverse=True)
        
        # Crop main face
        print_section("Cropping Main Portrait")
        
        boxes = [detections[0][0]]
        crops = crop_regions(image_bgr, boxes, margin_percent=10)
        
        if crops:
            print_result("✓ Cropped", f"Portrait dimensions: {crops[0].shape[1]}×{crops[0].shape[0]}")
            
            # Save
            os.makedirs("outputs/portraits", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            portrait_path = f"outputs/portraits/portrait_{timestamp}.jpg"
            cv2.imwrite(portrait_path, crops[0])
            print_result("✓ Saved", f"Portrait saved to {portrait_path}")
        else:
            print("❌ Failed to crop portrait")
    
    except Exception as e:
        print(f"❌ Face detection failed: {e}")


def demo_data_storage(ocr_data: dict, comparison_result: dict):
    """Demonstrate data storage.
    
    Args:
        ocr_data: Extracted data
        comparison_result: Comparison results
    """
    print_header("DEMO 6: Data Storage & Retrieval")
    
    if not ocr_data:
        print("❌ No data to store")
        return
    
    print_section("Storing in SQLite & CSV")
    
    try:
        storage = IDCardStorage()
        
        storage_result = storage.store_extraction(
            ocr_data,
            portrait_path=None,
            validation_summary=comparison_result.get("summary") if comparison_result else None
        )
        
        if storage_result["success"]:
            print_result("✓ Stored", f"Record ID: {storage_result['record_id']}")
            print_result("✓ Database", f"Path: {storage.db_path}")
            print_result("✓ CSV Export", f"Path: {storage.csv_path}")
        else:
            print(f"❌ Storage failed: {storage_result['message']}")
    
    except Exception as e:
        print(f"❌ Storage error: {e}")


def demo_full_workflow(image_path: str):
    """Run complete workflow demonstration.
    
    Args:
        image_path: Path to ID card image
    """
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "ID CARD EXTRACTION SYSTEM - COMPLETE WORKFLOW DEMO" + " " * 15 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Step 1: Basic Extraction
    card_data = demo_basic_extraction(image_path)
    if not card_data:
        print("\n❌ Demo stopped: Could not extract data")
        return
    
    # Step 2: Advanced OCR (optional)
    demo_advanced_ocr(image_path)
    
    # Step 3: User Verification
    user_data = demo_user_verification(card_data)
    if not user_data:
        print("\n⚠️  Demo stopped: User verification failed")
        return
    
    # Step 4: Comparison
    comparison_result = demo_comparison(card_data, user_data)
    if not comparison_result:
        print("\n❌ Demo stopped: Comparison failed")
        return
    
    # Step 5: Portrait Extraction
    demo_face_detection(image_path)
    
    # Step 6: Storage
    demo_data_storage(card_data, comparison_result)
    
    # Final summary
    print_header("DEMO SUMMARY")
    print(f"✅ Workflow completed successfully!")
    print(f"✅ Card Type: {card_data['card_type']}")
    print(f"✅ Overall Status: {comparison_result['summary']['overall_status']}")
    print(f"✅ Confidence Score: {comparison_result['summary']['confidence_score']:.0%}")
    print(f"✅ Weighted Score: {comparison_result['summary']['weighted_score']:.0%}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ID Card Extraction System Demo")
    parser.add_argument("image_path", nargs="?", help="Path to ID card image")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5, 6],
                       help="Run only a specific demo step")
    
    args = parser.parse_args()
    
    if not args.image_path:
        print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                     ID Card Extraction System Demo                         ║
╚════════════════════════════════════════════════════════════════════════════╝

Usage: python example_complete.py <image_path> [--step N]

Arguments:
  image_path    Path to ID card image (JPG, PNG, WEBP)
  --step N      Run only step N (1-6):
                1: Basic OCR Extraction
                2: Advanced OCR (Hybrid Engine)
                3: User Verification
                4: Comparison Analysis
                5: Portrait Extraction
                6: Data Storage

Example:
  python example_complete.py path/to/id_card.jpg
  python example_complete.py path/to/id_card.jpg --step 3
        """)
    else:
        if args.step:
            print(f"Running step {args.step}...")
            # Single step execution would go here
        else:
            demo_full_workflow(args.image_path)
