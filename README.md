# ResearchOS

Un « système d'exploitation » pour la recherche scientifique, basé sur des agents IA collaboratifs et un routeur multi-modèles intelligent.

## Stack

- **Backend** : Python 3.12, Flask, SQLAlchemy, JWT, Flask-SocketIO, Celery + Redis, PostgreSQL, Swagger/OpenAPI
- **Frontend** : React 19, Vite, Material UI, React Router, React Query, Axios, Framer Motion, Recharts, Monaco Editor
- **IA** : couche multi-fournisseurs (OpenAI, Anthropic, Gemini, Ollama, Groq, OpenRouter, HuggingFace, DeepSeek, Qwen, Llama, Mistral, Grok) avec routeur intelligent (coût / vitesse / qualité / confidentialité / contexte).

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
- [x] **Phase 6** — WebSocket temps réel (SocketIO) + tâches asynchrones (runner local, Celery optionnel)
- [x] **Bonus** — Workflow Builder (drag & drop d'agents, exécution DAG + progression temps réel par nœud)
- [x] **Bonus** — Knowledge Graph interactif (extraction entités/relations, viz force-directed)
- [x] **Bonus** — Évaluation auto des réponses (fact-check, score de confiance, corrections)
- [x] **Bonus** — Memory Engine (mémoire persistante scopée, rappel sémantique, injection auto dans le chat)
- [x] **Bonus** — Revue de littérature (recherche réelle EN PARALLÈLE -> tableau comparatif interactif -> BibTeX/PDF ; synthèse IA optionnelle)
- [x] **Bonus** — Import de fichiers (PDF, Word, Excel, Markdown -> RAG ; images/vidéos en pièces jointes)
- [x] **Bonus** — Conversations de chat persistantes (sauvegarde et relecture entre sessions)
- [x] **Bonus** — Agents outillés (research->recherche web réelle, pdf->RAG, graph->Knowledge Graph) : collaboration réelle
- [x] **Bonus** — Gestion des workflows (exécuter / pause / reprendre / arrêter, reprise reprenable, historique des runs)
- [x] **Bonus** — Mail : boîte IMAP (lecture seule) + tri IA (important / à répondre / catégorie / résumé)
- [x] **Phase 7** — Frontend React (Vite + MUI) : Login, Dashboard, LLM Manager, Chat, Agents, Documents (RAG), Recherche sci., temps réel

## Démarrage (dev)

**Tout en une commande** (Ollama + backend + frontend, Ctrl-C pour arrêter) :
```bash
./start.sh
```

Ou séparément :

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python wsgi.py            # http://localhost:5000  (Swagger : /docs)
```

**Frontend**
```bash
cd frontend
npm install
npm run dev              # http://localhost:5173  (proxy /api -> :5000)
```
