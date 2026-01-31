"""User credential loader for automation (env or JSON)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def load_user_credentials() -> Dict[str, Dict[str, str]]:
    """Load user credentials from env or a JSON file.

    Env format (examples):
      WHATSAPP_EMAIL, WHATSAPP_PASSWORD
      TELEGRAM_EMAIL, TELEGRAM_PASSWORD
      DISCORD_EMAIL, DISCORD_PASSWORD
      SLACK_EMAIL, SLACK_PASSWORD
      EMAIL_ADDRESS, EMAIL_PASSWORD

    JSON format (USER_CREDENTIALS_PATH):
    {
      "email": {"address": "user@domain.com", "password": "..."},
      "whatsapp": {"email": "...", "password": "..."},
      "telegram": {"email": "...", "password": "..."},
      "discord": {"email": "...", "password": "..."},
      "slack": {"email": "...", "password": "..."}
    }
    """

    credentials: Dict[str, Dict[str, str]] = {}

    env_map = {
        "whatsapp": ("WHATSAPP_EMAIL", "WHATSAPP_PASSWORD"),
        "telegram": ("TELEGRAM_EMAIL", "TELEGRAM_PASSWORD"),
        "discord": ("DISCORD_EMAIL", "DISCORD_PASSWORD"),
        "slack": ("SLACK_EMAIL", "SLACK_PASSWORD"),
        "email": ("EMAIL_ADDRESS", "EMAIL_PASSWORD"),
    }

    for platform, (user_key, pass_key) in env_map.items():
        username = os.getenv(user_key, "").strip()
        password = os.getenv(pass_key, "").strip()
        if username and password:
            credentials[platform] = {"email": username, "password": password}

    json_path = os.getenv("USER_CREDENTIALS_PATH", "").strip()
    if json_path:
        try:
            path = Path(json_path).expanduser()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for platform, creds in data.items():
                        if isinstance(creds, dict):
                            email = str(creds.get("email") or creds.get("address") or "").strip()
                            password = str(creds.get("password") or "").strip()
                            if email and password:
                                credentials[str(platform).lower()] = {
                                    "email": email,
                                    "password": password,
                                }
        except Exception:
            pass

    return credentials
