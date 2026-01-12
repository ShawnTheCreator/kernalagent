from datetime import datetime
from .firebase_client import get_db

def save_activity_event(session_id: str, event_data: dict):
    db = get_db()
    event_data['timestamp'] = datetime.utcnow()
    db.collection('agent_sessions').document(session_id).collection('events').add(event_data)
