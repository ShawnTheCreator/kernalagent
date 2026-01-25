from datetime import datetime
from .firebase_client import get_firestore_client

def save_activity_event(session_id: str, event_data: dict):
    db = get_firestore_client()
    event_data['timestamp'] = datetime.utcnow()
    db.collection('agent_sessions').document(session_id).collection('events').add(event_data)

