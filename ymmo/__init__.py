"""Application factory Ymmo.

Le pattern factory permet de créer plusieurs instances de l'application
(développement, tests) avec des configurations différentes sans état
global. Toutes les extensions sont initialisées ici, puis les blueprints
sont enregistrés.

L'instance ``AnalyticsService`` est attachée à ``app.extensions`` plutôt
que créée au niveau module dans chaque blueprint : un singleton partagé
entre threads ne pose plus de soucis de concurrence et reste réutilisable
par tous les blueprints via ``current_app.extensions["analytics"]``.
"""

from __future__ import annotations

import logging
import time
import uuid

from flask import Flask, g, render_template, request

from config import BaseConfig, get_config

from .extensions import babel, csrf, db, limiter, login_manager, migrate

# Métadonnées d'app exposées dans le health check (et l'export CSV).
APP_VERSION = "1.0.0"
APP_STARTED_AT = time.time()


def _select_locale():
    cookie_name = "ymmo_lang"
    supported = ("fr", "en")
    lang = request.cookies.get(cookie_name)
    if lang in supported:
        return lang
    return request.accept_languages.best_match(supported) or "fr"


def _setup_logging(app: Flask) -> None:
    """Logger structuré : un format unique pour app + Werkzeug, niveau INFO en dev."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(logging.INFO if not app.debug else logging.DEBUG)


def _install_request_logging(app: Flask) -> None:
    """Middleware : trace chaque requête avec un request-id et son temps."""
    @app.before_request
    def _trace_start() -> None:
        g.request_id = uuid.uuid4().hex[:8]
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _trace_end(response):
        duration_ms = (time.perf_counter() - g.get("request_started_at", time.perf_counter())) * 1000
        app.logger.info(
            "req=%s %s %s -> %s in %.1fms",
            g.get("request_id", "-"),
            request.method,
            request.path,
            response.status_code,
            duration_ms,
        )
        return response


def create_app(config_class: type[BaseConfig] | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_class or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)
    if not app.config.get("TESTING"):
        # Le rate-limiter parasite les tests (faux 429). On le coupe en testing.
        limiter.init_app(app)

    _setup_logging(app)
    _install_request_logging(app)

    # Service analytics partagé : un seul predictor entraîné par instance d'app,
    # évite la duplication mémoire et les ré-entraînements inutiles.
    from .services import AnalyticsService

    app.extensions["analytics"] = AnalyticsService()

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    from .blueprints.admin import admin_bp
    from .blueprints.agent import agent_bp
    from .blueprints.api import api_bp
    from .blueprints.auth import auth_bp
    from .blueprints.client import client_bp
    from .blueprints.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(client_bp, url_prefix="/espace-client")
    app.register_blueprint(agent_bp, url_prefix="/espace-agent")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def too_many(_error):
        # Limiter renvoie 429 ; on a un template dédié pour rester cohérent.
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    @app.context_processor
    def inject_globals():
        from flask_babel import get_locale
        from flask_login import current_user

        unread_alerts = 0
        if current_user.is_authenticated and current_user.is_client:
            try:
                from .services import SavedSearchService

                unread_alerts = SavedSearchService.count_new_matches(current_user)
            except Exception:  # noqa: BLE001 — on ne casse JAMAIS le rendu
                unread_alerts = 0

        return {
            "app_name": "Ymmo",
            "app_version": APP_VERSION,
            "current_locale": str(get_locale() or "fr"),
            "unread_alerts": unread_alerts,
        }

    with app.app_context():
        db.create_all()

    return app
