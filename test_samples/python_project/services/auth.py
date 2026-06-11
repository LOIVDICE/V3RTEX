import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from constants import TOKEN_EXPIRE_MINUTES, HASH_ALGORITHM
from models.user import User, UserRole


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}:{digest}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split(":", 1)
    except ValueError:
        return False
    expected = hashlib.sha256(f"{plain}{salt}".encode()).hexdigest()
    return hmac.compare_digest(expected, digest)


class AuthService:
    def __init__(self):
        self._secret = settings.secret_key
        self._tokens: dict = {}

    def create_token(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        self._tokens[token] = {"user_id": user.id, "expires": expires}
        return token

    def validate_token(self, token: str) -> Optional[int]:
        entry = self._tokens.get(token)
        if not entry:
            return None
        if datetime.utcnow() > entry["expires"]:
            del self._tokens[token]
            return None
        return entry["user_id"]

    def revoke_token(self, token: str) -> None:
        self._tokens.pop(token, None)

    def revoke_all(self, user_id: int) -> int:
        before = len(self._tokens)
        self._tokens = {t: e for t, e in self._tokens.items() if e["user_id"] != user_id}
        return before - len(self._tokens)

    def check_permission(self, user: User, required_role: UserRole) -> bool:
        hierarchy = [UserRole.GUEST, UserRole.USER, UserRole.ADMIN]
        return hierarchy.index(user.role) >= hierarchy.index(required_role)
