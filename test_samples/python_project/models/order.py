from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from .base import BaseModel
from .user import User
from .product import Product


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class OrderItem:
    product: Product
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.quantity, 2)


@dataclass
class Order(BaseModel):
    user: Optional[User] = None
    items: List[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = None

    def total_amount(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)

    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    def cancel(self) -> None:
        if self.status not in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            self.status = OrderStatus.CANCELLED

    def confirm(self) -> None:
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.CONFIRMED

    def ship(self) -> None:
        if self.status == OrderStatus.CONFIRMED:
            self.status = OrderStatus.SHIPPED
