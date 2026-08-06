#!/usr/bin/env bash
# Démarre TOUT ResearchOS d'un coup : Ollama (si besoin) + backend + frontend.
# Laisse tourner jusqu'à Ctrl-C (arrête proprement les deux serveurs).
#
#   ./start.sh
#
# Astuce : forcer un interpréteur Python -> PYTHON=/chemin/python ./start.sh
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- Choisit un Python qui a bien les dépendances backend ---
pick_python() {
  for c in "$PYTHON" "$ROOT/backend/.venv/bin/python" /opt/anaconda3/bin/python3 python3; do
    [ -n "$c" ] || continue
    if "$c" -c 'import flask, flask_smorest, flask_socketio' >/dev/null 2>&1; then
      echo "$c"; return
    fi
  done
  echo "ERREUR: aucun Python avec les dépendances (pip install -r backend/requirements.txt)" >&2
  exit 1
}
PY="$(pick_python)"
echo "→ Python : $PY"

# --- Ollama (socle local) : démarre le démon s'il est absent ---
if command -v ollama >/dev/null 2>&1; then
  if ! curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "→ Démarrage d'Ollama…"; (ollama serve >/tmp/researchos-ollama.log 2>&1 &); sleep 3
  fi
  echo "→ Ollama OK ($(curl -s http://localhost:11434/api/tags | "$PY" -c 'import sys,json;print(len(json.load(sys.stdin).get("models",[])),"modèle(s)")' 2>/dev/null || echo '?'))"
else
  echo "→ Ollama non installé (facultatif : la plateforme marche aussi avec un fournisseur cloud)."
fi

# --- Backend :5000 ---
echo "→ Backend  : http://localhost:5000  (Swagger /docs)"
( cd "$ROOT/backend" && FLASK_CONFIG=dev "$PY" wsgi.py ) &
BACK=$!

# --- Frontend :5173 ---
echo "→ Frontend : http://localhost:5173"
( cd "$ROOT/frontend" && [ -d node_modules ] || npm install; npm run dev ) &
FRONT=$!

trap 'echo; echo "→ Arrêt…"; kill "$BACK" "$FRONT" 2>/dev/null' EXIT INT TERM
echo "→ Prêt. Ctrl-C pour tout arrêter."
wait
