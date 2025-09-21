import cv2
import numpy as np
from PIL import Image
from typing import Any


def preprocess_image(image_path: str) -> Any:
    """Load and preprocess image for OCR. Returns a numpy array suitable for pytesseract.image_to_data."""
    # Try multiple ways to load image with OpenCV
    img = None
    try:
        img = cv2.imread(image_path)
    except Exception:
        img = None

    # Fallback to PIL if cv2 can't read
    if img is None:
        pil_img = Image.open(image_path)
        if pil_img.mode != 'L':
            pil_img = pil_img.convert('L')
        return np.array(pil_img)

    # Convert to grayscale
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # Apply basic preprocessing
    try:
        denoised = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    except Exception:
        return gray
