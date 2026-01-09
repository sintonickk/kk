import os
import json
import time
import threading
import signal
from datetime import datetime
from typing import Any, Dict, List

import cv2


class GracefulKiller:
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        # SIGTERM may not be available on some Windows setups, but try to register
        try:
            signal.signal(signal.SIGTERM, self.exit_gracefully)
        except Exception:
            pass

    def exit_gracefully(self, *args):
        self.kill_now = True


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def timestamp_ms() -> int:
    return int(time.time() * 1000)


def format_filename(pattern: str, stream_index: int, ext: str) -> str:
    now = datetime.now()
    # Provide common tokens
    tokens = {
        "stream_index": stream_index,
        "timestamp_ms": timestamp_ms(),
        "date": now.strftime("%Y%m%d"),
        "time": now.strftime("%H%M%S"),
        "datetime": now.strftime("%Y%m%d_%H%M%S"),
    }
    try:
        base = pattern.format(**tokens)
    except Exception:
        base = f"{stream_index}_{tokens['timestamp_ms']}"
    if not base.lower().endswith(f".{ext.lower()}"):
        base = f"{base}.{ext}"
    return base


def read_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Basic validation: prefer new 'rtsp' list; fallback to legacy 'streams'
    if "rtsp" in cfg:
        if not isinstance(cfg["rtsp"], list) or len(cfg["rtsp"]) == 0:
            raise ValueError("config.json 'rtsp' must be a non-empty list of RTSP URLs")
    elif "streams" in cfg:
        streams = cfg.get("streams")
        if not isinstance(streams, list) or len(streams) == 0:
            raise ValueError("config.json 'streams' must be a non-empty list")
        # derive a list of urls for backward compatibility
        urls = []
        for s in streams:
            if isinstance(s, dict) and s.get("url"):
                urls.append(s["url"])
        if not urls:
            raise ValueError("config.json legacy 'streams' contains no valid 'url'")
        cfg["rtsp"] = urls
    else:
        raise ValueError("config.json must contain 'rtsp' (list of RTSP URLs)")
    return cfg


def capture_worker(stream_index: int, url: str, global_cfg: Dict[str, Any], killer: GracefulKiller):
    fps = float(global_cfg.get("fps", 1))
    output_dir = global_cfg.get("output_dir")
    output_format = (global_cfg.get("output_format") or "jpg").lower()
    filename_pattern = global_cfg.get("filename_pattern") or "{stream_index}_{timestamp_ms}.jpg"
    reconnect_interval = int(global_cfg.get("reconnect_interval_sec", 5))
    max_retries = int(global_cfg.get("max_retries", 0))  # 0 for infinite

    if not url:
        print(f"[Stream {stream_index}] Missing URL; skipping")
        return
    if not output_dir:
        print(f"[Stream {stream_index}] Missing global 'output_dir' in config; skipping")
        return
    if fps <= 0:
        print(f"[Stream {stream_index}] Invalid fps={fps}; must be > 0; skipping")
        return

    ensure_dir(output_dir)
    interval = 1.0 / fps

    retries = 0
    while not killer.kill_now:
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            print(f"[Stream {stream_index}] Unable to open stream. Retrying in {reconnect_interval}s...")
            cap.release()
            retries += 1
            if max_retries and retries > max_retries:
                print(f"[Stream {stream_index}] Exceeded max_retries={max_retries}. Stopping.")
                break
            time.sleep(reconnect_interval)
            continue

        print(f"[Stream {stream_index}] Connected. Sampling {fps} fps -> {output_dir}")
        last_saved = 0.0
        while not killer.kill_now:
            ok, frame = cap.read()
            if not ok or frame is None:
                print(f"[Stream {stream_index}] Frame read failed. Reconnecting in {reconnect_interval}s...")
                cap.release()
                time.sleep(reconnect_interval)
                break  # break inner loop to reconnect

            now = time.time()
            if (now - last_saved) >= interval:
                filename = format_filename(filename_pattern, stream_index, output_format)
                save_path = os.path.join(output_dir, filename)
                try:
                    success = cv2.imwrite(save_path, frame)
                    if not success:
                        print(f"[Stream {stream_index}] Failed to write frame to {save_path}")
                    else:
                        last_saved = now
                except Exception as e:
                    print(f"[Stream {stream_index}] Error saving frame: {e}")

            time.sleep(0.001)

        if killer.kill_now:
            break
        retries += 1
        if max_retries and retries > max_retries:
            print(f"[Stream {stream_index}] Exceeded max_retries={max_retries}. Stopping.")
            break

    print(f"[Stream {stream_index}] Exiting.")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    cfg = read_config(config_path)

    killer = GracefulKiller()

    global_cfg = {
        "fps": cfg.get("fps", 1),
        "output_dir": cfg.get("output_dir"),
        "output_format": cfg.get("output_format", "jpg"),
        "filename_pattern": cfg.get("filename_pattern", "{stream_index}_{timestamp_ms}.jpg"),
        "reconnect_interval_sec": cfg.get("reconnect_interval_sec", 5),
        "max_retries": cfg.get("max_retries", 0),
    }

    threads: List[threading.Thread] = []
    rtsp_list: List[str] = cfg.get("rtsp", [])
    for idx, url in enumerate(rtsp_list):
        t = threading.Thread(target=capture_worker, args=(idx, url, global_cfg, killer), daemon=True)
        t.start()
        threads.append(t)

    print(f"Started {len(threads)} stream worker(s). Press Ctrl+C to stop.")

    try:
        while not killer.kill_now:
            time.sleep(0.5)
    finally:
        print("Stopping workers...")
        for t in threads:
            t.join(timeout=2.0)
        print("All workers stopped.")


if __name__ == "__main__":
    main()
