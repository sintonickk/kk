import os
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

app = FastAPI(title="Alarm Service", version="0.1.0")

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
                    except Exception:
                        # ignore failures for individual devices
                        pass
            finally:
                db.close()
        except Exception:
            # ignore loop-level failures
            pass
        time.sleep(interval)


def _start_background_tasks():
    t = threading.Thread(target=_refresh_devices_loop, name="device-refresher", daemon=True)
    t.start()


# start background tasks on import
_start_background_tasks()
