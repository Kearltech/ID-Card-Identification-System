"""Comparison engine for validating OCR-extracted data against user input.

This module provides:
- Field-by-field comparison with configurable matching strategies
- Similarity scoring and fuzzy matching
- Comprehensive validation summary
- Detailed mismatch reporting
"""

import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime
import re

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz
    HAVE_RAPIDFUZZ = True
except ImportError:
    HAVE_RAPIDFUZZ = False


class ComparisonResult:
    """Result of a field comparison."""
    
    VALID = "✅ Valid Match"
    PARTIAL = "⚠️ Partial Match"
    INVALID = "❌ Invalid/Mismatch"
    MISSING_OCR = "⚠️ Missing in OCR"
    MISSING_USER = "⚠️ Missing in User Input"
    
    def __init__(self, field_name: str, ocr_value: Optional[str], user_value: Optional[str]):
        """Initialize comparison result.
        
        Args:
            field_name: Name of the field
            ocr_value: Value from OCR extraction
            user_value: Value from user input
        """
        self.field_name = field_name
        self.ocr_value = ocr_value
        self.user_value = user_value
        self.status = self._determine_status()
        self.similarity_score = self._calculate_similarity()
        self.details = self._generate_details()
    
    def _determine_status(self) -> str:
        """Determine comparison status."""
        if not self.ocr_value and not self.user_value:
            return self.MISSING_OCR  # Both missing
        
        if not self.ocr_value:
            return self.MISSING_OCR
        
        if not self.user_value:
            return self.MISSING_USER
        
        # Both present - compare
        similarity = self._calculate_similarity()
        
        if similarity >= 0.95:
            return self.VALID
        elif similarity >= 0.70:
            return self.PARTIAL
        else:
            return self.INVALID
    
    def _calculate_similarity(self) -> float:
        """Calculate similarity score between OCR and user values.
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not self.ocr_value or not self.user_value:
            return 0.0
        
        # Normalize values for comparison
        ocr_norm = self._normalize_value(self.ocr_value)
        user_norm = self._normalize_value(self.user_value)
        
        # Exact match
        if ocr_norm == user_norm:
            return 1.0
        
        # Try fuzzy matching
        if HAVE_RAPIDFUZZ:
            similarity = fuzz.token_set_ratio(ocr_norm, user_norm) / 100.0
        else:
            # Fallback: SequenceMatcher
            similarity = SequenceMatcher(None, ocr_norm, user_norm).ratio()
        
        return similarity
    
    @staticmethod
    def _normalize_value(value: str) -> str:
        """Normalize value for comparison.
        
        Args:
            value: Raw value string
            
        Returns:
            Normalized value
        """
        if not value:
            return ""
        
        # Convert to lowercase
        normalized = value.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # For numeric-looking values, remove non-alphanumeric
        if re.match(r'^[A-Z0-9\-/\s]+$', value, re.IGNORECASE):
            normalized = re.sub(r'[^\w\d]', '', normalized)
        
        return normalized
    
    def _generate_details(self) -> str:
        """Generate detailed comparison message."""
        if self.status == self.VALID:
            return "Values match exactly or very closely"
        elif self.status == self.PARTIAL:
            return f"Values are similar (similarity: {self.similarity_score:.1%})"
        elif self.status == self.INVALID:
            return f"Values differ significantly (similarity: {self.similarity_score:.1%})"
        elif self.status == self.MISSING_OCR:
            return "OCR could not extract this field"
        else:
            return "User did not provide this field"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "field_name": self.field_name,
            "ocr_value": self.ocr_value,
            "user_value": self.user_value,
            "status": self.status,
            "similarity_score": round(self.similarity_score, 3),
            "details": self.details
        }


class ComparisonEngine:
    """Engine for comparing OCR-extracted data with user input."""
    
    # Field importance weights (for overall scoring)
    FIELD_IMPORTANCE = {
        "Surname": 0.15,
        "Firstnames": 0.15,
        "Name": 0.15,
        "Date of Birth": 0.15,
        "Personal ID Number": 0.20,
        "Passport Number": 0.20,
        "Licence #": 0.20,
        "License #": 0.20,
        "Document Number": 0.15,
        "Nationality": 0.10,
        "Sex": 0.08,
        "Gender": 0.08,
        "Expiry Date": 0.10,
        "Date of Expiry": 0.10,
        "Height": 0.05,
    }
    
    def __init__(self, threshold_valid: float = 0.95, threshold_partial: float = 0.70):
        """Initialize comparison engine.
        
        Args:
            threshold_valid: Similarity threshold for "Valid Match"
            threshold_partial: Similarity threshold for "Partial Match"
        """
        self.threshold_valid = threshold_valid
        self.threshold_partial = threshold_partial
    
    def compare_fields(self, ocr_data: Dict[str, str],
                      user_data: Dict[str, str]) -> List[ComparisonResult]:
        """Compare OCR and user data field by field.
        
        Args:
            ocr_data: Dictionary of OCR-extracted fields
            user_data: Dictionary of user-provided fields
            
        Returns:
            List of ComparisonResult objects
        """
        # Get all unique field names
        all_fields = set(ocr_data.keys()) | set(user_data.keys())
        
        results = []
        for field in sorted(all_fields):
            ocr_value = ocr_data.get(field, "").strip() if field in ocr_data else None
            user_value = user_data.get(field, "").strip() if field in user_data else None
            
            # Skip empty fields
            if not ocr_value and not user_value:
                continue
            
            result = ComparisonResult(field, ocr_value or "", user_value or "")
            results.append(result)
        
        logger.info(f"Completed field comparison for {len(results)} fields")
        return results
    
    def generate_summary(self, comparison_results: List[ComparisonResult]) -> Dict:
        """Generate comprehensive validation summary.
        
        Args:
            comparison_results: List of ComparisonResult objects
            
        Returns:
            Dictionary with summary statistics
        """
        if not comparison_results:
            return {
                "total_fields": 0,
                "valid_matches": 0,
                "partial_matches": 0,
                "mismatches": 0,
                "missing_ocr": 0,
                "missing_user": 0,
                "overall_status": "No fields to compare",
                "overall_similarity": 0.0,
                "confidence_score": 0.0,
                "weighted_score": 0.0
            }
        
        # Count by status
        valid_count = sum(1 for r in comparison_results if r.status == ComparisonResult.VALID)
        partial_count = sum(1 for r in comparison_results if r.status == ComparisonResult.PARTIAL)
        invalid_count = sum(1 for r in comparison_results if r.status == ComparisonResult.INVALID)
        missing_ocr_count = sum(1 for r in comparison_results if r.status == ComparisonResult.MISSING_OCR)
        missing_user_count = sum(1 for r in comparison_results if r.status == ComparisonResult.MISSING_USER)
        
        total_fields = len(comparison_results)
        
        # Calculate overall similarity
        similarities = [r.similarity_score for r in comparison_results if r.similarity_score > 0]
        overall_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # Calculate weighted score (considering field importance)
        weighted_score = self._calculate_weighted_score(comparison_results)
        
        # Calculate confidence score
        confidence_score = (valid_count + 0.5 * partial_count) / total_fields if total_fields > 0 else 0.0
        
        # Determine overall status
        if invalid_count > 0:
            overall_status = ComparisonResult.INVALID
        elif missing_ocr_count > 0 and missing_ocr_count == total_fields:
            overall_status = ComparisonResult.MISSING_OCR
        elif partial_count > 0 and valid_count == 0:
            overall_status = ComparisonResult.PARTIAL
        elif valid_count == total_fields:
            overall_status = ComparisonResult.VALID
        else:
            overall_status = ComparisonResult.PARTIAL if valid_count > invalid_count else ComparisonResult.INVALID
        
        return {
            "total_fields": total_fields,
            "valid_matches": valid_count,
            "partial_matches": partial_count,
            "mismatches": invalid_count,
            "missing_ocr": missing_ocr_count,
            "missing_user": missing_user_count,
            "overall_status": overall_status,
            "overall_similarity": round(overall_similarity, 3),
            "confidence_score": round(confidence_score, 3),
            "weighted_score": round(weighted_score, 3)
        }
    
    def _calculate_weighted_score(self, comparison_results: List[ComparisonResult]) -> float:
        """Calculate weighted score based on field importance.
        
        Args:
            comparison_results: List of ComparisonResult objects
            
        Returns:
            Weighted score (0.0 to 1.0)
        """
        total_weight = 0.0
        weighted_sum = 0.0
        
        for result in comparison_results:
            # Get field importance weight
            weight = self.FIELD_IMPORTANCE.get(result.field_name, 0.10)
            total_weight += weight
            
            # Calculate contribution
            if result.status == ComparisonResult.VALID:
                contribution = weight * 1.0
            elif result.status == ComparisonResult.PARTIAL:
                contribution = weight * result.similarity_score
            elif result.status in [ComparisonResult.INVALID, ComparisonResult.MISSING_OCR, ComparisonResult.MISSING_USER]:
                contribution = weight * 0.0
            else:
                contribution = 0.0
            
            weighted_sum += contribution
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def perform_full_comparison(self, ocr_data: Dict[str, str],
                               user_data: Dict[str, str]) -> Dict:
        """Perform full comparison and generate detailed report.
        
        Args:
            ocr_data: Dictionary of OCR-extracted fields
            user_data: Dictionary of user-provided fields
            
        Returns:
            Comprehensive comparison report
        """
        # Perform field-by-field comparison
        results = self.compare_fields(ocr_data, user_data)
        
        # Generate summary
        summary = self.generate_summary(results)
        
        # Convert results to dictionaries
        detailed_results = [r.to_dict() for r in results]
        
        # Group results by status for easier review
        by_status = {}
        for result in results:
            status = result.status
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(result.to_dict())
        
        # Create comprehensive report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "detailed_results": detailed_results,
            "by_status": by_status,
            "recommendations": self._generate_recommendations(summary, by_status)
        }
        
        logger.info(f"Comparison report generated. Overall status: {summary['overall_status']}")
        return report
    
    @staticmethod
    def _generate_recommendations(summary: Dict, by_status: Dict) -> List[str]:
        """Generate recommendations based on comparison results.
        
        Args:
            summary: Summary statistics
            by_status: Results grouped by status
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if summary["overall_status"] == ComparisonResult.VALID:
            recommendations.append("✅ All critical fields match - data is validated")
            recommendations.append("Safe to proceed with processing")
        
        elif summary["overall_status"] == ComparisonResult.PARTIAL:
            recommendations.append("⚠️ Some fields have partial matches")
            if summary["missing_ocr"] > 0:
                recommendations.append(f"OCR could not extract {summary['missing_ocr']} field(s) - please verify manually")
            if summary["mismatches"] > 0:
                recommendations.append(f"{summary['mismatches']} field(s) differ - please review and correct")
        
        elif summary["overall_status"] == ComparisonResult.INVALID:
            recommendations.append("❌ Critical fields have significant mismatches")
            recommendations.append("Please verify the source image quality and user input")
            recommendations.append("Consider re-uploading the image or correcting the manual entry")
        
        # General recommendations
        if summary["missing_ocr"] > 0:
            recommendations.append(f"Note: {summary['missing_ocr']} field(s) missing from OCR - verify image clarity")
        
        if summary["confidence_score"] < 0.7:
            recommendations.append("Low confidence detected - please manually verify all extracted data")
        
        return recommendations


def compare_extractions(ocr_data: Dict[str, str],
                       user_data: Dict[str, str],
                       threshold_valid: float = 0.95,
                       threshold_partial: float = 0.70) -> Dict:
    """Convenience function to perform comparison.
    
    Args:
        ocr_data: Dictionary of OCR-extracted fields
        user_data: Dictionary of user-provided fields
        threshold_valid: Similarity threshold for valid match
        threshold_partial: Similarity threshold for partial match
        
    Returns:
        Comprehensive comparison report
    """
    engine = ComparisonEngine(threshold_valid, threshold_partial)
    return engine.perform_full_comparison(ocr_data, user_data)
