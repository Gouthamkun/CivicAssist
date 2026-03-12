import re
import logging
import io
import os
from typing import Dict, Optional, Set, List
from datetime import datetime
from backend.services.ocr_service import get_reader, preprocess_image

logger = logging.getLogger("civicassist.identity_service")

def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Helper to extract text using EasyOCR (English + Hindi) with Advanced Preprocessing."""
    try:
        r = get_reader()
        # Apply the advanced preprocessing pipeline before OCR
        processed_bytes = preprocess_image(file_bytes)
        
        # EasyOCR can take processed bytes directly
        results = r.readtext(processed_bytes, detail=0, paragraph=True)
        text = " ".join(results)
        
        # Fallback to raw if processed text is too sparse (sometimes aggressive sharpening backfires)
        if len(text.strip()) < 10:
            results = r.readtext(file_bytes, detail=0, paragraph=True)
            text = " ".join(results)
            
        return text.strip()
    except Exception as e:
        logger.error(f"EasyOCR extraction with preprocessing failed: {e}")
        return ""

def normalize_name(name: Optional[str]) -> Set[str]:
    """Normalize name into a set of lowercase words for robust matching."""
    if not name:
        return set()
    return set(re.findall(r"\w+", name.lower()))

def normalize_dob(dob: Optional[str]) -> Optional[str]:
    """Normalize DOB into YYYY-MM-DD format."""
    if not dob:
        return None
    # Support DD/MM/YYYY or YYYY/MM/DD with various separators
    patterns = [
        r"(\d{4})[-/.](\d{2})[-/.](\d{2})",
        r"(\d{2})[-/.](\d{2})[-/.](\d{4})"
    ]
    for p in patterns:
        match = re.search(p, dob)
        if match:
            g = match.groups()
            if len(g[0]) == 4: # YYYY-MM-DD
                return f"{g[0]}-{g[1]}-{g[2]}"
            else: # DD-MM-YYYY
                return f"{g[2]}-{g[1]}-{g[0]}"
                
    return None

def extract_info_from_doc(file_bytes: bytes, doc_type: str) -> Dict[str, Optional[str]]:
    """
    Extract Name and DOB from Aadhaar or PAN using OCR and regex.
    """
    text = extract_text_from_bytes(file_bytes)
    result: Dict[str, Optional[str]] = {"name": None, "dob": None}
    
    # More robust DOB pattern (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY)
    dob_pattern = r"(\d{2}[-/.]\d{2}[-/.]\d{4})"
    name_match = re.search(r"(?:Name|NAME)[:\s]*([A-Z][A-Z\s]{3,})", text)
    dob_match = re.search(dob_pattern, text)

    if name_match:
        result["name"] = re.sub(r"\s+", " ", name_match.group(1)).strip()
    if dob_match:
        result["dob"] = dob_match.group(1).replace("-", "/").replace(".", "/")
        
    # Fallback for Aadhaar "Year of Birth"
    if not result["dob"]:
        yob_match = re.search(r"(?:Year of Birth|YOB)[:\s]*(\d{4})", text, re.IGNORECASE)
        if yob_match:
            result["dob"] = f"01/01/{yob_match.group(1)}"

    return result

def extract_uan_from_passbook(file_bytes: bytes) -> Dict[str, Optional[str]]:
    """
    Extract UAN, Name, Member ID, and DOB from a passbook screenshot using OCR and robust regex.
    """
    text = extract_text_from_bytes(file_bytes)
    result: Dict[str, Optional[str]] = {"uan": None, "name": None, "dob": None, "member_id": None}
    
    # Improved patterns with better flexiblity
    uan_match = re.search(r"(?:Universal Account Number|UAN)[:\s]*(\d{12})", text, re.IGNORECASE)
    name_match = re.search(r"(?:Member Name|Name)[:\s]*([A-Z\s]{5,})", text, re.IGNORECASE)
    dob_match = re.search(r"(?:DOB|Date of Birth)[:\s]*(\d{2}[-/.]\d{2}[-/.]\d{4})", text, re.IGNORECASE)
    member_id_match = re.search(r"(?:Member ID|MEMBER_ID)[:\s]*([A-Z0-9]+)", text, re.IGNORECASE)

    if uan_match:
        result["uan"] = uan_match.group(1)
    if name_match:
        # Simple cleanup for multiple spaces
        result["name"] = re.sub(r"\s+", " ", name_match.group(1).strip())
    if dob_match:
        result["dob"] = dob_match.group(1).replace("-", "/").replace(".", "/")
    if member_id_match:
        result["member_id"] = member_id_match.group(1)
        
    return result
