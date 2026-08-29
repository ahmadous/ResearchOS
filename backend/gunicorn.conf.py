"""Configuration gunicorn (serveur WSGI de production).

Choix : 1 SEUL worker + plusieurs threads (gthread). Raison : SocketIO et les
tâches de fond (InlineRunner via start_background_task) vivent en mémoire du
processus. Avec un seul worker, tout reste cohérent SANS Redis. Pour scaler à
plusieurs workers/instances, il faudra brancher un message_queue Redis sur
SocketIO + Celery (voir DEPLOY.md « scalabilité »).
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"   # Render fournit $PORT
worker_class = "gthread"
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "300"))   # tâches LLM/RAG longues
graceful_timeout = 30
keepalive = 5
accesslog = "-"      # stdout (visible dans les logs Render)
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
