"""
type_annotations.py

Pure helpers for reading Python type annotations off node metadata.

Used by the call resolver to:
  - type a function's own parameters, so method calls on them resolve
    (e.g. ``def f(card: Card)`` makes ``card.matches_value()`` resolvable)
  - propagate a callee's return type onto the variable that stores its
    result (e.g. ``gs = get_game(id)`` where ``get_game -> GameState``).

Every function takes plain strings and returns plain data — no engine
state — so the logic is unit-testable in isolation.
"""
from typing import Dict, List, Optional

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = set(_OPENERS.values())


def split_top_level(text: str, sep: str = ",") -> List[str]:
    """
    Split ``text`` on ``sep``, ignoring separators nested inside (), [] or {}.

    ``"a, Dict[str, int], b"`` -> ``["a", " Dict[str, int]", " b"]``
    """
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    for ch in text:
        if ch in _OPENERS:
            depth += 1
            buf.append(ch)
        elif ch in _CLOSERS:
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def parse_param_types(parameters: str) -> Dict[str, str]:
    """
    Parse a parameter signature string into ``{param_name: annotation}``.

    Handles the extractor's raw form, which keeps the surrounding
    parentheses and may span lines::

        "(card: Card, tatami: Card, active: Optional[str] = None)"
          -> {"card": "Card", "tatami": "Card", "active": "Optional[str]"}

    Bracketed annotations (``Dict[str, int]``) are kept intact;
    ``self`` / ``cls`` and unannotated params are dropped.
    """
    if not parameters:
        return {}
    inner = parameters.strip()
    if inner.startswith("("):
        inner = inner[1:]
    if inner.endswith(")"):
        inner = inner[:-1]

    result: Dict[str, str] = {}
    for part in split_top_level(inner, ","):
        part = part.strip().lstrip("*").strip()
        if not part or ":" not in part:
            continue
        name, ann = part.split(":", 1)
        name = name.strip()
        ann = ann.split("=", 1)[0].strip()      # drop default value
        if name and name not in ("self", "cls") and ann:
            result[name] = ann
    return result


def core_type_name(annotation: Optional[str]) -> Optional[str]:
    """
    Reduce a type annotation to a single concrete class name, or ``None``
    when it does not denote exactly one instance.

        "GameState"            -> "GameState"
        "Optional[GameState]"  -> "GameState"
        "GameState | None"     -> "GameState"
        "List[Card]"           -> None   (a container, not one instance)
        "Dict[str, Card]"      -> None
        "models.GameState"     -> None   (dotted — caller looks up bare names)
    """
    if not annotation:
        return None
    ann = annotation.strip()

    # "X | None" / "X | Y" union → keep only when a single non-None member
    if "|" in ann:
        members = [p.strip() for p in split_top_level(ann, "|")]
        members = [m for m in members if m and m not in ("None", "none")]
        if len(members) != 1:
            return None
        ann = members[0]

    # Optional[X] → X
    if ann.startswith("Optional[") and ann.endswith("]"):
        ann = ann[len("Optional["):-1].strip()

    # Any remaining subscript/comma is a container → not a single class
    if "[" in ann or "]" in ann or "," in ann:
        return None
    return ann if ann.isidentifier() else None
