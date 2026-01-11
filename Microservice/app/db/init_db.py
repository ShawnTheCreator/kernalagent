"""
Database Initialization - Firebase Version

Initializes Firebase connection for Skills storage.
SQLite has been replaced with Firebase Firestore.
"""
from .firebase_client import get_firestore_client


def init_database():
    """
    Initialize Firebase connection.
    
    This is called on app startup to ensure Firebase is ready.
    """
    try:
        db = get_firestore_client()
        print("[SKILLS DB] Firebase Firestore initialized successfully")
        return True
    except Exception as e:
        print(f"[SKILLS DB] Warning: Firebase initialization failed: {e}")
        print("[SKILLS DB] Skills functionality may be limited")
        return False
