from typing import Any, Dict
from models.user import User
from models.product import Product
from models.order import Order


def format_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def format_product(product: Product) -> Dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "stock": product.stock,
        "category": product.category.value,
        "in_stock": product.is_in_stock(),
        "sku": product.sku,
    }


def format_order(order: Order) -> Dict[str, Any]:
    return {
        "id": order.id,
        "user_id": order.user.id if order.user else None,
        "status": order.status.value,
        "total": order.total_amount(),
        "item_count": order.item_count(),
        "items": [
            {"product_id": i.product.id, "quantity": i.quantity, "subtotal": i.subtotal}
            for i in order.items
        ],
    }
