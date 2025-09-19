# firebase_client.py
import firebase_admin
from firebase_admin import credentials, firestore
import os, datetime

# Path to your Firebase service account JSON
FIREBASE_KEY_PATH = os.path.join(
    os.path.dirname(__file__),
    "voicebridge-88122-firebase-adminsdk-fbsvc-39e758707c.json"
)

# Initialize Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION = "misinfo_analysis"


def save_analysis(result: dict):
    """
    Save analysis results to Firebase Firestore.
    Stores both raw AI output and user-friendly fields.
    """
    try:
        record = {
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "summary": result.get("summary"),
            "when": result.get("when"),
            "where": result.get("where"),
            "why": result.get("why"),
            "how": result.get("how"),
            "real_platform_id": result.get("real_platform_id"),
            "sources": result.get("sources", []),
            "guidelines": result.get("guidelines", []),

            # Extra human-friendly fields
            "status_text": result.get("status_text"),
            "brief_summary": result.get("brief_summary"),
            "education": result.get("education", []),
            "factcheck_links": result.get("factcheck_links", []),

            # Metadata
            "created_at": datetime.datetime.utcnow()
        }

        db.collection(COLLECTION).add(record)
        print("✅ Saved analysis to Firebase:", record["status_text"])

    except Exception as e:
        print("❌ Error saving to Firebase:", str(e))


def get_all_analyses(limit: int = 50):
    """
    Fetch latest analyses from Firestore (newest first).
    """
    try:
        docs = (
            db.collection(COLLECTION)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print("❌ Error fetching from Firebase:", str(e))
        return []
