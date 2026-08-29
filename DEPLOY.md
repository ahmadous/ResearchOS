# Déploiement — Vercel (frontend) + Render (backend) + Supabase (Postgres)

Montage gratuit et fonctionnel. Ordre : **Supabase → Render → Vercel** (puis on
reboucle le CORS). Compter ~30 min.

> ⚠️ Le plan gratuit Render met le backend en veille après ~15 min d'inactivité :
> la 1ʳᵉ requête ensuite prend ~30–60 s (réveil), puis c'est rapide.

---

## 1. Base de données — Supabase

1. Crée un projet sur [supabase.com](https://supabase.com) (note le mot de passe DB).
2. **Project Settings → Database → Connection string → « Connection pooling »**
   (mode *Session*). Copie l'URI ; elle ressemble à :
   ```
   postgresql://postgres.xxxx:MOTDEPASSE@aws-0-....pooler.supabase.com:5432/postgres
   ```
3. Remplace `postgresql://` par **`postgresql+psycopg2://`**. Garde cette valeur
   pour `DATABASE_URL` (étape suivante).

> On utilise le *pooler* (et non la connexion directe) car Render se connecte en
> IPv4. Les tables sont créées automatiquement au premier démarrage du backend.

---

## 2. Backend — Render

1. Sur [render.com](https://render.com) → **New → Blueprint** → connecte le dépôt
   GitHub `ahmadous/ResearchOS`. Render détecte [`render.yaml`](render.yaml).
2. Renseigne les variables `sync:false` (dans le dashboard) :
   | Variable | Valeur |
   |---|---|
   | `DATABASE_URL` | l'URI Supabase de l'étape 1 |
   | `CREDENTIAL_KEY` | une clé Fernet (voir ci-dessous) |
   | `CORS_ORIGINS` | *(laisser vide pour l'instant, on la remplira à l'étape 3)* |
   - Génère la clé Fernet :
     ```bash
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     ```
   - `SECRET_KEY` et `JWT_SECRET_KEY` sont générés automatiquement par Render.
3. **Deploy**. Une fois en ligne, note l'URL du service, ex :
   `https://researchos-api.onrender.com`
4. Vérifie : ouvre `https://researchos-api.onrender.com/health` → `{"status":"ok"}`.

---

## 3. Frontend — Vercel

1. Sur [vercel.com](https://vercel.com) → **Add New → Project** → importe le dépôt.
2. **Root Directory** : `frontend`. Vercel détecte Vite ([`vercel.json`](frontend/vercel.json)).
3. **Environment Variables** → ajoute :
   | Variable | Valeur |
   |---|---|
   | `VITE_API_URL` | l'URL Render, ex `https://researchos-api.onrender.com` *(sans `/` final)* |
4. **Deploy**. Note l'URL Vercel, ex : `https://researchos.vercel.app`.

---

## 4. Reboucler le CORS

1. Retourne sur **Render → ton service → Environment** → mets :
   ```
   CORS_ORIGINS = https://researchos.vercel.app
   ```
   (l'URL Vercel exacte ; plusieurs domaines possibles, séparés par des virgules).
2. Render redéploie. Fini : le frontend Vercel peut appeler le backend.

---

## 5. Utiliser l'app

- Ouvre l'URL Vercel, crée un compte.
- **LLM Manager → Ajouter un fournisseur** : ajoute **Gemini** ou **Groq** avec ta
  clé (il n'y a pas d'Ollama dans le cloud, donc un fournisseur cloud est requis).
- Le chat, les agents, la revue de littérature et le graphe fonctionnent.

---

## Passer à l'échelle (plus tard)

Le montage ci-dessus tourne sur **1 instance** (SocketIO + tâches de fond
en mémoire, sans Redis — c'est volontaire et suffisant pour démarrer). Pour
scaler horizontalement :

1. **Render Redis** (« Key Value ») → passe `message_queue` Redis sur SocketIO.
2. `TASK_RUNNER=celery` + un **Render Background Worker** (broker Redis).
3. Plusieurs instances web + **sticky sessions** sur le load balancer.
4. Migrations **Alembic** (mettre `AUTO_CREATE_TABLES=0` une fois en place).

Les *coutures* sont déjà prévues (TaskRunner abstrait, `CORS_ORIGINS`,
`message_queue` anticipé) : c'est du branchement, pas une refonte.
