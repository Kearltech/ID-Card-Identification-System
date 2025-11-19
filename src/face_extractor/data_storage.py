"""Data storage module for extracted ID card information.

This module provides functions to store extracted ID card data
in CSV and SQLite formats for easy querying and analysis.
"""

import csv
import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


class IDCardStorage:
    """Storage manager for ID card extraction data."""
    
    def __init__(self, db_path: str = "outputs/id_cards.db", csv_path: str = "outputs/id_cards.csv"):
        """Initialize storage manager.
        
        Args:
            db_path: Path to SQLite database file
            csv_path: Path to CSV file
        """
        self.db_path = db_path
        self.csv_path = csv_path
        self._init_database()
        self._init_csv()
    
    def _init_database(self):
        """Initialize SQLite database with schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                extraction_timestamp TEXT NOT NULL,
                card_type TEXT,
                card_type_confidence REAL,
                name TEXT,
                surname TEXT,
                firstnames TEXT,
                given_names TEXT,
                date_of_birth TEXT,
                nationality TEXT,
                sex TEXT,
                gender TEXT,
                height TEXT,
                personal_id_number TEXT,
                document_number TEXT,
                licence_number TEXT,
                license_number TEXT,
                passport_number TEXT,
                voter_id_number TEXT,
                nhis_number TEXT,
                ssnit_number TEXT,
                tin_number TEXT,
                date_of_issue TEXT,
                date_of_issuance TEXT,
                date_of_expiry TEXT,
                expiry_date TEXT,
                place_of_birth TEXT,
                place_of_issuance TEXT,
                address TEXT,
                constituency TEXT,
                polling_station TEXT,
                electoral_area TEXT,
                class_of_licence TEXT,
                authority TEXT,
                employer TEXT,
                fathers_name TEXT,
                mothers_name TEXT,
                registration_number TEXT,
                taxpayer_type TEXT,
                registration_date TEXT,
                portrait_path TEXT,
                ocr_text TEXT,
                raw_fields TEXT,
                validation_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on card_type for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_card_type ON id_cards(card_type)
        """)
        
        # Create index on extraction_timestamp
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON id_cards(extraction_timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist."""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        if not os.path.exists(self.csv_path):
            # Write headers
            headers = [
                "extraction_timestamp", "card_type", "card_type_confidence",
                "name", "surname", "firstnames", "given_names",
                "date_of_birth", "nationality", "sex", "gender", "height",
                "personal_id_number", "document_number", "licence_number",
                "license_number", "passport_number", "voter_id_number",
                "nhis_number", "ssnit_number", "tin_number",
                "date_of_issue", "date_of_issuance", "date_of_expiry",
                "expiry_date", "place_of_birth", "place_of_issuance",
                "address", "constituency", "polling_station", "electoral_area",
                "class_of_licence", "authority", "employer",
                "fathers_name", "mothers_name", "registration_number",
                "taxpayer_type", "registration_date", "portrait_path",
                "ocr_text", "raw_fields", "validation_summary"
            ]
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
    
    def store_extraction(self, 
                        card_data: Dict[str, Any],
                        portrait_path: Optional[str] = None,
                        validation_summary: Optional[Dict] = None) -> Dict[str, Any]:
        """Store extracted ID card data.
        
        Args:
            card_data: Dictionary containing extracted card data
            portrait_path: Path to cropped portrait image
            validation_summary: Validation results summary
            
        Returns:
            Dictionary with storage results:
            {
                "success": bool,
                "record_id": int or None,
                "timestamp": str,
                "message": str
            }
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepare data for storage
        fields = card_data.get("fields", {})
        validated_fields = validation_summary.get("validated_fields", {}) if validation_summary else fields
        
        # Build record
        record = {
            "extraction_timestamp": timestamp,
            "card_type": card_data.get("card_type", "Unknown"),
            "card_type_confidence": card_data.get("card_type_confidence", 0.0),
            "portrait_path": portrait_path or "",
            "ocr_text": card_data.get("ocr_text", ""),
            "raw_fields": json.dumps(fields, ensure_ascii=False),
            "validation_summary": json.dumps(validation_summary, ensure_ascii=False) if validation_summary else ""
        }
        
        # Add validated fields
        for field_name, field_value in validated_fields.items():
            # Normalize field names for database columns
            db_field_name = field_name.lower().replace(" ", "_").replace("#", "number")
            if db_field_name in ["licence_#", "license_#"]:
                db_field_name = "licence_number" if "licence" in field_name.lower() else "license_number"
            record[db_field_name] = field_value
        
        # Store in SQLite
        db_success, db_record_id = self._store_in_db(record)
        
        # Store in CSV
        csv_success = self._store_in_csv(record)
        
        success = db_success and csv_success
        
        return {
            "success": success,
            "record_id": db_record_id,
            "timestamp": timestamp,
            "message": "Data stored successfully" if success else "Error storing data"
        }
    
    def _store_in_db(self, record: Dict[str, Any]) -> Tuple[bool, Optional[int]]:
        """Store record in SQLite database.
        
        Args:
            record: Record data dictionary
            
        Returns:
            Tuple of (success, record_id)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get column names from table
            cursor.execute("PRAGMA table_info(id_cards)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Filter record to only include valid columns
            filtered_record = {k: v for k, v in record.items() if k in columns}
            
            # Build INSERT statement
            columns_str = ", ".join(filtered_record.keys())
            placeholders = ", ".join(["?"] * len(filtered_record))
            values = list(filtered_record.values())
            
            cursor.execute(
                f"INSERT INTO id_cards ({columns_str}) VALUES ({placeholders})",
                values
            )
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, record_id
        except Exception as e:
            print(f"Error storing in database: {e}")
            return False, None
    
    def _store_in_csv(self, record: Dict[str, Any]) -> bool:
        """Store record in CSV file.
        
        Args:
            record: Record data dictionary
            
        Returns:
            Success status
        """
        try:
            # Read existing headers
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
            
            # Filter record to match headers
            filtered_record = {k: v for k, v in record.items() if k in headers}
            
            # Fill missing fields with empty strings
            for header in headers:
                if header not in filtered_record:
                    filtered_record[header] = ""
            
            # Append row
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(filtered_record)
            
            return True
        except Exception as e:
            print(f"Error storing in CSV: {e}")
            return False
    
    def query_by_card_type(self, card_type: str) -> List[Dict[str, Any]]:
        """Query records by card type.
        
        Args:
            card_type: Type of ID card
            
        Returns:
            List of matching records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM id_cards WHERE card_type = ?", (card_type,))
        rows = cursor.fetchall()
        
        records = [dict(row) for row in rows]
        conn.close()
        
        return records
    
    def query_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Query records by date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of matching records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM id_cards WHERE date(created_at) BETWEEN ? AND ?",
            (start_date, end_date)
        )
        rows = cursor.fetchall()
        
        records = [dict(row) for row in rows]
        conn.close()
        
        return records
    
    def get_all_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all records.
        
        Args:
            limit: Optional limit on number of records
            
        Returns:
            List of all records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM id_cards ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        records = [dict(row) for row in rows]
        conn.close()
        
        return records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored records.
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM id_cards")
        total_count = cursor.fetchone()[0]
        
        # Count by card type
        cursor.execute("SELECT card_type, COUNT(*) FROM id_cards GROUP BY card_type")
        card_type_counts = dict(cursor.fetchall())
        
        # Latest extraction
        cursor.execute("SELECT MAX(created_at) FROM id_cards")
        latest = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_records": total_count,
            "card_type_counts": card_type_counts,
            "latest_extraction": latest
        }

