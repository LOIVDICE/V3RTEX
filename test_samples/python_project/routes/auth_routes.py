from typing import Any, Dict

from services.auth import AuthService
from services.user_service import UserService
from models.user import UserRole
from utils.formatters import format_user


class AuthRouter:
    def __init__(self, user_service: UserService, auth_service: AuthService):
        self.users = user_service
        self.auth = auth_service

    def login(self, email: str, password: str) -> Dict[str, Any]:
        user, error = self.users.authenticate(email, password)
        if not user:
            return {"error": error, "status": 401}
        token = self.auth.create_token(user)
        return {"token": token, "user": format_user(user), "status": 200}

    def logout(self, token: str) -> Dict[str, Any]:
        self.auth.revoke_token(token)
        return {"message": "Logged out successfully", "status": 200}

    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        user, error = self.users.create_user(username, email, password, UserRole.USER)
        if not user:
            return {"error": error, "status": 400}
        return {"user": format_user(user), "status": 201}

    def me(self, token: str) -> Dict[str, Any]:
        user_id = self.auth.validate_token(token)
        if not user_id:
            return {"error": "Invalid or expired token", "status": 401}
        user = self.users.get_user(user_id)
        if not user:
            return {"error": "User not found", "status": 404}
        return {"user": format_user(user), "status": 200}
