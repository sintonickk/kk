import cv2
import time
import queue
import os
from datetime import datetime
from logger_setup import get_logger
from collections import deque
from config_manager import load_config

def rtsp_processor(rtsp_url, frame_queue, stop_event, fps=2, resize_size=(640, 640),
                   record_cmd_queue=None, clip_dir="outputs/clips", clip_duration_sec=60):
    """
    读取RTSP流：
    - 抽帧：按 original_fps / fps 的间隔将帧放入 frame_queue
    - 录制：使用 RTSP 原始帧率 original_fps 持续录制到本地
    """
    logger = get_logger(__name__)
    cap = None
    writer = None
    recording_end_ts = 0.0
    pending_start = False
    pending_duration = float(clip_duration_sec)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    try:
        _cfg = load_config()
    except Exception:
        _cfg = {}
    _rt = _cfg.get("record_trigger", {}) if isinstance(_cfg, dict) else {}
    try:
        _save_video = bool(_cfg.get("save_video", False))
    except Exception:
        _save_video = False
    try:
        _buffer_sec = float(_rt.get("record_buffer_sec", 0))
    except Exception:
        _buffer_sec = 0.0
    _frame_buffer = deque() if (_save_video and _buffer_sec > 0) else None
    if not _save_video:
        logger.info("save_video=false，不会保存视频（不维护预录缓冲，忽略开始录制命令）")

    def _ensure_rtsp_tcp(url: str) -> str:
        try:
            if url.startswith("rtsp://") and "rtsp_transport=" not in url:
                sep = "&" if "?" in url else "?"
                return f"{url}{sep}rtsp_transport=tcp"
        except Exception:
            pass
        return url

    def _augment_rtsp_url(url: str) -> str:
        """为 RTSP URL 补充常用的 FFmpeg 可靠性参数（若未显式设置）。"""
        try:
            if not url.startswith("rtsp://"):
                return url
            q = "?" in url
            def add_param(u: str, k: str, v: str) -> str:
                return u if (k+"=") in u else (f"{u}{'&' if q or ('?' in u) else '?'}{k}={v}")
            u = url
            u = add_param(u, "rtsp_transport", "tcp")
            u = add_param(u, "stimeout", "30000000")  # 增加到30秒
            u = add_param(u, "rw_timeout", "30000000")  # 读写超时
            u = add_param(u, "max_delay", "5000000")    # 最大延迟5秒
            u = add_param(u, "fflags", "nobuffer")      # 减少缓冲
            u = add_param(u, "flags", "low_delay")      # 低延迟模式
            return u
        except Exception:
            return url

    def _setup_ffmpeg_env():
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            "rtsp_transport;tcp|stimeout;30000000|rw_timeout;30000000"
        )

    def _open_capture(url: str):
        try:
            c = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        except Exception:
            c = None
        if c is not None and c.isOpened():
            try:
                if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                    c.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            except Exception:
                pass
            return c
        if c is not None:
            try:
                c.release()
            except Exception:
                pass
        return None

    def _buffer_push(frame_buffer: deque, buffer_sec: float, now_ts: float, frame):
        if frame_buffer is None or buffer_sec <= 0:
            return
        try:
            frame_buffer.append((now_ts, frame.copy()))
            while frame_buffer and (now_ts - frame_buffer[0][0] > buffer_sec):
                frame_buffer.popleft()
        except Exception:
            if frame_buffer:
                frame_buffer.popleft()

    def _start_recording_and_preroll(out_dir: str, now_ts: float, frame_shape, original_fps: float,
                                     writer_fourcc, preroll: deque, buffer_sec: float):
        h, w = frame_shape[:2]
        try:
            rec_fps = float(original_fps)
            if rec_fps <= 0:
                rec_fps = 25.0
        except Exception:
            rec_fps = 25.0
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(out_dir, f"clip_{ts}.mp4")
        _writer = cv2.VideoWriter(out_path, writer_fourcc, rec_fps, (w, h))
        if _writer is None or not _writer.isOpened():
            return None, out_path
        if buffer_sec > 0 and preroll:
            try:
                for ts_buf, f_buf in list(preroll):
                    if (now_ts - ts_buf) <= buffer_sec:
                        try:
                            _writer.write(f_buf)
                        except Exception:
                            pass
            except Exception:
                pass
        return _writer, out_path

    while not stop_event.is_set():
        # 初始化或重连RTSP流
        if not cap or not cap.isOpened():
            # _setup_ffmpeg_env()
            robust_url = _augment_rtsp_url(rtsp_url)
            cap = _open_capture(robust_url)
            # cap = _open_capture(rtsp_url)
            used_mode = "ffmpeg_tcp"
            if not cap or not cap.isOpened():
                logger.warning(f"无法连接RTSP流: {rtsp_url}，10秒后重试（已尝试 FFmpeg+TCP 及默认）...")
                time.sleep(10)
                continue
            # 获取原帧率（用于计算抽帧间隔）
            original_fps = cap.get(cv2.CAP_PROP_FPS) or 25  # 默认为25FPS
            frame_interval = max(1, round(original_fps / fps))
            logger.info(f"RTSP流连接成功（mode={used_mode}），原帧率: {original_fps:.1f}FPS，抽帧间隔: {frame_interval}帧")
            frame_count = 0  # 重置帧计数器
        
        if record_cmd_queue is not None:
            try:
                cmd = record_cmd_queue.get_nowait()
                if isinstance(cmd, dict):
                    try:
                        c = str(cmd.get("cmd", "")).strip().lower()
                    except Exception:
                        c = ""
                    if c == "start":
                        if _save_video:
                            pending_start = True
                        else:
                            logger.info("收到开始录制命令，但 save_video=false，已忽略")
                        try:
                            pending_duration = float(cmd.get("duration", clip_duration_sec))
                        except Exception:
                            pending_duration = float(clip_duration_sec)
                    elif c == "stop":
                        recording_end_ts = 0.0
                else:
                    # 忽略非字典命令
                    pass
                record_cmd_queue.task_done()
            except queue.Empty:
                pass

        # 读取帧
        ret, frame = cap.read()
        if not ret:
            logger.warning("读取帧失败，尝试重连...")
            cap.release()
            cap = None
            time.sleep(1)
            continue
        
        now = time.time()
        if _save_video and _buffer_sec > 0:
            _buffer_push(_frame_buffer, _buffer_sec, now, frame)

        if pending_start:
            try:
                os.makedirs(clip_dir, exist_ok=True)
                writer, out_path = _start_recording_and_preroll(
                    clip_dir, now, frame.shape, original_fps, fourcc, _frame_buffer, _buffer_sec
                )
                if writer is None or not writer.isOpened():
                    logger.error(f"启动录制失败: 无法打开输出文件 {out_path}")
                    writer = None
                else:
                    recording_end_ts = now + float(pending_duration)
                    logger.info(f"开始录制: {out_path}，预计持续 {pending_duration} 秒")
            except Exception as e:
                logger.exception(f"启动录制异常: {e}")
                writer = None
                recording_end_ts = 0.0
            finally:
                pending_start = False

        if writer is not None:
            try:
                writer.write(frame)
            except Exception as e:
                logger.exception(f"写入录制帧失败: {e}")
            if now >= recording_end_ts or stop_event.is_set():
                try:
                    writer.release()
                except Exception:
                    pass
                writer = None
                recording_end_ts = 0.0
                logger.info("录制结束")

        # 按间隔抽帧
        if frame_count % frame_interval == 0:
            # 放入队列（队列满时丢弃）
            try:
                frame_queue.put(frame, block=True, timeout=1)
                logger.debug(f"帧放入队列，当前队列大小: {frame_queue.qsize()}")
            except queue.Full:
                logger.warning("帧队列已满，丢弃当前帧")
        
        frame_count += 1
        # 检查退出信号（避免阻塞在read()时无法退出）
        if stop_event.is_set():
            break
    
    # 释放资源
    if cap:
        cap.release()
    if writer is not None:
        try:
            writer.release()
        except Exception:
            pass
    logger.info("RTSP流处理模块已停止")