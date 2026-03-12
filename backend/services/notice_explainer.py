"""
Notice Explanation Builder.
Generates structured civic guidance from classified documents and retrieved knowledge.
"""
import re
import os
import logging
from typing import Dict, Any, List, Optional
from backend.rag.retrieval_pipeline import retrieve

logger = logging.getLogger("civicassist.notice_explainer")


def _extract_steps(text: str) -> List[str]:
    """Extract numbered or bulleted steps from document text."""
    steps = []
    for line in text.split("\n"):
        line = line.strip()
        if re.match(r"^(\d+[\.\)]\s|[-*]\s)", line):
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            steps.append(clean)
    return steps


def _extract_deadline(text: str) -> Optional[str]:
    """Find deadline information in text."""
    keywords = ["deadline", "due date", "last date", "within", "30 days", "15 days", "July 31", "October 31"]
    for line in text.split("\n"):
        for kw in keywords:
            if kw.lower() in line.lower():
                return re.sub(r"\*\*(.+?)\*\*", r"\1", line.strip())
    return None


# ── Fallback explanations when RAG has no match ──
FALLBACK_EXPLANATIONS = {
    "income_tax": {
        "explanation": "This appears to be a notice from the Income Tax Department.",
        "recommended_action": "Log in to the Income Tax e-Filing portal and check your pending notices under 'e-Proceedings'.",
    },
    "epfo": {
        "explanation": "This appears to be a communication from EPFO regarding your Provident Fund account.",
        "recommended_action": "Log in to the EPFO member portal (https://unifiedportal-mem.epfindia.gov.in) and check your claim status.",
    },
    "passport": {
        "explanation": "This appears to be a communication from the Passport Office.",
        "recommended_action": "Check your application status at https://passportindia.gov.in and contact the Regional Passport Office if needed.",
    },
    "unknown": {
        "explanation": "The uploaded document could not be identified as a known government notice.",
        "recommended_action": "Please verify that the uploaded file is a valid government notice and try again.",
    },
}


def explain_notice(
    raw_text: str,
    department: str,
    notice_type: Optional[str],
) -> Dict[str, Any]:
    """
    Build a structured explanation for a government notice.
    Uses RAG retrieval for known notice types, falls back to generic guidance.
    """
    # ── Step 1: Try RAG retrieval ──
    retrieved_docs = []
    if notice_type and department == "income_tax":
        query = f"Section {notice_type} income tax notice"
        retrieval_result = retrieve(query)
        retrieved_docs = retrieval_result.get("documents", [])
        logger.info(f"Retrieved {len(retrieved_docs)} docs for notice type '{notice_type}'")
    elif department in ("epfo", "passport") and notice_type:
        query = f"{department} {notice_type}"
        retrieval_result = retrieve(query)
        retrieved_docs = retrieval_result.get("documents", [])

    # ── Step 2: Build explanation from retrieved docs or fallback ──
    if retrieved_docs:
        primary_text = retrieved_docs[0]["content"]

        # Build explanation from content (skip headers)
        explanation_lines = []
        for line in primary_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("**Page ID") or line.startswith("**Category"):
                continue
            if line.startswith("## Official Sources") or line.startswith("## Typical Queries"):
                continue
            explanation_lines.append(re.sub(r"\*\*(.+?)\*\*", r"\1", line))
            if len(" ".join(explanation_lines)) > 500:
                break
        explanation = " ".join(explanation_lines).strip()

        # Steps and deadline from all docs
        all_steps = []
        for doc in retrieved_docs:
            all_steps.extend(_extract_steps(doc["content"]))
        seen = set()
        unique_steps = [s for s in all_steps if not (s in seen or seen.add(s))]

        deadline = None
        for doc in retrieved_docs:
            deadline = _extract_deadline(doc["content"])
            if deadline:
                break

        # Recommended action based on department
        action_map = {
            "income_tax": "Read the notice carefully, gather supporting documents, and respond within the specified deadline via the e-Filing portal.",
            "epfo": "Log in to the EPFO member portal and address the identified issue with your employer or EPFO office.",
            "passport": "Visit the Passport Seva portal or contact the Regional Passport Office to resolve the issue.",
        }
        recommended_action = action_map.get(department, "Follow the instructions mentioned in the notice.")

        sources = list(set(os.path.basename(d["source"]) for d in retrieved_docs))
    else:
        # Fallback
        fallback = FALLBACK_EXPLANATIONS.get(department, FALLBACK_EXPLANATIONS["unknown"])
        explanation = fallback["explanation"]
        recommended_action = fallback["recommended_action"]
        unique_steps = []
        deadline = None
        sources = []

    # ── Step 3: Format notice type label ──
    notice_label = None
    if notice_type:
        if department == "income_tax":
            label_map = {
                "143(1)": "Section 143(1) – Intimation Notice",
                "139(9)": "Section 139(9) – Defective Return Notice",
                "148": "Section 148 – Income Escaping Assessment",
                "142(1)": "Section 142(1) – Inquiry Before Assessment",
                "156": "Section 156 – Demand Notice",
            }
            notice_label = label_map.get(notice_type, f"Section {notice_type}")
        elif department == "epfo":
            label_map = {
                "pf_claim_rejection": "PF Claim Rejection",
                "kyc_mismatch": "KYC Mismatch",
                "bank_verification_issue": "Bank Verification Issue",
            }
            notice_label = label_map.get(notice_type, notice_type)
        elif department == "passport":
            label_map = {
                "police_verification_pending": "Police Verification Pending",
                "document_verification_issue": "Document Verification Issue",
            }
            notice_label = label_map.get(notice_type, notice_type)

    return {
        "department": department,
        "notice_type": notice_label or notice_type,
        "explanation": explanation,
        "recommended_action": recommended_action,
        "steps": unique_steps[:10],
        "deadline": deadline,
        "sources": sources,
    }
