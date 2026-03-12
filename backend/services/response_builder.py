import re
from typing import Dict, Any, List, Optional


def _extract_steps(text: str) -> List[str]:
    """Extract numbered or bulleted steps from document text."""
    steps = []
    # Match lines starting with number+dot or dash/star bullet
    for line in text.split("\n"):
        line = line.strip()
        if re.match(r"^(\d+[\.\)]\s|[-*]\s)", line):
            # Clean markdown bold markers
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            steps.append(clean)
    return steps


def _extract_deadline(text: str) -> Optional[str]:
    """Try to find deadline-related sentences in the text."""
    deadline_keywords = ["deadline", "due date", "last date", "within", "30 days", "15 days", "July 31", "October 31"]
    for line in text.split("\n"):
        for keyword in deadline_keywords:
            if keyword.lower() in line.lower():
                clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line.strip())
                return clean
    return None


def build_response(retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts retrieved knowledge documents into a structured civic guidance
    response. No LLM is used — this is pure text extraction and formatting.
    """
    query = retrieval_result.get("query", "")
    query_type = retrieval_result.get("query_type", "general")
    documents = retrieval_result.get("documents", [])

    if not documents:
        return {
            "query": query,
            "query_type": query_type,
            "explanation": "Sorry, I could not find relevant information for your query.",
            "recommended_action": "Please rephrase your question or visit https://www.incometax.gov.in for official guidance.",
            "steps": [],
            "deadline": None,
            "sources": [],
        }

    # Use the top document as primary source for the explanation
    primary = documents[0]
    primary_text = primary["content"]

    # Build explanation: take the first ~300 chars as a summary
    explanation_lines = []
    for line in primary_text.split("\n"):
        line = line.strip()
        # Skip header lines and empty lines
        if not line or line.startswith("#") or line.startswith("**Page ID") or line.startswith("**Category"):
            continue
        if line.startswith("## Official Sources") or line.startswith("## Typical Queries"):
            continue
        explanation_lines.append(re.sub(r"\*\*(.+?)\*\*", r"\1", line))
        if len(" ".join(explanation_lines)) > 400:
            break
    explanation = " ".join(explanation_lines).strip()

    # Extract steps from all documents
    all_steps = []
    for doc in documents:
        all_steps.extend(_extract_steps(doc["content"]))
    # Deduplicate while preserving order
    seen = set()
    unique_steps = []
    for step in all_steps:
        if step not in seen:
            seen.add(step)
            unique_steps.append(step)

    # Extract deadline
    deadline = None
    for doc in documents:
        deadline = _extract_deadline(doc["content"])
        if deadline:
            break

    # Build recommended action based on query type
    action_map = {
        "tax_notice": "Read the notice carefully, gather the required documents, and respond within the specified deadline via the e-Filing portal.",
        "itr_filing": "Login to the Income Tax e-Filing portal and follow the step-by-step filing process.",
        "tax_forms": "Review the eligibility criteria for each form and select the one matching your income profile.",
        "refund_status": "Track your refund status on the e-Filing portal under 'View Filed Returns'.",
        "filing_deadlines": "Ensure you file your ITR before the applicable deadline to avoid penalties.",
        "general": "Visit https://www.incometax.gov.in for detailed guidance.",
    }
    recommended_action = action_map.get(query_type, action_map["general"])

    # Collect sources
    sources = list(set(doc["source"] for doc in documents))

    return {
        "query": query,
        "query_type": query_type,
        "explanation": explanation,
        "recommended_action": recommended_action,
        "steps": unique_steps[:10],  # Limit to top 10 steps
        "deadline": deadline,
        "sources": sources,
    }
