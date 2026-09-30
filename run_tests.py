"""
Test runner for deterministic loan eligibility engine.
Supports running all tests or a specific applicant ID.
"""

import json
import sys
import time
from pathlib import Path
from engine import evaluate

# Configure UTF-8 output for Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TEST_FILE = Path(__file__).resolve().parent / "test_applicants.json"



def print_applicant_detail(app_id: str, data: dict):
    applicant = data.get("applicant", {})
    expected = data.get("expected_verdict", "UNKNOWN")
    note = data.get("note", "")

    result = evaluate(applicant)
    is_match = result["status"] == expected

    print("=" * 60)
    print(f"APPLICANT BREAKDOWN: {app_id}")
    print("=" * 60)
    print(f"Note:             {note}")
    print(f"Expected Verdict: {expected}")
    print(f"Actual Verdict:   {result['status']} ({'MATCH' if is_match else 'MISMATCH'})")
    print("-" * 60)
    print("Applicant Data:")
    for k, v in applicant.items():
        print(f"  - {k}: {v}")
    print("-" * 60)
    print("Metrics:")
    for k, v in result.get("metrics", {}).items():
        print(f"  - {k}: {v}")
    print("-" * 60)
    print("Checks:")
    for c in result.get("checks", []):
        print(f"  [{c['status'].upper():6s}] {c['rule']}: {c['detail']}")
    if result.get("missing_fields"):
        print("-" * 60)
        print("Missing Fields:")
        for mf in result["missing_fields"]:
            print(f"  - {mf}")
    if result.get("reasons"):
        print("-" * 60)
        print("Reasons:")
        for r in result["reasons"]:
            print(f"  - {r}")
    if result.get("suggestions"):
        print("-" * 60)
        print("Suggestions:")
        for s in result["suggestions"]:
            print(f"  - {s}")
    print("=" * 60)


def run_all_tests():
    if not TEST_FILE.exists():
        print(f"Error: {TEST_FILE} not found.")
        sys.exit(1)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    passed = 0

    print("=" * 85)
    print(f"{'ID':<8} | {'Expected':<12} | {'Actual':<12} | {'Result':<6} | {'Note'}")
    print("=" * 85)

    start_time = time.perf_counter()

    for app_id, data in test_cases.items():
        applicant = data.get("applicant", {})
        expected = data.get("expected_verdict")
        note = data.get("note", "")

        result = evaluate(applicant)
        actual = result.get("status")

        if actual == expected:
            passed += 1
            status_str = "PASS"
        else:
            status_str = "FAIL"

        print(f"{app_id:<8} | {expected:<12} | {actual:<12} | {status_str:<6} | {note}")

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    percentage = (passed / total * 100.0) if total > 0 else 0.0

    print("=" * 85)
    print(f"Agreement: {passed}/{total} = {percentage:.1f}%")
    print(f"Engine time for all cases: {elapsed_ms:.2f} ms")
    print("=" * 85)

    if passed != total:
        sys.exit(1)


def main():
    if len(sys.argv) > 1:
        target_id = sys.argv[1].strip()
        if not TEST_FILE.exists():
            print(f"Error: {TEST_FILE} not found.")
            sys.exit(1)
        with open(TEST_FILE, "r", encoding="utf-8") as f:
            test_cases = json.load(f)
        if target_id in test_cases:
            print_applicant_detail(target_id, test_cases[target_id])
        else:
            print(f"Applicant ID '{target_id}' not found in {TEST_FILE.name}")
            print(f"Available IDs: {', '.join(test_cases.keys())}")
            sys.exit(1)
    else:
        run_all_tests()


if __name__ == "__main__":
    main()
