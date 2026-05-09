"""Modèle utilisateur avec gestion des rôles.

Trois rôles métier sont prévus, conformément au brief : administrateur,
agent immobilier et client. Le mot de passe n'est jamais stocké en clair :
on garde uniquement le hash via Werkzeug.
"""

from __future__ import annotations

from enum import Enum

from flask_babel import gettext as _
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .._time import utcnow
from ..extensions import db


class UserRole(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    CLIENT = "client"

    @property
    def label(self) -> str:
        return {
            UserRole.ADMIN: _("Administrateur"),
            UserRole.AGENT: _("Agent immobilier"),
            UserRole.CLIENT: _("Client"),
        }[self]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30))
    role = db.Column(
        db.Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.CLIENT,
        index=True,
    )
    is_active_user = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    agency_id = db.Column(db.Integer, db.ForeignKey("agencies.id"), nullable=True)
    agency = db.relationship("Agency", back_populates="agents")

    properties = db.relationship(
        "Property",
        back_populates="agent",
        foreign_keys="Property.agent_id",
    )
    favorites = db.relationship(
        "Favorite", back_populates="user", cascade="all, delete-orphan"
    )
    visit_requests = db.relationship(
        "VisitRequest",
        back_populates="client",
        foreign_keys="VisitRequest.client_id",
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_agent(self) -> bool:
        return self.role == UserRole.AGENT

    @property
    def is_client(self) -> bool:
        return self.role == UserRole.CLIENT

    def has_role(self, *roles: UserRole) -> bool:
        return self.role in roles

    @property
    def is_active(self) -> bool:
        return self.is_active_user

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role.value}>"
