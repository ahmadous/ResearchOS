"""Point d'entrée WSGI : `flask --app wsgi:app run` ou gunicorn wsgi:app."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
