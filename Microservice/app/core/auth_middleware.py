"""
Firebase Authentication Middleware for FastAPI

Provides dependency injection for verifying Firebase ID tokens.
Use `verify_firebase_token` as a dependency in protected routes.

Auto-creates user documents in Firestore on first login.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from typing import Optional
import logging

from app.db.users_repo import get_user, create_user, update_last_login, update_user

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Verify Firebase ID token and return user_id.
    
    Use as FastAPI dependency:
        current_user_id: str = Depends(verify_firebase_token)
    
    On first login, automatically creates user document in Firestore.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Firebase user UID (user_id)
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or missing
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        token = credentials.credentials
        decoded = auth.verify_id_token(token)
        user_id = decoded["uid"]
        
        # Extract user info from token claims
        email = decoded.get("email")
        name = decoded.get("name")
        photo_url = decoded.get("picture")
        
        # Auto-create user document on first login (sync Auth → Firestore)
        existing_user = get_user(user_id)
        if existing_user is None:
            logger.info(f"[AUTH] First login for user: {user_id}, creating Firestore document")
            create_user(
                user_id=user_id,
                email=email,
                name=name,
                photo_url=photo_url
            )
        else:
            # Update last login timestamp
            update_last_login(user_id)
            updates = {}
            if email and email != existing_user.get("email"):
                updates["email"] = email
            if name and name != existing_user.get("name"):
                updates["name"] = name
            if photo_url and photo_url != existing_user.get("photoURL"):
                updates["photoURL"] = photo_url
            if updates:
                update_user(user_id, updates)
        
        return user_id
        
    except auth.InvalidIdTokenError:
        logger.warning("[AUTH] Invalid ID token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.ExpiredIdTokenError:
        logger.warning("[AUTH] Expired ID token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired, please re-authenticate",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.RevokedIdTokenError:
        logger.warning("[AUTH] Revoked ID token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"[AUTH] Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[str]:
    """
    Optionally verify Firebase ID token. Returns None if not authenticated.
    
    Use for endpoints that work with or without authentication:
        user_id: Optional[str] = Depends(get_optional_user)
    
    Args:
        credentials: Bearer token from Authorization header (optional)
        
    Returns:
        Firebase user UID or None if not authenticated
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        decoded = auth.verify_id_token(token)
        user_id = decoded["uid"]
        
        # Sync user to Firestore if needed
        email = decoded.get("email")
        name = decoded.get("name")
        photo_url = decoded.get("picture")

        existing_user = get_user(user_id)
        if existing_user is None:
            create_user(user_id=user_id, email=email, name=name, photo_url=photo_url)
        else:
            update_last_login(user_id)
            updates = {}
            if email and email != existing_user.get("email"):
                updates["email"] = email
            if name and name != existing_user.get("name"):
                updates["name"] = name
            if photo_url and photo_url != existing_user.get("photoURL"):
                updates["photoURL"] = photo_url
            if updates:
                update_user(user_id, updates)
        
        return user_id
        
    except Exception as e:
        logger.debug(f"[AUTH] Optional auth failed (proceeding unauthenticated): {e}")
        return None
