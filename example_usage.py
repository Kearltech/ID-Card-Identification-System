"""Example usage script for ID card extraction system.

This script demonstrates how to use the improved ID card extraction system
programmatically (without Streamlit UI).
"""

import cv2
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from face_extractor.text_extractor import process_id_card
from face_extractor.validator import validate_all_fields
from face_extractor.data_storage import IDCardStorage
from face_extractor.detector import detect_faces, crop_regions


def extract_id_card(image_path: str, output_dir: str = "outputs"):
    """Extract information from an ID card image.
    
    Args:
        image_path: Path to ID card image
        output_dir: Directory to save outputs
    """
    print(f"Processing ID card: {image_path}")
    
    # Load image
    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        return None
    
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        print(f"Error: Could not load image: {image_path}")
        return None
    
    print("✓ Image loaded successfully")
    
    # Step 1: Extract text and detect card type
    print("\n[Step 1] Extracting text and detecting card type...")
    try:
        card_data = process_id_card(image_bgr, preprocess=True)
        print(f"✓ Card type detected: {card_data['card_type']} (confidence: {card_data['card_type_confidence']:.2%})")
        print(f"✓ OCR text extracted ({len(card_data['ocr_text'])} characters)")
    except Exception as e:
        print(f"✗ OCR extraction failed: {e}")
        return None
    
    # Step 2: Validate extracted fields
    print("\n[Step 2] Validating extracted fields...")
    validation_results = validate_all_fields(
        card_data["fields"],
        card_data.get("card_type", "Unknown")
    )
    
    validated_fields = validation_results["validated_fields"]
    invalid_fields = validation_results["invalid_fields"]
    
    print(f"✓ Validated {len(validated_fields)} fields")
    if invalid_fields:
        print(f"⚠ {len(invalid_fields)} fields failed validation:")
        for field, error in invalid_fields.items():
            print(f"  - {field}: {error}")
    
    # Step 3: Detect and crop portrait
    print("\n[Step 3] Detecting face and cropping portrait...")
    detections = detect_faces(image_bgr, min_confidence=0.6)
    
    if len(detections) == 0:
        print("⚠ No faces detected")
        portrait_path = None
    else:
        # Sort by area and get largest
        detections.sort(key=lambda d: (d[0][2] - d[0][0]) * (d[0][3] - d[0][1]), reverse=True)
        main_detection = detections[0]
        boxes = [main_detection[0]]
        
        # Crop portrait
        crops = crop_regions(image_bgr, boxes, margin_percent=10)
        if len(crops) > 0:
            # Save portrait
            os.makedirs(os.path.join(output_dir, "portraits"), exist_ok=True)
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            portrait_filename = f"portrait_{timestamp}.jpg"
            portrait_path = os.path.join(output_dir, "portraits", portrait_filename)
            cv2.imwrite(portrait_path, crops[0])
            print(f"✓ Portrait saved: {portrait_path}")
        else:
            portrait_path = None
            print("⚠ Failed to crop portrait")
    
    # Step 4: Store in database and CSV
    print("\n[Step 4] Storing extracted data...")
    try:
        storage = IDCardStorage(
            db_path=os.path.join(output_dir, "id_cards.db"),
            csv_path=os.path.join(output_dir, "id_cards.csv")
        )
        
        storage_result = storage.store_extraction(
            card_data,
            portrait_path=portrait_path,
            validation_summary=validation_results
        )
        
        if storage_result["success"]:
            print(f"✓ Data stored successfully (Record ID: {storage_result['record_id']})")
            print(f"  - Database: {storage.db_path}")
            print(f"  - CSV: {storage.csv_path}")
        else:
            print(f"✗ Failed to store data: {storage_result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"✗ Storage failed: {e}")
    
    # Step 5: Display results
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    print(f"Card Type: {card_data['card_type']}")
    print(f"Confidence: {card_data['card_type_confidence']:.2%}")
    print(f"\nExtracted Fields ({len(validated_fields)} validated):")
    for field, value in validated_fields.items():
        print(f"  • {field}: {value}")
    
    if invalid_fields:
        print(f"\nInvalid Fields ({len(invalid_fields)}):")
        for field, error in invalid_fields.items():
            print(f"  • {field}: {error}")
    
    if portrait_path:
        print(f"\nPortrait: {portrait_path}")
    
    print("="*60)
    
    return {
        "card_data": card_data,
        "validation_results": validation_results,
        "portrait_path": portrait_path
    }


def query_database(card_type: str = None):
    """Query stored ID card records.
    
    Args:
        card_type: Optional card type filter
    """
    print("\n" + "="*60)
    print("DATABASE QUERY")
    print("="*60)
    
    try:
        storage = IDCardStorage()
        
        if card_type:
            records = storage.query_by_card_type(card_type)
            print(f"Records for card type '{card_type}': {len(records)}")
        else:
            records = storage.get_all_records(limit=10)
            print(f"Recent records (last 10): {len(records)}")
        
        for i, record in enumerate(records, 1):
            print(f"\n[{i}] Record ID: {record.get('id', 'N/A')}")
            print(f"    Card Type: {record.get('card_type', 'N/A')}")
            print(f"    Name: {record.get('name', 'N/A')}")
            print(f"    Date of Birth: {record.get('date_of_birth', 'N/A')}")
            print(f"    Extracted: {record.get('extraction_timestamp', 'N/A')}")
        
        # Get statistics
        stats = storage.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  Total Records: {stats['total_records']}")
        print(f"  Card Type Counts: {stats['card_type_counts']}")
        print(f"  Latest Extraction: {stats['latest_extraction']}")
        
    except Exception as e:
        print(f"Error querying database: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ID Card Extraction Example")
    parser.add_argument("image_path", nargs="?", help="Path to ID card image")
    parser.add_argument("--query", action="store_true", help="Query database instead of processing image")
    parser.add_argument("--card-type", help="Filter by card type when querying")
    parser.add_argument("--output-dir", default="outputs", help="Output directory")
    
    args = parser.parse_args()
    
    if args.query:
        query_database(card_type=args.card_type)
    elif args.image_path:
        extract_id_card(args.image_path, args.output_dir)
    else:
        print("Usage:")
        print("  Process image: python example_usage.py <image_path>")
        print("  Query database: python example_usage.py --query")
        print("  Query by type: python example_usage.py --query --card-type 'Ghana Card'")

