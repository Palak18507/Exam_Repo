"""
FastAPI dependencies for route protection.

Usage in endpoints:
    @app.get("/api/papers")
    def get_papers(user=Depends(require_student)):
        ...  # only authenticated students/librarians/admins can access

    @app.post("/api/upload")
    def upload(user=Depends(require_librarian)):
        ...  # only librarians and admins can access
"""

from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.utils import decode_token

security = HTTPBearer(auto_error=False)

# Role hierarchy: admin > librarian > student
ROLE_LEVEL = {"admin": 3, "librarian": 2, "student": 1}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and verify the current user from JWT token.
    Returns the token payload dict: {sub, email, role, exp}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
        )

    # Update last_active timestamp (fire-and-forget, don't block the request)
    try:
        from db.database import get_session
        from auth.models import User
        session = get_session()
        session.query(User).filter_by(id=payload["sub"]).update({"last_active": datetime.utcnow()})
        session.commit()
        session.close()
    except Exception:
        pass  # Don't fail the request if tracking fails

    return payload


def require_role(min_role: str):
    """Create a dependency that requires a minimum role level."""
    min_level = ROLE_LEVEL.get(min_role, 0)

    def checker(user=Depends(get_current_user)):
        user_level = ROLE_LEVEL.get(user.get("role"), 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires {min_role} role or higher.",
            )
        return user

    return checker


# Pre-built dependencies for common use
require_student = require_role("student")      # student, librarian, admin
require_librarian = require_role("librarian")  # librarian, admin only
require_admin = require_role("admin")          # admin only
