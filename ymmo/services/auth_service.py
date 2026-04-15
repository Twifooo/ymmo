"""Service d'authentification et de gestion de comptes."""

from __future__ import annotations

from ..models import User, UserRole
from ..repositories import UserRepository


class AuthError(Exception):
    """Erreur métier d'authentification (à afficher à l'utilisateur)."""


class AuthService:
    @staticmethod
    def register(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str | None = None,
        role: UserRole = UserRole.CLIENT,
        agency_id: int | None = None,
    ) -> User:
        email = email.lower().strip()
        if UserRepository.get_by_email(email):
            raise AuthError("Un compte existe déjà avec cette adresse email.")
        if len(password) < 8:
            raise AuthError("Le mot de passe doit contenir au moins 8 caractères.")

        user = User(
            email=email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone,
            role=role,
            agency_id=agency_id,
        )
        user.set_password(password)
        return UserRepository.add(user)

    @staticmethod
    def authenticate(email: str, password: str) -> User:
        user = UserRepository.get_by_email(email)
        if not user or not user.check_password(password):
            raise AuthError("Email ou mot de passe incorrect.")
        if not user.is_active_user:
            raise AuthError("Ce compte est désactivé.")
        return user
