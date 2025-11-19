"""Database models for storing extracted ID information.

Uses sqlite3 for simplicity and creates per-ID-type tables if missing.
"""
import sqlite3
import os
from typing import Dict, Any

DB_PATH = os.getenv("ID_VERIFY_DB", os.path.join(os.path.dirname(__file__), "id_verify.db"))

SCHEMAS = {
    "national_id": ["surname","firstname","nationality","sex","dob","id_number","document_number","issue_date","expiry_date","place_of_issue"],
    "passport": ["full_name","passport_number","nationality","dob","place_of_birth","issue_date","expiry_date","issuing_authority"],
    "voter_id": ["name","voter_id_number","dob","sex","polling_station","region","issue_date"],
    "drivers_license": ["name","license_number","dob","issue_date","expiry_date","class","issuing_authority"],
}


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    conn = _connect()
    cur = conn.cursor()
    for tbl, fields in SCHEMAS.items():
        cols = ", ".join([f"{f} TEXT" for f in fields])
        cols += ", portrait_path TEXT, verification_result TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        sql = f"CREATE TABLE IF NOT EXISTS {tbl} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})"
        cur.execute(sql)
    conn.commit()
    conn.close()


def insert_record(id_type: str, fields: Dict[str, Any], portrait_path: str, verification: str):
    if id_type not in SCHEMAS:
        raise ValueError("Unknown id_type")
    conn = _connect()
    cur = conn.cursor()
    cols = SCHEMAS[id_type]
    keys = cols + ["portrait_path","verification_result"]
    vals = [fields.get(k, "") for k in cols] + [portrait_path, verification]
    placeholders = ",".join(["?"] * len(keys))
    sql = f"INSERT INTO {id_type} ({','.join(keys)}) VALUES ({placeholders})"
    cur.execute(sql, vals)
    conn.commit()
    conn.close()
