"""Schémas Marshmallow — validation entrée + documentation OpenAPI."""
from __future__ import annotations

from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True,
                          validate=validate.Length(min=8))
    full_name = fields.Str(load_default="")


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


class TokenSchema(Schema):
    access_token = fields.Str()
    refresh_token = fields.Str()
    user = fields.Dict()


class ProviderCreateSchema(Schema):
    provider_key = fields.Str(required=True)
    api_key = fields.Str(load_default="", load_only=True)
    base_url = fields.Str(load_default=None, allow_none=True)
    label = fields.Str(load_default="default")
    is_default = fields.Bool(load_default=False)


class ProviderSchema(Schema):
    id = fields.Str()
    provider_key = fields.Str()
    label = fields.Str()
    api_key_masked = fields.Str(allow_none=True)
    base_url = fields.Str(allow_none=True)
    enabled = fields.Bool()
    is_default = fields.Bool()


class TestModelSchema(Schema):
    model = fields.Str(required=True)


class MessageSchema(Schema):
    role = fields.Str(required=True,
                      validate=validate.OneOf(["system", "user", "assistant"]))
    content = fields.Str(required=True)


class TaskCreateSchema(Schema):
    kind = fields.Str(required=True,
                      validate=validate.OneOf(
                          ["agent", "rag_ingest", "scholar_import", "workflow"]))
    params = fields.Dict(required=True)


class WorkflowSchema(Schema):
    name = fields.Str(load_default="Nouveau workflow")
    graph = fields.Dict(load_default=None, allow_none=True)


class GraphExtractSchema(Schema):
    text = fields.Str(load_default=None, allow_none=True)
    document_id = fields.Str(load_default=None, allow_none=True)


class ScholarSearchSchema(Schema):
    query = fields.Str(required=True, validate=validate.Length(min=2))
    sources = fields.List(fields.Str(), load_default=None, allow_none=True)
    limit = fields.Int(load_default=10, validate=validate.Range(min=1, max=50))


class ScholarImportSchema(Schema):
    # On accepte un objet `Paper` (tel que renvoyé par /search).
    title = fields.Str(load_default="")
    abstract = fields.Str(load_default="")
    authors = fields.List(fields.Str(), load_default=list)
    year = fields.Int(load_default=None, allow_none=True)
    doi = fields.Str(load_default=None, allow_none=True)
    url = fields.Str(load_default=None, allow_none=True)
    source = fields.Str(load_default="external")
    external_id = fields.Str(load_default=None, allow_none=True)


class DocumentIngestSchema(Schema):
    title = fields.Str(load_default="Sans titre")
    text = fields.Str(required=True, validate=validate.Length(min=1))
    source_type = fields.Str(load_default="text")
    source_ref = fields.Str(load_default=None, allow_none=True)


class RAGQuerySchema(Schema):
    question = fields.Str(required=True, validate=validate.Length(min=1))
    document_id = fields.Str(load_default=None, allow_none=True)
    strategy = fields.Str(load_default="balanced",
                          validate=validate.OneOf(
                              ["balanced", "cost", "speed", "quality", "privacy"]))
    require_privacy = fields.Str(load_default=None, allow_none=True,
                                 validate=validate.OneOf(["local", "cloud", "private_cloud"]))


class AgentRunSchema(Schema):
    task = fields.Str(required=True, validate=validate.Length(min=1))
    goal = fields.Str(load_default=None, allow_none=True)


class AgentStepSchema(Schema):
    agent = fields.Str(required=True)
    task = fields.Str(required=True)


class AgentPipelineSchema(Schema):
    goal = fields.Str(required=True)
    steps = fields.List(fields.Nested(AgentStepSchema), required=True,
                        validate=validate.Length(min=1))


class AgentAutoSchema(Schema):
    goal = fields.Str(required=True, validate=validate.Length(min=1))
    max_steps = fields.Int(load_default=5, validate=validate.Range(min=1, max=10))


class ChatSchema(Schema):
    messages = fields.List(fields.Nested(MessageSchema), required=True,
                           validate=validate.Length(min=1))
    strategy = fields.Str(load_default="balanced",
                          validate=validate.OneOf(
                              ["balanced", "cost", "speed", "quality", "privacy"]))
    pinned_model = fields.Str(load_default=None, allow_none=True)
    require_privacy = fields.Str(load_default=None, allow_none=True,
                                 validate=validate.OneOf(["local", "cloud", "private_cloud"]))
    needs_tools = fields.Bool(load_default=False)
    temperature = fields.Float(load_default=0.7)
    max_tokens = fields.Int(load_default=None, allow_none=True)
