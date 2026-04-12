"""Décorateurs de contrôle d'accès basés sur les rôles."""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort
from flask_login import current_user

from .models import UserRole


def role_required(*roles: UserRole) -> Callable:
    """N'autorise l'accès qu'aux utilisateurs disposant d'un des rôles."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_role(*roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
