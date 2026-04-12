"""Configuration centralisée de l'application Ymmo.

Suit le pattern de configuration par environnement pour faciliter le
déploiement (dev, test, prod) sans modifier le code applicatif.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


class BaseConfig:
    SECRET_KEY = os.environ.get("YMMO_SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "YMMO_DATABASE_URI",
        f"sqlite:///{INSTANCE_DIR / 'ymmo.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    WTF_CSRF_TIME_LIMIT = 3600

    UPLOAD_FOLDER = BASE_DIR / "ymmo" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    ITEMS_PER_PAGE = 12

    BABEL_DEFAULT_LOCALE = "fr"
    BABEL_SUPPORTED_LOCALES = ("fr", "en")
    BABEL_TRANSLATION_DIRECTORIES = str(BASE_DIR / "ymmo" / "translations")
    LANGUAGE_COOKIE = "ymmo_lang"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "testing"


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    name = name or os.environ.get("YMMO_ENV", "development")
    return CONFIG_MAP.get(name, DevelopmentConfig)
