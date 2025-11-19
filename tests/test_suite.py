"""Unit tests for the ID card extraction system.

This test suite covers:
- Comparison engine functionality
- User verification forms
- Data storage operations
- OCR extraction
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from face_extractor.comparison_engine import (
    ComparisonEngine, ComparisonResult, compare_extractions
)
from face_extractor.user_verification import UserInputForm, UserDataStore
from face_extractor.data_storage import IDCardStorage


class TestComparisonEngine:
    """Tests for comparison engine."""
    
    def test_exact_match(self):
        """Test exact field matching."""
        result = ComparisonResult("Name", "John Doe", "John Doe")
        assert result.status == ComparisonResult.VALID
        assert result.similarity_score == 1.0
    
    def test_partial_match(self):
        """Test partial field matching."""
        result = ComparisonResult("Name", "John Doe", "John Deo")  # Typo
        assert result.status == ComparisonResult.PARTIAL
        assert result.similarity_score >= 0.70
    
    def test_complete_mismatch(self):
        """Test complete mismatch."""
        result = ComparisonResult("Name", "John", "Jane")
        assert result.status == ComparisonResult.INVALID
        assert result.similarity_score < 0.70
    
    def test_missing_ocr_value(self):
        """Test missing OCR value."""
        result = ComparisonResult("Name", "", "John Doe")
        assert result.status == ComparisonResult.MISSING_OCR
    
    def test_missing_user_value(self):
        """Test missing user value."""
        result = ComparisonResult("Name", "John Doe", "")
        assert result.status == ComparisonResult.MISSING_USER
    
    def test_comparison_engine_summary(self):
        """Test comparison engine summary generation."""
        engine = ComparisonEngine()
        
        ocr_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25"
        }
        
        user_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25"
        }
        
        results = engine.compare_fields(ocr_data, user_data)
        summary = engine.generate_summary(results)
        
        assert summary["total_fields"] == 3
        assert summary["valid_matches"] == 3
        assert summary["mismatches"] == 0
        assert summary["overall_status"] == ComparisonResult.VALID
    
    def test_full_comparison_report(self):
        """Test full comparison report generation."""
        engine = ComparisonEngine()
        
        ocr_data = {
            "Name": "John Doe",
            "Date of Birth": "1990-12-25",
            "ID Number": "GHA-123456789-0"
        }
        
        user_data = {
            "Name": "John Doe",
            "Date of Birth": "1990-12-25",
            "ID Number": "GHA-123456789-0"
        }
        
        report = engine.perform_full_comparison(ocr_data, user_data)
        
        assert "timestamp" in report
        assert "summary" in report
        assert "detailed_results" in report
        assert "by_status" in report
        assert "recommendations" in report
        assert len(report["detailed_results"]) == 3


class TestUserInputForm:
    """Tests for user input form."""
    
    def test_form_creation(self):
        """Test creating form for Ghana Card."""
        form = UserInputForm("Ghana Card")
        fields = form.get_form_fields()
        
        assert "Surname" in fields
        assert "Firstnames" in fields
        assert "Date of Birth" in fields
        assert fields["Surname"]["required"] == True
    
    def test_form_validation_valid(self):
        """Test form validation with valid data."""
        form = UserInputForm("Ghana Card")
        
        user_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25",
            "Personal ID Number": "GHA-123456789-0"
        }
        
        is_valid, errors = form.validate_input(user_data)
        assert is_valid == True
        assert len(errors) == 0
    
    def test_form_validation_invalid_date(self):
        """Test form validation with invalid date."""
        form = UserInputForm("Ghana Card")
        
        user_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "invalid-date",
            "Personal ID Number": "GHA-123456789-0"
        }
        
        is_valid, errors = form.validate_input(user_data)
        assert is_valid == False
        assert "Date of Birth" in errors
    
    def test_form_validation_invalid_id_number(self):
        """Test form validation with invalid ID number."""
        form = UserInputForm("Ghana Card")
        
        user_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25",
            "Personal ID Number": "INVALID"
        }
        
        is_valid, errors = form.validate_input(user_data)
        assert is_valid == False
        assert "Personal ID Number" in errors
    
    def test_form_validation_missing_required(self):
        """Test form validation with missing required field."""
        form = UserInputForm("Ghana Card")
        
        user_data = {
            "Surname": "Doe",
            # Missing Firstnames (required)
            "Date of Birth": "1990-12-25",
            "Personal ID Number": "GHA-123456789-0"
        }
        
        is_valid, errors = form.validate_input(user_data)
        assert is_valid == False
        assert "Firstnames" in errors
    
    def test_field_normalization(self):
        """Test field value normalization."""
        # Name normalization
        normalized = UserInputForm.normalize_field_value("Surname", "doe")
        assert normalized == "Doe"
        
        # ID normalization
        normalized = UserInputForm.normalize_field_value("Personal ID Number", "gha-123456789-0")
        assert normalized == "GHA-123456789-0"
        
        # Gender normalization
        normalized = UserInputForm.normalize_field_value("Sex", "male")
        assert normalized == "Male"


class TestUserDataStore:
    """Tests for user data store."""
    
    def test_save_and_retrieve(self):
        """Test saving and retrieving user data."""
        store = UserDataStore()
        
        session_id = "test_session_123"
        user_data = {
            "Name": "John Doe",
            "Date of Birth": "1990-12-25"
        }
        
        # Save
        success = store.save_user_input(session_id, user_data, "Ghana Card")
        assert success == True
        
        # Retrieve
        retrieved = store.get_user_input(session_id)
        assert retrieved is not None
        assert retrieved["card_type"] == "Ghana Card"
        assert retrieved["fields"]["Name"] == "John Doe"
    
    def test_clear_user_input(self):
        """Test clearing user input."""
        store = UserDataStore()
        
        session_id = "test_session_456"
        user_data = {"Name": "John Doe"}
        
        store.save_user_input(session_id, user_data, "Ghana Card")
        
        # Clear
        success = store.clear_user_input(session_id)
        assert success == True
        
        # Verify cleared
        retrieved = store.get_user_input(session_id)
        assert retrieved is None


class TestDataStorage:
    """Tests for data storage."""
    
    def test_database_initialization(self):
        """Test database initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = IDCardStorage(db_path=db_path, csv_path=os.path.join(tmpdir, "test.csv"))
            
            assert os.path.exists(db_path)
    
    def test_store_extraction(self):
        """Test storing extraction result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            csv_path = os.path.join(tmpdir, "test.csv")
            
            storage = IDCardStorage(db_path=db_path, csv_path=csv_path)
            
            card_data = {
                "card_type": "Ghana Card",
                "card_type_confidence": 0.92,
                "ocr_text": "Sample OCR text",
                "fields": {
                    "Surname": "Doe",
                    "Firstnames": "John"
                }
            }
            
            result = storage.store_extraction(card_data, portrait_path=None)
            
            assert result["success"] == True
            assert result["record_id"] is not None
            assert os.path.exists(csv_path)
    
    def test_query_by_card_type(self):
        """Test querying by card type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            csv_path = os.path.join(tmpdir, "test.csv")
            
            storage = IDCardStorage(db_path=db_path, csv_path=csv_path)
            
            # Store two records
            card_data_1 = {
                "card_type": "Ghana Card",
                "card_type_confidence": 0.92,
                "fields": {"Surname": "Doe"}
            }
            
            card_data_2 = {
                "card_type": "Passport",
                "card_type_confidence": 0.85,
                "fields": {"Surname": "Smith"}
            }
            
            storage.store_extraction(card_data_1)
            storage.store_extraction(card_data_2)
            
            # Query
            results = storage.query_by_card_type("Ghana Card")
            assert len(results) >= 1
    
    def test_get_statistics(self):
        """Test getting statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            csv_path = os.path.join(tmpdir, "test.csv")
            
            storage = IDCardStorage(db_path=db_path, csv_path=csv_path)
            
            # Store records
            for i in range(3):
                card_data = {
                    "card_type": "Ghana Card" if i % 2 == 0 else "Passport",
                    "card_type_confidence": 0.9,
                    "fields": {"Surname": f"Person{i}"}
                }
                storage.store_extraction(card_data)
            
            stats = storage.get_statistics()
            
            assert stats["total_records"] >= 3
            assert "card_type_counts" in stats
            assert stats["latest_extraction"] is not None


class TestIntegration:
    """Integration tests for full workflows."""
    
    def test_full_workflow(self):
        """Test complete extraction -> verification -> comparison workflow."""
        # Simulate OCR extraction
        ocr_data = {
            "card_type": "Ghana Card",
            "card_type_confidence": 0.92,
            "fields": {
                "Surname": "Doe",
                "Firstnames": "John",
                "Date of Birth": "1990-12-25",
                "Personal ID Number": "GHA-123456789-0"
            }
        }
        
        # User input (with slight mismatch)
        form = UserInputForm("Ghana Card")
        user_data = {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25",
            "Personal ID Number": "GHA-123456789-0"
        }
        
        is_valid, errors = form.validate_input(user_data)
        assert is_valid == True
        
        # Comparison
        comparison_result = compare_extractions(ocr_data["fields"], user_data)
        
        assert comparison_result["summary"]["overall_status"] == ComparisonResult.VALID
        assert comparison_result["summary"]["confidence_score"] == 1.0
        assert comparison_result["summary"]["valid_matches"] == 4
        
        # Storage
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            csv_path = os.path.join(tmpdir, "test.csv")
            
            storage = IDCardStorage(db_path=db_path, csv_path=csv_path)
            result = storage.store_extraction(ocr_data)
            
            assert result["success"] == True


# Fixtures

@pytest.fixture
def sample_ocr_data():
    """Sample OCR extracted data."""
    return {
        "card_type": "Ghana Card",
        "card_type_confidence": 0.92,
        "fields": {
            "Surname": "Doe",
            "Firstnames": "John",
            "Date of Birth": "1990-12-25",
            "Nationality": "Ghanaian",
            "Sex": "Male",
            "Personal ID Number": "GHA-123456789-0"
        }
    }


@pytest.fixture
def sample_user_data():
    """Sample user input data."""
    return {
        "Surname": "Doe",
        "Firstnames": "John",
        "Date of Birth": "1990-12-25",
        "Nationality": "Ghanaian",
        "Sex": "Male",
        "Personal ID Number": "GHA-123456789-0"
    }


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
