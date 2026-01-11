"""
Database module - Firebase Firestore implementation.

Exports:
    - init_database: Initialize Firebase connection
    - skills_repo: Skills CRUD operations
    - firebase_client: Firebase client utilities
"""
from .init_db import init_database
from . import skills_repo
from . import firebase_client
