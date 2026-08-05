from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..repositories import UserRepository
from ..services import AuthError, AuthService
from .schemas import LoginSchema, RegisterSchema, TokenSchema

blp = Blueprint("auth", __name__, url_prefix="/api/auth",
                description="Authentification (JWT)")


@blp.route("/register")
class Register(MethodView):
    @blp.arguments(RegisterSchema)
    @blp.response(201, TokenSchema)
    def post(self, data):
        try:
            return AuthService().register(**data)
        except AuthError as e:
            abort(400, message=str(e))


@blp.route("/login")
class Login(MethodView):
    @blp.arguments(LoginSchema)
    @blp.response(200, TokenSchema)
    def post(self, data):
        try:
            return AuthService().login(**data)
        except AuthError as e:
            abort(401, message=str(e))


@blp.route("/me")
class Me(MethodView):
    @jwt_required()
    @blp.response(200)
    def get(self):
        user = UserRepository().get(get_jwt_identity())
        if not user:
            abort(404, message="Utilisateur introuvable")
        return user.to_dict()
