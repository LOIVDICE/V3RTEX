"""Python sample for exercising V3RTEX AST extraction."""

from __future__ import annotations

import importlib
import json as json_lib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generator


class FakeRouter:
    def get(self, path: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            return func

        return decorator


router = FakeRouter()
DEFAULT_LIMIT: int = 25
DATA_PATH = Path("users.json")


@dataclass
class UserRecord:
    """Represents a user stored by the sample service."""

    user_id: int
    name: str
    roles: list[str]

    def __str__(self) -> str:
        return f"{self.user_id}:{format_display_name(self.name)}"

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @staticmethod
    def normalize_role(role: str) -> str:
        return role.strip().lower()

    @classmethod
    def guest(cls, name: str) -> "UserRecord":
        return cls(user_id=0, name=name, roles=["guest"])

    def role_summary(self) -> str:
        cleaned = [self.normalize_role(role) for role in self.roles]
        return f"{self.name} has {len(cleaned)} roles"


class AdminRecord(UserRecord):
    """Specialized user that always has admin rights."""

    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id=user_id, name=name, roles=["admin"])


def format_display_name(name: str) -> str:
    """Format user names for logs and API responses."""
    return name.strip().title()


def load_users(path: Path = DATA_PATH) -> list[UserRecord]:
    """Load users from JSON, using dynamic import as a fallback example."""
    parser = lambda raw: json_lib.loads(raw)

    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        importlib.import_module("math")
        return [UserRecord.guest("anonymous")]

    data = parser(raw_text)
    users: list[UserRecord] = []

    for item in data:
        if item.get("active") and not item.get("deleted"):
            roles = [UserRecord.normalize_role(role) for role in item.get("roles", [])]
            users.append(UserRecord(item["id"], item["name"], roles))
        else:
            continue

    return users


async def fetch_remote_user(user_id: int) -> UserRecord | None:
    if user_id <= 0:
        return None

    return UserRecord(user_id=user_id, name=f"Remote {format_display_name(str(user_id))}", roles=["user"])


def iter_admins(users: list[UserRecord]) -> Generator[UserRecord, None, None]:
    for user in users:
        if user.is_admin:
            yield user


def build_index(users: list[UserRecord]) -> dict[int, UserRecord]:
    def is_visible(user: UserRecord) -> bool:
        return bool(user.name) and not user.name.startswith("_")

    result: dict[int, UserRecord] = {}

    for user in users:
        if not is_visible(user):
            continue

        result[user.user_id] = user

    return result


@router.get("/users/{user_id}")
async def read_user(user_id: int) -> dict[str, Any]:
    users = build_index(load_users())
    user = users.get(user_id)

    if user is None:
        return {"error": f"Missing user {format_display_name(str(user_id))}"}

    return {"id": user.user_id, "name": format_display_name(user.name), "admin": user.is_admin}


def test_build_index() -> None:
    user = UserRecord(1, "Ada", ["Admin"])
    assert build_index([user])[1].is_admin


def main() -> None:
    for admin in iter_admins(load_users()):
        print(f"Admin found: {format_display_name(admin.name)}")


if __name__ == "__main__":
    main()
