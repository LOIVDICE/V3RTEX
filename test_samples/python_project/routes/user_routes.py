from typing import Any, Dict

from services.auth import AuthService
from services.user_service import UserService
from models.user import UserRole
from utils.formatters import format_user
from utils.validators import validate_page_params


class UserRouter:
    def __init__(self, user_service: UserService, auth_service: AuthService):
        self.users = user_service
        self.auth = auth_service

    def _require_auth(self, token: str) -> Dict[str, Any]:
        user_id = self.auth.validate_token(token)
        if not user_id:
            return {"error": "Unauthorized", "status": 401}
        user = self.users.get_user(user_id)
        if not user:
            return {"error": "User not found", "status": 404}
        return {"user": user, "status": 200}

    def get_user(self, token: str, user_id: int) -> Dict[str, Any]:
        auth = self._require_auth(token)
        if auth["status"] != 200:
            return auth
        requesting_user = auth["user"]
        if not self.auth.check_permission(requesting_user, UserRole.ADMIN):
            if requesting_user.id != user_id:
                return {"error": "Forbidden", "status": 403}
        target = self.users.get_user(user_id)
        if not target:
            return {"error": "User not found", "status": 404}
        return {"user": format_user(target), "status": 200}

    def list_users(self, token: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        auth = self._require_auth(token)
        if auth["status"] != 200:
            return auth
        if not self.auth.check_permission(auth["user"], UserRole.ADMIN):
            return {"error": "Forbidden", "status": 403}
        page, size = validate_page_params(page, size)
        result = self.users.list_users(page, size)
        return {
            "users": [format_user(u) for u in result.items],
            "pagination": result.to_dict(),
            "status": 200,
        }

    def deactivate_user(self, token: str, user_id: int) -> Dict[str, Any]:
        auth = self._require_auth(token)
        if auth["status"] != 200:
            return auth
        if not self.auth.check_permission(auth["user"], UserRole.ADMIN):
            return {"error": "Forbidden", "status": 403}
        success = self.users.deactivate(user_id)
        if not success:
            return {"error": "User not found", "status": 404}
        return {"message": "User deactivated", "status": 200}
