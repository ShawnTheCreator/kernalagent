"""
Firebase Client Initialization

Initializes Firebase Admin SDK for Firestore access.
Used by skills_repo.py to store/retrieve skills.
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Global Firestore client
_db = None

def get_firestore_client():
    """
    Get or initialize Firestore client.
    
    Uses GOOGLE_APPLICATION_CREDENTIALS env var for service account key.
    Can also use FIREBASE_SERVICE_ACCOUNT_JSON for inline JSON (Render).
    
    Returns:
        Firestore client instance
    """
    global _db
    
    if _db is not None:
        return _db
    
    # Check if Firebase is already initialized
    if len(firebase_admin._apps) > 0:
        _db = firestore.client()
        return _db
    
    # Try to get credentials from environment
    cred = None
    
    # Option 1: Inline JSON from env variable (for Render/cloud deployment)
    firebase_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    if firebase_json:
        try:
            service_account_info = json.loads(firebase_json)
            cred = credentials.Certificate(service_account_info)
            print("[FIREBASE] Initialized from FIREBASE_SERVICE_ACCOUNT_JSON")
        except json.JSONDecodeError as e:
            print(f"[FIREBASE] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")
    
    # Option 2: File path from GOOGLE_APPLICATION_CREDENTIALS
    if cred is None:
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            print(f"[FIREBASE] Initialized from file: {cred_path}")
        elif cred_path:
            print(f"[FIREBASE] Warning: GOOGLE_APPLICATION_CREDENTIALS path not found: {cred_path}")
    
    # Option 3: Look for key file in common locations
    if cred is None:
        common_paths = [
            'firebase-key.json',
            'service-account.json',
            '../firebase-key.json',
            os.path.join(os.path.dirname(__file__), '..', '..', 'firebase-key.json'),
        ]
        for path in common_paths:
            if os.path.exists(path):
                cred = credentials.Certificate(path)
                print(f"[FIREBASE] Initialized from discovered file: {path}")
                break
    
    if cred is None:
        raise RuntimeError(
            "[FIREBASE] No credentials found! Set FIREBASE_SERVICE_ACCOUNT_JSON "
            "or GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )
    
    # Initialize Firebase app
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    print("[FIREBASE] Firestore client initialized successfully")
    
    return _db


def get_skills_collection():
    """
    Get the skills collection reference.
    
    Returns:
        Firestore collection reference for 'skills'
    """
    db = get_firestore_client()
    return db.collection('skills')
