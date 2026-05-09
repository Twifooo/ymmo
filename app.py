"""Point d'entrée de l'application Ymmo.

Lance le serveur de développement Flask. En production utiliser un WSGI
comme gunicorn ou waitress : `waitress-serve --port=8000 app:app`.
"""

from __future__ import annotations

# On charge .env AVANT d'importer le reste : `config.py` lit les variables
# d'environnement à l'import, donc si on charge dotenv après, c'est trop tard
# et la config par défaut est utilisée même quand .env est présent.
from dotenv import load_dotenv

load_dotenv()

from ymmo import create_app  # noqa: E402

app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
