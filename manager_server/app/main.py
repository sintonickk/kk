import os
import logging
from logging.handlers import RotatingFileHandler
import threading
import time
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base, SessionLocal
from .routers import alarms, config, users, routes, devices
from .config import get_settings
from . import crud, schemas

Base.metadata.create_all(bind=engine)


def _setup_logging():
    settings = get_settings()
    log_dir = getattr(settings, "log_dir", "./logs")
    log_level = getattr(settings, "log_level", "INFO")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "manager_server.log")

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(console_handler)
    root.setLevel(getattr(logging, str(log_level).upper(), logging.INFO))


_setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Alarm Service", version="0.1.0")
logger.info("FastAPI application initialized")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alarms.router)
app.include_router(config.router)
app.include_router(users.router)
app.include_router(routes.router)
app.include_router(devices.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def _refresh_devices_loop():
    settings = get_settings()
    interval = max(1, int(getattr(settings, "device_refresh_time", 180)))
    listen_port = int(getattr(settings, "device_listen_port", 9000))
    while True:
        try:
            db = SessionLocal()
            try:
                items = crud.list_devices(db)
                for d in items:
                    ip = getattr(d, "device_ip", None)
                    if not ip:
                        continue
                    url = f"http://{ip}:{listen_port}/api/v1/client/device"
                    try:
                        r = requests.get(url, timeout=5)
                        if r.status_code == 200:
                            body = r.json() or {}
                            dev_cfg = body.get("device_config")
                            dev_info = body.get("device_info")
                            update = schemas.DeviceUpdate(
                                device_config=dev_cfg,
                                device_info=dev_info,
                            )
                            crud.update_device(db, d.device_id, update)
                            logger.debug("Refreshed device info from %s", ip)
                        else:
                            logger.warning("Device %s responded with status %s", ip, r.status_code)
                    except Exception:
                        # ignore failures for individual devices
                        logger.exception("Failed to refresh device info from %s", ip)
            finally:
                db.close()
        except Exception:
            # ignore loop-level failures
            logger.exception("Device refresher loop iteration failed")
        time.sleep(interval)


def _start_background_tasks():
    t = threading.Thread(target=_refresh_devices_loop, name="device-refresher", daemon=True)
    t.start()
    logger.info("Started background task: device-refresher")


# start background tasks on import
_start_background_tasks()
