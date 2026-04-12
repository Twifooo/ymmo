"""Point d'entrée de l'application Ymmo.

Lance le serveur de développement Flask. En production utiliser un WSGI
comme gunicorn ou waitress : `waitress-serve --port=8000 app:app`.
"""

from ymmo import create_app

app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
