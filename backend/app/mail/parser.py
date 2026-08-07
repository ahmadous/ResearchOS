"""Parsing d'emails bruts (RFC822) — pur et testable, aucune I/O réseau."""
from __future__ import annotations

import email
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime


def _decode(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _body_text(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", ""))
            if part.get_content_type() == "text/plain" and "attachment" not in disp:
                try:
                    return part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(
            msg.get_content_charset() or "utf-8", "ignore")
    except Exception:
        return ""


def parse_email(raw: bytes, flags: bytes | None = None) -> dict:
    msg = email.message_from_bytes(raw)
    name, addr = parseaddr(msg.get("From", ""))
    try:
        date = parsedate_to_datetime(msg.get("Date")).isoformat()
    except Exception:
        date = None
    snippet = " ".join(_body_text(msg).split())[:280]
    unread = flags is not None and b"\\Seen" not in flags
    return {
        "from": _decode(name) or addr,
        "from_email": addr,
        "subject": _decode(msg.get("Subject", "")),
        "date": date,
        "snippet": snippet,
        "unread": unread,
    }
