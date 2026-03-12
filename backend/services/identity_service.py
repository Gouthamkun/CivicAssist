"""
Identity Service for extracting user information from government documents.
Uses pytesseract for OCR and regex for pattern matching.
"""
import re
import logging
from typing import Dict, Optional, Set
from datetime import datetime

logger = logging.getLogger("civicassist.identity_service")

try:
    from PIL import Image
    import pytesseract
    import io
except ImportError:
    logger.error("OCR dependencies missing.")

def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Helper to extract text from image bytes."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""

def normalize_name(name: Optional[str]) -> Set[str]:
    """
    Standardize name for comparison. 
    Returns a set of words to handle reversed names and case-insensitivity.
    """
    if not name:
        return set()
    # Remove special chars, lower case, split into words
    clean_name = re.sub(r"[^a-zA-Z\s]", "", name).lower()
    return set(clean_name.split())

def normalize_dob(dob_str: Optional[str]) -> Optional[str]:
    """
    Normalize DOB to YYYY-MM-DD format.
    Handles DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD etc.
    """
    if not dob_str:
        return None
    
    # Common patterns
    patterns = [
        r"(\d{2})[-/](\d{2})[-/](\d{4})", # DD-MM-YYYY or DD/MM/YYYY
        r"(\d{4})[-/](\d{2})[-/](\d{2})", # YYYY-MM-DD or YYYY/MM/DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, dob_str)
        if match:
            g = match.groups()
            if len(g[0]) == 4: # YYYY-MM-DD
                return f"{g[0]}-{g[1]}-{g[2]}"
            else: # DD-MM-YYYY
                return f"{g[2]}-{g[1]}-{g[0]}"
                
    return None

def extract_info_from_doc(file_bytes: bytes, doc_type: str) -> Dict[str, Optional[str]]:
    """
    Extract Name and DOB from Aadhaar or PAN.
    Note: Highly simplified patterns for demonstration/hackathon.
    """
    text = extract_text_from_bytes(file_bytes)
    result = {"name": None, "dob": None}
    
    # Generic regex patterns
    dob_pattern = r"(\d{2}/\d{2}/\d{4})"
    name_match = re.search(r"Name:\s*([A-Za-z\s]+)", text, re.IGNORECASE)
    dob_match = re.search(dob_pattern, text)

    if name_match:
        result["name"] = name_match.group(1).strip()
    if dob_match:
        result["dob"] = dob_match.group(1)
        
    # Fallback for Aadhaar "Year of Birth"
    if not result["dob"]:
        yob_match = re.search(r"Year of Birth:\s*(\d{4})", text, re.IGNORECASE)
        if yob_match:
            result["dob"] = f"01/01/{yob_match.group(1)}"

    return result

def extract_uan_from_passbook(file_bytes: bytes) -> Dict[str, Optional[str]]:
    """
    Extract UAN, Name, and DOB from a passbook screenshot.
    """
    text = extract_text_from_bytes(file_bytes)
    result = {"uan": None, "name": None, "dob": None}
    
    uan_match = re.search(r"UAN:?\s*(\d{12})", text, re.IGNORECASE)
    name_match = re.search(r"Member Name:?\s*([A-Za-z\s]+)", text, re.IGNORECASE)
    dob_match = re.search(r"DOB:?\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)

    if uan_match:
        result["uan"] = uan_match.group(1)
    if name_match:
        result["name"] = name_match.group(1).strip()
    if dob_match:
        result["dob"] = dob_match.group(1)
        
    return result
