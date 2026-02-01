import queue
from datetime import datetime
from pathlib import Path
from config_manager import load_config
from image_tiling import split_into_tiles
from logger_setup import get_logger
from gps_ser import get_gps_info

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

# GPS 获取定位信息（从串口读取一次，失败则返回 0.0, 0.0）
def _get_gps_location():
    try:
        info = get_gps_info()
        if info.get("latitude") is None or info.get("longitude") is None:
            get_logger(__name__).warning("未获取到GPS定位信息")
            return 0.0, 0.0
        lon = float(info.get("longitude") or 0.0)
        lat = float(info.get("latitude") or 0.0)
        return lon, lat
    except Exception:
        return 0.0, 0.0

def _is_match(classification, conf_threshold, target_classes):
    try:
        if classification is None:
            return False
        name = classification.get("name")
        score = float(classification.get("score", 0.0))
        if score < float(conf_threshold):
            return False
        if target_classes is not None and name not in target_classes:
            return False
        return True
    except Exception:
        return False

def _extract_classification(results, names, logger):
    classification = None
    try:
        if results and len(results) > 0:
            r = results[0]
            probs = getattr(r, "probs", None)
            if probs is not None:
                try:
                    cls_id = int(getattr(probs, "top1"))
                    score = float(getattr(probs, "top1conf", probs.data.max().item()))
                    logger.debug(f"分类结果：{cls_id} {score}")
                except Exception:
                    import numpy as np
                    arr = getattr(probs, "data", None)
                    if arr is not None:
                        try:
                            idx = int(arr.argmax())
                            val = float(arr.max())
                        except Exception:
                            idx = -1
                            val = 0.0
                    else:
                        idx = -1
                        val = 0.0
                    cls_id, score = idx, val
                label_map = names if isinstance(names, dict) else {}
                name = label_map.get(cls_id, str(cls_id))
                classification = {"name": name, "class_id": cls_id, "score": score}
    except Exception:
        classification = None
    return classification

def frame_analyzer(frame_queue, alarm_queue, stop_event, trigger_threshold=100):
    """
    从帧队列取帧分析，满足条件时生成报警信息放入报警队列
    示例条件：帧的平均亮度超过阈值（可替换为实际业务逻辑）
    """
    try:
        _cfg = load_config()
    except Exception:
        _cfg = {}

    logger = get_logger(__name__)
    model = None
    names = {}
    if YOLO is None:
        logger.warning("未安装ultralytics，无法进行识别。运行: pip install ultralytics")
    else:
        cfg_w = _cfg.get("weights_path") if isinstance(_cfg, dict) else None
        weights = Path(cfg_w).expanduser() if isinstance(cfg_w, str) and cfg_w else None
        if not weights or not weights.exists():
            logger.error("未找到训练权重，请在配置 weights_path 指定有效的 best.pt 路径")
        else:
            try:
                model = YOLO(str(weights))
                try:
                    names = model.names if hasattr(model, "names") and isinstance(model.names, dict) else {}
                except Exception:
                    names = {}
                logger.info(f"已加载检测模型: {weights}")
            except Exception as e:
                logger.exception(f"加载模型失败: {e}")

    try:
        conf_threshold = float(_cfg.get("conf_threshold", 0.25))
    except Exception:
        conf_threshold = 0.25
    tc = _cfg.get("target_classes")
    target_classes = set(tc) if isinstance(tc, (list, set, tuple)) and tc else None
    device = _cfg.get("device", "cpu") if isinstance(_cfg, dict) else "cpu"

    while not stop_event.is_set():
        try:
            frame = frame_queue.get(block=True, timeout=1)
            frame_queue.task_done()

            if model is None:
                # 仅识别逻辑，未加载模型时跳过
                # 可在此打印一次性提示
                logger.warning("未加载检测模型，跳过本帧。")
                continue

            matched_payload = None
            try:
                results_full = model.predict(source=frame, imgsz=640, device=device, verbose=False)
            except Exception:
                results_full = None
            cls_full = _extract_classification(results_full, names, logger)
            longitude, latitude = _get_gps_location()
            if _is_match(cls_full, conf_threshold, target_classes):
                alarm_info = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": cls_full.get("name"),
                    "class_id": cls_full.get("class_id"),
                    "confidence": round(float(cls_full.get("score", 0.0)), 4),
                    "details": "classification",
                    "frame_shape": frame.shape,
                    "saved_path": None,
                    "longitude": longitude,
                    "latitude": latitude,
                }
                payload = alarm_info.copy()
                payload["frame"] = frame
                matched_payload = payload
            else:
                tile_count = _cfg.get("tile_count", 4)
                start_top = _cfg.get("location_top", 0.0)
                start_left = _cfg.get("location_left", 0.0)
                tiles_info = split_into_tiles(frame, tile_count, overlap=0.05, start_top=start_top, start_left=start_left)
                for tile, _ in tiles_info:
                    try:
                        results = model.predict(source=tile, imgsz=640, device=device, verbose=False)
                    except Exception:
                        continue
                    classification = _extract_classification(results, names, logger)
                    if not _is_match(classification, conf_threshold, target_classes):
                        continue
                    alarm_info = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "type": classification.get("name"),
                        "class_id": classification.get("class_id"),
                        "confidence": round(float(classification.get("score", 0.0)), 4),
                        "details": "classification",
                        "frame_shape": frame.shape,
                        "saved_path": None,
                        "longitude": longitude,
                        "latitude": latitude,
                    }
                    payload = alarm_info.copy()
                    payload["frame"] = frame
                    matched_payload = payload
                    break

            if matched_payload is not None:
                try:
                    alarm_queue.put(matched_payload, block=True, timeout=1)
                except queue.Full:
                    pass
        except queue.Empty:
            continue
        except Exception as e:
            logger.exception(f"帧分析出错: {str(e)}")
    
    logger.info("帧分析模块已停止")