"""
Automated tests for FastAPI Loan Eligibility API.
Covers all 6 required scenarios and edge cases.
"""

import sys
from fastapi.testclient import TestClient
from main import app

# Setup UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)


def run_api_tests():
    print("=" * 70)
    print("RUNNING API TEST SUITE")
    print("=" * 70)

    # Health & Rules Checks
    r = client.get("/")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json().get("ok") is True
    print("[PASS] Health Check endpoints (GET / and GET /health: ok=True)")

    r_rules = client.get("/rules")
    assert r_rules.status_code == 200
    assert "rules" in r_rules.json() and "emi_assumptions" in r_rules.json()
    print("[PASS] Rules endpoint (GET /rules: loaded from rules.json)")

    # Test Case 1: Standard Eligible
    c1_payload = {
        "age": 35,
        "monthly_income": 90000,
        "credit_score": 780,
        "employment_years": 8,
        "existing_emi": 0,
        "loan_amount": 500000,
    }
    r_c1 = client.post("/eligibility", json=c1_payload)
    assert r_c1.status_code == 200
    d_c1 = r_c1.json()
    assert d_c1["status"] == "ELIGIBLE", f"Expected ELIGIBLE, got {d_c1['status']}"
    print(f"[PASS] Case 1 — Eligible: status={d_c1['status']}")

    # Test Case 2: Text Normalization
    c2_payload = {
        "age": "27 years",
        "monthly_income": "₹60k",
        "credit_score": 760,
        "employment_years": "3 years",
        "existing_emi": "Rs. 15,000",
        "loan_amount": "2 lakh",
    }
    r_c2 = client.post("/eligibility", json=c2_payload)
    assert r_c2.status_code == 200
    d_c2 = r_c2.json()
    assert d_c2["status"] == "ELIGIBLE", f"Expected ELIGIBLE, got {d_c2['status']}"
    print(f"[PASS] Case 2 — Text normalization: status={d_c2['status']}")

    # Test Case 3: Missing credit score
    c3_payload = {
        "age": 29,
        "monthly_income": 45000,
        "employment_years": 3,
        "existing_emi": 0,
        "loan_amount": 150000,
    }
    r_c3 = client.post("/eligibility", json=c3_payload)
    assert r_c3.status_code == 200
    d_c3 = r_c3.json()
    assert d_c3["status"] == "INCOMPLETE", f"Expected INCOMPLETE, got {d_c3['status']}"
    assert "credit_score" in d_c3["missing_fields"]
    print(f"[PASS] Case 3 — Missing credit score: status={d_c3['status']}, missing={d_c3['missing_fields']}")

    # Test Case 4: Invalid amount ("a lot") -> HTTP 422
    c4_payload = {
        "age": 27,
        "monthly_income": "a lot",
        "credit_score": 760,
        "employment_years": 3,
        "existing_emi": 0,
        "loan_amount": 200000,
    }
    r_c4 = client.post("/eligibility", json=c4_payload)
    assert r_c4.status_code == 422, f"Expected 422, got {r_c4.status_code}"
    d_c4 = r_c4.json()
    assert "detail" in d_c4
    assert any(err.get("field") == "monthly_income" for err in d_c4["detail"])
    print(f"[PASS] Case 4 — Invalid amount: status=422, detail={d_c4['detail']}")

    # Test Case 5: Zero income -> HTTP 200, status=NOT_ELIGIBLE, metrics.dti=null
    c5_payload = {
        "age": 27,
        "monthly_income": 0,
        "credit_score": 760,
        "employment_years": 3,
        "existing_emi": 0,
        "loan_amount": 200000,
    }
    r_c5 = client.post("/eligibility", json=c5_payload)
    assert r_c5.status_code == 200, f"Expected 200, got {r_c5.status_code}"
    d_c5 = r_c5.json()
    assert d_c5["status"] == "NOT_ELIGIBLE", f"Expected NOT_ELIGIBLE, got {d_c5['status']}"
    assert d_c5["metrics"]["dti"] is None, f"Expected dti null, got {d_c5['metrics']['dti']}"
    print(f"[PASS] Case 5 — Zero income: status={d_c5['status']}, dti={d_c5['metrics']['dti']}")

    # Test 1: Eligible
    t1_payload = {
        "age": 27,
        "monthly_income": 60000,
        "credit_score": 760,
        "employment_years": 3,
        "existing_emi": 15000,
        "loan_amount": 200000,
    }
    r1 = client.post("/eligibility", json=t1_payload)
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"
    data1 = r1.json()
    assert data1["status"] == "ELIGIBLE", f"Expected ELIGIBLE, got {data1['status']}"
    print(f"[PASS] Test 1 — Eligible: Status={data1['status']}, new_emi={data1['metrics']['new_emi']}, dti={data1['metrics']['dti']}")

    # Test 2: High DTI
    t2_payload = {
        "age": 27,
        "monthly_income": 60000,
        "credit_score": 760,
        "employment_years": 3,
        "existing_emi": 15000,
        "loan_amount": 1000000,
    }
    r2 = client.post("/eligibility", json=t2_payload)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "NOT_ELIGIBLE", f"Expected NOT_ELIGIBLE, got {data2['status']}"
    print(f"[PASS] Test 2 — High DTI: Status={data2['status']}, dti={data2['metrics']['dti']}")

    # Test 3: Missing credit score
    t3_payload = {
        "age": 27,
        "monthly_income": 60000,
        "employment_years": 3,
        "existing_emi": 15000,
        "loan_amount": 200000,
    }
    r3 = client.post("/eligibility", json=t3_payload)
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["status"] == "INCOMPLETE", f"Expected INCOMPLETE, got {data3['status']}"
    assert "credit_score" in data3["missing_fields"], "Expected credit_score in missing_fields"
    print(f"[PASS] Test 3 — Missing credit score: Status={data3['status']}, missing={data3['missing_fields']}")

    # Test 4: Review credit score (690)
    t4_payload = {
        "age": 27,
        "monthly_income": 60000,
        "credit_score": 690,
        "employment_years": 3,
        "existing_emi": 15000,
        "loan_amount": 200000,
    }
    r4 = client.post("/eligibility", json=t4_payload)
    assert r4.status_code == 200
    data4 = r4.json()
    assert data4["status"] == "REVIEW", f"Expected REVIEW, got {data4['status']}"
    print(f"[PASS] Test 4 — Review credit score: Status={data4['status']}")

    # Test 5: Mock API
    r5 = client.get("/mock/income/APP001")
    assert r5.status_code == 200
    data5 = r5.json()
    assert data5["applicant_id"] == "APP001"
    assert data5["monthly_income"] == 60000
    assert data5["source"] == "SIMULATED_BANK_API"
    print(f"[PASS] Test 5 — Mock API GET /mock/income/APP001: income={data5['monthly_income']}, source={data5['source']}")

    # Test 6: Verified eligibility
    t6_payload = {
        "applicant_id": "APP001",
        "age": 27,
        "loan_amount": 200000,
    }
    r6 = client.post("/eligibility/verified", json=t6_payload)
    assert r6.status_code == 200
    data6 = r6.json()
    assert data6["status"] == "ELIGIBLE", f"Expected ELIGIBLE, got {data6['status']}"
    assert "data_sources" in data6, "Expected data_sources in response"
    assert data6["data_sources"]["monthly_income"] == "VERIFIED_API"
    assert data6["data_sources"]["age"] == "USER_PROVIDED"
    print(f"[PASS] Test 6 — Verified Eligibility POST /eligibility/verified: Status={data6['status']}, Sources verified")

    # Extra: Normalization test
    norm_payload = {
        "monthly_income": "₹5,00,000",
        "existing_emi": "15,000",
        "loan_amount": "5 lakh",
    }
    r_norm = client.post("/normalize", json=norm_payload)
    assert r_norm.status_code == 200
    d_norm = r_norm.json()
    assert d_norm["monthly_income"] == 500000
    assert d_norm["existing_emi"] == 15000
    assert d_norm["loan_amount"] == 500000
    print(f"[PASS] Normalization POST /normalize: {norm_payload} -> {d_norm}")

    # Extra: Validation & Error handling
    r_neg = client.post("/eligibility", json={"monthly_income": -5000})
    assert r_neg.status_code == 422
    assert "detail" in r_neg.json()
    print(f"[PASS] Error Handling (negative income): Status={r_neg.status_code}, detail={r_neg.json()['detail']}")

    r_404 = client.get("/mock/income/APP999")
    assert r_404.status_code == 404
    assert "error" in r_404.json()
    print(f"[PASS] Error Handling (404 not found): Status={r_404.status_code}, error={r_404.json()['error']}")

    # Test 7: Add Mock Applicant via POST /mock/applicant
    new_mock_payload = {
        "applicant_id": "TEST_APP01",
        "monthly_income": 75000,
        "credit_score": 750,
        "employment_years": 4.0,
        "existing_emi": 10000,
    }
    r_create = client.post("/mock/applicant", json=new_mock_payload)
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}: {r_create.text}"
    create_data = r_create.json()
    assert create_data["status"] == "success"
    assert create_data["applicant_id"] == "TEST_APP01"
    print(f"[PASS] Test 7 — Add Mock Applicant POST /mock/applicant: ID={create_data['applicant_id']}")

    # Verify retrieval of newly created mock applicant
    r_get_created = client.get("/mock/applicant/TEST_APP01")
    assert r_get_created.status_code == 200
    assert r_get_created.json()["monthly_income"] == 75000

    # Verify integration with verified eligibility endpoint
    r_verified_new = client.post("/eligibility/verified", json={"applicant_id": "TEST_APP01", "age": 30, "loan_amount": 250000})
    assert r_verified_new.status_code == 200
    assert r_verified_new.json()["status"] == "ELIGIBLE"
    print(f"[PASS] Test 8 — Verified Eligibility for newly created applicant: Status={r_verified_new.json()['status']}")

    # Clean up test applicant
    r_del = client.delete("/mock/applicant/TEST_APP01")
    assert r_del.status_code == 200
    print("[PASS] Cleaned up TEST_APP01 from mock database")

    print("=" * 70)
    print("ALL API TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_api_tests()
