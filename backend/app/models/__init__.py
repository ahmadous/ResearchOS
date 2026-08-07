"""Import de tous les modèles pour que SQLAlchemy enregistre les tables."""
from .conversation import ChatMessage, Conversation
from .document import Chunk, Document
from .graph_entity import GraphEntity, GraphRelation
from .memory import MemoryItem
from .provider import ProviderCredential
from .report import Report
from .task import Task
from .usage import ModelUsage
from .user import User
from .workflow import Workflow
from .workflow_run import WorkflowRun

__all__ = ["User", "ProviderCredential", "ModelUsage", "Document", "Chunk",
           "Task", "Workflow", "GraphEntity", "GraphRelation", "MemoryItem",
           "Report", "Conversation", "ChatMessage", "WorkflowRun"]
