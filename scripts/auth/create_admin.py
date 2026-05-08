"""
Create an admin user account.

Usage:
    python -m auth.create_admin admin@igdtuw.ac.in mypassword
    python -m auth.create_admin admin@igdtuw.ac.in mypassword --role librarian
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_session, init_db
from auth.models import User
from auth.utils import hash_password


def create_user(email, password, role="admin"):
    init_db()
    session = get_session()
    try:
        existing = session.query(User).filter_by(email=email.lower()).first()
        if existing:
            print(f"User {email} already exists (role: {existing.role}). Updating password and role...")
            existing.password_hash = hash_password(password)
            existing.role = role
            session.commit()
            print(f"Updated: {email} -> role={role}")
        else:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                role=role,
            )
            session.add(user)
            session.commit()
            print(f"Created: {email} (role={role})")
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a user account")
    parser.add_argument("email", help="Email address")
    parser.add_argument("password", help="Password")
    parser.add_argument("--role", default="admin", choices=["admin", "librarian", "student"])
    args = parser.parse_args()
    create_user(args.email, args.password, args.role)
