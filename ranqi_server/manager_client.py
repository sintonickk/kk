import requests
import cv2
from datetime import datetime
from typing import Optional, Dict, Any

from config_manager import load_config
from system_info import get_system_info
import json
from pathlib import Path
from net_utils import get_local_ip
import uuid

# Lightweight REST listener to update local config
try:
    from fastapi import FastAPI, HTTPException
    import uvicorn
except Exception:
    FastAPI = None  # type: ignore
    uvicorn = None  # type: ignore


def get_manager_base_url(default: str = "http://127.0.0.1:8000") -> str:
    try:
        cfg = load_config()
        if isinstance(cfg, dict):
            return str(cfg.get("manager_base_url", default))
    except Exception:
        pass
    return default


def _normalize_alarm_time(ts_val: Optional[str]) -> str:
    # Accept timestamp with space or ISO8601; normalize to ISO8601
    ts = str(ts_val or datetime.now().isoformat())
    return ts.replace(" ", "T")


def send_alarm(
    alarm_info: Dict[str, Any],
    frame,
    device_ip: str,
    base_url: str,
    timeout: int = 10,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    try:
        url = f"{base_url.rstrip('/')}/api/v1/alarms"
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            return
        img_bytes = bytes(buf)

        alarm_time = _normalize_alarm_time(alarm_info.get("timestamp"))
        longitude = float(alarm_info.get("longitude", 0.0))
        latitude = float(alarm_info.get("latitude", 0.0))
        alarm_type = str(alarm_info.get("type", ""))
        confidence = alarm_info.get("confidence")

        data = {
            "alarm_time": alarm_time,
            "longitude": str(longitude),
            "latitude": str(latitude),
            "alarm_type": alarm_type,
            "device_ip": device_ip,
        }
        if confidence is not None:
            data["confidence"] = str(confidence)

        files = {"image": ("frame.jpg", img_bytes, "image/jpeg")}
        requests.post(url, data=data, files=files, headers=headers or {}, timeout=timeout)
    except Exception:
        # Do not raise to avoid breaking caller loops
        pass


def _get_local_mac() -> str:
    """Return local MAC address in standard AA:BB:CC:DD:EE:FF format."""
    try:
        node = uuid.getnode()
        mac = ":".join([f"{(node >> ele) & 0xff:02X}" for ele in range(40, -1, -8)])
        return mac
    except Exception:
        return ""


def update_device_by_code(base_url: str, timeout: int = 5, headers: Optional[Dict[str, str]] = None) -> bool:
    """Update device info on manager_server using device_code = local MAC.
    Returns True if request sent successfully (HTTP 200/201/204), else False.
    """
    try:
        device_code = _get_local_mac()
        if not device_code:
            return False
        url = f"{base_url.rstrip('/')}/api/v1/devices/by-code/{device_code}"
        device_ip = get_local_ip()
        cfg = {}
        info = {}
        try:
            cfg = load_config() or {}
        except Exception:
            cfg = {}
        try:
            info = get_system_info() or {}
        except Exception:
            info = {}
        body = {
            "device_ip": device_ip,
            "device_config": cfg,
            "device_info": info,
            "status": "online",
        }
        resp = requests.put(url, json=body, headers=headers or {}, timeout=timeout)
        return resp.status_code in (200, 201, 204)
    except Exception:
        return False


def update_device_by_code_startup(default_base: str = "http://127.0.0.1:8001") -> None:
    """Convenience wrapper to update device info on startup.
    base_url is resolved from config (manager_base_url) with fallback to default_base.
    """
    base_url = get_manager_base_url(default=default_base)
    # 如果没有成功就一直重试
    while True:
        ret = update_device_by_code(base_url)
        if ret:
            break
        logger.warning("Failed to update device info on startup: base_url=%s", base_url)
        time.sleep(1)


# ---------------- RESTful Config Listener ----------------
_app: Optional["FastAPI"] = None


def _get_config_file_path(filename: str = "config.json") -> Path:
    try:
        from config_manager import get_config_path
        return get_config_path(filename)
    except Exception:
        # fallback to ./config/config.json next to this file
        return Path(__file__).resolve().parent / "config" / filename


def _save_config_to_file(data: Dict[str, Any], filename: str = "config.json") -> Path:
    path = _get_config_file_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _deep_merge_dicts(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge incoming into base. For dict values, recurse; for lists/scalars, override.
    This mutates and returns base.
    """
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge_dicts(base[k], v)  # type: ignore[index]
        else:
            base[k] = v
    return base


def get_app() -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Please install fastapi and uvicorn.")
    global _app
    if _app is None:
        _app = FastAPI(title="Ranqi Manager Client", version="0.1.0")

        @_app.get("/health")
        def health():
            return {"status": "ok"}

        @_app.get("/api/v1/client/config")
        def get_config():
            try:
                cfg = load_config()
                return cfg
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @_app.put("/api/v1/client/config")
        def update_config(body: Dict[str, Any]):
            try:
                # load current config and do a shallow update
                current = {}
                try:
                    current = load_config()
                except Exception:
                    current = {}
                if not isinstance(body, dict):
                    raise HTTPException(status_code=400, detail="Body must be a JSON object")
                # deep merge nested dicts; lists/scalars overwrite
                current = _deep_merge_dicts(current, body)
                path = _save_config_to_file(current)
                return {"updated": True, "path": str(path)}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @_app.get("/api/v1/client/device")
        def get_device():
            try:
                cfg = load_config()
                info = get_system_info()
                device_ip = get_local_ip()
                return {
                    "device_ip": device_ip,
                    "device_config": cfg,
                    "device_info": info,
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    return _app


def run_config_listener(host: str = "0.0.0.0", port: int = 9000, log_level: str = "info") -> None:
    if uvicorn is None or FastAPI is None:
        raise RuntimeError("FastAPI/uvicorn not installed. Install with: pip install fastapi uvicorn")
    app = get_app()
    uvicorn.run(app, host=host, port=port, log_level=log_level)
