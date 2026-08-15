"""
Security Utilities

Handles password hashing (for admin users) and API key hashing (for agents).
Uses bcrypt for passwords (slow, salted, secure) and SHA-256 for API keys
(API keys are already high-entropy, so we need fast comparison).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from app.core.config import get_settings


# --- Password Hashing (bcrypt) ---
# passlib's CryptContext handles salt generation and verification automatically.
# bcrypt is deliberately slow (~100ms) to resist brute-force attacks.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt. Store the result in the database."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    Returns True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# --- API Key Hashing (SHA-256) ---
import hashlib


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    Why SHA-256 and not bcrypt for API keys?
    - API keys are already high-entropy random strings (32+ chars)
    - bcrypt's slowness is unnecessary and would slow down every agent request
    - We need fast comparison since agents send metrics every 60 seconds
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_api_key_prefix(api_key: str) -> str:
    """Extract first 8 characters of API key for display/identification."""
    return api_key[:8]


# --- JWT Token Management ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    The token contains:
    - sub (subject): typically the user's email or ID
    - exp (expiration): when the token becomes invalid
    - Any additional claims passed in `data`
    
    Args:
        data: Dictionary of claims to encode (e.g., {"sub": user_id})
        expires_delta: Custom expiration time. Defaults to settings.
    
    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Returns the payload dict if valid, None if expired or invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
