"""
Tests for the Government Notice Explanation feature.
Run with: python tests/test_notice_explanation.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from backend.classifier.document_classifier import classify_department, detect_notice_type, classify_document
from backend.services.notice_explainer import explain_notice


# ── 1. Department Classification Tests ──

def test_department_classification():
    cases = [
        ("This is an intimation under Section 143(1) of the Income Tax Act.", "income_tax"),
        ("Your PF claim has been rejected due to KYC mismatch. Contact your EPFO office.", "epfo"),
        ("Your passport application requires police verification. Visit Passport Seva.", "passport"),
        ("Hello, this is a random document with no keywords.", "unknown"),
        ("The Income Tax Department has issued a notice under Section 148.", "income_tax"),
        ("UAN 100123456789 — Your provident fund withdrawal is pending.", "epfo"),
    ]

    print("\n=== Department Classification Tests ===")
    passed = 0
    for text, expected in cases:
        result = classify_department(text)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] '{text[:60]}...' => {result} (expected: {expected})")
    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


# ── 2. Notice Type Detection Tests ──

def test_notice_type_detection():
    cases = [
        ("Section 143(1) intimation notice", "income_tax", "143(1)"),
        ("Defective return notice under Section 139(9)", "income_tax", "139(9)"),
        ("Notice under Section 148 for reassessment", "income_tax", "148"),
        ("Your PF claim has been rejected", "epfo", "pf_claim_rejection"),
        ("KYC mismatch found in your records", "epfo", "kyc_mismatch"),
        ("Police verification pending for your passport", "passport", "police_verification_pending"),
    ]

    print("=== Notice Type Detection Tests ===")
    passed = 0
    for text, dept, expected in cases:
        result = detect_notice_type(text, dept)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] dept={dept}, text='{text[:50]}...' => {result} (expected: {expected})")
    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


# ── 3. Full Pipeline Tests (classify + explain) ──

def test_full_pipeline():
    cases = [
        {
            "text": "This is an intimation under Section 143(1) of the Income Tax Act. The total income assessed is different from what was declared.",
            "expected_dept": "income_tax",
            "expected_notice": "143(1)",
        },
        {
            "text": "Your provident fund claim has been rejected due to Aadhaar KYC mismatch with EPFO records. Please update your UAN details.",
            "expected_dept": "epfo",
            "expected_notice": "pf_claim_rejection",
        },
    ]

    print("=== Full Pipeline Tests ===")
    passed = 0
    for case in cases:
        classification = classify_document(case["text"])
        dept = classification["department"]
        notice = classification["notice_type"]

        dept_ok = dept == case["expected_dept"]
        notice_ok = notice == case["expected_notice"]

        response = explain_notice(case["text"], dept, notice)
        has_explanation = bool(response.get("explanation"))
        has_action = bool(response.get("recommended_action"))

        all_ok = dept_ok and notice_ok and has_explanation and has_action
        status = "PASS" if all_ok else "FAIL"
        if all_ok:
            passed += 1

        print(f"  [{status}] Dept: {dept} (exp: {case['expected_dept']}), Notice: {notice} (exp: {case['expected_notice']})")
        print(f"         Explanation: {response['explanation'][:100]}...")
        print(f"         Action: {response['recommended_action']}")
    print(f"\n  Result: {passed}/{len(cases)} passed\n")
    return passed == len(cases)


if __name__ == "__main__":
    print("=" * 60)
    print("Government Notice Explanation — Tests")
    print("=" * 60)

    r1 = test_department_classification()
    r2 = test_notice_type_detection()
    r3 = test_full_pipeline()

    print("=" * 60)
    if r1 and r2 and r3:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)
