"""Simple Flask endpoints to handle the verification flow described.

This file provides a minimal proof-of-concept server that accepts uploads,
selects an ID type, calls the OCR extractor, runs face matching, validates IDs,
and stores results using sqlite models.

Note: For the user's Streamlit app integration, adapt the functions below into
the Streamlit flow. This module is intentionally standalone for testing.
"""
import os
from flask import Flask, request, jsonify
from .services.ocr_extractor import extract_with_gemini
from .services.face_matcher import compare_faces
from .db.models import ensure_tables, insert_record, SCHEMAS

app = Flask(__name__)


@app.route('/verify', methods=['POST'])
def verify():
    # expected form: id_type, id_number (entered by user), passport_photo file, id_card_image file
    id_type = request.form.get('id_type')
    entered_id = request.form.get('id_number', '')
    passport_file = request.files.get('passport_photo')
    id_card_file = request.files.get('id_card_image')

    if not id_type or id_type not in SCHEMAS:
        return jsonify({'error': 'invalid id_type'}), 400
    if not passport_file or not id_card_file:
        return jsonify({'error': 'missing files'}), 400

    passport_bytes = passport_file.read()
    card_bytes = id_card_file.read()

    # OCR extraction
    ocr = extract_with_gemini(card_bytes)
    # Map fields
    mapped = {k: ocr.get('fields', {}).get(k, '') for k in SCHEMAS[id_type]}

    # Basic ID number check: compare entered with any of fields that look like id
    extracted_id = ''
    for key in mapped:
        if 'id' in key or 'number' in key or 'passport' in key or 'license' in key:
            if mapped[key]:
                extracted_id = mapped[key]
                break

    id_match = (entered_id.strip().lower() == extracted_id.strip().lower()) if entered_id and extracted_id else False

    # Face compare
    face_match, face_details = compare_faces(passport_bytes, card_bytes)

    verification = 'validated' if id_match and face_match else 'mismatch'

    # Ensure DB
    ensure_tables()
    # Save portrait to disk
    save_dir = os.path.join(os.path.dirname(__file__), '..', 'storage')
    os.makedirs(save_dir, exist_ok=True)
    portrait_path = os.path.join(save_dir, f"portrait_{os.urandom(6).hex()}.jpg")
    with open(portrait_path, 'wb') as f:
        f.write(passport_bytes)

    insert_record(id_type, mapped, portrait_path, verification)

    return jsonify({
        'verification': verification,
        'id_match': id_match,
        'extracted_id': extracted_id,
        'face_match': face_match,
        'face_details': face_details,
        'mapped': mapped,
        'ocr_summary': {'card_type': ocr.get('card_type'), 'ocr_used': ocr.get('ocr_used')}
    })


if __name__ == '__main__':
    app.run(port=8503, debug=True)
