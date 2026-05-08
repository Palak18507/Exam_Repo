"""
Auth utilities:
  - Password hashing (bcrypt)
  - JWT token creation and verification
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import bcrypt
from jose import jwt, JWTError

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PROJECT_ROOT
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-to-a-random-secret-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

ALLOWED_EMAIL_DOMAIN = "igdtuw.ac.in"


# ── Password ──

def hash_password(plain: str) -> str:
    """Hash a plain text password with bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ──

def create_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token containing user id, email, and role."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Returns the payload or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# ── Validation ──

def is_valid_email(email: str) -> bool:
    """Check if email belongs to the allowed university domain."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[1].lower()
    return domain == ALLOWED_EMAIL_DOMAIN


def create_reset_token(email: str) -> str:
    """Create a short-lived token for password reset (15 min)."""
    payload = {
        "email": email,
        "purpose": "reset",
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_reset_token(token: str) -> str:
    """Decode a reset token. Returns email or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != "reset":
            return None
        return payload.get("email")
    except JWTError:
        return None
