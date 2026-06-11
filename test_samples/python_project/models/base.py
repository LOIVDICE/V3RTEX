from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BaseModel:
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def validate(self) -> bool:
        return self.id is not None
