import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("civicassist.pdf_parser")

# Notice type detection patterns
NOTICE_PATTERNS = {
    "143(1)": [r"143\s*\(\s*1\s*\)", r"intimation", r"section\s*143"],
    "139(9)": [r"139\s*\(\s*9\s*\)", r"defective\s*return"],
    "148":    [r"\b148\b", r"income\s*escaping", r"reassessment"],
    "142(1)": [r"142\s*\(\s*1\s*\)", r"inquiry\s*before\s*assessment"],
    "156":    [r"\b156\b", r"demand\s*notice"],
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
        return ""

    text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
    return text.strip()


def detect_notice_type(text: str) -> Optional[str]:
    """
    Detect the type of income tax notice from extracted PDF text.
    Returns the notice section number (e.g., '143(1)') or None.
    """
    text_lower = text.lower()
    
    # Check each notice type's patterns
    for notice_type, patterns in NOTICE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                logger.info(f"Detected notice type: {notice_type}")
                return notice_type

    logger.warning("Could not detect notice type from PDF text.")
    return None


def parse_notice(file_bytes: bytes) -> Dict[str, Any]:
    """
    Full PDF notice parsing pipeline:
      1. Extract text from PDF bytes
      2. Detect notice type
      3. Return structured result
    """
    raw_text = extract_text_from_pdf(file_bytes)
    
    if not raw_text:
        return {
            "notice_type": None,
            "raw_text": "",
            "error": "Could not extract text from PDF.",
        }
    
    notice_type = detect_notice_type(raw_text)
    
    return {
        "notice_type": notice_type,
        "raw_text": raw_text,
    }
