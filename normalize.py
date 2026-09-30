"""
Input Normalization and Parsing Module for Loan Eligibility API.
Handles human-entered strings, Indian currency notations, age, and employment vintage formats.
"""

import math
import re
from typing import Any


class NormalizationError(ValueError):
    """Exception raised when a field value cannot be normalized or validated."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class NormalizationValidationException(Exception):
    """Raised when one or more applicant fields fail normalization."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__(str(errors))


def _check_number_sanity(val: float | int, field_name: str) -> None:
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            raise NormalizationError(field_name, f"Value for {field_name} must be a finite number")
    if abs(val) > 1e12:
        raise NormalizationError(field_name, f"Value for {field_name} is unrealistically large")


def normalize_money(raw: Any, field_name: str = "amount") -> float | int | None:
    """
    Normalizes numeric and string currency amounts to numeric float/int.
    Supports:
      - 60000, 60000.0, 0
      - "₹60k", "60k", "60 k" -> 60000
      - "5 lakh", "2.5 lakh", "5L", "5 lac", "5 lacs" -> 500000 / 250000
      - "₹5,00,000", "5,00,000" -> 500000
      - "Rs. 15,000", "Rs 15000", "15000 INR" -> 15000
      - "15000/month", "15000 / month", "15000/pm", "15000 pm", "15000/mo" -> 15000
      - "1 crore", "1.5 cr" -> 10000000 / 15000000
    Raises NormalizationError if input is invalid or negative.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        _check_number_sanity(raw, field_name)
        if raw < 0:
            raise NormalizationError(field_name, f"{field_name} cannot be negative")
        return int(raw) if isinstance(raw, int) or (isinstance(raw, float) and raw.is_integer()) else round(raw, 2)

    if not isinstance(raw, str):
        raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")

    text = raw.strip()
    if not text:
        return None

    # Check for negative sign upfront
    if text.startswith("-"):
        raise NormalizationError(field_name, f"{field_name} cannot be negative")

    # Remove per-month notations (e.g., /month, /pm, /mo)
    cleaned = re.sub(r"/(?:month|mo|pm)\b|\b(?:per\s+month|pm)\b", "", text, flags=re.IGNORECASE).strip()

    # Remove currency symbols (INR, Rs., Rs, ₹, $, commas, spaces)
    cleaned = re.sub(r"^(?:₹|\u20b9|Rs\.?|INR|\$)\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s*(?:INR|Rs\.?)\s*$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace(",", "").strip()

    if not cleaned:
        raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")

    # Check for crore / cr pattern
    crore_match = re.match(r"^([\d\.]+)\s*(?:crores?|cr)$", cleaned, re.IGNORECASE)
    if crore_match:
        try:
            val = float(crore_match.group(1)) * 10000000
            _check_number_sanity(val, field_name)
            if val < 0:
                raise NormalizationError(field_name, f"{field_name} cannot be negative")
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")

    # Check for lakh / lac / L pattern
    lakh_match = re.match(r"^([\d\.]+)\s*(?:lakhs?|lac|lacs|l)$", cleaned, re.IGNORECASE)
    if lakh_match:
        try:
            val = float(lakh_match.group(1)) * 100000
            _check_number_sanity(val, field_name)
            if val < 0:
                raise NormalizationError(field_name, f"{field_name} cannot be negative")
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")

    # Check for k / thousand pattern
    k_match = re.match(r"^([\d\.]+)\s*(?:k|thousands?)$", cleaned, re.IGNORECASE)
    if k_match:
        try:
            val = float(k_match.group(1)) * 1000
            _check_number_sanity(val, field_name)
            if val < 0:
                raise NormalizationError(field_name, f"{field_name} cannot be negative")
            return int(val) if val.is_integer() else round(val, 2)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")

    # Standard numeric float / int conversion
    try:
        val = float(cleaned)
        _check_number_sanity(val, field_name)
        if val < 0:
            raise NormalizationError(field_name, f"{field_name} cannot be negative")
        return int(val) if val.is_integer() else round(val, 2)
    except ValueError:
        raise NormalizationError(field_name, f"Could not read '{raw}' as an amount in rupees")


def normalize_age(raw: Any, field_name: str = "age") -> int | None:
    """
    Normalizes age inputs to an integer.
    Supports:
      - 27
      - "27", "27 years", "27 yrs old", "27 yrs", "27 yr", "27 yo", "27 years old"
    Raises NormalizationError if input is invalid or impossible.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        _check_number_sanity(raw, field_name)
        if raw < 0 or raw > 120:
            raise NormalizationError(field_name, f"Age {raw} is invalid. Age must be between 0 and 120")
        return int(raw)

    if not isinstance(raw, str):
        raise NormalizationError(field_name, f"Could not read '{raw}' as an age in years")

    text = raw.strip()
    if not text:
        return None

    if text.startswith("-"):
        raise NormalizationError(field_name, "age cannot be negative")

    match = re.match(r"^(\d+)\s*(?:years?\s*old|yrs?\s*old|years?|yrs?|yr|yo|y/o)?$", text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        if val < 0 or val > 120:
            raise NormalizationError(field_name, f"Age {val} is invalid. Age must be between 0 and 120")
        return val

    raise NormalizationError(field_name, f"Could not read '{raw}' as an age in years")


def normalize_employment(raw: Any, field_name: str = "employment_years") -> float | None:
    """
    Normalizes employment vintage inputs to float years.
    Supports:
      - 3, 1.5
      - "3", "3 years", "3 yrs" -> 3.0
      - "18 months", "18 mos" -> 1.5
      - "1 year 6 months", "1 yr 6 mos" -> 1.5
      - "6 months" -> 0.5
    Raises NormalizationError if input is invalid or negative.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        _check_number_sanity(raw, field_name)
        if raw < 0:
            raise NormalizationError(field_name, f"{field_name} cannot be negative")
        if raw > 80:
            raise NormalizationError(field_name, f"Employment years {raw} is unrealistically high")
        return float(raw)

    if not isinstance(raw, str):
        raise NormalizationError(field_name, f"Could not read '{raw}' as employment vintage in years")

    text = raw.strip()
    if not text:
        return None

    if text.startswith("-"):
        raise NormalizationError(field_name, f"{field_name} cannot be negative")

    # Match compound: "X year(s) Y month(s)" e.g. "1 year 6 months"
    compound_match = re.match(
        r"^([\d\.]+)\s*(?:years?|yrs?|yr)\s*(?:and\s*)?([\d\.]+)\s*(?:months?|mos?|m)$",
        text,
        re.IGNORECASE,
    )
    if compound_match:
        try:
            yrs = float(compound_match.group(1))
            mos = float(compound_match.group(2))
            val = yrs + (mos / 12.0)
            _check_number_sanity(val, field_name)
            return round(val, 2)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as employment vintage in years")

    # Match months only: "18 months", "6 mos"
    months_match = re.match(r"^([\d\.]+)\s*(?:months?|mos?|m)$", text, re.IGNORECASE)
    if months_match:
        try:
            mos = float(months_match.group(1))
            val = mos / 12.0
            _check_number_sanity(val, field_name)
            return round(val, 2)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as employment vintage in years")

    # Match years only: "3 years", "3 yrs", "3"
    years_match = re.match(r"^([\d\.]+)\s*(?:years?|yrs?|yr)?$", text, re.IGNORECASE)
    if years_match:
        try:
            val = float(years_match.group(1))
            _check_number_sanity(val, field_name)
            if val < 0:
                raise NormalizationError(field_name, f"{field_name} cannot be negative")
            if val > 80:
                raise NormalizationError(field_name, f"Employment years {val} is unrealistically high")
            return float(val) if not val.is_integer() else float(int(val))
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as employment vintage in years")

    raise NormalizationError(field_name, f"Could not read '{raw}' as employment vintage in years")


def normalize_credit_score(raw: Any, field_name: str = "credit_score") -> int | None:
    """
    Normalizes credit score inputs to integer.
    Supports:
      - 760, "760"
    Raises NormalizationError if input is not a valid score between 300 and 900.
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        _check_number_sanity(raw, field_name)
        val = int(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            val = int(text)
        except ValueError:
            raise NormalizationError(field_name, f"Could not read '{raw}' as a credit score")
    else:
        raise NormalizationError(field_name, f"Could not read '{raw}' as a credit score")

    if val < 0 or val > 950:
        raise NormalizationError(field_name, f"Credit score {val} is invalid (expected 300-900)")
    return val


def normalize_applicant_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validates and normalizes all fields in an incoming applicant dictionary.
    Returns normalized dictionary with numeric types.
    Collects all errors into a list of {field, message} dicts.
    """
    errors: list[dict[str, str]] = []
    normalized: dict[str, Any] = {}

    # applicant_id (optional string)
    if "applicant_id" in data and data["applicant_id"] is not None:
        normalized["applicant_id"] = str(data["applicant_id"]).strip()

    # age
    if "age" in data and data["age"] is not None:
        try:
            normalized["age"] = normalize_age(data["age"], "age")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["age"] = None

    # monthly_income
    if "monthly_income" in data and data["monthly_income"] is not None:
        try:
            normalized["monthly_income"] = normalize_money(data["monthly_income"], "monthly_income")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["monthly_income"] = None

    # credit_score
    if "credit_score" in data and data["credit_score"] is not None:
        try:
            normalized["credit_score"] = normalize_credit_score(data["credit_score"], "credit_score")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["credit_score"] = None

    # employment_years
    if "employment_years" in data and data["employment_years"] is not None:
        try:
            normalized["employment_years"] = normalize_employment(data["employment_years"], "employment_years")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["employment_years"] = None

    # existing_emi
    if "existing_emi" in data and data["existing_emi"] is not None:
        try:
            normalized["existing_emi"] = normalize_money(data["existing_emi"], "existing_emi")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["existing_emi"] = None

    # loan_amount
    if "loan_amount" in data and data["loan_amount"] is not None:
        try:
            normalized["loan_amount"] = normalize_money(data["loan_amount"], "loan_amount")
        except NormalizationError as e:
            errors.append({"field": e.field, "message": e.message})
    else:
        normalized["loan_amount"] = None

    if errors:
        raise NormalizationValidationException(errors)

    return normalized
