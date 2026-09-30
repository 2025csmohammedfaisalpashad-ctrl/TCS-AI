import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama3.2:3b"
)

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434/v1"
)

client = OpenAI(
    api_key="ollama",
    base_url=OLLAMA_BASE_URL
)


def extract_applicant_information(message: str):

    system_prompt = """
You are an information extraction assistant for a
banking loan eligibility chatbot.

Your job is ONLY to extract applicant information
from the user's natural-language message.

Return ONLY valid JSON.

Use exactly these fields:

{
    "age": null,
    "monthly_income": null,
    "credit_score": null,
    "employment_years": null,
    "loan_amount": null,
    "existing_emi": null
}

Rules:

1. Extract only information explicitly provided.
2. If information is missing, use null.
3. Convert amounts such as "10 lakh" into numbers.
4. Convert "60k" into 60000.
5. Do not determine loan eligibility.
6. Do not approve or reject the applicant.
7. Do not invent information.
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": message
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    return json.loads(content)