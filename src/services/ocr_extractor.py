"""OCR extractor service.

Provides a wrapper over Gemini + local OCR (EasyOCR / Tesseract) and
returns structured extracted fields and confidence scores.
"""
import os
import io
import logging
from typing import Dict, Any, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_DRY_RUN = os.getenv("GEMINI_DRY_RUN", "true").lower() in ("1","true","yes")


def _try_easyocr(image_bytes: bytes) -> Tuple[str, Dict[str, float]]:
    try:
        import easyocr
        import numpy as np
    except Exception:
        logger.debug("EasyOCR not available")
        return "", {}
    reader = easyocr.Reader(["en"])
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    arr = np.array(img)
    texts = reader.readtext(arr, detail=1)  # (bbox, text, conf)
    raw = "\n".join([t[1] for t in texts])
    confidences = {str(i): float(t[2]) for i, t in enumerate(texts)}
    return raw, confidences


def _try_tesseract(image_bytes: bytes) -> Tuple[str, Dict[str, float]]:
    try:
        import pytesseract
    except Exception:
        logger.debug("pytesseract not available")
        return "", {}
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    raw = pytesseract.image_to_string(img)
    # pytesseract doesn't give per-line confidences easily; return empty map
    return raw, {}


def extract_with_gemini(image_bytes: bytes) -> Dict[str, Any]:
    """High level extraction that will attempt Gemini then fallback to local OCR.

    Returns dict: {raw_text, card_type, fields, confidences, ocr_used}
    """
    # First try local OCR to get raw text
    raw_text, confs = _try_easyocr(image_bytes)
    if not raw_text:
        raw_text, confs = _try_tesseract(image_bytes)

    # If Gemini configured and not dry run, attempt network parsing
    gemini_enabled = bool(GEMINI_API_KEY) and not GEMINI_DRY_RUN
    parsed = None
    if gemini_enabled:
        try:
            # Reuse existing gemini client logic from ocr_gemini if present via import
            from ..ocr_gemini import GeminiOCRClient
            client = GeminiOCRClient()
            parsed = client._call_gemini_parse(raw_text)
            parsed.setdefault("raw_text", raw_text)
            parsed.setdefault("fields", {})
            parsed.setdefault("card_type", parsed.get("card_type", "Unknown"))
            parsed["ocr_used"] = "gemini"
            parsed["confidences"] = confs
            return parsed
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}")

    # Fallback: perform local heuristic extraction using ocr_gemini helper
    try:
        from ..ocr_gemini import GeminiOCRClient
        client = GeminiOCRClient()
        local = client._easyocr_extract(image_bytes)
        local["confidences"] = confs
        local["ocr_used"] = "easyocr" if confs else "tesseract"
        return local
    except Exception as e:
        logger.exception("Local extraction failed")
        return {"raw_text": raw_text or "", "card_type": "Unknown", "fields": {}, "confidences": confs, "ocr_used": "local"}
