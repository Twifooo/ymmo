"""Application factory Ymmo.

Le pattern factory permet de créer plusieurs instances de l'application
(développement, tests) avec des configurations différentes sans état
global. Toutes les extensions sont initialisées ici, puis les blueprints
sont enregistrés.
"""

from __future__ import annotations

from flask import Flask, render_template

from config import BaseConfig, get_config

from .extensions import babel, csrf, db, login_manager


def _select_locale():
    from flask import request

    cookie_name = "ymmo_lang"
    supported = ("fr", "en")
    lang = request.cookies.get(cookie_name)
    if lang in supported:
        return lang
    return request.accept_languages.best_match(supported) or "fr"


def create_app(config_class: type[BaseConfig] | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_class or get_config())

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)

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

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    @app.context_processor
    def inject_globals():
        from flask_babel import get_locale

        return {
            "app_name": "Ymmo",
            "current_locale": str(get_locale() or "fr"),
        }

    with app.app_context():
        db.create_all()

    return app
