"""Rapports API — générer (async), lister, consulter, télécharger le PDF."""
from __future__ import annotations

from flask import send_file
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, ReportService, TaskService
from .schemas import ReportCreateSchema

blp = Blueprint("reports", __name__, url_prefix="/api/reports",
                description="Rapports (recherche réelle -> état de l'art -> PDF)")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Reports(MethodView):
    @jwt_required()
    def get(self):
        return {"reports": ReportService().list(_uid())}

    @jwt_required()
    @blp.arguments(ReportCreateSchema)
    def post(self, data):
        # Génération asynchrone : progression via WebSocket.
        params = {k: v for k, v in data.items() if v is not None}
        try:
            return TaskService().enqueue(_uid(), "report", params), 202
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/<report_id>")
class ReportItem(MethodView):
    @jwt_required()
    def get(self, report_id):
        try:
            return ReportService().get(_uid(), report_id, full=True)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/<report_id>/pdf")
class ReportPdf(MethodView):
    @jwt_required()
    def get(self, report_id):
        try:
            path = ReportService().pdf_path(_uid(), report_id)
        except LLMServiceError as e:
            abort(404, message=str(e))
        return send_file(path, mimetype="application/pdf", as_attachment=True,
                         download_name=f"rapport-{report_id[:8]}.pdf")
