from services.grok_service import extract_applicant_information


message = """
I am 27 years old.
I earn 60000 rupees per month.
My credit score is 760.
I have been working for 3 years.
I want a loan of 10 lakh rupees.
My existing EMI is 5000 rupees.
"""


result = extract_applicant_information(message)

print(result)