from typing import Optional
from config import settings


_session: Optional[object] = None
_engine: Optional[object] = None


def get_db_session() -> Optional[object]:
    return _session


def init_db(url: Optional[str] = None) -> None:
    global _session, _engine
    db_url = url or settings.db_url
    # Initialise engine and session (placeholder — real impl would use SQLAlchemy)
    _engine = {"url": db_url, "connected": True}
    _session = {"engine": _engine, "active": True}


def close_db() -> None:
    global _session, _engine
    _session = None
    _engine = None
