"""Repository utilisateurs."""

from __future__ import annotations

from sqlalchemy import select

from ..extensions import db
from ..models import User, UserRole


class UserRepository:
    @staticmethod
    def get(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower().strip())
        return db.session.scalar(stmt)

    @staticmethod
    def list_by_role(role: UserRole) -> list[User]:
        stmt = select(User).where(User.role == role).order_by(User.last_name)
        return list(db.session.scalars(stmt))

    @staticmethod
    def list_all() -> list[User]:
        return list(db.session.scalars(select(User).order_by(User.created_at.desc())))

    @staticmethod
    def add(user: User) -> User:
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def save() -> None:
        db.session.commit()
