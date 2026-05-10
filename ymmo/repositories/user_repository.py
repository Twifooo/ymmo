"""Repository utilisateurs."""

from __future__ import annotations

from sqlalchemy import or_, select

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
    def search(query: str | None = None, role: UserRole | None = None,
               page: int = 1, per_page: int = 20) -> tuple[list[User], int]:
        """Recherche/filtrage paginée pour la console admin."""
        stmt = select(User)
        count_stmt = select(db.func.count(User.id))
        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)
        if query:
            q = f"%{query.lower().strip()}%"
            cond = or_(
                db.func.lower(User.email).like(q),
                db.func.lower(User.first_name).like(q),
                db.func.lower(User.last_name).like(q),
            )
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)
        total = db.session.execute(count_stmt).scalar_one()
        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
        return list(db.session.scalars(stmt)), int(total)

    @staticmethod
    def add(user: User) -> User:
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def save() -> None:
        db.session.commit()
