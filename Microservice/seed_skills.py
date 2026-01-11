from dotenv import load_dotenv
import os
from app.db.skills_repo import save_skill

if __name__ == "__main__":
    load_dotenv()
    # Now GOOGLE_APPLICATION_CREDENTIALS will be loaded from .env if present
    skill_id = save_skill(
        name="Open Word and Type",
        intent_signature="open word and type",
        steps=[
            {"action": "open_app", "app": "Word"},
            {"action": "type_text", "text": "Hello, world!"}
        ]
    )
    print(f"Seeded skill with ID: {skill_id}")
