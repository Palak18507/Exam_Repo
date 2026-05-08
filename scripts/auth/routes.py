"""
Auth API routes: signup, login, me.

POST /api/auth/signup  — register with @igdtuw.ac.in email
POST /api/auth/login   — login, get JWT token
GET  /api/auth/me      — get current user info (requires token)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_session
from auth.models import User
from auth.utils import hash_password, verify_password, create_token, is_valid_email, create_reset_token, decode_reset_token
from auth.middleware import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request/Response schemas ──

class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "student"  # default role for new signups


class LoginRequest(BaseModel):
    email: str
    password: str


# ── POST /api/auth/signup ──

@router.post("/signup")
def signup(req: SignupRequest):
    """Register a new user. Email must be @igdtuw.ac.in."""
    email = req.email.strip().lower()

    # Validate email domain
    if not is_valid_email(email):
        raise HTTPException(
            status_code=400,
            detail="Only @igdtuw.ac.in email addresses are allowed."
        )

    # Only allow student signup via API. Librarian/admin accounts are created manually.
    if req.role not in ("student",):
        raise HTTPException(
            status_code=400,
            detail="Only student accounts can be created via signup. Contact admin for librarian access."
        )

    session = get_session()
    try:
        # Check if email already exists
        existing = session.query(User).filter_by(email=email).first()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")

        # Create user
        user = User(
            email=email,
            password_hash=hash_password(req.password),
            role="student",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # Return token immediately (auto-login after signup)
        token = create_token(user.id, user.email, user.role)

        return {
            "message": "Account created successfully.",
            "token": token,
            "user": {"id": user.id, "email": user.email, "role": user.role},
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")
    finally:
        session.close()


# ── POST /api/auth/login ──

@router.post("/login")
def login(req: LoginRequest):
    """Login with email and password. Returns JWT token."""
    email = req.email.strip().lower()

    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()

        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password."
            )

        token = create_token(user.id, user.email, user.role)

        return {
            "token": token,
            "user": {"id": user.id, "email": user.email, "role": user.role},
        }
    finally:
        session.close()


# ── GET /api/auth/me ──

@router.get("/me")
def get_me(user=Depends(get_current_user)):
    """Get the current logged-in user's info from their JWT token."""
    return {
        "id": user["sub"],
        "email": user["email"],
        "role": user["role"],
    }


# ── POST /api/auth/forgot-password ──

class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """Request a password reset. Returns a reset token (in production, this would be emailed)."""
    email = req.email.strip().lower()

    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            # Don't reveal whether email exists
            return {"message": "If this email is registered, a reset link has been generated."}

        reset_token = create_reset_token(email)

        return {
            "message": "If this email is registered, a reset link has been generated.",
            "reset_token": reset_token,  # In production: send via email, don't return here
        }
    finally:
        session.close()


# ── POST /api/auth/reset-password ──

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    """Reset password using a valid reset token."""
    email = decode_reset_token(req.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link. Please request a new one.")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    session = get_session()
    try:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")

        user.password_hash = hash_password(req.new_password)
        session.commit()

        return {"message": "Password reset successfully. You can now log in with your new password."}
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to reset password.")
    finally:
        session.close()
