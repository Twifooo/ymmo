"""Tests du service d'authentification."""

import pytest

from ymmo.services import AuthError, AuthService


def test_register_creates_user(app):
    with app.app_context():
        user = AuthService.register(
            email="JANE@Example.com",
            password="strongpass1",
            first_name="Jane",
            last_name="Doe",
        )
        assert user.id is not None
        assert user.email == "jane@example.com"
        assert user.role.value == "client"
        assert user.check_password("strongpass1")


def test_register_rejects_short_password(app):
    with app.app_context():
        with pytest.raises(AuthError):
            AuthService.register(
                email="a@b.com",
                password="short",
                first_name="A",
                last_name="B",
            )


def test_register_rejects_duplicate(app):
    with app.app_context():
        AuthService.register(
            email="dup@b.com",
            password="strongpass1",
            first_name="A",
            last_name="B",
        )
        with pytest.raises(AuthError):
            AuthService.register(
                email="dup@b.com",
                password="strongpass1",
                first_name="A",
                last_name="B",
            )


def test_authenticate_ok(app):
    with app.app_context():
        AuthService.register(
            email="ok@b.com",
            password="strongpass1",
            first_name="A",
            last_name="B",
        )
        user = AuthService.authenticate("ok@b.com", "strongpass1")
        assert user.email == "ok@b.com"


def test_authenticate_wrong_password(app):
    with app.app_context():
        AuthService.register(
            email="wp@b.com",
            password="strongpass1",
            first_name="A",
            last_name="B",
        )
        with pytest.raises(AuthError):
            AuthService.authenticate("wp@b.com", "bad")
