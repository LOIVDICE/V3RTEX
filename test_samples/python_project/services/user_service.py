from typing import List, Optional, Tuple

from models.user import User, UserRole
from services.auth import AuthService, hash_password, verify_password
from utils.validators import validate_email, validate_password
from utils.pagination import Paginator, PaginatedResult


class UserService:
    def __init__(self, auth_service: AuthService):
        self.auth = auth_service
        self._store: dict = {}
        self._next_id: int = 1

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> Tuple[Optional[User], str]:
        ok, msg = validate_email(email)
        if not ok:
            return None, msg
        ok, msg = validate_password(password)
        if not ok:
            return None, msg
        if self.get_by_email(email):
            return None, "Email already registered"
        user = User(
            id=self._next_id,
            username=username,
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        self._store[self._next_id] = user
        self._next_id += 1
        return user, ""

    def get_user(self, user_id: int) -> Optional[User]:
        return self._store.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return next((u for u in self._store.values() if u.email == email), None)

    def list_users(self, page: int = 1, size: int = 20) -> PaginatedResult:
        p = Paginator(page=page, size=size)
        all_users = list(self._store.values())
        return p.paginate(all_users[p.offset : p.offset + p.size], len(all_users))

    def authenticate(self, email: str, password: str) -> Tuple[Optional[User], str]:
        user = self.get_by_email(email)
        if not user:
            return None, "User not found"
        if not verify_password(password, user.hashed_password):
            return None, "Invalid password"
        if not user.is_active:
            return None, "Account is deactivated"
        return user, ""

    def deactivate(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if user:
            user.deactivate()
            self.auth.revoke_all(user_id)
            return True
        return False
