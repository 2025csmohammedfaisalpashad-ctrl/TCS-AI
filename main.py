"""
FastAPI Backend Application for Bank Loan Eligibility.
TCS Technology Day Hackathon Project.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from engine import evaluate, load_rules
from normalize import NormalizationValidationException, normalize_applicant_dict

# Initialize FastAPI App
app = FastAPI(
    title="Loan Eligibility API",
    description="Deterministic bank loan eligibility API for TCS Technology Day",
    version="1.0.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_DATA_PATH = Path(__file__).resolve().parent / "mock_data.json"


# Custom Exception Handlers for Clean JSON Responses
@app.exception_handler(NormalizationValidationException)
async def normalization_validation_handler(request: Request, exc: NormalizationValidationException):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field_loc = err.get("loc", [])
        field_name = str(field_loc[-1]) if field_loc else "body"
        errors.append({"field": field_name, "message": err.get("msg", "Invalid input")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail if isinstance(exc.detail, (str, list, dict)) else str(exc.detail),
            "error": str(exc.detail),
        },
    )


# -----------------------------------------------------------------------------
# Data Models with Swagger Examples
# -----------------------------------------------------------------------------
class ApplicantRequest(BaseModel):
    applicant_id: str | None = Field(default=None, description="Optional applicant ID", examples=["APP001"])
    age: Any | None = Field(default=None, description="Applicant age in years (e.g. 27 or '27 years')", examples=[27])
    monthly_income: Any | None = Field(default=None, description="Gross monthly income in INR (e.g. 60000 or '₹60k')", examples=[60000])
    credit_score: Any | None = Field(default=None, description="CIBIL / Credit bureau score (e.g. 760)", examples=[760])
    employment_years: Any | None = Field(default=None, description="Employment vintage in years (e.g. 3.0 or '3 years', '18 months')", examples=[3.0])
    existing_emi: Any | None = Field(default=None, description="Current ongoing monthly EMI payments in INR (e.g. 15000 or 'Rs. 15,000')", examples=[15000])
    loan_amount: Any | None = Field(default=None, description="Requested loan amount in INR (e.g. 200000 or '2 lakh')", examples=[200000])

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "age": 27,
                "monthly_income": 60000,
                "credit_score": 760,
                "employment_years": 3,
                "existing_emi": 15000,
                "loan_amount": 200000,
            }
        },
    }


Applicant = ApplicantRequest


class VerifiedApplicantRequest(BaseModel):
    applicant_id: str = Field(..., description="Simulated Applicant ID (APP001 - APP015)", examples=["APP001"])
    age: int | None = Field(default=None, description="User-provided age in years", examples=[27])
    loan_amount: float | None = Field(default=None, description="User-requested loan amount in INR", examples=[200000])

    model_config = {
        "json_schema_extra": {
            "example": {
                "applicant_id": "APP001",
                "age": 27,
                "loan_amount": 200000,
            }
        }
    }


class NormalizeRequest(BaseModel):
    monthly_income: Any | None = Field(default=None, description="E.g. ₹5,00,000 or 500000", examples=["₹5,00,000"])
    existing_emi: Any | None = Field(default=None, description="E.g. 15,000", examples=["15,000"])
    loan_amount: Any | None = Field(default=None, description="E.g. 5 lakh or 5L", examples=["5 lakh"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "monthly_income": "₹5,00,000",
                "existing_emi": "15,000",
                "loan_amount": "5 lakh",
            }
        }
    }


class MockApplicantCreate(BaseModel):
    applicant_id: str | None = Field(
        default=None,
        description="Optional applicant ID (e.g. APP016). Auto-generated if omitted.",
        examples=["APP016"],
    )
    monthly_income: float = Field(
        ...,
        ge=0,
        description="Gross monthly income in INR",
        examples=[75000],
    )
    credit_score: int = Field(
        ...,
        ge=300,
        le=900,
        description="CIBIL / Credit bureau score (300-900)",
        examples=[750],
    )
    employment_years: float = Field(
        ...,
        ge=0,
        description="Employment vintage in years",
        examples=[4.0],
    )
    existing_emi: float = Field(
        default=0.0,
        ge=0,
        description="Current ongoing monthly EMI payments in INR",
        examples=[10000],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "applicant_id": "APP016",
                "monthly_income": 75000,
                "credit_score": 750,
                "employment_years": 4.0,
                "existing_emi": 10000,
            }
        }
    }



# Basic input validation helper
def validate_applicant(applicant: Applicant):
    if applicant.age is not None and applicant.age < 0:
        raise HTTPException(status_code=400, detail="age cannot be negative")
    if applicant.monthly_income is not None and applicant.monthly_income < 0:
        raise HTTPException(status_code=400, detail="monthly_income cannot be negative")
    if applicant.credit_score is not None and applicant.credit_score < 0:
        raise HTTPException(status_code=400, detail="credit_score cannot be negative")
    if applicant.employment_years is not None and applicant.employment_years < 0:
        raise HTTPException(status_code=400, detail="employment_years cannot be negative")
    if applicant.existing_emi is not None and applicant.existing_emi < 0:
        raise HTTPException(status_code=400, detail="existing_emi cannot be negative")
    if applicant.loan_amount is not None and applicant.loan_amount < 0:
        raise HTTPException(status_code=400, detail="loan_amount cannot be negative")


def get_mock_database() -> Dict[str, Any]:
    if not MOCK_DATA_PATH.exists():
        raise HTTPException(status_code=500, detail="mock_data.json file not found")
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mock_database(data: Dict[str, Any]) -> None:
    """Safely persist mock applicant data into mock_data.json."""
    with open(MOCK_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_next_applicant_id(db: Dict[str, Any]) -> str:
    """Generate the next applicant ID like APP016 based on existing APPxxx IDs."""
    numbers = []
    for key in db.keys():
        match = re.match(r"^APP(\d+)$", key, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
    next_num = (max(numbers) + 1) if numbers else 1
    return f"APP{next_num:03d}"


def normalize_numeric_string(raw: Any) -> float | int | None:
    """
    Normalizes common Indian currency notations and shorthand to numbers.
    Supports ₹5,00,000, 5,00,000, 500000, 5 lakh, 5L, ₹5 lakh, 2.5 lakh, etc.
    Does not convert annual notations silently.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return raw
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    # Strip currency symbols, prefix symbols (? if Windows cp1252 converts ₹), and commas
    cleaned = re.sub(r"[₹\u20b9?Rs\.INR,\s$]", "", text, flags=re.IGNORECASE)

    # Check for lakh / lac / L pattern
    lakh_match = re.match(r"^([\d\.]+)\s*(?:lakhs?|lac|lacs|l)$", cleaned, re.IGNORECASE)
    if lakh_match:
        try:
            val = float(lakh_match.group(1)) * 100000
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            pass

    # Check for crore / cr pattern
    crore_match = re.match(r"^([\d\.]+)\s*(?:crores?|cr)$", cleaned, re.IGNORECASE)
    if crore_match:
        try:
            val = float(crore_match.group(1)) * 10000000
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            pass

    # Check for k / thousand pattern
    k_match = re.match(r"^([\d\.]+)\s*(?:k|thousand)$", cleaned, re.IGNORECASE)
    if k_match:
        try:
            val = float(k_match.group(1)) * 1000
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            pass

    # Standard numeric conversion
    try:
        val = float(cleaned)
        return int(val) if val.is_integer() else round(val, 2)
    except ValueError:
        return raw


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.get("/")
def root():
    """Root health check endpoint."""
    return {"status": "ok", "service": "Loan Eligibility API"}


@app.get("/health")
def health():
    """Service health status endpoint."""
    return {"ok": True, "status": "healthy"}


@app.get("/rules")
def get_rules():
    """
    Returns the currently active loan evaluation rules from rules.json.
    Does not hardcode rules.
    """
    return load_rules()


@app.post("/eligibility")
def check_eligibility(req: ApplicantRequest):
    """
    Evaluates loan eligibility using the deterministic engine.
    Supports raw numbers as well as Indian shorthand strings (e.g. ₹60k, 27 years, 18 months, 2 lakh).
    All applicant fields are optional to support conversational chatbots collecting data over time.
    """
    t_start = time.perf_counter()
    raw_dict = req.model_dump()
    normalized = normalize_applicant_dict(raw_dict)

    applicant_data = {
        "age": normalized.get("age"),
        "monthly_income": normalized.get("monthly_income"),
        "credit_score": normalized.get("credit_score"),
        "employment_years": normalized.get("employment_years"),
        "existing_emi": normalized.get("existing_emi"),
        "loan_amount": normalized.get("loan_amount"),
    }

    result = evaluate(applicant_data)

    if normalized.get("applicant_id"):
        result["applicant_id"] = normalized["applicant_id"]

    elapsed_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    result["elapsed_ms"] = elapsed_ms

    return result


@app.post("/normalize")
def normalize_input(
    payload: Dict[str, Any] = Body(
        ...,
        openapi_examples={
            "standard": {
                "summary": "Sample currency shorthand",
                "value": {
                    "monthly_income": "₹5,00,000",
                    "existing_emi": "15,000",
                    "loan_amount": "5 lakh",
                },
            }
        },
    )
):
    """
    Normalizes numeric values with shorthand (e.g. ₹5,00,000, 5 lakh, 5L) to numbers.
    """
    normalized: Dict[str, Any] = {}
    for key, value in payload.items():
        normalized[key] = normalize_numeric_string(value)
    return normalized


# -----------------------------------------------------------------------------
# Simulated Banking APIs
# -----------------------------------------------------------------------------


@app.get("/mock/applicants")
def list_mock_applicants():
    """List all available simulated applicants in the mock database."""
    db = get_mock_database()
    return {"total": len(db), "applicant_ids": list(db.keys()), "applicants": db}


@app.get("/mock/applicant/{applicant_id}")
def get_mock_applicant(applicant_id: str):
    """Retrieve complete simulated banking profile for an applicant."""
    db = get_mock_database()
    app_id = applicant_id.strip().upper()
    if app_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    return {
        "applicant_id": app_id,
        **db[app_id],
        "source": "SIMULATED_BANK_DATABASE",
    }


@app.post("/mock/applicant", status_code=status.HTTP_201_CREATED)
@app.post("/mock/applicants", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def add_mock_applicant(payload: MockApplicantCreate):
    """
    Adds a new simulated banking applicant record to mock_data.json.
    Exposes an interactive POST endpoint in Swagger UI to add mock applicants.
    If applicant_id is omitted, an ID (e.g. APP016) is auto-generated.
    """
    db = get_mock_database()

    app_id = (
        payload.applicant_id.strip().upper()
        if payload.applicant_id and payload.applicant_id.strip()
        else get_next_applicant_id(db)
    )

    db[app_id] = {
        "monthly_income": payload.monthly_income,
        "credit_score": payload.credit_score,
        "employment_years": payload.employment_years,
        "existing_emi": payload.existing_emi,
    }

    save_mock_database(db)

    return {
        "status": "success",
        "message": f"Applicant {app_id} successfully added to mock database",
        "applicant_id": app_id,
        "data": db[app_id],
    }


@app.delete("/mock/applicant/{applicant_id}")
def delete_mock_applicant(applicant_id: str):
    """Remove a mock applicant from mock_data.json (useful for test teardown)."""
    db = get_mock_database()
    app_id = applicant_id.strip().upper()
    if app_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    removed = db.pop(app_id)
    save_mock_database(db)
    return {"status": "success", "message": f"Applicant {app_id} deleted", "data": removed}


@app.get("/mock/income/{applicant_id}")
def mock_income(applicant_id: str):
    db = get_mock_database()
    if applicant_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    return {
        "applicant_id": applicant_id,
        "monthly_income": db[applicant_id]["monthly_income"],
        "source": "SIMULATED_BANK_API",
    }


@app.get("/mock/credit/{applicant_id}")
def mock_credit(applicant_id: str):
    db = get_mock_database()
    if applicant_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    return {
        "applicant_id": applicant_id,
        "credit_score": db[applicant_id]["credit_score"],
        "source": "SIMULATED_CREDIT_API",
    }


@app.get("/mock/employment/{applicant_id}")
def mock_employment(applicant_id: str):
    db = get_mock_database()
    if applicant_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    return {
        "applicant_id": applicant_id,
        "employment_years": db[applicant_id]["employment_years"],
        "source": "SIMULATED_EMPLOYMENT_API",
    }


@app.get("/mock/loans/{applicant_id}")
def mock_loans(applicant_id: str):
    db = get_mock_database()
    if applicant_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {applicant_id} not found")
    return {
        "applicant_id": applicant_id,
        "existing_emi": db[applicant_id]["existing_emi"],
        "source": "SIMULATED_LOAN_API",
    }


# -----------------------------------------------------------------------------
# Verified Data Eligibility Endpoint
# -----------------------------------------------------------------------------


@app.post("/eligibility/verified")
def check_verified_eligibility(req: VerifiedApplicantRequest):
    """
    Combines simulated banking data with user-provided parameters,
    runs the deterministic rules engine, and marks data origins.
    """
    if req.age is not None and req.age < 0:
        raise HTTPException(status_code=400, detail="age cannot be negative")
    if req.loan_amount is not None and req.loan_amount < 0:
        raise HTTPException(status_code=400, detail="loan_amount cannot be negative")

    db = get_mock_database()
    if req.applicant_id not in db:
        raise HTTPException(status_code=404, detail=f"Applicant {req.applicant_id} not found")

    verified_data = db[req.applicant_id]

    applicant_data = {
        "age": req.age,
        "monthly_income": verified_data.get("monthly_income"),
        "credit_score": verified_data.get("credit_score"),
        "employment_years": verified_data.get("employment_years"),
        "existing_emi": verified_data.get("existing_emi"),
        "loan_amount": req.loan_amount,
    }

    result = evaluate(applicant_data)

    result["data_sources"] = {
        "monthly_income": "VERIFIED_API",
        "credit_score": "VERIFIED_API",
        "employment_years": "VERIFIED_API",
        "existing_emi": "VERIFIED_API",
        "age": "USER_PROVIDED",
        "loan_amount": "USER_PROVIDED",
    }

    return result
