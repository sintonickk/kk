import time
import cv2
import numpy as np
from logger_setup import get_logger
from image_tiling import split_into_tiles

try:
    from ultralytics import YOLO
except Exception:
    YOLO = None


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


def _preprocess(frame, input_size):
    try:
        w, h = int(input_size[0]), int(input_size[1])
        img = cv2.resize(frame, (w, h))
        return img
    except Exception:
        return frame


def inference_service(frame_queue, alarm_queue, stop_event, cfg: dict):
    logger = get_logger("inference")
    inf_cfg = cfg.get("inference", {})
    max_batch = int(inf_cfg.get("max_batch_size", 4))
    window_ms = int(inf_cfg.get("batch_window_ms", 8))
    input_size = inf_cfg.get("input_size", [640, 640])

    # 识别配置
    weights_path = cfg.get("weights_path")
    try:
        conf_threshold = float(cfg.get("conf_threshold", 0.25))
    except Exception:
        conf_threshold = 0.25
    tc = cfg.get("target_classes")
    target_classes = set(tc) if isinstance(tc, (list, set, tuple)) and tc else None
    device = cfg.get("device", "cpu")
    tile_count = int(cfg.get("tile_count", 4))

    # 加载模型
    model = None
    names = {}
    if YOLO is None:
        logger.warning("未安装ultralytics，无法进行识别。运行: pip install ultralytics")
    else:
        if not weights_path:
            logger.error("未配置 weights_path，无法加载模型")
        else:
            try:
                model = YOLO(str(weights_path))
                try:
                    names = model.names if hasattr(model, "names") and isinstance(model.names, dict) else {}
                except Exception:
                    names = {}
                logger.info(f"已加载检测模型: {weights_path}")
            except Exception as e:
                logger.exception(f"加载模型失败: {e}")

    # 每路最小告警间隔，避免刷屏
    last_emit = {}
    emit_interval = 1.5

    while not stop_event.is_set():
        try:
            batch = []
            sources = []
            t0 = time.time()
            while len(batch) < max_batch and (time.time() - t0) * 1000 < window_ms:
                try:
                    src, frame = frame_queue.get(timeout=window_ms / 1000.0)
                    frame_queue.task_done()
                    # 不在此处resize，保持原图给模型或切片
                    batch.append(frame)
                    sources.append((src, frame))
                except Exception:
                    break

            if not batch:
                continue

            now = time.time()
            for (src, frame) in sources:
                # 如果未加载模型，跳过
                if model is None:
                    continue

                matched_payload = None
                try:
                    results_full = model.predict(source=frame, imgsz=640, device=device, verbose=False)
                except Exception:
                    results_full = None
                cls_full = _extract_classification(results_full, names, logger)
                if _is_match(cls_full, conf_threshold, target_classes):
                    alarm_info = {
                        "type": cls_full.get("name"),
                        "class_id": cls_full.get("class_id"),
                        "confidence": round(float(cls_full.get("score", 0.0)), 4),
                        "details": "classification",
                        "source": src,
                        "ts": now,
                        "frame": frame,
                    }
                    matched_payload = alarm_info
                else:
                    tiles_info = split_into_tiles(frame, tile_count, overlap=0.05)
                    for tile, _ in tiles_info:
                        try:
                            results = model.predict(source=tile, imgsz=640, device=device, verbose=False)
                        except Exception:
                            continue
                        classification = _extract_classification(results, names, logger)
                        if not _is_match(classification, conf_threshold, target_classes):
                            continue
                        alarm_info = {
                            "type": classification.get("name"),
                            "class_id": classification.get("class_id"),
                            "confidence": round(float(classification.get("score", 0.0)), 4),
                            "details": "classification",
                            "source": src,
                            "ts": now,
                            "frame": frame,
                        }
                        matched_payload = alarm_info
                        break

                if matched_payload is not None:
                    last = last_emit.get(src, 0.0)
                    if now - last >= emit_interval:
                        try:
                            alarm_queue.put(matched_payload, timeout=0.1)
                            last_emit[src] = now
                        except Exception:
                            pass
        except Exception:
            logger.exception("推理服务异常，继续运行")
            continue

    logger.info("推理服务已停止")
