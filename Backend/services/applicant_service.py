from datetime import datetime, timezone

from database.mongodb import applicants_collection


def save_applicant(applicant_data):
    document = {
        **applicant_data,
        "created_at": datetime.now(timezone.utc)
    }

    result = applicants_collection.insert_one(document)

    return str(result.inserted_id)