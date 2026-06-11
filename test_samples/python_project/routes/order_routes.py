from typing import Any, Dict, List, Tuple

from services.auth import AuthService
from services.order_service import OrderService
from models.product import Product
from utils.formatters import format_order
from utils.validators import validate_page_params


class OrderRouter:
    def __init__(self, order_service: OrderService, auth_service: AuthService):
        self.orders = order_service
        self.auth = auth_service

    def _get_user_id(self, token: str) -> int:
        return self.auth.validate_token(token)

    def create_order(
        self,
        token: str,
        items: List[Tuple[Product, int]],
    ) -> Dict[str, Any]:
        user_id = self._get_user_id(token)
        if not user_id:
            return {"error": "Unauthorized", "status": 401}
        # In a real app, user would be fetched from UserService
        order, error = self.orders.create_order(None, items)
        if not order:
            return {"error": error, "status": 400}
        return {"order": format_order(order), "status": 201}

    def get_order(self, token: str, order_id: int) -> Dict[str, Any]:
        user_id = self._get_user_id(token)
        if not user_id:
            return {"error": "Unauthorized", "status": 401}
        order = self.orders.get_order(order_id)
        if not order:
            return {"error": "Order not found", "status": 404}
        return {"order": format_order(order), "status": 200}

    def my_orders(self, token: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        user_id = self._get_user_id(token)
        if not user_id:
            return {"error": "Unauthorized", "status": 401}
        page, size = validate_page_params(page, size)
        result = self.orders.get_user_orders(user_id, page, size)
        return {
            "orders": [format_order(o) for o in result.items],
            "pagination": result.to_dict(),
            "status": 200,
        }

    def cancel_order(self, token: str, order_id: int) -> Dict[str, Any]:
        user_id = self._get_user_id(token)
        if not user_id:
            return {"error": "Unauthorized", "status": 401}
        success, error = self.orders.cancel_order(order_id, user_id)
        if not success:
            return {"error": error, "status": 400}
        return {"message": "Order cancelled", "status": 200}
