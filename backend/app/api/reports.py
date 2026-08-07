"""Revue de littérature API — recherche immédiate (sync) + export PDF.

- POST /api/reports/search : renvoie directement les articles (+ BibTeX, + synthèse
  optionnelle) pour affichage interactif.
- POST /api/reports/pdf    : rend un PDF (tableau comparatif + résumés) depuis les
  articles fournis.
"""
from __future__ import annotations

from io import BytesIO

from flask import send_file
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, ReportService
from .schemas import ReportPdfSchema, ReportSearchSchema, ReportSynthesizeSchema

blp = Blueprint("reports", __name__, url_prefix="/api/reports",
                description="Revue de littérature (recherche réelle, tableau, PDF, BibTeX)")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("/search")
class Search(MethodView):
    @jwt_required()
    @blp.arguments(ReportSearchSchema)
    def post(self, data):
        try:
            return ReportService().search(
                _uid(), data["query"], sources=data.get("sources"), limit=data["limit"])
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:  # réseau/API tierce
            abort(502, message=f"Échec de la recherche: {e}")


@blp.route("/synthesize")
class Synthesize(MethodView):
    @jwt_required()
    @blp.arguments(ReportSynthesizeSchema)
    def post(self, data):
        """Synthèse IA séparée (optionnelle) — n'affecte jamais la recherche."""
        try:
            return {"synthesis": ReportService().synthesize(
                _uid(), data["query"], data["papers"], data.get("pinned_model"))}
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de la synthèse: {e}")


@blp.route("/pdf")
class Pdf(MethodView):
    @jwt_required()
    @blp.arguments(ReportPdfSchema)
    def post(self, data):
        pdf = ReportService().render_pdf(
            data["query"], data["papers"], data.get("synthesis", ""))
        return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                         download_name="revue-litterature.pdf")
