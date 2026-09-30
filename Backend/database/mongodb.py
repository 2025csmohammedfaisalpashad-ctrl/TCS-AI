import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv(
    "MONGODB_DATABASE",
    "loan_eligibility"
)

if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not configured")

client = MongoClient(MONGODB_URI)

db = client[MONGODB_DATABASE]

applicants_collection = db["applicants"]
chat_history_collection = db["chat_history"]
eligibility_checks_collection = db["eligibility_checks"]


def test_mongodb_connection():
    client.admin.command("ping")
    return True