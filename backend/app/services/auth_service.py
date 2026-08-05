from __future__ import annotations

from flask_jwt_extended import create_access_token, create_refresh_token

from ..models import User
from ..repositories import UserRepository
from ..security import hash_password, verify_password


class AuthError(Exception):
    status_code = 400


class AuthService:
    def __init__(self, users: UserRepository | None = None):
        self.users = users or UserRepository()

    def register(self, email: str, password: str, full_name: str = "") -> dict:
        email = email.lower().strip()
        if self.users.by_email(email):
            raise AuthError("Un compte existe déjà avec cet email")
        if len(password) < 8:
            raise AuthError("Le mot de passe doit faire au moins 8 caractères")
        user = User(email=email, full_name=full_name,
                    password_hash=hash_password(password))
        self.users.add(user)
        return self._tokens(user)

    def login(self, email: str, password: str) -> dict:
        user = self.users.by_email(email.lower().strip())
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Identifiants invalides")
        if not user.is_active:
            raise AuthError("Compte désactivé")
        return self._tokens(user)

    @staticmethod
    def _tokens(user: User) -> dict:
        claims = {"role": user.role, "email": user.email}
        return {
            "access_token": create_access_token(identity=user.id, additional_claims=claims),
            "refresh_token": create_refresh_token(identity=user.id),
            "user": user.to_dict(),
        }
