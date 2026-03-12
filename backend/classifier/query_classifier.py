import re
from typing import Dict

# Define rule-based categorization logic
CATEGORIES = {
    "tax_notice": [
        "notice", "143(1)", "intimation", "139(9)", "defective", 
        "148", "reassessment", "respond to notice", "sent me a notice", "demand"
    ],
    "itr_filing": [
        "file itr", "file my itr", "submit return", "how to file", "filing process", 
        "step-by-step", "verify", "evc", "aadhaar otp", "login",
        "e-filing", "efiling", "file return", "file tax"
    ],
    "tax_forms": [
        "which form", "itr form", "itr-1", "itr-2", "itr-3", "itr-4", "sahaj", 
        "sugam", "form 16", "form 26as", "ais", "annual information statement"
    ],
    "refund_status": [
        "refund", "delay", "not received refund", "track refund", 
        "refund status", "when will i get my refund"
    ],
    "filing_deadlines": [
        "deadline", "due date", "last date", "penalty", "late fee", 
        "234f", "belated", "revised return"
    ]
}

def classify_query(query: str) -> Dict[str, str]:
    """
    Classifies a user query into one of the predefined tax categories 
    using keyword matching.
    """
    query_lower = query.lower()
    
    # Check for direct matches based on rules
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            # Using boundaries to prevent partial word matches, though some 
            # keywords are phrases so a simple substring search works well enough for an MVP.
            if re.search(rf"\b{re.escape(keyword)}\b", query_lower):
                return {"query_type": category}
                
    # Fallback to a general category if no keyword matches
    return {"query_type": "general"}
