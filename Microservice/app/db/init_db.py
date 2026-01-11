"""
Database initialization for Skills DB.
Creates SQLite database and skills table if they don't exist.

Safe to run multiple times - idempotent.
"""
import sqlite3
import os

# Database file path (same directory as this file)
DB_PATH = os.path.join(os.path.dirname(__file__), "skills.db")


def init_database():
    """
    Initialize the skills database.
    Creates the database file and table if they don't exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            intent_signature TEXT,
            steps_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT,
            success_count INTEGER DEFAULT 0
        )
    """)
    
    # Create index on intent_signature for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_intent_signature 
        ON skills(intent_signature)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"[SKILLS DB] Initialized at {DB_PATH}")


if __name__ == "__main__":
    init_database()
    print("[SKILLS DB] Database ready!")
