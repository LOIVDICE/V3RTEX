from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .base import BaseModel


class Category(Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    OTHER = "other"


@dataclass
class Product(BaseModel):
    name: str = ""
    price: float = 0.0
    stock: int = 0
    category: Category = Category.OTHER
    description: Optional[str] = None
    sku: Optional[str] = None

    def is_in_stock(self) -> bool:
        return self.stock > 0

    def apply_discount(self, percent: float) -> float:
        return round(self.price * (1 - percent / 100), 2)

    def restock(self, quantity: int) -> None:
        self.stock += quantity
