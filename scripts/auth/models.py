"""
User model for authentication.

Roles:
  - admin: full access to everything (student + librarian + user management)
  - librarian: can upload/delete papers + all student access
  - student: can search, view, download papers
"""

import uuid
from sqlalchemy import Column, String, DateTime, func
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="student")  # admin, librarian, student
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
