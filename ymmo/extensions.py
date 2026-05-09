"""Instances des extensions Flask, séparées du factory pour éviter
les imports circulaires entre modèles, services et blueprints.
"""

from flask_babel import Babel
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
babel = Babel()
migrate = Migrate()

# Limiter mémoire suffisant pour un projet pédagogique. En prod on pointe
# vers Redis via storage_uri="redis://...".
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri="memory://",
    headers_enabled=True,
)

login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"
