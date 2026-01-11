"""
Skills Repository - Simple SQLite CRUD for learned skills.

No ORM, no complexity. Just sqlite3 + JSON.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional
import os

from app.db.init_db import DB_PATH, init_database


def _get_connection():
    """Get a database connection. Auto-initializes if needed."""
    if not os.path.exists(DB_PATH):
        init_database()
    return sqlite3.connect(DB_PATH)


def save_skill(name: str, intent_signature: str, steps: list[dict]) -> str:
    """
    Save a new skill to the database.
    
    Args:
        name: Human-readable skill name (e.g., "Export PDF")
        intent_signature: Intent pattern for matching (e.g., "export file")
        steps: List of step dictionaries
        
    Returns:
        The generated skill ID
        
    Example steps:
        [
            {"step_index": 1, "action_type": "CLICK", "context": "File menu", "vision_expectation": "UI_STABLE"},
            {"step_index": 2, "action_type": "CLICK", "context": "Export option", "vision_expectation": "SCREEN_CHANGED"}
        ]
    """
    skill_id = str(uuid.uuid4())[:8]  # Short ID for readability
    created_at = datetime.now().isoformat()
    
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO skills (id, name, intent_signature, steps_json, created_at, success_count)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (skill_id, name, intent_signature, json.dumps(steps), created_at))
    
    conn.commit()
    conn.close()
    
    print(f"[SKILLS DB] Saved skill: {name} (id={skill_id})")
    return skill_id


def get_all_skills() -> list[dict]:
    """
    Get all skills from the database.
    
    Returns:
        List of skill dictionaries with parsed steps
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM skills ORDER BY success_count DESC, created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    skills = []
    for row in rows:
        skills.append({
            "id": row["id"],
            "name": row["name"],
            "intent_signature": row["intent_signature"],
            "steps": json.loads(row["steps_json"]),
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            "success_count": row["success_count"]
        })
    
    return skills


def get_skills_by_intent(intent_signature: str) -> list[dict]:
    """
    Find skills matching an intent signature.
    Uses LIKE for fuzzy matching.
    
    Args:
        intent_signature: Intent pattern to search for
        
    Returns:
        List of matching skill dictionaries
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fuzzy match with LIKE
    cursor.execute("""
        SELECT * FROM skills 
        WHERE intent_signature LIKE ? 
        ORDER BY success_count DESC
    """, (f"%{intent_signature}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    skills = []
    for row in rows:
        skills.append({
            "id": row["id"],
            "name": row["name"],
            "intent_signature": row["intent_signature"],
            "steps": json.loads(row["steps_json"]),
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
            "success_count": row["success_count"]
        })
    
    return skills


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """
    Get a single skill by ID.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        Skill dictionary or None if not found
    """
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    return {
        "id": row["id"],
        "name": row["name"],
        "intent_signature": row["intent_signature"],
        "steps": json.loads(row["steps_json"]),
        "created_at": row["created_at"],
        "last_used_at": row["last_used_at"],
        "success_count": row["success_count"]
    }


def increment_skill_usage(skill_id: str) -> bool:
    """
    Increment success count and update last_used_at for a skill.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        True if skill was found and updated, False otherwise
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    cursor.execute("""
        UPDATE skills 
        SET success_count = success_count + 1,
            last_used_at = ?
        WHERE id = ?
    """, (now, skill_id))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if updated:
        print(f"[SKILLS DB] Incremented usage for skill: {skill_id}")
    
    return updated


def delete_skill(skill_id: str) -> bool:
    """
    Delete a skill by ID.
    
    Args:
        skill_id: The skill's unique ID
        
    Returns:
        True if skill was deleted, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    if deleted:
        print(f"[SKILLS DB] Deleted skill: {skill_id}")
    
    return deleted
