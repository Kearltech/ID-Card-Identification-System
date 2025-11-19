"""Face matching utilities.

Try multiple strategies:
- face_recognition (preferred) for embedding-based match
- imagehash (phash) fallback to compare visual similarity
"""
import io
import logging
from typing import Tuple
from PIL import Image

logger = logging.getLogger(__name__)


def _phash_distance(img1: Image.Image, img2: Image.Image) -> int:
    try:
        import imagehash
    except Exception:
        raise
    h1 = imagehash.phash(img1.convert('L'))
    h2 = imagehash.phash(img2.convert('L'))
    return h1 - h2


def compare_faces(img_bytes_a: bytes, img_bytes_b: bytes) -> Tuple[bool, dict]:
    """Return (match:bool, details).

    details includes 'method' used and 'score' (distance or similarity).
    """
    img_a = Image.open(io.BytesIO(img_bytes_a)).convert('RGB')
    img_b = Image.open(io.BytesIO(img_bytes_b)).convert('RGB')

    # Try face_recognition first
    try:
        import face_recognition
        import numpy as np
        arr_a = np.array(img_a)
        arr_b = np.array(img_b)
        locs_a = face_recognition.face_locations(arr_a)
        locs_b = face_recognition.face_locations(arr_b)
        if not locs_a or not locs_b:
            # No face detected in one or both
            logger.debug("face_recognition did not find faces in one/both images")
        else:
            enc_a = face_recognition.face_encodings(arr_a, known_face_locations=locs_a)
            enc_b = face_recognition.face_encodings(arr_b, known_face_locations=locs_b)
            if enc_a and enc_b:
                # Compare first face from each
                dist = face_recognition.face_distance([enc_a[0]], enc_b[0])[0]
                # lower distance is better; threshold ~0.6
                match = dist < 0.6
                return match, {"method": "face_recognition", "score": float(dist)}
    except Exception as e:
        logger.debug(f"face_recognition not available or failed: {e}")

    # phash fallback
    try:
        d = _phash_distance(img_a, img_b)
        # phash distance: 0 identical, up to ~64. (threshold subjective)
        match = d <= 10
        return match, {"method": "phash", "score": int(d)}
    except Exception as e:
        logger.debug(f"phash fallback failed: {e}")

    # Last resort: use simple mean-squared pixel diff
    try:
        import numpy as np
        a = np.array(img_a.resize((256, 256))).astype('float32')
        b = np.array(img_b.resize((256, 256))).astype('float32')
        mse = float(((a - b) ** 2).mean())
        match = mse < 2000
        return match, {"method": "mse", "score": mse}
    except Exception as e:
        logger.exception("All face matching methods failed")
        return False, {"method": "none", "score": None}
