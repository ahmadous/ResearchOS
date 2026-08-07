"""RAG API — importer un document, lister, interroger avec citations."""
from __future__ import annotations

from flask import request, send_file
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, RAGService
from .schemas import DocumentIngestSchema, RAGQuerySchema

blp = Blueprint("rag", __name__, url_prefix="/api/rag",
                description="Moteur RAG : ingestion et réponses sourcées")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("/documents")
class Documents(MethodView):
    @jwt_required()
    def get(self):
        return {"documents": RAGService().list_documents(_uid())}

    @jwt_required()
    @blp.arguments(DocumentIngestSchema)
    def post(self, data):
        try:
            return RAGService().ingest_text(_uid(), **data), 201
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/upload")
class Upload(MethodView):
    @jwt_required()
    def post(self):
        """Import multipart : PDF, Word, Excel, Markdown/texte, images, vidéos."""
        f = request.files.get("file")
        if not f or not f.filename:
            abort(400, message="Aucun fichier fourni (champ 'file')")
        try:
            return RAGService().ingest_file(_uid(), f.filename, f.read()), 201
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/documents/<doc_id>/file")
class DocumentFile(MethodView):
    @jwt_required()
    def get(self, doc_id):
        """Sert la pièce jointe (image/vidéo) pour aperçu/téléchargement."""
        try:
            path, mime = RAGService().attachment_path(_uid(), doc_id)
        except LLMServiceError as e:
            abort(404, message=str(e))
        return send_file(path, mimetype=mime or "application/octet-stream")


@blp.route("/documents/<doc_id>")
class DocumentItem(MethodView):
    @jwt_required()
    @blp.response(204)
    def delete(self, doc_id):
        try:
            RAGService().delete_document(_uid(), doc_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/query")
class Query(MethodView):
    @jwt_required()
    @blp.arguments(RAGQuerySchema)
    def post(self, data):
        try:
            return RAGService().query(_uid(), **data)
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de la requête RAG: {e}")
