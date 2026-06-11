from dataclasses import dataclass
from enum import Enum
from typing import Optional
from .base import BaseModel


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


@dataclass
class User(BaseModel):
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    role: UserRole = UserRole.USER
    is_active: bool = True

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def deactivate(self) -> None:
        self.is_active = False

    def promote(self) -> None:
        self.role = UserRole.ADMIN
