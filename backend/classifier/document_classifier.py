"""
Document Classification Module.
Classifies extracted text into a government department and detects the specific notice type.
"""
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("civicassist.document_classifier")

# ── Department Keywords ──
DEPARTMENT_KEYWORDS = {
    "income_tax": [
        "income tax", "section 143", "section 139", "section 148", "section 142",
        "section 156", "itr", "income tax department", "assessing officer",
        "central board of direct taxes", "cbdt", "e-filing", "form 26as",
        "form 16", "pan", "tax deducted at source", "tds",
    ],
    "epfo": [
        "epfo", "uan", "provident fund", "employees provident fund",
        "pf claim", "eps", "pension", "epf", "pf withdrawal",
        "member id", "establishment code",
    ],
    "passport": [
        "passport seva", "passport office", "police verification",
        "passport application", "regional passport office", "mea",
        "ministry of external affairs", "passport number",
    ],
}

# ── Notice Type Patterns per Department ──
NOTICE_PATTERNS = {
    "income_tax": {
        "143(1)": [r"143\s*\(\s*1\s*\)", r"intimation\s*under\s*section\s*143"],
        "139(9)": [r"139\s*\(\s*9\s*\)", r"defective\s*return"],
        "148":    [r"\b148\b.*(?:notice|reassessment)", r"income\s*escaping\s*assessment"],
        "142(1)": [r"142\s*\(\s*1\s*\)", r"inquiry\s*before\s*assessment"],
        "156":    [r"\b156\b", r"demand\s*notice"],
    },
    "epfo": {
        "pf_claim_rejection":      [r"claim\s*(?:has been|is)\s*rejected", r"rejection\s*of\s*(?:pf|provident fund)\s*claim"],
        "kyc_mismatch":            [r"kyc\s*mismatch", r"aadhaar\s*(?:not|mismatch)", r"name\s*mismatch"],
        "bank_verification_issue": [r"bank\s*(?:verification|account)\s*(?:failed|issue|mismatch)", r"ifsc\s*(?:invalid|mismatch)"],
    },
    "passport": {
        "police_verification_pending":  [r"police\s*verification\s*(?:pending|awaited|required)", r"verification\s*report"],
        "document_verification_issue":  [r"document\s*(?:verification|discrepancy)", r"supporting\s*documents?\s*(?:missing|required|incomplete)"],
    },
}


def classify_department(text: str) -> str:
    """Classify extracted text into a government department."""
    text_lower = text.lower()
    scores = {}

    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[dept] = score

    best_dept = max(scores, key=scores.get)
    if scores[best_dept] == 0:
        logger.info("No department keywords found. Classified as 'unknown'.")
        return "unknown"

    logger.info(f"Classified department: {best_dept} (score: {scores[best_dept]})")
    return best_dept


def detect_notice_type(text: str, department: str) -> Optional[str]:
    """Detect the specific notice type within a department."""
    if department == "unknown" or department not in NOTICE_PATTERNS:
        return None

    text_lower = text.lower()
    patterns = NOTICE_PATTERNS[department]

    for notice_type, regexes in patterns.items():
        for pattern in regexes:
            if re.search(pattern, text_lower):
                logger.info(f"Detected notice type: {notice_type}")
                return notice_type

    logger.warning(f"Could not detect specific notice type for department '{department}'.")
    return None


def classify_document(raw_text: str) -> Dict[str, Any]:
    """
    Full classification pipeline:
      1. Detect department
      2. Detect notice type
    """
    department = classify_department(raw_text)
    notice_type = detect_notice_type(raw_text, department)

    return {
        "department": department,
        "notice_type": notice_type,
    }
