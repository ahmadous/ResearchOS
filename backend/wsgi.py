"""Point d'entrée WSGI/ASGI.

On lance via SocketIO (et non app.run) pour activer le WebSocket. En prod :
    gunicorn -k eventlet -w 1 wsgi:app     (ou uvicorn/gevent selon le déploiement)
"""
from app import create_app
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True,
                 allow_unsafe_werkzeug=True)
