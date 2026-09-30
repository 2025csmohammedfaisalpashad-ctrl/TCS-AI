from fastapi import FastAPI
from pydantic import BaseModel

from rules import check_eligibility


app = FastAPI(
    title="Loan Eligibility API",
    description="Backend API for automated loan eligibility checking",
    version="1.0.0"
)


from pydantic import BaseModel, Field


class Applicant(BaseModel):

    age: int = Field(..., ge=0)

    monthly_income: float = Field(..., gt=0)

    credit_score: int = Field(..., ge=0, le=900)

    employment_years: float = Field(..., ge=0)

    existing_emi: float = Field(..., ge=0)

    loan_amount: float = Field(..., gt=0)
@app.get("/")
def home():
    return {
        "message": "Loan Eligibility Backend is running"
    }


@app.post("/eligibility")
def eligibility(applicant: Applicant):

    applicant_data = applicant.model_dump()

    result = check_eligibility(applicant_data)

    return result