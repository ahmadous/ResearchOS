"""Mail API — connecter un compte IMAP (lecture seule), lister, trier (LLM)."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, MailService
from .schemas import MailConnectSchema, MailTriageSchema

blp = Blueprint("mail", __name__, url_prefix="/api/mail",
                description="Boîte mail (IMAP lecture seule) + tri IA")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("/account")
class Account(MethodView):
    @jwt_required()
    def get(self):
        return {"account": MailService().get_account(_uid())}

    @jwt_required()
    @blp.arguments(MailConnectSchema)
    def post(self, data):
        try:
            return MailService().connect_account(
                _uid(), data["email"], data["password"],
                data.get("imap_host", "imap.gmail.com")), 201
        except LLMServiceError as e:
            abort(400, message=str(e))

    @jwt_required()
    @blp.response(204)
    def delete(self):
        MailService().delete_account(_uid())


@blp.route("/inbox")
class Inbox(MethodView):
    @jwt_required()
    def get(self):
        try:
            return MailService().inbox(_uid())
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/triage")
class Triage(MethodView):
    @jwt_required()
    @blp.arguments(MailTriageSchema)
    def post(self, data):
        try:
            return MailService().triage(_uid(), data["emails"], data.get("pinned_model"))
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec du tri: {e}")
