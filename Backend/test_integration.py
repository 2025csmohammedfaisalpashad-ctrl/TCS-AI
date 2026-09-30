from services.grok_service import extract_applicant_information
from services.applicant_service import save_applicant


message = """
I am 27 years old.
I earn 60000 rupees per month.
My credit score is 760.
I have been working for 3 years.
I want a loan of 10 lakh rupees.
My existing EMI is 5000 rupees.
"""


print("User message:")
print(message)

print("\nCalling local LLM...")

applicant_data = extract_applicant_information(message)

print("\nExtracted applicant information:")
print(applicant_data)

print("\nSaving applicant to MongoDB...")

applicant_id = save_applicant(applicant_data)

print("\nApplicant saved successfully!")
print("MongoDB ID:", applicant_id)