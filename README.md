# AI-Powered Bank Loan Eligibility Chatbot Backend

Deterministic Bank Loan Eligibility API built for TCS Technology Day hackathon.

## Architecture

```text
Chat UI
   ↓
FastAPI
   ↓
LLM extraction  [future]
   ↓
Verified / normalized applicant data
   ↓
Deterministic Rules Engine
   ↓
Eligibility result
```

> **Core Principle**: The LLM does not make the loan decision. It extracts information and explains the deterministic rules-engine result. The deterministic engine is the single source of truth for all eligibility verdicts.

---

## Installation & Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the development server:
   ```bash
   uvicorn main:app --reload
   ```

3. Interactive API Documentation (Swagger UI):
   - **Local Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints

### 1. Health Checks
* **`GET /`**
  - Returns service status and name.
  - Response: `{"status": "ok", "service": "Loan Eligibility API"}`
* **`GET /health`**
  - Returns operational health status.
  - Response: `{"status": "healthy"}`

### 2. Direct Eligibility Evaluation
* **`POST /eligibility`**
  - Evaluates an applicant payload against the deterministic rules engine. Supports partial inputs (`INCOMPLETE` status with `missing_fields`).
  - Request body:
    ```json
    {
      "age": 27,
      "monthly_income": 60000,
      "credit_score": 760,
      "employment_years": 3,
      "existing_emi": 15000,
      "loan_amount": 200000
    }
    ```
  - Response:
    ```json
    {
      "status": "ELIGIBLE",
      "missing_fields": [],
      "checks": [
        {"rule": "age", "status": "pass", "detail": "Age 27 (allowed 21-60)"},
        {"rule": "monthly_income", "status": "pass", "detail": "Monthly income ₹60,000 (minimum ₹25,000)"},
        {"rule": "credit_score", "status": "pass", "detail": "Credit score 760 (700+ required for instant approval)"},
        {"rule": "employment_years", "status": "pass", "detail": "Employment 3.0 years (minimum 1 year)"},
        {"rule": "loan_amount", "status": "pass", "detail": "Loan amount ₹200,000 (allowed ₹50,000 - ₹2,000,000)"},
        {"rule": "dti", "status": "pass", "detail": "DTI ratio 32.4% (allowed <= 50%)"}
      ],
      "reasons": [],
      "suggestions": ["Congratulations! Your profile meets all standard eligibility criteria for approval."],
      "metrics": {
        "new_emi": 4449,
        "dti": 0.324,
        "max_affordable_loan": 674326
      }
    }
    ```

### 3. Normalization Utility
* **`POST /normalize`**
  - Converts human-entered currency strings and Indian shorthand formats into numbers.
  - Supports: `₹5,00,000`, `5,00,000`, `500000`, `5 lakh`, `5L`, `₹5 lakh`, `2.5 lakh`, etc.
  - Request body:
    ```json
    {
      "monthly_income": "₹5,00,000",
      "existing_emi": "15,000",
      "loan_amount": "5 lakh"
    }
    ```
  - Response:
    ```json
    {
      "monthly_income": 500000,
      "existing_emi": 15000,
      "loan_amount": 500000
    }
    ```

### 4. Simulated Banking APIs
* **`POST /mock/applicant`** (Swagger / Interactive)
  - Adds a new applicant to `mock_data.json` directly from Swagger UI or via API request.
  - Auto-generates ID if omitted (e.g. `APP016`).
  - Request body:
    ```json
    {
      "applicant_id": "APP016",
      "monthly_income": 75000,
      "credit_score": 750,
      "employment_years": 4.0,
      "existing_emi": 10000
    }
    ```
* **`GET /mock/applicants`**: Lists all simulated applicants and total count.
* **`GET /mock/applicant/{applicant_id}`**: Retrieves complete simulated profile.
* **`GET /mock/income/{applicant_id}`**: Retrieves simulated monthly income.
* **`GET /mock/credit/{applicant_id}`**: Retrieves simulated credit score.
* **`GET /mock/employment/{applicant_id}`**: Retrieves verified employment vintage.
* **`GET /mock/loans/{applicant_id}`**: Retrieves simulated existing monthly debt obligations.
* **`DELETE /mock/applicant/{applicant_id}`**: Deletes an applicant from mock database.

### 5. Verified Data Loan Evaluation
* **`POST /eligibility/verified`**
  - Fetches applicant's verified financial data from simulated banking endpoints, merges it with user-provided `age` and `loan_amount`, runs the engine, and tags data provenance.
  - Request body:
    ```json
    {
      "applicant_id": "APP001",
      "age": 27,
      "loan_amount": 200000
    }
    ```
  - Response includes `data_sources` indicating which fields were user-provided versus retrieved from verified APIs:
    ```json
    {
      "status": "ELIGIBLE",
      "data_sources": {
        "monthly_income": "VERIFIED_API",
        "credit_score": "VERIFIED_API",
        "employment_years": "VERIFIED_API",
        "existing_emi": "VERIFIED_API",
        "age": "USER_PROVIDED",
        "loan_amount": "USER_PROVIDED"
      },
      ...
    }
    ```

---

## Testing the Engine

Run the deterministic test suite:
```bash
python run_tests.py
```

Inspect specific applicant evaluation:
```bash
python run_tests.py APP001
```
