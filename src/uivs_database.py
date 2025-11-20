"""
Universal ID Verification System (UIVS) - Database Management
Handles database schemas for different ID types and verification records.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class UIVSDatabase:
    """Database management for UIVS verification records."""
    
    def __init__(self, db_path: str = "outputs/uivs_verification.db"):
        """Initialize UIVS database."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize all required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # National ID / Ghana Card Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS national_id (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                surname TEXT,
                firstname TEXT,
                nationality TEXT,
                sex TEXT,
                date_of_birth TEXT,
                id_number TEXT UNIQUE,
                card_number TEXT,
                issue_date TEXT,
                expiry_date TEXT,
                height TEXT,
                place_of_issuance TEXT,
                extracted_portrait BLOB,
                uploaded_portrait BLOB,
                face_match_score REAL,
                card_type_match BOOLEAN,
                id_number_match BOOLEAN,
                validation_result TEXT,
                verification_status TEXT,
                confidence_score REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Passport Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS passport (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                surname TEXT,
                given_names TEXT,
                nationality TEXT,
                passport_number TEXT UNIQUE,
                date_of_birth TEXT,
                issue_date TEXT,
                expiry_date TEXT,
                place_of_birth TEXT,
                mrz_data TEXT,
                extracted_portrait BLOB,
                uploaded_portrait BLOB,
                face_match_score REAL,
                card_type_match BOOLEAN,
                id_number_match BOOLEAN,
                validation_result TEXT,
                verification_status TEXT,
                confidence_score REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Voter ID Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voters_id (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                voter_id_number TEXT UNIQUE,
                name TEXT,
                date_of_birth TEXT,
                nationality TEXT,
                constituency TEXT,
                polling_station TEXT,
                electoral_area TEXT,
                extracted_portrait BLOB,
                uploaded_portrait BLOB,
                face_match_score REAL,
                card_type_match BOOLEAN,
                id_number_match BOOLEAN,
                validation_result TEXT,
                verification_status TEXT,
                confidence_score REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Driver's License Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drivers_license (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                license_number TEXT UNIQUE,
                name TEXT,
                date_of_birth TEXT,
                nationality TEXT,
                license_class TEXT,
                issue_date TEXT,
                expiry_date TEXT,
                address TEXT,
                extracted_portrait BLOB,
                uploaded_portrait BLOB,
                face_match_score REAL,
                card_type_match BOOLEAN,
                id_number_match BOOLEAN,
                validation_result TEXT,
                verification_status TEXT,
                confidence_score REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Verification Audit Log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_type TEXT,
                user_id TEXT,
                action TEXT,
                result TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✓ UIVS database initialized")
    
    def save_national_id(self, data: Dict[str, Any]) -> int:
        """Save national ID verification record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO national_id (
                    timestamp, surname, firstname, nationality, sex, date_of_birth,
                    id_number, card_number, issue_date, expiry_date, height,
                    place_of_issuance, extracted_portrait, uploaded_portrait,
                    face_match_score, card_type_match, id_number_match,
                    validation_result, verification_status, confidence_score, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                data.get('surname'),
                data.get('firstname'),
                data.get('nationality'),
                data.get('sex'),
                data.get('date_of_birth'),
                data.get('id_number'),
                data.get('card_number'),
                data.get('issue_date'),
                data.get('expiry_date'),
                data.get('height'),
                data.get('place_of_issuance'),
                data.get('extracted_portrait'),
                data.get('uploaded_portrait'),
                data.get('face_match_score'),
                data.get('card_type_match'),
                data.get('id_number_match'),
                data.get('validation_result'),
                data.get('verification_status'),
                data.get('confidence_score'),
                data.get('notes')
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"✓ Saved national ID record: {record_id}")
            return record_id
        finally:
            conn.close()
    
    def save_passport(self, data: Dict[str, Any]) -> int:
        """Save passport verification record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO passport (
                    timestamp, surname, given_names, nationality, passport_number,
                    date_of_birth, issue_date, expiry_date, place_of_birth,
                    mrz_data, extracted_portrait, uploaded_portrait,
                    face_match_score, card_type_match, id_number_match,
                    validation_result, verification_status, confidence_score, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                data.get('surname'),
                data.get('given_names'),
                data.get('nationality'),
                data.get('passport_number'),
                data.get('date_of_birth'),
                data.get('issue_date'),
                data.get('expiry_date'),
                data.get('place_of_birth'),
                data.get('mrz_data'),
                data.get('extracted_portrait'),
                data.get('uploaded_portrait'),
                data.get('face_match_score'),
                data.get('card_type_match'),
                data.get('id_number_match'),
                data.get('validation_result'),
                data.get('verification_status'),
                data.get('confidence_score'),
                data.get('notes')
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"✓ Saved passport record: {record_id}")
            return record_id
        finally:
            conn.close()
    
    def save_voters_id(self, data: Dict[str, Any]) -> int:
        """Save voter ID verification record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO voters_id (
                    timestamp, voter_id_number, name, date_of_birth,
                    nationality, constituency, polling_station, electoral_area,
                    extracted_portrait, uploaded_portrait,
                    face_match_score, card_type_match, id_number_match,
                    validation_result, verification_status, confidence_score, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                data.get('voter_id_number'),
                data.get('name'),
                data.get('date_of_birth'),
                data.get('nationality'),
                data.get('constituency'),
                data.get('polling_station'),
                data.get('electoral_area'),
                data.get('extracted_portrait'),
                data.get('uploaded_portrait'),
                data.get('face_match_score'),
                data.get('card_type_match'),
                data.get('id_number_match'),
                data.get('validation_result'),
                data.get('verification_status'),
                data.get('confidence_score'),
                data.get('notes')
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"✓ Saved voter ID record: {record_id}")
            return record_id
        finally:
            conn.close()
    
    def save_drivers_license(self, data: Dict[str, Any]) -> int:
        """Save driver's license verification record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO drivers_license (
                    timestamp, license_number, name, date_of_birth,
                    nationality, license_class, issue_date, expiry_date,
                    address, extracted_portrait, uploaded_portrait,
                    face_match_score, card_type_match, id_number_match,
                    validation_result, verification_status, confidence_score, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                data.get('license_number'),
                data.get('name'),
                data.get('date_of_birth'),
                data.get('nationality'),
                data.get('license_class'),
                data.get('issue_date'),
                data.get('expiry_date'),
                data.get('address'),
                data.get('extracted_portrait'),
                data.get('uploaded_portrait'),
                data.get('face_match_score'),
                data.get('card_type_match'),
                data.get('id_number_match'),
                data.get('validation_result'),
                data.get('verification_status'),
                data.get('confidence_score'),
                data.get('notes')
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            logger.info(f"✓ Saved driver license record: {record_id}")
            return record_id
        finally:
            conn.close()
    
    def log_audit(self, id_type: str, user_id: str, action: str, result: str, details: str = ""):
        """Log verification audit trail."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO verification_audit (id_type, user_id, action, result, details)
                VALUES (?, ?, ?, ?, ?)
            """, (id_type, user_id, action, result, details))
            
            conn.commit()
            logger.info(f"✓ Audit logged: {action} - {result}")
        finally:
            conn.close()
    
    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            # Count by ID type
            for table in ['national_id', 'passport', 'voters_id', 'drivers_license']:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE verification_status='VERIFIED'")
                stats[f"{table}_verified"] = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_total"] = cursor.fetchone()[0]
            
            # Count recent verifications (count each table separately and sum)
            count_24h = 0
            for table in ['national_id', 'passport', 'voters_id', 'drivers_license']:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE datetime(timestamp) > datetime('now', '-24 hours')
                """)
                count_24h += cursor.fetchone()[0]
            stats['verifications_24h'] = count_24h
            
        finally:
            conn.close()
        
        return stats
