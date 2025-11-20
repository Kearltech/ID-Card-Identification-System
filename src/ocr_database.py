"""
Database Storage for Label-Guided OCR Results

Stores OCR extraction results, field parsing, validation, and user comparison
in type-specific database tables.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class OCRResultsDatabase:
    """Store and retrieve OCR results from database."""
    
    def __init__(self, db_path: str = "outputs/ocr_results.db"):
        """
        Initialize OCR results database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_tables()
        logger.info(f"OCR Results Database initialized: {db_path}")
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def init_tables(self):
        """Initialize database tables for OCR results."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # OCR Extraction Results table (all ID types)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ocr_extractions (
                    extraction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_type TEXT NOT NULL,
                    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ocr_engine TEXT,
                    raw_text TEXT,
                    text_length INTEGER,
                    extraction_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Extracted Fields table (generic, maps to any ID type)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extracted_fields (
                    field_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    field_value TEXT,
                    field_type TEXT,
                    validation_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # Field Validation Results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS field_validations (
                    validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    id_type TEXT NOT NULL,
                    overall_valid BOOLEAN,
                    valid_field_count INTEGER,
                    invalid_field_count INTEGER,
                    missing_required TEXT,
                    validation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # User Input Comparison table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_comparisons (
                    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    id_type TEXT NOT NULL,
                    user_input JSONB,
                    matches JSONB,
                    mismatches JSONB,
                    missing_on_id JSONB,
                    match_confidence REAL,
                    overall_match BOOLEAN,
                    comparison_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # Type-specific Ghana Card results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ghana_card_results (
                    ghana_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    surname TEXT,
                    firstnames TEXT,
                    date_of_birth TEXT,
                    sex TEXT,
                    nationality TEXT,
                    id_number TEXT UNIQUE,
                    height TEXT,
                    document_number TEXT,
                    date_of_issuance TEXT,
                    date_of_expiry TEXT,
                    religion TEXT,
                    occupation TEXT,
                    verified BOOLEAN DEFAULT 0,
                    verification_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # Type-specific Passport results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS passport_results (
                    passport_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    surname TEXT,
                    given_names TEXT,
                    passport_number TEXT UNIQUE,
                    nationality TEXT,
                    sex TEXT,
                    date_of_birth TEXT,
                    place_of_birth TEXT,
                    date_of_issue TEXT,
                    date_of_expiry TEXT,
                    authority TEXT,
                    verified BOOLEAN DEFAULT 0,
                    verification_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # Type-specific Voter ID results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voters_id_results (
                    voters_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    full_name TEXT,
                    voter_id TEXT UNIQUE,
                    sex TEXT,
                    date_of_birth TEXT,
                    polling_station TEXT,
                    region TEXT,
                    district TEXT,
                    constituency TEXT,
                    date_of_issue TEXT,
                    date_of_expiry TEXT,
                    verified BOOLEAN DEFAULT 0,
                    verification_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            # Type-specific Driver License results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drivers_license_results (
                    license_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    extraction_id INTEGER NOT NULL,
                    license_number TEXT UNIQUE,
                    name TEXT,
                    date_of_birth TEXT,
                    address TEXT,
                    expiration TEXT,
                    class TEXT,
                    issue_date TEXT,
                    sex TEXT,
                    restrictions TEXT,
                    verified BOOLEAN DEFAULT 0,
                    verification_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(extraction_id) REFERENCES ocr_extractions(extraction_id)
                )
            """)
            
            conn.commit()
            logger.info("Database tables initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
            raise
        
        finally:
            conn.close()
    
    def store_extraction(self, ocr_result: Dict[str, Any]) -> int:
        """
        Store OCR extraction result.
        
        Args:
            ocr_result: Result from OCR pipeline
        
        Returns:
            extraction_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Store main extraction
            cursor.execute("""
                INSERT INTO ocr_extractions (id_type, ocr_engine, raw_text, text_length, extraction_status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ocr_result.get("id_type"),
                ocr_result.get("steps", {}).get("text_extraction", {}).get("engine"),
                ocr_result.get("raw_text", "")[:10000],  # Limit to 10K chars
                len(ocr_result.get("raw_text", "")),
                ocr_result.get("status")
            ))
            
            extraction_id = cursor.lastrowid
            
            # Store individual fields
            for field_name, field_value in ocr_result.get("extracted_fields", {}).items():
                cursor.execute("""
                    INSERT INTO extracted_fields (extraction_id, field_name, field_value, field_type)
                    VALUES (?, ?, ?, ?)
                """, (
                    extraction_id,
                    field_name,
                    str(field_value) if field_value else None,
                    self._get_field_type(field_name)
                ))
            
            conn.commit()
            logger.info(f"Stored extraction result: extraction_id={extraction_id}")
            return extraction_id
        
        except Exception as e:
            logger.error(f"Failed to store extraction: {e}")
            raise
        
        finally:
            conn.close()
    
    def store_validation(self, extraction_id: int, validation_result: Dict[str, Any]) -> int:
        """
        Store field validation result.
        
        Args:
            extraction_id: ID of extraction
            validation_result: Validation result from parser
        
        Returns:
            validation_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO field_validations 
                (extraction_id, id_type, overall_valid, valid_field_count, invalid_field_count, missing_required)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                extraction_id,
                validation_result.get("id_type"),
                validation_result.get("overall_valid"),
                len(validation_result.get("valid_fields", {})),
                len(validation_result.get("invalid_fields", {})),
                json.dumps(validation_result.get("missing_required", []))
            ))
            
            validation_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Stored validation result: validation_id={validation_id}")
            return validation_id
        
        except Exception as e:
            logger.error(f"Failed to store validation: {e}")
            raise
        
        finally:
            conn.close()
    
    def store_user_comparison(self, extraction_id: int, comparison_result: Dict[str, Any]) -> int:
        """
        Store user input comparison result.
        
        Args:
            extraction_id: ID of extraction
            comparison_result: Comparison result from validator
        
        Returns:
            comparison_id
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            comparison = comparison_result.get("comparison", {})
            
            cursor.execute("""
                INSERT INTO user_comparisons
                (extraction_id, id_type, matches, mismatches, missing_on_id, match_confidence, overall_match)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                extraction_id,
                comparison_result.get("validation", {}).get("id_type"),
                json.dumps(comparison.get("matches", {})),
                json.dumps(comparison.get("mismatches", {})),
                json.dumps(comparison.get("missing_on_id", {})),
                comparison.get("overall_confidence", 0),
                comparison_result.get("overall_match", False)
            ))
            
            comparison_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Stored comparison result: comparison_id={comparison_id}")
            return comparison_id
        
        except Exception as e:
            logger.error(f"Failed to store comparison: {e}")
            raise
        
        finally:
            conn.close()
    
    def store_type_specific_result(self, extraction_id: int, extracted_fields: Dict[str, Any], id_type: str) -> bool:
        """
        Store type-specific OCR result in appropriate table.
        
        Args:
            extraction_id: ID of extraction
            extracted_fields: Extracted field values
            id_type: Type of ID card
        
        Returns:
            True if successful, False otherwise
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            id_type_lower = id_type.lower()
            
            if id_type_lower == "ghana_card":
                cursor.execute("""
                    INSERT INTO ghana_card_results
                    (extraction_id, surname, firstnames, date_of_birth, sex, nationality, id_number, 
                     height, document_number, date_of_issuance, date_of_expiry, religion, occupation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    extracted_fields.get("Surname"),
                    extracted_fields.get("Firstnames"),
                    extracted_fields.get("Date of Birth"),
                    extracted_fields.get("Sex"),
                    extracted_fields.get("Nationality"),
                    extracted_fields.get("ID Number"),
                    extracted_fields.get("Height"),
                    extracted_fields.get("Document Number"),
                    extracted_fields.get("Date of Issuance"),
                    extracted_fields.get("Date of Expiry"),
                    extracted_fields.get("Religion"),
                    extracted_fields.get("Occupation")
                ))
            
            elif id_type_lower == "passport":
                cursor.execute("""
                    INSERT INTO passport_results
                    (extraction_id, surname, given_names, passport_number, nationality, sex, date_of_birth,
                     place_of_birth, date_of_issue, date_of_expiry, authority)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    extracted_fields.get("Surname"),
                    extracted_fields.get("Given Names"),
                    extracted_fields.get("Passport Number"),
                    extracted_fields.get("Nationality"),
                    extracted_fields.get("Sex"),
                    extracted_fields.get("Date of Birth"),
                    extracted_fields.get("Place of Birth"),
                    extracted_fields.get("Date of Issue"),
                    extracted_fields.get("Date of Expiry"),
                    extracted_fields.get("Authority")
                ))
            
            elif id_type_lower == "voters_id":
                cursor.execute("""
                    INSERT INTO voters_id_results
                    (extraction_id, full_name, voter_id, sex, date_of_birth, polling_station,
                     region, district, constituency, date_of_issue, date_of_expiry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    extracted_fields.get("Full Name"),
                    extracted_fields.get("Voter ID"),
                    extracted_fields.get("Sex"),
                    extracted_fields.get("Date of Birth"),
                    extracted_fields.get("Polling Station"),
                    extracted_fields.get("Region"),
                    extracted_fields.get("District"),
                    extracted_fields.get("Constituency"),
                    extracted_fields.get("Date of Issue"),
                    extracted_fields.get("Date of Expiry")
                ))
            
            elif id_type_lower == "drivers_license":
                cursor.execute("""
                    INSERT INTO drivers_license_results
                    (extraction_id, license_number, name, date_of_birth, address, expiration,
                     class, issue_date, sex, restrictions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    extracted_fields.get("License Number"),
                    extracted_fields.get("Name"),
                    extracted_fields.get("Date of Birth"),
                    extracted_fields.get("Address"),
                    extracted_fields.get("Expiration"),
                    extracted_fields.get("Class"),
                    extracted_fields.get("Issue Date"),
                    extracted_fields.get("Sex"),
                    extracted_fields.get("Restrictions")
                ))
            
            conn.commit()
            logger.info(f"Stored type-specific result for {id_type}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to store type-specific result: {e}")
            return False
        
        finally:
            conn.close()
    
    def get_extraction_by_id(self, extraction_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve extraction result by ID.
        
        Args:
            extraction_id: ID of extraction
        
        Returns:
            Extraction result dictionary or None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM ocr_extractions WHERE extraction_id = ?", (extraction_id,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
        
        finally:
            conn.close()
    
    def search_by_id_number(self, id_number: str, id_type: str) -> Optional[Dict[str, Any]]:
        """
        Search for records by ID number.
        
        Args:
            id_number: ID number to search
            id_type: Type of ID card
        
        Returns:
            Result dictionary or None
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            id_type_lower = id_type.lower()
            
            if id_type_lower == "ghana_card":
                cursor.execute("SELECT * FROM ghana_card_results WHERE id_number = ?", (id_number,))
            elif id_type_lower == "passport":
                cursor.execute("SELECT * FROM passport_results WHERE passport_number = ?", (id_number,))
            elif id_type_lower == "voters_id":
                cursor.execute("SELECT * FROM voters_id_results WHERE voter_id = ?", (id_number,))
            elif id_type_lower == "drivers_license":
                cursor.execute("SELECT * FROM drivers_license_results WHERE license_number = ?", (id_number,))
            else:
                return None
            
            result = cursor.fetchone()
            return dict(result) if result else None
        
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total extractions by type
            cursor.execute("""
                SELECT id_type, COUNT(*) as count
                FROM ocr_extractions
                GROUP BY id_type
            """)
            stats["extractions_by_type"] = dict(cursor.fetchall())
            
            # Validation statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_valid THEN 1 ELSE 0 END) as valid,
                    SUM(CASE WHEN NOT overall_valid THEN 1 ELSE 0 END) as invalid
                FROM field_validations
            """)
            row = cursor.fetchone()
            stats["validations"] = {
                "total": row[0] or 0,
                "valid": row[1] or 0,
                "invalid": row[2] or 0
            }
            
            # User comparison statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN overall_match THEN 1 ELSE 0 END) as matched,
                    AVG(match_confidence) as avg_confidence
                FROM user_comparisons
            """)
            row = cursor.fetchone()
            stats["user_comparisons"] = {
                "total": row[0] or 0,
                "matched": row[1] or 0,
                "avg_confidence": round(row[2], 3) if row[2] else 0
            }
            
            return stats
        
        finally:
            conn.close()
    
    @staticmethod
    def _get_field_type(field_name: str) -> str:
        """Get field type based on field name."""
        field_name_lower = field_name.lower()
        
        if "date" in field_name_lower:
            return "date"
        elif "sex" in field_name_lower or "gender" in field_name_lower:
            return "choice"
        elif "id" in field_name_lower or "number" in field_name_lower:
            return "id_number"
        elif "height" in field_name_lower:
            return "number"
        else:
            return "text"
