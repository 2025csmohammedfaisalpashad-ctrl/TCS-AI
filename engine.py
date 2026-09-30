"""
Deterministic Bank Loan Eligibility Engine.
Single source of truth for loan evaluation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# Load rules from rules.json
RULES_PATH = Path(__file__).resolve().parent / "rules.json"


def load_rules() -> Dict[str, Any]:
    """Load evaluation rules and EMI assumptions from rules.json."""
    if RULES_PATH.exists():
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # Default fallback in case file is missing
    return {
        "loan_type": "personal",
        "emi_assumptions": {
            "annual_interest_rate": 0.12,
            "tenure_months": 60,
        },
        "rules": {
            "age": {"min": 21, "max": 60},
            "monthly_income": {"min": 25000},
            "credit_score": {"min": 700, "review_min": 680},
            "employment_years": {"min": 1},
            "dti": {"max": 0.50, "review_max": 0.55},
            "loan_amount": {"min": 50000, "max": 2000000},
        },
    }


REQUIRED_FIELDS = [
    "age",
    "monthly_income",
    "credit_score",
    "employment_years",
    "existing_emi",
    "loan_amount",
]


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate monthly reducing balance EMI."""
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    monthly_rate = annual_rate / 12.0
    if monthly_rate == 0:
        return principal / tenure_months
    factor = (1 + monthly_rate) ** tenure_months
    return principal * (monthly_rate * factor) / (factor - 1)


def calculate_max_affordable_loan(
    monthly_income: float,
    existing_emi: float,
    max_dti: float,
    annual_rate: float,
    tenure_months: int,
    max_loan_cap: float,
) -> float:
    """Calculate the maximum loan amount affordable within the allowable DTI cap."""
    if monthly_income <= 0:
        return 0.0
    max_total_emi = monthly_income * max_dti
    available_emi = max_total_emi - existing_emi
    if available_emi <= 0:
        return 0.0

    monthly_rate = annual_rate / 12.0
    if monthly_rate == 0:
        max_loan = available_emi * tenure_months
    else:
        factor = (1 + monthly_rate) ** tenure_months
        max_loan = available_emi * (factor - 1) / (monthly_rate * factor)

    return min(max_loan, max_loan_cap)


def evaluate(applicant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically evaluates an applicant for personal loan eligibility.
    Returns status: ELIGIBLE | NOT_ELIGIBLE | REVIEW | INCOMPLETE
    """
    # 1. Check for missing required fields
    missing_fields = [
        field for field in REQUIRED_FIELDS if field not in applicant or applicant[field] is None
    ]

    if missing_fields:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing_fields,
            "checks": [],
            "reasons": [f"Missing required field: {field}" for field in missing_fields],
            "suggestions": [
                f"Please provide {', '.join(missing_fields)} to proceed with eligibility evaluation."
            ],
            "metrics": {
                "new_emi": 0,
                "dti": 0,
                "max_affordable_loan": 0,
            },
        }

    config = load_rules()
    rules = config.get("rules", {})
    emi_cfg = config.get("emi_assumptions", {"annual_interest_rate": 0.12, "tenure_months": 60})

    annual_rate = emi_cfg.get("annual_interest_rate", 0.12)
    tenure = emi_cfg.get("tenure_months", 60)

    age = int(applicant["age"])
    monthly_income = float(applicant["monthly_income"])
    credit_score = int(applicant["credit_score"])
    employment_years = float(applicant["employment_years"])
    existing_emi = float(applicant["existing_emi"])
    loan_amount = float(applicant["loan_amount"])

    # 2. Metric Calculations
    new_emi = calculate_emi(loan_amount, annual_rate, tenure)
    total_monthly_debt = existing_emi + new_emi
    dti = total_monthly_debt / monthly_income if monthly_income > 0 else None

    dti_rule = rules.get("dti", {"max": 0.50, "review_max": 0.55})
    loan_rule = rules.get("loan_amount", {"min": 50000, "max": 2000000})

    max_affordable = calculate_max_affordable_loan(
        monthly_income=monthly_income,
        existing_emi=existing_emi,
        max_dti=dti_rule.get("max", 0.50),
        annual_rate=annual_rate,
        tenure_months=tenure,
        max_loan_cap=loan_rule.get("max", 2000000),
    )

    checks: List[Dict[str, str]] = []
    reasons: List[str] = []
    suggestions: List[str] = []

    # 3. Rule Checks

    # Check 1: Age
    age_rule = rules.get("age", {"min": 21, "max": 60})
    age_min = age_rule.get("min", 21)
    age_max = age_rule.get("max", 60)
    if age_min <= age <= age_max:
        checks.append({
            "rule": "age",
            "status": "pass",
            "detail": f"Age {age} (allowed {age_min}-{age_max})",
        })
    else:
        checks.append({
            "rule": "age",
            "status": "fail",
            "detail": f"Age {age} (allowed {age_min}-{age_max})",
        })
        reasons.append(
            f"Applicant age {age} is outside the allowed range of {age_min} to {age_max} years."
        )

    # Check 2: Monthly Income
    inc_rule = rules.get("monthly_income", {"min": 25000})
    inc_min = inc_rule.get("min", 25000)
    if monthly_income >= inc_min:
        checks.append({
            "rule": "monthly_income",
            "status": "pass",
            "detail": f"Monthly income ₹{monthly_income:,.0f} (minimum ₹{inc_min:,.0f})",
        })
    else:
        checks.append({
            "rule": "monthly_income",
            "status": "fail",
            "detail": f"Monthly income ₹{monthly_income:,.0f} (minimum ₹{inc_min:,.0f})",
        })
        reasons.append(
            f"Monthly income of ₹{monthly_income:,.0f} is below the minimum required ₹{inc_min:,.0f}."
        )
        suggestions.append(
            "Adding a co-applicant or guarantor with steady income can help satisfy income criteria."
        )

    # Check 3: Credit Score
    cs_rule = rules.get("credit_score", {"min": 700, "review_min": 680})
    cs_min = cs_rule.get("min", 700)
    cs_review = cs_rule.get("review_min", 680)
    if credit_score >= cs_min:
        checks.append({
            "rule": "credit_score",
            "status": "pass",
            "detail": f"Credit score {credit_score} (700+ required for instant approval)",
        })
    elif credit_score >= cs_review:
        checks.append({
            "rule": "credit_score",
            "status": "review",
            "detail": f"Credit score {credit_score} (review range {cs_review}-{cs_min - 1})",
        })
        reasons.append(
            f"Credit score of {credit_score} falls in the review band ({cs_review}-{cs_min - 1}) and requires underwriter review."
        )
        suggestions.append(
            "Consistently paying credit dues on time and lowering credit utilization can raise your score to 700+."
        )
    else:
        checks.append({
            "rule": "credit_score",
            "status": "fail",
            "detail": f"Credit score {credit_score} (minimum {cs_review} required)",
        })
        reasons.append(
            f"Credit score of {credit_score} is below the minimum threshold of {cs_review}."
        )
        suggestions.append(
            "A credit score above 700 is required for approval. Check credit report for discrepancies or clear overdue debts."
        )

    # Check 4: Employment Years
    emp_rule = rules.get("employment_years", {"min": 1})
    emp_min = emp_rule.get("min", 1)
    if employment_years >= emp_min:
        checks.append({
            "rule": "employment_years",
            "status": "pass",
            "detail": f"Employment {employment_years} years (minimum {emp_min} year)",
        })
    else:
        checks.append({
            "rule": "employment_years",
            "status": "fail",
            "detail": f"Employment {employment_years} years (minimum {emp_min} year)",
        })
        reasons.append(
            f"Employment duration of {employment_years} year(s) is below the minimum requirement of {emp_min} year."
        )
        suggestions.append(
            "At least 1 year of continuous employment or business vintage is required for personal loan eligibility."
        )

    # Check 5: Loan Amount
    la_min = loan_rule.get("min", 50000)
    la_max = loan_rule.get("max", 2000000)
    if la_min <= loan_amount <= la_max:
        checks.append({
            "rule": "loan_amount",
            "status": "pass",
            "detail": f"Loan amount ₹{loan_amount:,.0f} (allowed ₹{la_min:,.0f} - ₹{la_max:,.0f})",
        })
    else:
        checks.append({
            "rule": "loan_amount",
            "status": "fail",
            "detail": f"Loan amount ₹{loan_amount:,.0f} (allowed ₹{la_min:,.0f} - ₹{la_max:,.0f})",
        })
        if loan_amount < la_min:
            reasons.append(
                f"Requested loan amount of ₹{loan_amount:,.0f} is below the minimum permissible ₹{la_min:,.0f}."
            )
        else:
            reasons.append(
                f"Requested loan amount of ₹{loan_amount:,.0f} exceeds the maximum permissible ₹{la_max:,.0f}."
            )
        suggestions.append(
            f"Please choose a loan amount between ₹{la_min:,.0f} and ₹{la_max:,.0f}."
        )

    # Check 6: Debt-to-Income (DTI)
    dti_max = dti_rule.get("max", 0.50)
    dti_review_max = dti_rule.get("review_max", 0.55)
    if dti is None:
        checks.append({
            "rule": "dti",
            "status": "fail",
            "detail": "DTI cannot be computed with zero income",
        })
        reasons.append("Debt-to-income ratio cannot be computed with zero monthly income.")
    elif dti <= dti_max:
        checks.append({
            "rule": "dti",
            "status": "pass",
            "detail": f"DTI ratio {dti * 100:.1f}% (allowed <= {dti_max * 100:.0f}%)",
        })
    elif dti <= dti_review_max:
        checks.append({
            "rule": "dti",
            "status": "review",
            "detail": f"DTI ratio {dti * 100:.1f}% (review range {dti_max * 100:.0f}%-{dti_review_max * 100:.0f}%)",
        })
        reasons.append(
            f"Debt-to-income ratio ({dti * 100:.1f}%) is in the review range ({dti_max * 100:.0f}% to {dti_review_max * 100:.0f}%)."
        )
        suggestions.append(
            f"Reducing loan amount towards ₹{max_affordable:,.0f} or clearing existing EMI can bring DTI within normal threshold."
        )
    else:
        checks.append({
            "rule": "dti",
            "status": "fail",
            "detail": f"DTI ratio {dti * 100:.1f}% (exceeds {dti_review_max * 100:.0f}%)",
        })
        reasons.append(
            f"Total monthly debt burden (DTI of {dti * 100:.1f}%) exceeds the maximum allowable limit of {dti_review_max * 100:.0f}%."
        )
        suggestions.append(
            f"Based on your profile, the maximum affordable loan is approximately ₹{max_affordable:,.0f}."
        )

    # 4. Final Verdict Determination
    has_fail = any(c["status"] == "fail" for c in checks)
    has_review = any(c["status"] == "review" for c in checks)

    if has_fail:
        status = "NOT_ELIGIBLE"
    elif has_review:
        status = "REVIEW"
    else:
        status = "ELIGIBLE"
        suggestions.append(
            "Congratulations! Your profile meets all standard eligibility criteria for approval."
        )

    return {
        "status": status,
        "missing_fields": [],
        "checks": checks,
        "reasons": reasons,
        "suggestions": suggestions,
        "metrics": {
            "new_emi": round(new_emi),
            "dti": round(dti, 3) if dti is not None else None,
            "max_affordable_loan": round(max_affordable),
        },
    }
