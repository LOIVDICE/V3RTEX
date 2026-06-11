import os
from dataclasses import dataclass


@dataclass
class Settings:
    db_url: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    allowed_hosts: list = None
    max_upload_size: int = 5_000_000

    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = ["localhost", "127.0.0.1"]


settings = Settings()
