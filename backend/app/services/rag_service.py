"""Service RAG — ingestion et interrogation, câblés à la base et au routeur IA.

Le moteur RAG reste pur ; ce service fournit l'embedder (config), la persistance
(Document/Chunk) et le LLM (RouterLLMClient, donc Ollama-first).
"""
from __future__ import annotations

from flask import current_app

from ..extensions import db
from ..models import Chunk, Document
from ..rag import RAGEngine, get_embedder
from ..repositories import ChunkRepository, DocumentRepository
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError


class RAGService:
    def __init__(self, llm_service: LLMService | None = None,
                 documents: DocumentRepository | None = None,
                 chunks: ChunkRepository | None = None):
        self.llm_service = llm_service or LLMService()
        self.documents = documents or DocumentRepository()
        self.chunks = chunks or ChunkRepository()

    def _embedder(self):
        return get_embedder(
            current_app.config.get("EMBEDDING_BACKEND", "hashing"),
            model=current_app.config.get("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=current_app.config.get("OLLAMA_URL", "http://localhost:11434"),
        )

    def _engine(self, user_id: str) -> RAGEngine:
        return RAGEngine(self._embedder(), RouterLLMClient(user_id, self.llm_service))

    # --- Ingestion ---
    def ingest_text(self, user_id: str, title: str, text: str,
                    source_type: str = "text", source_ref: str | None = None) -> dict:
        if not text.strip():
            raise LLMServiceError("Document vide")
        embedder = self._embedder()
        engine = RAGEngine(embedder, RouterLLMClient(user_id, self.llm_service))
        embedded = engine.chunk_and_embed(text)

        doc = Document(user_id=user_id, title=title[:300], source_type=source_type,
                       source_ref=source_ref, embedder=embedder.name,
                       n_chunks=len(embedded))
        self.documents.add(doc, commit=False)
        db.session.flush()   # matérialise doc.id avant d'y rattacher les chunks
        for ec in embedded:
            c = Chunk(document_id=doc.id, ordinal=ec.chunk.ordinal,
                      text=ec.chunk.text, token_count=ec.chunk.token_count)
            c.embedding = ec.embedding
            self.chunks.add(c, commit=False)
        self.documents.commit()
        return doc.to_dict()

    def ingest_file(self, user_id: str, filename: str, data: bytes) -> dict:
        """Importe un fichier : PDF/Word/Excel/texte -> indexé RAG ;
        image/vidéo -> stockée comme pièce jointe (non indexée)."""
        import mimetypes
        import os
        from ..ingest import extract
        from ..ingest.parsers import BINARY_KINDS

        if not data:
            raise LLMServiceError("Fichier vide")
        parsed = extract(filename, data)
        kind = parsed["kind"]

        if kind in BINARY_KINDS or (not parsed["text"] and kind != "unknown"):
            # Pièce jointe (image/vidéo) ou texte non extractible -> on stocke le fichier.
            uploads = current_app.config["UPLOADS_DIR"]
            os.makedirs(uploads, exist_ok=True)
            doc = Document(user_id=user_id, title=filename[:300], source_type=kind,
                           n_chunks=0, mime_type=mimetypes.guess_type(filename)[0])
            self.documents.add(doc, commit=False)
            db.session.flush()
            path = os.path.join(uploads, f"{doc.id}{os.path.splitext(filename)[1]}")
            with open(path, "wb") as f:
                f.write(data)
            doc.file_path = path
            self.documents.commit()
            note = parsed["error"] or ("stocké (non indexé)" if kind in BINARY_KINDS
                                       else "texte non extractible")
            return {**doc.to_dict(), "indexed": False, "note": note}

        if not parsed["text"].strip():
            raise LLMServiceError(parsed["error"] or f"Aucun texte extrait ({kind})")

        # Fichier textuel -> indexation RAG classique.
        doc = self.ingest_text(user_id, title=filename, text=parsed["text"],
                               source_type=kind, source_ref=filename)
        return {**doc, "indexed": True, "chars": len(parsed["text"])}

    def attachment_path(self, user_id: str, doc_id: str) -> tuple[str, str | None]:
        doc = self.documents.get(doc_id)
        if not doc or doc.user_id != user_id:
            raise LLMServiceError("Document introuvable")
        import os
        if not doc.file_path or not os.path.exists(doc.file_path):
            raise LLMServiceError("Aucun fichier attaché")
        return doc.file_path, doc.mime_type

    def list_documents(self, user_id: str) -> list[dict]:
        return [d.to_dict() for d in self.documents.for_user(user_id)]

    def delete_document(self, user_id: str, doc_id: str) -> None:
        doc = self.documents.get(doc_id)
        if not doc or doc.user_id != user_id:
            raise LLMServiceError("Document introuvable")
        self.documents.delete(doc)

    # --- Interrogation (réponse citée) ---
    def query(self, user_id: str, question: str, *, document_id: str | None = None,
              strategy: str = "balanced", require_privacy: str | None = None,
              lang: str | None = None) -> dict:
        if document_id:
            doc = self.documents.get(document_id)
            if not doc or doc.user_id != user_id:
                raise LLMServiceError("Document introuvable")
            records = self.chunks.records_for_document(document_id, title=doc.title)
        else:
            records = self.chunks.records_for_user(user_id)

        if not records:
            raise LLMServiceError("Aucun document indexé. Importez d'abord un document.")
        # Garde-fou modèles (comme le chat) : message clair si aucun LLM dispo.
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError(
                "Aucun modèle disponible pour générer la réponse. Configurez un "
                "fournisseur ou démarrez Ollama.")
        from ..language import directive_for
        return self._engine(user_id).answer(
            question, records, strategy=strategy, require_privacy=require_privacy,
            system_extra=directive_for(lang, question))
