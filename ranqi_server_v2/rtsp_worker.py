import os
import time
import cv2
import queue
from collections import deque
from pathlib import Path
from datetime import datetime
from logger_setup import get_logger

def _augment_rtsp_url(url: str) -> str:
    try:
        if not url.startswith("rtsp://"):
            return url
        q = "?" in url
        def add_param(u: str, k: str, v: str) -> str:
            return u if (k+"=") in u else (f"{u}{'&' if q or ('?' in u) else '?'}{k}={v}")
        u = url
        u = add_param(u, "rtsp_transport", "tcp")
        u = add_param(u, "stimeout", "30000000")
        u = add_param(u, "rw_timeout", "30000000")
        u = add_param(u, "max_delay", "5000000")
        u = add_param(u, "fflags", "nobuffer")
        u = add_param(u, "flags", "low_delay")
        return u
    except Exception:
        return url


def rtsp_worker(name: str, rtsp_url: str, frame_queue, stop_event, cfg: dict, record_cmd_queue=None, clip_dir: str | None = None):
    logger = get_logger(f"rtsp.{name}")
    cap = None
    fps_cap = int(cfg.get("fps_cap", 15))
    drop_policy = str(cfg.get("drop_policy", "drop_old")).lower()
    save_frame = bool(cfg.get("save_frame", False))
    save_video = bool(cfg.get("save_video", False))
    rt = cfg.get("record_trigger", {}) if isinstance(cfg, dict) else {}
    try:
        buffer_sec = float(rt.get("record_buffer_sec", 0))
    except Exception:
        buffer_sec = 0.0
    frame_buffer: deque | None = deque() if (save_video and buffer_sec > 0) else None
    writer = None
    recording_end_ts = 0.0
    pending_start = False
    pending_duration = 0.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    robust_url = _augment_rtsp_url(rtsp_url)

    while not stop_event.is_set():
        try:
            if cap is None or not cap.isOpened():
                cap = cv2.VideoCapture(robust_url, cv2.CAP_FFMPEG)
                if not cap or not cap.isOpened():
                    logger.warning("连接失败，5秒后重试...")
                    time.sleep(5)
                    continue
                src_fps = cap.get(cv2.CAP_PROP_FPS) or 25
                interval = max(1, round(src_fps / max(1, fps_cap)))
                logger.info(f"连接成功，源FPS={src_fps:.1f}，抽帧间隔={interval}")
                frame_idx = 0

            ret, frame = cap.read()
            if not ret:
                logger.warning("读取失败，重连...")
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
                time.sleep(1)
                continue

            now_ts = time.time()
            # 维护预录缓冲
            if save_video and buffer_sec > 0 and frame_buffer is not None:
                try:
                    frame_buffer.append((now_ts, frame.copy()))
                    while frame_buffer and (now_ts - frame_buffer[0][0] > buffer_sec):
                        frame_buffer.popleft()
                except Exception:
                    try:
                        if frame_buffer:
                            frame_buffer.popleft()
                    except Exception:
                        pass

            # 处理录像命令
            if record_cmd_queue is not None:
                try:
                    cmd = record_cmd_queue.get_nowait()
                    if isinstance(cmd, dict):
                        c = str(cmd.get("cmd", "")).strip().lower()
                        if c == "start":
                            if save_video:
                                pending_start = True
                                try:
                                    pending_duration = float(cmd.get("duration", 30))
                                except Exception:
                                    pending_duration = 30.0
                            else:
                                logger.info("收到开始录制命令，但 save_video=false，忽略")
                        elif c == "stop":
                            recording_end_ts = 0.0
                    record_cmd_queue.task_done()
                except queue.Empty:
                    pass

            # 启动录像并写入预录
            if pending_start:
                try:
                    out_dir = Path(clip_dir or (Path(__file__).resolve().parent / "outputs" / "clips"))
                    out_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    h, w = frame.shape[:2]
                    rec_fps = float(src_fps) if src_fps and src_fps > 0 else 25.0
                    out_path = out_dir / f"{name}_{ts}.mp4"
                    writer = cv2.VideoWriter(str(out_path), fourcc, rec_fps, (w, h))
                    if writer is None or not writer.isOpened():
                        logger.error(f"启动录制失败: 无法打开 {out_path}")
                        writer = None
                    else:
                        if buffer_sec > 0 and frame_buffer:
                            try:
                                for ts_buf, f_buf in list(frame_buffer):
                                    if (now_ts - ts_buf) <= buffer_sec:
                                        try:
                                            writer.write(f_buf)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                        recording_end_ts = now_ts + float(pending_duration)
                        logger.info(f"开始录制: {out_path} 持续 {pending_duration} 秒")
                except Exception:
                    logger.exception("启动录制异常")
                    writer = None
                    recording_end_ts = 0.0
                finally:
                    pending_start = False

            if frame_idx % interval == 0:
                if save_frame:
                    try:
                        out_dir = Path(__file__).resolve().parent / "outputs" / "save_frames"
                        out_dir.mkdir(parents=True, exist_ok=True)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        cv2.imwrite(str(out_dir / f"{name}_{ts}.jpg"), frame)
                    except Exception:
                        pass
                try:
                    if drop_policy == "drop_old":
                        try:
                            while True:
                                frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                        frame_queue.put_nowait((name, frame))
                    else:
                        frame_queue.put((name, frame), timeout=1)
                except queue.Full:
                    pass

            # 写入录像帧并结束判断
            if writer is not None:
                try:
                    writer.write(frame)
                except Exception:
                    logger.exception("写入录制帧失败")
                if now_ts >= recording_end_ts or stop_event.is_set():
                    try:
                        writer.release()
                    except Exception:
                        pass
                    writer = None
                    recording_end_ts = 0.0
                    logger.info("录制结束")

            frame_idx += 1
            if stop_event.is_set():
                break
        except Exception:
            logger.exception("RTSP工作进程异常，3秒后重试")
            try:
                if cap:
                    cap.release()
            except Exception:
                pass
            cap = None
            time.sleep(3)
            continue

    try:
        if cap:
            cap.release()
    except Exception:
        pass
    logger.info("退出")
