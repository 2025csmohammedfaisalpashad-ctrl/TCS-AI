# ==========================================
# LOAN ELIGIBILITY RULE ENGINE
# ==========================================


# ==========================================
# 1. CALCULATE DTI
# ==========================================

def calculate_dti(monthly_income, existing_emi):
    """
    Calculate Debt-to-Income Ratio (DTI).

    Formula:
    DTI = (Existing Monthly EMI / Monthly Income) * 100
    """

    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than zero.")

    dti = (existing_emi / monthly_income) * 100

    return round(dti, 2)


# ==========================================
# 2. CHECK LOAN ELIGIBILITY
# ==========================================

def check_eligibility(applicant):

    # Store individual rule results
    rules = {}

    # Store reasons for failed rules
    failed_reasons = []


    # ======================================
    # RULE 1: AGE
    # Requirement: 21 to 60 years
    # ======================================

    age = applicant["age"]

    if 21 <= age <= 60:

        rules["age"] = True

    else:

        rules["age"] = False

        failed_reasons.append(
            "Age must be between 21 and 60 years."
        )


    # ======================================
    # RULE 2: MONTHLY INCOME
    # Requirement: Minimum ₹30,000
    # ======================================

    monthly_income = applicant["monthly_income"]

    if monthly_income >= 30000:

        rules["income"] = True

    else:

        rules["income"] = False

        failed_reasons.append(
            "Monthly income must be at least ₹30,000."
        )


    # ======================================
    # RULE 3: CREDIT SCORE
    # Requirement: Minimum 700
    # ======================================

    credit_score = applicant["credit_score"]

    if credit_score >= 700:

        rules["credit_score"] = True

    else:

        rules["credit_score"] = False

        failed_reasons.append(
            "Credit score must be at least 700."
        )


    # ======================================
    # RULE 4: EMPLOYMENT
    # Requirement: Minimum 1 year
    # ======================================

    employment_years = applicant["employment_years"]

    if employment_years >= 1:

        rules["employment"] = True

    else:

        rules["employment"] = False

        failed_reasons.append(
            "Employment duration must be at least 1 year."
        )


    # ======================================
    # RULE 5: DTI
    # Requirement: Maximum 40%
    # ======================================

    existing_emi = applicant["existing_emi"]

    dti = calculate_dti(
        monthly_income,
        existing_emi
    )

    if dti <= 40:

        rules["dti"] = True

    else:

        rules["dti"] = False

        failed_reasons.append(
            "Debt-to-Income ratio must not exceed 40%."
        )


    # ======================================
    # RULE 6: LOAN AMOUNT
    # Requirement:
    # Minimum ₹1,00,000
    # Maximum ₹20,00,000
    # ======================================

    loan_amount = applicant["loan_amount"]

    if 100000 <= loan_amount <= 2000000:

        rules["loan_amount"] = True

    else:

        rules["loan_amount"] = False

        failed_reasons.append(
            "Loan amount must be between ₹1 lakh and ₹20 lakh."
        )


    # ======================================
    # OVERALL ELIGIBILITY
    # ======================================

    eligible = all(rules.values())


    # ======================================
    # FINAL RESULT
    # ======================================

    return {

        "eligible": eligible,

        "dti": dti,

        "rules": rules,

        "failed_reasons": failed_reasons
    }


# ==========================================
# TESTING
# ==========================================

if __name__ == "__main__":

    # --------------------------------------
    # TEST APPLICANT
    # --------------------------------------

    applicant = {

        "age": 27,

        "monthly_income": 60000,

        "credit_score": 760,

        "employment_years": 3,

        "existing_emi": 15000,

        "loan_amount": 1000000
    }


    # --------------------------------------
    # RUN RULE ENGINE
    # --------------------------------------

    result = check_eligibility(applicant)


    # --------------------------------------
    # DISPLAY RESULT
    # --------------------------------------

    print("\n======================================")
    print("       LOAN ELIGIBILITY RESULT")
    print("======================================")

    print(
        "Overall Eligibility:",
        "ELIGIBLE" if result["eligible"] else "NOT ELIGIBLE"
    )

    print("DTI:", str(result["dti"]) + "%")


    print("\nRule-wise Results:")

    for rule, status in result["rules"].items():

        if status:

            print(f"  ✓ {rule}: PASS")

        else:

            print(f"  ✗ {rule}: FAIL")


    print("\nFailed Reasons:")

    if result["failed_reasons"]:

        for reason in result["failed_reasons"]:

            print(f"  - {reason}")

    else:

        print("  None")


    print("======================================")