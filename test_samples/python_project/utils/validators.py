import re
from typing import Tuple
from constants import PASSWORD_MIN_LENGTH, MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE


EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(email: str) -> Tuple[bool, str]:
    if not email:
        return False, "Email is required"
    if not EMAIL_RE.match(email):
        return False, "Invalid email format"
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain an uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain a digit"
    return True, ""


def validate_page_params(page: int, size: int) -> Tuple[int, int]:
    page = max(1, page)
    size = min(max(1, size), MAX_PAGE_SIZE)
    return page, size
