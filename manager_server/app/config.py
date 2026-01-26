import os
import sys
from functools import lru_cache
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")


@lru_cache(maxsize=1)
def load_settings() -> dict:
    # In frozen exe, look for config next to exe first; then fallback to bundled
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        config_path_exe = os.path.join(exe_dir, "config", "config.yaml")
        if os.path.exists(config_path_exe):
            config_path = config_path_exe
        else:
            # fallback to bundled config (read-only)
            config_path = os.path.join(getattr(sys, "_MEIPASS", "."), "config", "config.yaml")
    else:
        config_path = CONFIG_PATH
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
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
        routes_file = server.get("routes_file", None)
        if routes_file:
            if getattr(sys, "frozen", False):
                # In exe, look next to exe first
                exe_dir = os.path.dirname(sys.executable)
                candidate = os.path.join(exe_dir, os.path.basename(routes_file))
                self.routes_file = candidate if os.path.exists(candidate) else routes_file
            else:
                self.routes_file = routes_file
        else:
            self.routes_file = None
        # logging
        self.log_dir = server.get("log_dir", "./logs")
        self.log_level = str(server.get("log_level", "INFO")).upper()

        # compute absolute upload directory
        if os.path.isabs(self.save_path):
            self.upload_dir = self.save_path
        else:
            # In frozen exe, base dir is where the exe resides; otherwise use script dir
            base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR
            self.upload_dir = os.path.normpath(os.path.join(base_dir, self.save_path))

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
