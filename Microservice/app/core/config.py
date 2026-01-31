"""
Configuration settings for Kernal Agent AI Brain.
Loads environment variables and initializes the Gemini client.
"""
import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env files (Microservice first, then repo root)
env_paths = [
    Path(__file__).parent.parent.parent / '.env',
    Path(__file__).parent.parent.parent.parent / '.env',  # Parent of Microservice
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=False)

class Settings:
    """Application settings loaded from environment."""
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    
    # Gemini 2.0 Models (latest)
    MODEL_THINKING: str = "gemini-2.0-flash-thinking-exp-01-21"  # Complex reasoning
    MODEL_FLASH: str = "gemini-2.0-flash-exp"                    # Fast standard tasks
    MODEL_LEGACY: str = "gemini-1.5-flash-002"                   # Fallback
    MODEL_ID: str = MODEL_FLASH  # Default model (backward compatibility)
    
    # Feature flags
    ENABLE_STRUCTURED_OUTPUT: bool = True   # Use native JSON mode
    ENABLE_THINKING_MODE: bool = True       # Use thinking model for complex tasks
    ENABLE_VISION: bool = True              # Re-enable vision with Gemini 2.0
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    def __init__(self):
        if not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in .env file")

# Global settings instance
settings = Settings()

# Initialize Gemini client (singleton)
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Export MODEL_ID for convenience
MODEL_ID = settings.MODEL_ID
