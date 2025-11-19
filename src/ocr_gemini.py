"""
Gemini OCR integration with EasyOCR fallback.

- If GEMINI_API_KEY is set and GEMINI_DRY_RUN is false, the client will attempt
  to call Gemini (network). Otherwise it will perform local OCR using EasyOCR
  and return a structured JSON extracted via heuristics.

The extract_structured(image_bytes) function returns a dict:
{
  "raw_text": "...",
  "card_type": "Ghana Card",  # guessed
  "fields": {"surname":..., "firstnames":..., ...}
}
"""
import os
import logging
from typing import Dict, Any
import re

from PIL import Image
import io

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_DRY_RUN = os.getenv("GEMINI_DRY_RUN", "true").lower() in ("1","true","yes")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception:
    EASYOCR_AVAILABLE = False


# Schema map for supported ID types
id_field_schema = {
    "national_id": ["surname", "firstname", "nationality", "sex", "dob", "id_number", "document_number", "issue_date", "expiry_date", "place_of_issue"],
    "passport": ["full_name", "passport_number", "nationality", "dob", "place_of_birth", "issue_date", "expiry_date", "issuing_authority"],
    "voter_id": ["name", "voter_id_number", "dob", "sex", "polling_station", "region", "issue_date"],
    "drivers_license": ["name", "license_number", "dob", "issue_date", "expiry_date", "class", "issuing_authority"]
}


class GeminiOCRClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.dry_run = GEMINI_DRY_RUN
        self.enabled = bool(self.api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        if not self.enabled:
            logger.info("Gemini OCR disabled (no GEMINI_API_KEY)")
        elif self.dry_run:
            logger.info("Gemini OCR in dry-run mode")
        else:
            logger.info("Gemini OCR enabled")

    def extract_structured(self, image_bytes: bytes) -> Dict[str, Any]:
        """Return structured extraction for an image (bytes).

        If Gemini is enabled and dry_run is False, attempt network call. On failure
        fall back to local OCR.
        """
        # First, perform local OCR to obtain raw text (we will send that to Gemini)
        try:
            raw_text = self._easyocr_get_text(image_bytes)
        except Exception as e:
            logger.warning(f"Local OCR failed before Gemini call: {e}")
            raw_text = ""

        # If Gemini is enabled and not dry-run, try network call using raw_text
        if self.enabled and not self.dry_run:
            try:
                gemini_result = self._call_gemini_parse(raw_text)
                # gemini_result should be dict with keys raw_text, card_type, fields
                if isinstance(gemini_result, dict) and gemini_result.get("fields"):
                    return gemini_result
                else:
                    logger.warning("Gemini returned unexpected result; falling back to local extractor")
            except Exception as e:
                logger.exception(f"Gemini remote call failed: {e}")
        # Fallback: run local structured extraction
        return self._easyocr_extract(image_bytes)

    def extract_and_map(self, image_bytes: bytes, id_type: str, schema_map: Dict[str, list]) -> Dict[str, Any]:
        """Extract and map fields according to provided schema_map for id_type.

        Returns dict with fields limited to schema_map[id_type] and confidences.
        """
        result = self.extract_structured(image_bytes)
        fields = result.get("fields", {}) or {}
        mapped = {}
        required = schema_map.get(id_type, [])
        # Simple mapping: try to find best key match ignoring punctuation and case
        norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
        fields_norm = {norm(k): v for k, v in fields.items()}
        for r in required:
            v = ""
            # exact
            if r in fields:
                v = fields[r]
            else:
                nr = norm(r)
                if nr in fields_norm:
                    v = fields_norm[nr]
                else:
                    # try contains
                    for k, val in fields.items():
                        if nr in norm(k) or norm(k) in nr:
                            v = val
                            break
            mapped[r] = v or ""
        result["mapped_fields"] = mapped
        return result

    def _easyocr_get_text(self, image_bytes: bytes) -> str:
        """Return plain OCR text from the image using EasyOCR (or empty string)."""
        if not EASYOCR_AVAILABLE:
            logger.error("EasyOCR not installed. Install easyocr to use local OCR fallback.")
            return ""
        reader = easyocr.Reader(["en"])  # English only for now
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        import numpy as np
        arr = np.array(img)
        ocr_result = reader.readtext(arr, detail=0)
        return "\n".join(ocr_result)

    def _call_gemini_parse(self, raw_text: str) -> Dict[str, Any]:
        """Call Google's Generative Language API (Gemini) to parse OCR text into JSON.

        This function uses the Generative Language REST endpoint. The request is
        made only when an API key is present and dry-run is False. The model is
        configurable via GEMINI_MODEL env var (default: gemini-1.5-pro).

        Note: This implementation sends the OCR text as the prompt to Gemini and
        asks for a strict JSON response. Network calls will execute on the
        host running the app; ensure your environment/network allow outgoing HTTPS.
        """
        try:
            # 'requests' is optional at runtime for Gemini network calls
            import requests
        except Exception:
            raise RuntimeError("The 'requests' package is required for Gemini network calls. Install it in your environment.")

        if not raw_text:
            raise ValueError("No OCR text available to send to Gemini")

        prompt = (
            "You are a JSON extractor for identity documents. "
            "Given the OCR text between triple backticks, extract the following fields: "
            "surname, firstnames, previous_names, date_of_birth, sex, nationality, document_number, "
            "date_of_issue, date_of_expiry, place_of_issue, height. Also guess a card_type (e.g., Ghana Card, Passport, Driver's License). "
            "Return only a single valid JSON object with keys: raw_text, card_type, fields (fields is an object with the exact field names). "
            "If any field is missing, use an empty string. Do not include any extra text or commentary.\n\n" 
            "OCR_TEXT_START\n```\n" + raw_text + "\n```\nOCR_TEXT_END"
        )

        # Build request to Generative Language API. The public v1beta2 endpoint accepts a POST to
        # models/{model}:generate with a prompt in JSON. We attach the API key as a query param.
        model = self.model
        url = f"https://generativelanguage.googleapis.com/v1beta2/models/{model}:generate?key={self.api_key}"

        body = {
            "prompt": {"text": prompt},
            "temperature": 0.0,
            "maxOutputTokens": 1024,
        }

        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Attempt to extract text from response robustly
        text_out = None
        # Common placements
        if isinstance(data, dict):
            # v1beta2 models:generate returns 'candidates' or 'output' depending on API
            if "candidates" in data and isinstance(data["candidates"], list) and data["candidates"]:
                candidate = data["candidates"][0]
                text_out = candidate.get("output") or candidate.get("content") or candidate.get("text")
            elif "output" in data and isinstance(data["output"], str):
                text_out = data["output"]
            elif "choices" in data and isinstance(data["choices"], list) and data["choices"]:
                # Some generic LLM response formats
                ch = data["choices"][0]
                text_out = ch.get("text") or ch.get("message") or ch.get("content")

        if not text_out:
            # Fall back to raw response text
            text_out = resp.text

        # Try to parse JSON from the returned string
        import json
        cleaned = text_out.strip()
        # Some models may wrap JSON in ``` blocks; strip them
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`\n ")

        try:
            parsed = json.loads(cleaned)
            # Ensure keys exist
            if "raw_text" not in parsed:
                parsed["raw_text"] = raw_text
            if "card_type" not in parsed:
                parsed["card_type"] = parsed.get("card_type", "Unknown")
            if "fields" not in parsed:
                parsed["fields"] = {}
            return parsed
        except Exception:
            # If the model didn't return pure JSON, attempt to find a JSON object inside
            import re
            m = re.search(r"\{[\s\S]*\}", cleaned)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    if "raw_text" not in parsed:
                        parsed["raw_text"] = raw_text
                    if "card_type" not in parsed:
                        parsed["card_type"] = parsed.get("card_type", "Unknown")
                    if "fields" not in parsed:
                        parsed["fields"] = {}
                    return parsed
                except Exception:
                    pass

        # As a final fallback, return a minimal structured dict
        return {"raw_text": raw_text, "card_type": "Unknown", "fields": {}}

    def _easyocr_extract(self, image_bytes: bytes) -> Dict[str, Any]:
        """Run EasyOCR on the image and apply simple heuristics to produce structured JSON."""
        text = ""
        fields: Dict[str, Any] = {}

        try:
            if not EASYOCR_AVAILABLE:
                logger.error("EasyOCR not installed. Install easyocr to use local OCR fallback.")
                return {"raw_text": "", "card_type": "Unknown", "fields": {}}

            reader = easyocr.Reader(["en"])  # English only for now
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # easyocr requires numpy array
            import numpy as np
            arr = np.array(img)
            ocr_result = reader.readtext(arr, detail=0)
            text = "\n".join(ocr_result)

            # Heuristic parsing
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            # Guess card type by keywords
            card_type = "Unknown"
            joined = " ".join(lines).lower()
            if "ghana" in joined or "ghana card" in joined:
                card_type = "Ghana Card"
            elif "passport" in joined:
                card_type = "Passport"
            elif "driver" in joined or "driving" in joined:
                card_type = "Driver's License"
            elif "voter" in joined:
                card_type = "Voter ID"
            elif "nhis" in joined:
                card_type = "NHIS Card"
            elif "ssnit" in joined:
                card_type = "SSNIT Card"
            elif "tin" in joined:
                card_type = "TIN Document"
            elif "birth" in joined:
                card_type = "Birth Certificate"

            # Very naive field extraction by regex patterns
            import re

            def extract_regex(pattern, default=""):
                for ln in lines:
                    m = re.search(pattern, ln, flags=re.IGNORECASE)
                    if m:
                        return m.group(1).strip()
                return default

            surname = extract_regex(r"surname[:\s]*([A-Za-z \-']+)") or extract_regex(r"surname\s*-\s*([A-Za-z \-']+)")
            firstname = extract_regex(r"(?:first|given)[:\s]*([A-Za-z \-']+)")
            dob = extract_regex(r"(\d{2}[\/\-]\d{2}[\/\-]\d{4})")
            docno = extract_regex(r"(GHA[-\s]?[0-9A-Z]+|[A-Z]{2,}\s?\d{3,})")
            gender = extract_regex(r"(Male|Female|M|F)")
            nationality = extract_regex(r"Nationality[:\s]*([A-Za-z ]+)")
            place = extract_regex(r"Place of Issue[:\s]*([A-Za-z ,]+)")
            date_issue = extract_regex(r"Date of Issue[:\s]*([0-9\-/]+)")
            date_expiry = extract_regex(r"Date of Expiry[:\s]*([0-9\-/]+)")

            # If not found, try line heuristics
            if not surname and lines:
                surname = lines[0]
            fields = {
                "surname": surname,
                "firstnames": firstname or (lines[1] if len(lines) > 1 else ""),
                "previous_names": "",
                "date_of_birth": dob,
                "sex": gender,
                "nationality": nationality,
                "document_number": docno,
                "date_of_issue": date_issue,
                "date_of_expiry": date_expiry,
                "place_of_issue": place,
                "height": "",
            }

            return {"raw_text": text, "card_type": card_type, "fields": fields}

        except Exception as e:
            logger.exception(f"Local OCR extraction failed: {e}")
            return {"raw_text": "", "card_type": "Unknown", "fields": {}}
