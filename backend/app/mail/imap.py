"""Connecteur IMAP en LECTURE SEULE (imaplib, stdlib).

Récupère les N derniers messages de la boîte de réception. Aucune écriture,
aucun envoi. Les identifiants viennent (chiffrés) de la base de l'utilisateur.
"""
from __future__ import annotations

import imaplib

from .parser import parse_email


class MailError(Exception):
    pass


class IMAPConnector:
    def __init__(self, host: str, email_addr: str, password: str):
        self.host = host
        self.email = email_addr
        self.password = password

    def _open(self) -> imaplib.IMAP4_SSL:
        try:
            m = imaplib.IMAP4_SSL(self.host)
            m.login(self.email, self.password)
            return m
        except imaplib.IMAP4.error as e:
            raise MailError(f"Connexion IMAP refusée : {e} "
                            "(vérifiez l'email, le mot de passe d'application et "
                            "que l'accès IMAP est activé).")
        except OSError as e:
            raise MailError(f"Serveur IMAP injoignable : {e}")

    def check(self) -> bool:
        m = self._open()
        try:
            m.logout()
        except Exception:
            pass
        return True

    def fetch_recent(self, n: int = 20) -> list[dict]:
        m = self._open()
        try:
            typ, _ = m.select("INBOX", readonly=True)
            if typ != "OK":
                raise MailError("Impossible d'ouvrir la boîte de réception (IMAP activé ?).")
            typ, data = m.search(None, "ALL")
            ids = (data[0] or b"").split()[-n:]
            out = []
            for i in reversed(ids):
                try:
                    typ, d = m.fetch(i, "(RFC822 FLAGS)")
                    if not d or not isinstance(d[0], tuple):
                        continue
                    try:
                        flags = imaplib.ParseFlags(d[0][0])
                        flag_bytes = b" ".join(flags) if flags else b""
                    except Exception:
                        flag_bytes = b""
                    e = parse_email(d[0][1], flag_bytes)
                    e["uid"] = i.decode()
                    out.append(e)
                except Exception:               # un message illisible n'arrête pas les autres
                    continue
            return out
        finally:
            try:
                m.logout()
            except Exception:
                pass
