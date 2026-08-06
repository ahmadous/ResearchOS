# ResearchOS

Un « système d'exploitation » pour la recherche scientifique, basé sur des agents IA collaboratifs et un routeur multi-modèles intelligent.

## Stack

- **Backend** : Python 3.12, Flask, SQLAlchemy, JWT, Flask-SocketIO, Celery + Redis, PostgreSQL, Swagger/OpenAPI
- **Frontend** : React 19, Vite, Material UI, React Router, React Query, Axios, Framer Motion, Recharts, Monaco Editor
- **IA** : couche multi-fournisseurs (OpenAI, Anthropic, Gemini, Ollama, OpenRouter, HuggingFace, DeepSeek, Qwen, Llama, Mistral, Grok) avec routeur intelligent (coût / vitesse / qualité / confidentialité / contexte).

## Architecture (Clean Architecture)

```
backend/app/
  api/           # Blueprints Flask (couche transport HTTP/WS)
  services/      # Use-cases (logique applicative)
  repositories/  # Accès données (Repository Pattern)
  models/        # Entités SQLAlchemy
  ai/            # Providers (Strategy) + Factory + Registry + Router
  agents/        # Agents spécialisés (Research, PDF, Citation, ...)
  rag/           # Chunking, embeddings, vector store, hybrid search
  tools/         # Outils appelables par les agents
  tasks/         # Tâches Celery
  auth/          # JWT, décorateurs, sécurité
  websocket/     # Handlers Socket.IO
  config.py      # Configuration par environnement
  extensions.py  # Instances d'extensions (db, jwt, socketio, ...)
```

## Roadmap d'implémentation

- [x] **Phase 1** — Fondation : couche IA (providers + registry + factory + router)
- [x] **Phase 2** — App factory, config, DB, auth JWT, LLM Manager + Chat (REST + Swagger)
- [x] **Phase 3** — 14 agents spécialisés + orchestrateur (run / pipeline / auto)
- [x] **Phase 4** — RAG complet (chunking, embeddings, recherche hybride BM25+dense, citations)
- [x] **Phase 5** — Recherche scientifique (arXiv, OpenAlex, Semantic Scholar, CrossRef, HAL) + import RAG
- [ ] Phase 6 — WebSocket temps réel + Celery
- [ ] Phase 7 — Frontend React (Dashboard, Workspace, LLM Manager, Workflow Builder)

## Démarrage (dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app app:create_app run --debug
```
