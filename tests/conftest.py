"""Fixtures pytest partagées."""

from __future__ import annotations

import pytest

from config import TestingConfig
from ymmo import create_app
from ymmo.extensions import db


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
