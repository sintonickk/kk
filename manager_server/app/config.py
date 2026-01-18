import os
from functools import lru_cache
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")


@lru_cache(maxsize=1)
def load_settings() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "database" not in data:
        raise KeyError("Missing 'database' section in config.yaml")
    return data


class Settings:
    def __init__(self, data: dict):
        db = data.get("database", {})
        self.db_driver = db.get("driver", "postgresql")
        self.db_host = db["host"]
        self.db_port = db.get("port", 5432)
        self.db_name = db["name"]
        self.db_user = db["user"]
        self.db_password = db["password"]
        self.pool_size = db.get("pool_size", 10)
        self.max_overflow = db.get("max_overflow", 20)
        self.pool_recycle = db.get("pool_recycle", 1800)

        # server section
        server = data.get("server", {})
        self.server_host = server.get("host", "0.0.0.0")
        self.server_port = int(server.get("port", 8001))
        self.device_listen_port = int(server.get("device_listen_port", 9000))
        self.device_refresh_time = int(server.get("device_refresh_time", 180))
        # JWT secret for HS256
        self.jwt_secret = server.get("jwt_secret", "CHANGE_ME_SECRET")
        self.save_path = server.get("save_path", "./uploads")
        # Optional routes file for temporary GPS data source
        self.routes_file = server.get("routes_file", None)

        # compute absolute upload directory
        if os.path.isabs(self.save_path):
            self.upload_dir = self.save_path
        else:
            self.upload_dir = os.path.normpath(os.path.join(BASE_DIR, self.save_path))

    @property
    def sqlalchemy_url(self) -> str:
        # Only PostgreSQL is supported per requirement
        if self.db_driver not in ("postgresql", "postgresql+psycopg2"):
            raise ValueError("Only PostgreSQL is supported. Set driver to 'postgresql' or 'postgresql+psycopg2'.")
        driver = "postgresql+psycopg2"
        return f"{driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(load_settings())
