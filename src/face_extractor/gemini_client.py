"""Lightweight Gemini API client scaffold.

This module provides a safe-to-use wrapper that will only perform network calls
when `GEMINI_API_KEY` is set and `GEMINI_DRY_RUN` is false. By default this acts
as a dry-run and returns no changes. Use it to optionally validate OCR fields
using a large language model (Gemini) for semantic checks.
"""
import os
import logging
from typing import Dict, Any

import json

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINT = os.getenv("GEMINI_ENDPOINT", "https://api.example.com/v1/gemini")
GEMINI_DRY_RUN = os.getenv("GEMINI_DRY_RUN", "true").lower() in ("1", "true", "yes")


class GeminiClient:
    """A minimal Gemini client scaffold.

    Usage:
        client = GeminiClient()
        if client.enabled:
            result = client.validate_fields(fields_dict)

    The client will not make network calls unless GEMINI_API_KEY is set and
    GEMINI_DRY_RUN is explicitly set to false.
    """

    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.endpoint = GEMINI_ENDPOINT
        self.dry_run = GEMINI_DRY_RUN
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.info("Gemini client disabled (no GEMINI_API_KEY found)")
        elif self.dry_run:
            logger.info("Gemini client in dry-run mode (no network calls will be made)")
        else:
            logger.info("Gemini client enabled")

    def validate_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Validate/augment fields using the Gemini API.

        Returns a dictionary with structure:
            {"enabled": bool, "corrections": {field_name: suggested_value}, "notes": str}

        In dry-run or disabled mode this returns empty corrections.
        """
        if not self.enabled:
            return {"enabled": False, "corrections": {}, "notes": "disabled"}

        if self.dry_run:
            # Simulate a harmless response without external calls
            notes = "dry-run: no external call made"
            logger.debug("Gemini dry-run validation requested")
            return {"enabled": True, "corrections": {}, "notes": notes}

        # Real network interaction (only if enabled and not dry_run)
        try:
            import requests

            payload = {
                "prompt": "Validate and correct these ID fields if necessary. Return JSON with suggested corrections.",
                "fields": fields,
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Expect data["corrections"] to be present
            return {"enabled": True, "corrections": data.get("corrections", {}), "notes": data.get("notes", "")}
        except Exception as e:
            logger.warning(f"Gemini validation failed: {e}")
            return {"enabled": True, "corrections": {}, "notes": f"error: {e}"}


if __name__ == "__main__":
    client = GeminiClient()
    print(client.validate_fields({"Name": "John Doe", "ID": "GHA-123456789-0"}))
