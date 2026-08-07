"""Génération de PDF de rapport (reportlab, pur).

Rendu simple depuis un corps « markdown léger » (## titres) + une bibliographie.
"""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def render_report_pdf(title: str, subtitle: str, body: str,
                      references: list[dict]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm, title=title)
    styles = getSampleStyleSheet()
    flow = [Paragraph(escape(title), styles["Title"])]
    if subtitle:
        flow.append(Paragraph(escape(subtitle), styles["Italic"]))
    flow.append(Spacer(1, 0.6 * cm))

    for line in (body or "").split("\n"):
        line = line.rstrip()
        if not line.strip():
            flow.append(Spacer(1, 0.2 * cm))
        elif line.startswith("## "):
            flow.append(Spacer(1, 0.2 * cm))
            flow.append(Paragraph(escape(line[3:]), styles["Heading2"]))
        elif line.startswith("# "):
            flow.append(Paragraph(escape(line[2:]), styles["Heading1"]))
        else:
            flow.append(Paragraph(escape(line), styles["BodyText"]))

    if references:
        flow.append(Spacer(1, 0.5 * cm))
        flow.append(Paragraph("Références", styles["Heading2"]))
        for i, r in enumerate(references, 1):
            authors = ", ".join(r.get("authors", [])[:4]) or "Anonyme"
            if len(r.get("authors", [])) > 4:
                authors += " et al."
            ref = (f"[{i}] {authors}. {r.get('title', '')} "
                   f"({r.get('year') or 's.d.'}). {r.get('url') or ''}")
            flow.append(Paragraph(escape(ref), styles["BodyText"]))
            flow.append(Spacer(1, 0.1 * cm))

    doc.build(flow)
    return buf.getvalue()
