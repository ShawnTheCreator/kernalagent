"""
Database module - Firebase Firestore + Local SQLite implementation.

Exports:
    - init_database: Initialize Firebase connection
    - skills_repo: Skills CRUD operations (global + user-scoped)
    - users_repo: User profile CRUD operations
    - settings_repo: User settings CRUD operations
    - sessions_repo: Agent sessions CRUD operations
    - memory_repo: Long-term memory CRUD operations
    - firebase_client: Firebase client utilities
    - local_episodic_memory: Local SQLite for AI conversations
    - memory_bridge: Bridge between Firebase and local storage
"""
from .init_db import init_database
from . import skills_repo
from . import users_repo
from . import settings_repo
from . import sessions_repo
from . import memory_repo
from . import firebase_client
from . import local_episodic_memory
from . import memory_bridge

