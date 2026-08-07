"""Tests Mail — parsing pur, tri LLM, API (IMAP simulé, aucun réseau).

Lancer : python tests/test_mail.py
"""
import sys
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.agents.base import AgentLLMResponse
from app.mail import MailTriager, parse_email


def _raw(from_, subject, body):
    m = EmailMessage()
    m["From"] = from_
    m["Subject"] = subject
    m["Date"] = "Mon, 07 Aug 2026 10:00:00 +0000"
    m.set_content(body)
    return m.as_bytes()


def test_parse_email():
    e = parse_email(_raw("Awa Diop <awa@lab.sn>", "Rapport à valider",
                         "Bonjour, peux-tu valider le rapport ? Merci."), flags=b"")
    assert e["from"] == "Awa Diop" and e["from_email"] == "awa@lab.sn"
    assert e["subject"] == "Rapport à valider" and "valider le rapport" in e["snippet"]
    assert e["unread"] is True and e["date"].startswith("2026-08-07")
    print(f"[parse]    from={e['from']} · sujet='{e['subject']}' · non-lu={e['unread']}")


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, messages, **kw):
        return AgentLLMResponse(content=self.payload, model="fake", provider="fake")


def test_triage_classifies_and_sorts():
    emails = [
        {"from": "Newsletter", "subject": "Promo -50%", "snippet": "soldes"},
        {"from": "Directeur", "subject": "Réunion demain", "snippet": "présence requise"},
    ]
    payload = ('[{"n":1,"importance":10,"needs_reply":false,"category":"pub","summary":"Promo."},'
               '{"n":2,"importance":90,"needs_reply":true,"category":"travail","summary":"Réunion demain."}]')
    out = MailTriager(FakeLLM(payload)).classify(emails)
    # Trié par importance décroissante -> le mail du directeur d'abord.
    assert out[0]["subject"] == "Réunion demain" and out[0]["needs_reply"] is True
    assert out[0]["importance"] == 90 and out[1]["importance"] == 10
    print(f"[triage]   trié par importance : '{out[0]['subject']}' (90, à répondre)")


def test_triage_handles_garbage():
    emails = [{"from": "x", "subject": "y", "snippet": "z"}]
    out = MailTriager(FakeLLM("pas du json")).classify(emails)
    assert out[0]["importance"] == 50 and out[0]["needs_reply"] is False
    print("[triage]   sortie non-JSON -> valeurs par défaut sûres")


# --- API (IMAP simulé) ---
def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "m@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_connect_account_masks_password_and_lists_inbox():
    from app.mail.imap import IMAPConnector
    c, h = _auth()
    fake_emails = [{"from": "Boss", "from_email": "b@x.com", "subject": "Urgent",
                    "date": None, "snippet": "à faire", "unread": True, "uid": "1"}]
    with patch.object(IMAPConnector, "check", return_value=True), \
         patch.object(IMAPConnector, "fetch_recent", return_value=fake_emails):
        r = c.post("/api/mail/account", headers=h,
                   json={"email": "me@gmail.com", "password": "app-pass-secret-xyz"})
        assert r.status_code == 201, r.get_json()
        acc = r.get_json()
        assert acc["email"] == "me@gmail.com"
        assert "secret" not in str(acc) and acc["password_masked"].startswith("app")

        box = c.get("/api/mail/inbox", headers=h).get_json()
        assert box["count"] == 1 and box["emails"][0]["subject"] == "Urgent"
    print("[api]      compte connecté (mdp masqué) + inbox listée")


def test_bad_credentials_rejected():
    from app.mail.imap import IMAPConnector, MailError
    c, h = _auth()
    with patch.object(IMAPConnector, "check", side_effect=MailError("Connexion IMAP refusée")):
        r = c.post("/api/mail/account", headers=h,
                   json={"email": "me@gmail.com", "password": "mauvais"})
    assert r.status_code == 400 and "IMAP" in r.get_json()["message"]
    print("[api]      identifiants invalides -> 400 message clair")


if __name__ == "__main__":
    for t in [test_parse_email, test_triage_classifies_and_sorts, test_triage_handles_garbage,
              test_connect_account_masks_password_and_lists_inbox, test_bad_credentials_rejected]:
        t()
    print("\n✅ 5 tests mail passés.")
