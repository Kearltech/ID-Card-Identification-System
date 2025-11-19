"""Image preprocessing module for improved OCR accuracy.

This module provides functions to enhance ID card images before OCR processing,
handling rotation, lighting variations, and contrast issues.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


def detect_rotation(image: np.ndarray) -> float:
    """Detect rotation angle of the image using text orientation.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Rotation angle in degrees (0-360)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Use edge detection to find text lines
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Detect lines using HoughLines
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    
    if lines is None or len(lines) == 0:
        return 0.0
    
    # Calculate average angle
    angles = []
    for line in lines[:20]:  # Use first 20 lines
        rho, theta = line[0]
        angle = np.degrees(theta) - 90
        if -45 <= angle <= 45:
            angles.append(angle)
    
    if not angles:
        return 0.0
    
    # Return median angle (more robust than mean)
    return np.median(angles)


def rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by given angle.
    
    Args:
        image: Input image in BGR format
        angle: Rotation angle in degrees
        
    Returns:
        Rotated image
    """
    if abs(angle) < 0.5:  # Skip rotation if angle is very small
        return image
    
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new dimensions
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    
    # Adjust rotation matrix for new dimensions
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    # Rotate image
    rotated = cv2.warpAffine(image, M, (new_w, new_h), 
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_REPLICATE)
    
    return rotated


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Contrast-enhanced image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return enhanced


def correct_lighting(image: np.ndarray) -> np.ndarray:
    """Correct non-uniform lighting using morphological operations.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Lighting-corrected image
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create background model using morphological opening
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    background = cv2.GaussianBlur(background, (5, 5), 0)
    
    # Normalize by background
    normalized = cv2.divide(gray, background, scale=255)
    
    # Convert back to BGR
    normalized_bgr = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
    
    return normalized_bgr


def denoise_image(image: np.ndarray) -> np.ndarray:
    """Remove noise from image while preserving edges.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Denoised image
    """
    # Use Non-local Means Denoising
    denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    return denoised


def sharpen_image(image: np.ndarray) -> np.ndarray:
    """Sharpen image to improve text clarity.
    
    Args:
        image: Input image in BGR format
        
    Returns:
        Sharpened image
    """
    # Create sharpening kernel
    kernel = np.array([[-1, -1, -1],
                      [-1,  9, -1],
                      [-1, -1, -1]])
    
    sharpened = cv2.filter2D(image, -1, kernel)
    return sharpened


def preprocess_for_ocr(image: np.ndarray, 
                       auto_rotate: bool = True,
                       enhance_contrast_flag: bool = True,
                       correct_lighting_flag: bool = True,
                       denoise: bool = True,
                       sharpen: bool = False) -> np.ndarray:
    """Comprehensive preprocessing pipeline for OCR.
    
    Args:
        image: Input image in BGR format
        auto_rotate: Whether to auto-detect and correct rotation
        enhance_contrast_flag: Whether to enhance contrast
        correct_lighting_flag: Whether to correct lighting
        denoise: Whether to denoise the image
        sharpen: Whether to sharpen the image (use carefully)
        
    Returns:
        Preprocessed image ready for OCR
    """
    processed = image.copy()
    
    # Step 1: Auto-rotate if enabled
    if auto_rotate:
        angle = detect_rotation(processed)
        if abs(angle) > 0.5:
            processed = rotate_image(processed, angle)
    
    # Step 2: Correct lighting (do this before contrast enhancement)
    if correct_lighting_flag:
        processed = correct_lighting(processed)
    
    # Step 3: Enhance contrast
    if enhance_contrast_flag:
        processed = enhance_contrast(processed)
    
    # Step 4: Denoise
    if denoise:
        processed = denoise_image(processed)
    
    # Step 5: Sharpen (optional, can sometimes hurt OCR)
    if sharpen:
        processed = sharpen_image(processed)
    
    return processed


def resize_for_ocr(image: np.ndarray, max_dimension: int = 2000) -> np.ndarray:
    """Resize image to optimal size for OCR while maintaining aspect ratio.
    
    Args:
        image: Input image in BGR format
        max_dimension: Maximum dimension (width or height)
        
    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    max_size = max(h, w)
    
    if max_size <= max_dimension:
        return image
    
    scale = max_dimension / max_size
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized

