import time
import queue
import json
from pathlib import Path
from datetime import datetime
import cv2
from logger_setup import get_logger
from concurrent.futures import ThreadPoolExecutor
from upload_detection import upload_numpy_image


def alarm_handler(alarm_queue, stop_event, record_cmd_queue=None, cfg: dict | None = None, record_cmd_queues_by_src: dict | None = None):
    logger = get_logger("alarm")
    executor = ThreadPoolExecutor(max_workers=3)
    cfg = cfg or {}
    rt = cfg.get("record_trigger", {}) if isinstance(cfg, dict) else {}
    try:
        required_hits = int(rt.get("required_hits", 1))
    except Exception:
        required_hits = 1
    try:
        cooldown = float(rt.get("duration_sec", rt.get("cooldown_sec", 60)))
    except Exception:
        cooldown = 60.0
    duration = cooldown

    save_pic = bool(cfg.get("save_pic", True))
    save_video = bool(cfg.get("save_video", False))

    last_trigger_ts = 0.0
    hit_streak = {}

    out_dir = Path(__file__).resolve().parent / "outputs" / "alarm_frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(__file__).resolve().parent / "outputs" / "alarm_log.jsonl"

    while not stop_event.is_set():
        try:
            info = alarm_queue.get(timeout=1)
            alarm_queue.task_done()

            src = str(info.get("source", ""))
            hit_streak[src] = hit_streak.get(src, 0) + 1

            # 日志
            obj = dict(info)
            obj.pop("frame", None)
            with open(str(log_path), "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            logger.info(f"alarm: {obj}")

            if save_pic and isinstance(info.get("frame", None), (type(None),)) is False:
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    cv2.imwrite(str(out_dir / f"{src}_{ts}.jpg"), info.get("frame"))
                except Exception:
                    pass

            # 异步上传报警图片到后端
            try:
                executor.submit(upload_numpy_image, info.get("frame"), obj.get("type", "未知"))
            except Exception:
                pass

            now = time.time()
            if hit_streak[src] >= required_hits and (now - last_trigger_ts) >= cooldown:
                if save_video:
                    try:
                        if record_cmd_queues_by_src and src in record_cmd_queues_by_src:
                            record_cmd_queues_by_src[src].put({"cmd": "start", "duration": duration}, block=False)
                        elif record_cmd_queue is not None:
                            record_cmd_queue.put({"cmd": "start", "duration": duration}, block=False)
                        last_trigger_ts = now
                        hit_streak[src] = 0
                    except Exception:
                        pass
        except queue.Empty:
            continue
        except Exception:
            logger.exception("报警处理异常")
            continue

    logger.info("报警处理停止")
