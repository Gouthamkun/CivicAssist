"""
Automated tests for the CivicAssist backend pipeline.
Run with: python -m pytest tests/test_pipeline.py -v
Or simply: python tests/test_pipeline.py
"""
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.classifier.query_classifier import classify_query
from backend.rag.retrieval_pipeline import retrieve
from backend.services.response_builder import build_response


# ── 1. Query Classification Tests ──

def test_classifier():
    cases = [
        ("I received a Section 139(9) notice", "tax_notice"),
        ("What is a 143(1) intimation?", "tax_notice"),
        ("How do I file my ITR?", "itr_filing"),
        ("What is the deadline for filing?", "filing_deadlines"),
        ("My tax refund has not been processed", "refund_status"),
        ("What is Form 26AS?", "tax_forms"),
        ("Which ITR form should I use?", "tax_forms"),
        ("When is the penalty for late filing?", "filing_deadlines"),
        ("How to verify my ITR using Aadhaar OTP?", "itr_filing"),
        ("I got a reassessment notice under Section 148", "tax_notice"),
    ]

    print("\n=== Classification Tests ===")
    passed = 0
    for query, expected in cases:
        result = classify_query(query)["query_type"]
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] '{query}' => {result} (expected: {expected})")
    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


# ── 2. Retrieval Tests ──

def test_retrieval():
    queries = [
        ("What is a Section 143(1) notice?", "notice_143_1"),
        ("How do I verify my ITR?", "itr_verification"),
        ("My tax refund has not been processed", "refund_process"),
        ("What is Form 26AS?", "form_26as"),
    ]

    print("=== Retrieval Tests ===")
    passed = 0
    for query, expected_source_fragment in queries:
        result = retrieve(query)
        docs = result.get("documents", [])
        sources = [os.path.basename(d["source"]) for d in docs]
        
        # Check if any returned source filename contains the expected fragment
        found = any(expected_source_fragment in s for s in sources)
        status = "PASS" if found else "FAIL"
        if found:
            passed += 1
        print(f"  [{status}] '{query}' => Sources: {sources}")
    print(f"\n  Result: {passed}/{len(queries)} passed\n")
    return passed == len(queries)


# ── 3. Response Builder Tests ──

def test_response_builder():
    queries = [
        "What is a Section 143(1) notice?",
        "How do I verify my ITR?",
        "My tax refund has not been processed.",
        "What is Form 26AS?",
    ]

    print("=== Response Builder Tests ===")
    passed = 0
    for query in queries:
        retrieval_result = retrieve(query)
        response = build_response(retrieval_result)

        # Validate response structure
        has_explanation = bool(response.get("explanation"))
        has_action = bool(response.get("recommended_action"))
        has_query_type = bool(response.get("query_type"))
        
        all_ok = has_explanation and has_action and has_query_type
        status = "PASS" if all_ok else "FAIL"
        if all_ok:
            passed += 1
        print(f"  [{status}] '{query}'")
        print(f"         Type: {response['query_type']}")
        print(f"         Explanation: {response['explanation'][:100]}...")
        print(f"         Action: {response['recommended_action']}")
        print(f"         Steps: {len(response.get('steps', []))} found")
        print(f"         Deadline: {response.get('deadline', 'None')}")
    print(f"\n  Result: {passed}/{len(queries)} passed\n")
    return passed == len(queries)


if __name__ == "__main__":
    # Reconfigure stdout for UTF-8 on Windows
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("CivicAssist Backend Pipeline Tests")
    print("=" * 60)

    r1 = test_classifier()
    r2 = test_retrieval()
    r3 = test_response_builder()

    print("=" * 60)
    if r1 and r2 and r3:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED — review output above")
    print("=" * 60)
