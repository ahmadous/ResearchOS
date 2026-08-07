"""Génération de PDF (reportlab, pur).

Deux rendus :
- `render_digest_pdf` : revue de littérature OUTILLÉE — tableau comparatif +
  résumés extractifs + bibliographie, construite à partir des vraies métadonnées.
- `render_report_pdf` : rendu d'un texte « markdown léger » (utilisé si une
  synthèse IA optionnelle est demandée).
"""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


def _doc(buf, title, landscape_mode=False):
    size = landscape(A4) if landscape_mode else A4
    return SimpleDocTemplate(buf, pagesize=size, topMargin=1.5 * cm,
                             bottomMargin=1.5 * cm, leftMargin=1.5 * cm,
                             rightMargin=1.5 * cm, title=title)


def render_digest_pdf(query: str, papers: list[dict], synthesis: str = "") -> bytes:
    buf = BytesIO()
    doc = _doc(buf, f"Revue : {query}", landscape_mode=True)
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small")
    small.fontSize = 8
    small.leading = 10
    flow = [Paragraph(escape(f"Revue de littérature : {query}"), styles["Title"]),
            Paragraph(escape(f"{len(papers)} articles · généré par ResearchOS"), styles["Italic"]),
            Spacer(1, 0.4 * cm)]

    # --- Tableau comparatif ---
    head = ["#", "Titre", "Auteurs", "Année", "Cit.", "Source"]
    rows = [[Paragraph(f"<b>{h}</b>", small) for h in head]]
    for i, p in enumerate(papers, 1):
        authors = ", ".join((p.get("authors") or [])[:3])
        if len(p.get("authors") or []) > 3:
            authors += " et al."
        rows.append([
            Paragraph(str(i), small),
            Paragraph(escape(p.get("title") or ""), small),
            Paragraph(escape(authors), small),
            Paragraph(str(p.get("year") or "—"), small),
            Paragraph(str(p.get("citations") if p.get("citations") is not None else "—"), small),
            Paragraph(escape(p.get("source") or ""), small),
        ])
    table = Table(rows, colWidths=[0.8 * cm, 10 * cm, 6 * cm, 1.6 * cm, 1.4 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(table)

    # --- Synthèse IA (optionnelle) ---
    if synthesis:
        flow.append(Spacer(1, 0.5 * cm))
        flow.append(Paragraph("Synthèse (IA)", styles["Heading2"]))
        for line in synthesis.split("\n"):
            if line.strip():
                flow.append(Paragraph(escape(line), styles["BodyText"]))

    # --- Résumés extractifs ---
    flow.append(Spacer(1, 0.5 * cm))
    flow.append(Paragraph("Résumés", styles["Heading2"]))
    for i, p in enumerate(papers, 1):
        abstract = (p.get("abstract") or "").strip()
        abstract = abstract[:400] + "…" if len(abstract) > 400 else (abstract or "(pas de résumé)")
        flow.append(Paragraph(f"<b>[{i}] {escape(p.get('title') or '')}</b> — "
                              f"{escape(p.get('url') or '')}", small))
        flow.append(Paragraph(escape(abstract), small))
        flow.append(Spacer(1, 0.15 * cm))

    doc.build(flow)
    return buf.getvalue()


def render_report_pdf(title: str, subtitle: str, body: str,
                      references: list[dict]) -> bytes:
    buf = BytesIO()
    doc = _doc(buf, title)
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
            flow.append(Paragraph(escape(line[3:]), styles["Heading2"]))
        else:
            flow.append(Paragraph(escape(line), styles["BodyText"]))
    doc.build(flow)
    return buf.getvalue()
