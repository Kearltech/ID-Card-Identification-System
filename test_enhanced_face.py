"""
Quick test script for Enhanced Face Comparator
Tests MediaPipe detection + Gemini embeddings integration
"""

import sys
import os
import cv2
import numpy as np
from PIL import Image
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import new modules
try:
    from advanced_face_detector import AdvancedFaceDetector
    from gemini_face_embeddings import GeminiFaceEmbeddings
    from enhanced_face_comparator import EnhancedFaceComparator
    logger.info("✓ All modules imported successfully")
except ImportError as e:
    logger.error(f"✗ Import failed: {e}")
    sys.exit(1)


def test_mediapipe_detection():
    """Test MediaPipe face detection."""
    logger.info("\n=== Testing MediaPipe Face Detection ===")

    try:
        detector = AdvancedFaceDetector(use_mediapipe=True)

        # Create a simple test image (random)
        test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        faces = detector.detect_faces(test_img)
        logger.info(f"✓ Detection completed. Faces found: {len(faces)}")

        if faces:
            for i, face in enumerate(faces):
                logger.info(f"  Face {i}: x={face['x']}, y={face['y']}, "
                           f"w={face['w']}, h={face['h']}, "
                           f"confidence={face['confidence']:.2f}, "
                           f"method={face['method']}")

        detector.close()
        return True

    except Exception as e:
        logger.error(f"✗ Detection test failed: {e}")
        return False


def test_gemini_availability():
    """Test Gemini API availability."""
    logger.info("\n=== Testing Gemini Availability ===")

    try:
        gemini = GeminiFaceEmbeddings()
        if gemini.available:
            logger.info("✓ Gemini API is available and configured")
        else:
            logger.warning("⚠ Gemini API not available - check GEMINI_API_KEY")
        return gemini.available

    except Exception as e:
        logger.error(f"✗ Gemini test failed: {e}")
        return False


def test_enhanced_comparator():
    """Test Enhanced Face Comparator initialization."""
    logger.info("\n=== Testing Enhanced Face Comparator ===")

    try:
        comparator = EnhancedFaceComparator()

        if comparator.detector:
            logger.info("✓ MediaPipe detector available")
        else:
            logger.warning("⚠ MediaPipe detector not available")

        if comparator.gemini_embeddings and comparator.gemini_embeddings.available:
            logger.info("✓ Gemini embeddings available")
        else:
            logger.warning("⚠ Gemini embeddings not available")

        if comparator.legacy_comparator:
            logger.info("✓ Legacy comparator available as fallback")
        else:
            logger.warning("⚠ Legacy comparator not available")

        comparator.close()
        return True

    except Exception as e:
        logger.error(f"✗ Comparator test failed: {e}")
        return False


def create_test_images():
    """Create synthetic test images."""
    logger.info("\n=== Creating Test Images ===")

    try:
        # Create simple gradient images (different)
        img1 = np.zeros((250, 250, 3), dtype=np.uint8)
        img1[:] = (100, 150, 200)  # Blue-ish

        img2 = np.zeros((250, 250, 3), dtype=np.uint8)
        img2[:] = (200, 150, 100)  # Orange-ish

        # Add some features
        cv2.circle(img1, (125, 125), 50, (255, 255, 255), -1)
        cv2.circle(img2, (125, 125), 50, (255, 255, 255), -1)

        pil1 = Image.fromarray(cv2.cvtColor(img1, cv2.COLOR_BGR2RGB))
        pil2 = Image.fromarray(cv2.cvtColor(img2, cv2.COLOR_BGR2RGB))

        logger.info("✓ Test images created")
        return pil1, pil2

    except Exception as e:
        logger.error(f"✗ Failed to create test images: {e}")
        return None, None


def test_comparison(pil1, pil2):
    """Test face comparison."""
    logger.info("\n=== Testing Face Comparison ===")

    try:
        comparator = EnhancedFaceComparator()

        result = comparator.compare_faces(pil1, pil2)

        logger.info(f"Match: {result['match']}")
        logger.info(f"Similarity: {result['similarity_score']:.2%}")
        logger.info(f"Engine: {result['engine_used']}")
        logger.info(f"Confidence: {result['confidence']:.2%}")
        logger.info(f"Details: {result['details']}")
        logger.info(f"Method chain: {' → '.join(result.get('method_chain', []))}")

        comparator.close()
        return True

    except Exception as e:
        logger.error(f"✗ Comparison test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("""
    ╔══════════════════════════════════════════════════════════════╗
    ║   Enhanced Face Comparator Integration Tests                ║
    ║   MediaPipe + Gemini Vision + Fallback Chain               ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    results = {
        'MediaPipe Detection': test_mediapipe_detection(),
        'Gemini Availability': test_gemini_availability(),
        'Enhanced Comparator': test_enhanced_comparator(),
    }

    # Test comparison with synthetic images
    img1, img2 = create_test_images()
    if img1 and img2:
        results['Face Comparison'] = test_comparison(img1, img2)

    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name:.<40} {status}")

    logger.info("=" * 60)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed!")
    elif passed >= total * 0.5:
        logger.info("⚠️  Some tests failed - check dependencies")
    else:
        logger.warning("❌ Most tests failed - install missing dependencies")


if __name__ == '__main__':
    main()
