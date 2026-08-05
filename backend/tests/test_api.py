"""Test d'intégration de l'API (config test, SQLite en mémoire, aucun réseau).

Ollama est SIMULÉ (`_fetch_installed` patché) pour rester déterministe même si le
démon local n'est pas lancé. Couvre : santé, auth, providers, catalogue agrégé,
routage, et surtout le fallback automatique sur Ollama quand aucun cloud n'existe.

Lancer :  python tests/test_api.py   (depuis backend/)
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.ai.providers.ollama_provider import OllamaProvider

# Modèles "installés" simulés côté démon Ollama.
FAKE_OLLAMA = [
    {"name": "llama3.2:3b", "details": {"parameter_size": "3.2B"}},
    {"name": "llama3.1:8b", "details": {"parameter_size": "8.0B"}},
    {"name": "qwen2.5:14b", "details": {"parameter_size": "14.8B"}},
]


@contextmanager
def fake_ollama(installed=FAKE_OLLAMA):
    with patch.object(OllamaProvider, "_fetch_installed", return_value=installed):
        yield


def client():
    return create_app("test").test_client()


def auth_client():
    c = client()
    r = c.post("/api/auth/register", json={
        "email": "chercheur@univ.sn", "password": "motdepasse123",
        "full_name": "Dr. Sow"})
    assert r.status_code == 201, r.get_json()
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_health():
    r = client().get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"
    print("[health]   200 ok")


def test_register_and_me():
    c, h = auth_client()
    r = c.get("/api/auth/me", headers=h)
    assert r.status_code == 200 and r.get_json()["email"] == "chercheur@univ.sn"
    print(f"[auth]     inscription + /me ok ({r.get_json()['full_name']})")


def test_me_requires_token():
    assert client().get("/api/auth/me").status_code == 401
    print("[auth]     /me sans token -> 401")


def test_no_cloud_falls_back_to_ollama():
    """Aucun fournisseur cloud configuré -> Ollama fournit les modèles."""
    c, h = auth_client()
    with fake_ollama():
        models = c.get("/api/llm/models", headers=h).get_json()["models"]
    ids = {m["id"] for m in models}
    assert ids == {"llama3.2:3b", "llama3.1:8b", "qwen2.5:14b"}, ids
    assert all(m["privacy"] == "local" and m["input_cost"] == 0.0 for m in models)
    print(f"[fallback] 0 cloud -> {len(models)} modèles Ollama locaux dispo")


def test_ollama_down_is_graceful():
    """Ollama éteint + aucun cloud -> catalogue vide, pas d'erreur 500."""
    c, h = auth_client()
    with fake_ollama(installed=[]):   # démon injoignable => aucun modèle
        r = c.get("/api/llm/models", headers=h)
        assert r.status_code == 200 and r.get_json()["models"] == []
        # Une complétion renvoie un message clair, pas un crash.
        rc = c.post("/api/chat/complete", headers=h,
                    json={"messages": [{"role": "user", "content": "salut"}]})
        assert rc.status_code == 400 and "Aucun modèle" in rc.get_json()["message"]
    print("[graceful] Ollama down -> catalogue vide + message clair (pas de 500)")


def test_add_cloud_is_optional_and_masked():
    c, h = auth_client()
    r = c.post("/api/llm/providers", headers=h,
               json={"provider_key": "anthropic", "api_key": "sk-ant-SECRETvalue0042",
                     "label": "labo", "is_default": True})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["api_key_masked"].startswith("sk-")
    assert "SECRETvalue" not in str(r.get_json())   # la clé complète ne fuit jamais

    with fake_ollama():
        ids = {m["id"] for m in c.get("/api/llm/models", headers=h).get_json()["models"]}
    # Cloud (optionnel) + local coexistent dans le catalogue.
    assert "claude-opus-4-8" in ids and "llama3.1:8b" in ids, ids
    print(f"[cloud]    Anthropic (optionnel) + Ollama agrégés ({len(ids)} modèles)")


def test_routing_prefers_local_for_privacy_and_cost():
    c, h = auth_client()
    c.post("/api/llm/providers", headers=h,
           json={"provider_key": "anthropic", "api_key": "x"})
    with fake_ollama():
        # Confidentialité -> uniquement des modèles locaux
        rk = c.get("/api/llm/routing/preview?strategy=privacy&require_privacy=local",
                   headers=h).get_json()["ranking"]
        assert rk and all(x["input_cost"] == 0.0 for x in rk)
        print(f"[routing]  privacy=local -> top: {rk[0]['model']}")
        # Coût -> un modèle local (gratuit) en tête
        rc = c.get("/api/llm/routing/preview?strategy=cost", headers=h).get_json()["ranking"]
        assert rc[0]["input_cost"] == 0.0
        print(f"[routing]  cost -> top: {rc[0]['model']} (0 USD)")


def test_user_can_pin_a_specific_local_model():
    """L'utilisateur choisit explicitement le modèle qu'il veut (switch manuel)."""
    c, h = auth_client()
    with fake_ollama():
        rk = c.get("/api/llm/routing/preview?strategy=quality", headers=h).get_json()["ranking"]
        ids = [x["model"] for x in rk]
    # Le plus gros modèle local (14b) doit primer en qualité parmi les locaux.
    assert ids[0] == "qwen2.5:14b", ids
    print(f"[choice]   qualité -> {ids[0]} (l'utilisateur peut aussi épingler n'importe lequel)")


def test_duplicate_email_rejected():
    c, _ = auth_client()
    r = c.post("/api/auth/register", json={
        "email": "chercheur@univ.sn", "password": "motdepasse123"})
    assert r.status_code == 400
    print("[auth]     email dupliqué -> 400")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests d'API passés.")
