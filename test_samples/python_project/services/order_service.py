from typing import List, Optional, Tuple

from models.order import Order, OrderItem, OrderStatus
from models.product import Product
from models.user import User
from utils.pagination import Paginator, PaginatedResult
from constants import MAX_PAGE_SIZE


class OrderService:
    def __init__(self):
        self._orders: dict = {}
        self._next_id: int = 1

    def create_order(
        self,
        user: User,
        items: List[Tuple[Product, int]],
    ) -> Tuple[Optional[Order], str]:
        if not items:
            return None, "Order must have at least one item"
        for product, qty in items:
            if not product.is_in_stock():
                return None, f"{product.name} is out of stock"
            if product.stock < qty:
                return None, f"Insufficient stock for {product.name}"
        order_items = [
            OrderItem(product=p, quantity=q, unit_price=p.price) for p, q in items
        ]
        order = Order(id=self._next_id, user=user, items=order_items)
        self._orders[self._next_id] = order
        self._next_id += 1
        for product, qty in items:
            product.stock -= qty
        return order, ""

    def get_order(self, order_id: int) -> Optional[Order]:
        return self._orders.get(order_id)

    def get_user_orders(self, user_id: int, page: int = 1, size: int = 20) -> PaginatedResult:
        p = Paginator(page=page, size=size)
        user_orders = [o for o in self._orders.values() if o.user and o.user.id == user_id]
        return p.paginate(user_orders[p.offset : p.offset + p.size], len(user_orders))

    def cancel_order(self, order_id: int, user_id: int) -> Tuple[bool, str]:
        order = self.get_order(order_id)
        if not order:
            return False, "Order not found"
        if not order.user or order.user.id != user_id:
            return False, "Unauthorized"
        if order.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            return False, "Cannot cancel a shipped or delivered order"
        order.cancel()
        return True, ""

    def confirm_order(self, order_id: int) -> Tuple[bool, str]:
        order = self.get_order(order_id)
        if not order:
            return False, "Order not found"
        order.confirm()
        return True, ""

    def ship_order(self, order_id: int) -> Tuple[bool, str]:
        order = self.get_order(order_id)
        if not order:
            return False, "Order not found"
        order.ship()
        return True, ""
