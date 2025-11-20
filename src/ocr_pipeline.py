"""
Label-Guided OCR Pipeline

Complete end-to-end pipeline for:
1. ID card type detection
2. Field schema loading
3. OCR text extraction
4. Field parsing and matching
5. User input validation
6. Database storage
"""

import logging
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class LabelGuidedOCRPipeline:
    """
    Complete label-guided OCR pipeline for ID card verification.
    
    Pipeline steps:
    1. Load field schema for ID type
    2. Extract text using OCR
    3. Parse and match fields based on labels
    4. Validate extracted fields
    5. Compare with user input
    6. Store results in database
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        """
        Initialize OCR pipeline.
        
        Args:
            gemini_api_key: Optional Gemini API key for Vision-based OCR
        """
        from ocr_text_extractor import OCRTextExtractor
        from ocr_field_parser import FieldParser, FieldValidator
        
        self.extractor = OCRTextExtractor(api_key=gemini_api_key, use_gemini=True)
        self.parser = FieldParser()
        self.validator = FieldValidator()
        
        logger.info("Label-Guided OCR Pipeline initialized")
    
    def process_id_card(self, image_input, id_type: str) -> Dict[str, Any]:
        """
        Process an ID card image through complete pipeline.
        
        Args:
            image_input: Image file path, numpy array, or PIL Image
            id_type: Type of ID card (ghana_card, passport, voters_id, drivers_license)
        
        Returns:
            Dictionary with processing results
        """
        result = {
            "id_type": id_type,
            "status": "processing",
            "steps": {},
            "error": None
        }
        
        try:
            # Step 1: Extract text from image
            logger.info(f"Step 1: Extracting text from {id_type}...")
            raw_text, engine_used = self.extractor.extract_text(image_input)
            
            if not raw_text:
                result["status"] = "failed"
                result["error"] = "OCR extraction failed - no text detected"
                logger.error(result["error"])
                return result
            
            result["steps"]["text_extraction"] = {
                "status": "success",
                "engine": engine_used,
                "text_length": len(raw_text),
                "preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text
            }
            
            # Step 2: Parse fields from extracted text
            logger.info("Step 2: Parsing fields from extracted text...")
            extracted_fields = self.parser.parse_fields_from_text(raw_text, id_type)
            
            extracted_count = len([f for f in extracted_fields.values() if f is not None])
            result["steps"]["field_parsing"] = {
                "status": "success",
                "fields_found": extracted_count,
                "total_fields": len(extracted_fields)
            }
            
            # Step 3: Validate extracted fields
            logger.info("Step 3: Validating extracted fields...")
            validation = self.validator.validate_extracted_fields(extracted_fields, id_type)
            
            result["steps"]["field_validation"] = {
                "status": "success",
                "overall_valid": validation["overall_valid"],
                "valid_count": len(validation["valid_fields"]),
                "invalid_count": len(validation["invalid_fields"]),
                "missing_required": validation["missing_required"]
            }
            
            # Compile final results
            result["status"] = "success"
            result["raw_text"] = raw_text
            result["extracted_fields"] = extracted_fields
            result["validation"] = validation
            result["processing_timestamp"] = datetime.now().isoformat()
            
            logger.info(f"Successfully processed {id_type}: {extracted_count} fields extracted")
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"Pipeline error: {e}", exc_info=True)
        
        return result
    
    def validate_user_input(self, user_input: Dict[str, Any], 
                          extracted_fields: Dict[str, Any],
                          id_type: str,
                          similarity_threshold: float = 0.85) -> Dict[str, Any]:
        """
        Validate user-provided input against extracted fields.
        
        Args:
            user_input: User-provided field values
            extracted_fields: Fields extracted from ID
            id_type: Type of ID card
            similarity_threshold: Minimum similarity for match (0-1)
        
        Returns:
            Validation and comparison results
        """
        logger.info("Step 4: Comparing user input with extracted fields...")
        
        # Compare fields
        comparison = self.validator.compare_fields(
            user_input, 
            extracted_fields,
            similarity_threshold=similarity_threshold
        )
        
        # Validate extracted fields
        validation = self.validator.validate_extracted_fields(extracted_fields, id_type)
        
        result = {
            "comparison": comparison,
            "validation": validation,
            "overall_match": comparison["overall_confidence"] >= similarity_threshold,
            "match_confidence": comparison["overall_confidence"],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Comparison complete: {result['overall_match']} (confidence: {result['match_confidence']:.2%})")
        
        return result
    
    def full_verification_pipeline(self, image_input, id_type: str, 
                                   user_input: Optional[Dict[str, Any]] = None,
                                   similarity_threshold: float = 0.85) -> Dict[str, Any]:
        """
        Run complete verification pipeline from image to validation.
        
        Args:
            image_input: ID card image
            id_type: Type of ID card
            user_input: Optional user-provided data for comparison
            similarity_threshold: Minimum similarity for match
        
        Returns:
            Complete verification results
        """
        logger.info("="*50)
        logger.info(f"Starting full verification pipeline for {id_type}")
        logger.info("="*50)
        
        # Step 1-3: Process ID card
        process_result = self.process_id_card(image_input, id_type)
        
        if process_result["status"] != "success":
            return process_result
        
        # Step 4: Validate user input if provided
        validation_result = None
        if user_input:
            validation_result = self.validate_user_input(
                user_input,
                process_result["extracted_fields"],
                id_type,
                similarity_threshold=similarity_threshold
            )
        
        # Compile complete result
        final_result = {
            "status": "success",
            "id_type": id_type,
            "id_card_processing": process_result,
            "user_validation": validation_result,
            "overall_verification": {
                "id_valid": process_result["steps"]["field_validation"]["overall_valid"],
                "user_match": validation_result["overall_match"] if validation_result else None,
                "verification_passed": (
                    process_result["steps"]["field_validation"]["overall_valid"] and 
                    (validation_result["overall_match"] if validation_result else True)
                )
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("="*50)
        logger.info(f"Pipeline complete: {final_result['overall_verification']['verification_passed']}")
        logger.info("="*50)
        
        return final_result
    
    def export_to_json(self, result: Dict[str, Any]) -> str:
        """
        Export pipeline result as JSON.
        
        Args:
            result: Pipeline result dictionary
        
        Returns:
            JSON string
        """
        return json.dumps(result, indent=2, default=str)
    
    def get_summary(self, result: Dict[str, Any]) -> str:
        """
        Get human-readable summary of pipeline results.
        
        Args:
            result: Pipeline result dictionary
        
        Returns:
            Summary string
        """
        if result["status"] != "success":
            return f"Error: {result.get('error', 'Unknown error')}"
        
        lines = [
            "="*50,
            "OCR PIPELINE SUMMARY",
            "="*50,
            f"ID Type: {result['id_type']}",
            f"Status: {result['status']}",
        ]
        
        if "id_card_processing" in result:
            proc = result["id_card_processing"]
            lines.append(f"\nID Card Processing:")
            lines.append(f"  - Engine: {proc['steps']['text_extraction']['engine']}")
            lines.append(f"  - Fields extracted: {proc['steps']['field_parsing']['fields_found']}/{proc['steps']['field_parsing']['total_fields']}")
            lines.append(f"  - Valid: {proc['steps']['field_validation']['overall_valid']}")
            
            if proc['steps']['field_validation']['missing_required']:
                lines.append(f"  - Missing required: {', '.join(proc['steps']['field_validation']['missing_required'])}")
        
        if "user_validation" in result and result["user_validation"]:
            val = result["user_validation"]
            lines.append(f"\nUser Validation:")
            lines.append(f"  - Match confidence: {val['match_confidence']:.1%}")
            lines.append(f"  - Overall match: {val['overall_match']}")
            lines.append(f"  - Matching fields: {len(val['comparison']['matches'])}")
            lines.append(f"  - Mismatches: {len(val['comparison']['mismatches'])}")
            lines.append(f"  - Missing on ID: {len(val['comparison']['missing_on_id'])}")
        
        if "overall_verification" in result:
            ov = result["overall_verification"]
            lines.append(f"\nOverall Verification:")
            lines.append(f"  - ID Valid: {ov['id_valid']}")
            lines.append(f"  - User Match: {ov['user_match']}")
            lines.append(f"  - VERIFICATION PASSED: {ov['verification_passed']}")
        
        lines.append("="*50)
        
        return "\n".join(lines)
    
    def get_available_ocr_engines(self) -> Dict[str, bool]:
        """Get status of available OCR engines."""
        return self.extractor.get_available_engines()
