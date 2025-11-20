"""
InsightFace Embeddings wrapper for UIVS
Generates ArcFace/InsightFace embeddings using the insightface library.

This module wraps `insightface.app.FaceAnalysis` and provides a simple
`extract_embedding` function that returns a float32 numpy vector or None.
"""

import logging
from typing import Optional
import numpy as np
from PIL import Image
import io

logger = logging.getLogger(__name__)

try:
    from insightface.app import FaceAnalysis
    HAVE_INSIGHTFACE = True
except Exception:
    HAVE_INSIGHTFACE = False
    logger.warning("insightface not available")


class InsightFaceEmbeddings:
    """Wrapper around insightface FaceAnalysis."""

    def __init__(self, ctx_id: int = 0, det_size=(640, 640)):
        self.available = False
        self.app = None
        if not HAVE_INSIGHTFACE:
            return

        try:
            self.app = FaceAnalysis(allowed_modules=['detection', 'recognition'])
            # Prepare may take time; ctx_id=-1 uses CPU
            self.app.prepare(ctx_id=ctx_id, det_size=det_size)
            self.available = True
            logger.info("InsightFace FaceAnalysis initialized")
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")

    def extract_embedding(self, face_image: Image.Image) -> Optional[np.ndarray]:
        """
        Extract embedding from a PIL Image of a face.

        Returns:
            numpy.ndarray (float32) embedding vector, or None
        """
        if not self.available:
            return None

        try:
            # Convert PIL to numpy BGR as expected by insightface
            arr = np.array(face_image.convert('RGB'))
            # insightface expects BGR
            arr = arr[:, :, ::-1].copy()

            faces = self.app.get(arr)
            if not faces:
                return None

            # Use first detected face
            emb = faces[0].embedding
            if emb is None:
                return None

            return np.asarray(emb, dtype=np.float32)

        except Exception as e:
            logger.error(f"InsightFace embedding extraction failed: {e}")
            return None
