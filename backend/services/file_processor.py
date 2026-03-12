"""
File Processing Layer for Government Notice Explanation.
Supports PDF (via PyMuPDF) and Images (via Tesseract OCR).
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger("civicassist.file_processor")

# Supported MIME types
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
}


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz
    text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
    return text.strip()


def _extract_image_text(file_bytes: bytes) -> str:
    """Extract text from image bytes using Tesseract OCR."""
    try:
        from PIL import Image
        import pytesseract
        import io

        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image, lang="eng")
        return text.strip()
    except ImportError:
        logger.error("Tesseract OCR dependencies not installed. Run: pip install pytesseract Pillow")
        return ""
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return ""


def detect_file_type(content_type: str, filename: str) -> str:
    """Detect file type from MIME type or extension."""
    # Try MIME type first
    if content_type in SUPPORTED_TYPES:
        return SUPPORTED_TYPES[content_type]
    
    # Fallback to extension
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in (".png", ".jpg", ".jpeg"):
        return "image"
    
    return "unsupported"


def process_file(file_bytes: bytes, content_type: str, filename: str) -> Dict[str, Any]:
    """
    Process an uploaded file and extract text.
    Returns: {"file_type": ..., "raw_text": ..., "error": ...}
    """
    file_type = detect_file_type(content_type, filename)
    logger.info(f"Processing file: {filename} (type: {file_type}, content_type: {content_type})")

    if file_type == "pdf":
        raw_text = _extract_pdf_text(file_bytes)
    elif file_type == "image":
        raw_text = _extract_image_text(file_bytes)
    else:
        return {
            "file_type": file_type,
            "raw_text": "",
            "error": f"Unsupported file type: {content_type} ({filename}). Please upload a PDF, PNG, or JPG file.",
        }

    if not raw_text:
        return {
            "file_type": file_type,
            "raw_text": "",
            "error": "Could not extract text from the uploaded file. Ensure the file is not password-protected and contains readable text.",
        }

    return {
        "file_type": file_type,
        "raw_text": raw_text,
    }
