"""Service Knowledge Graph — extraction + fusion dans le graphe de l'utilisateur."""
from __future__ import annotations

from ..knowledge import KGExtractor
from ..repositories import ChunkRepository, DocumentRepository, GraphRepository
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError


class KnowledgeGraphService:
    def __init__(self, llm_service: LLMService | None = None,
                 graph: GraphRepository | None = None):
        self.llm_service = llm_service or LLMService()
        self.graph = graph or GraphRepository()
        self.documents = DocumentRepository()
        self.chunks = ChunkRepository()

    def _text_of_document(self, user_id: str, document_id: str) -> str:
        doc = self.documents.get(document_id)
        if not doc or doc.user_id != user_id:
            raise LLMServiceError("Document introuvable")
        recs = self.chunks.records_for_document(document_id, title=doc.title)
        return "\n".join(r["text"] for r in recs)

    def extract_and_merge(self, user_id: str, *, text: str | None = None,
                          document_id: str | None = None) -> dict:
        if document_id:
            text = self._text_of_document(user_id, document_id)
        if not text or not text.strip():
            raise LLMServiceError("Aucun texte à analyser")
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError("Aucun modèle disponible pour l'extraction")

        extractor = KGExtractor(RouterLLMClient(user_id, self.llm_service))
        data = extractor.extract(text)

        # Fusion : entités d'abord (pour disposer des ids), puis relations.
        name_to_id: dict[str, str] = {}
        for e in data["entities"]:
            ent = self.graph.upsert_entity(user_id, e["name"], e["type"])
            name_to_id[e["name"].lower()] = ent.id
        rel_count = 0
        for r in data["relations"]:
            s = name_to_id.get(r["source"].lower())
            t = name_to_id.get(r["target"].lower())
            if s and t and s != t:
                self.graph.upsert_relation(user_id, s, t, r["label"])
                rel_count += 1
        self.graph.commit()
        return {"added_entities": len(data["entities"]), "added_relations": rel_count,
                **self.stats(user_id)}

    def get_graph(self, user_id: str) -> dict:
        ents = self.graph.entities(user_id)
        rels = self.graph.relations(user_id)
        ids = {e.id for e in ents}
        return {"nodes": [e.to_dict() for e in ents],
                "edges": [r.to_dict() for r in rels
                          if r.source_id in ids and r.target_id in ids]}

    def stats(self, user_id: str) -> dict:
        return {"entities_total": len(self.graph.entities(user_id)),
                "relations_total": len(self.graph.relations(user_id))}

    def clear(self, user_id: str) -> None:
        self.graph.clear(user_id)
