import sys
import time
import signal
from pathlib import Path
from multiprocessing import Process, Queue, Event, set_start_method

from config_manager import load_config
from logger_setup import get_logger
from rtsp_worker import rtsp_worker
from inference_service import inference_service
from alarm_handler import alarm_handler


def merge_cfg(global_cfg: dict, stream_cfg: dict) -> dict:
    cfg = dict(global_cfg)
    # shallow merge for top-level only; nested like record_trigger remains from global unless overridden entirely
    for k, v in stream_cfg.items():
        if k in ("name", "rtsp_url"):
            continue
        cfg[k] = v
    return cfg


def main():
    try:
        set_start_method('spawn')
    except RuntimeError:
        pass

    base_dir = Path(__file__).resolve().parent
    outputs = base_dir / 'outputs'
    outputs.mkdir(parents=True, exist_ok=True)

    logger = get_logger('main')
    cfg_all = load_config()
    global_cfg = cfg_all.get('global', {})
    streams = cfg_all.get('streams', [])

    if not streams:
        logger.error('streams 配置为空')
        return 1

    queue_size = int(global_cfg.get('queue_size', 4))

    # Shared queues/events
    frame_queue = Queue(maxsize=queue_size)
    alarm_queue = Queue(maxsize=queue_size * 4)
    stop_event = Event()

    # Per-source record command queues
    record_cmd_queues_by_src = {}

    procs: list[Process] = []

    # Start RTSP workers
    for s in streams:
        name = str(s.get('name') or s.get('rtsp_url') or f'cam{len(record_cmd_queues_by_src)+1}')
        url = s.get('rtsp_url')
        if not url:
            logger.warning(f'stream 缺少 rtsp_url: {s}')
            continue
        per_cfg = merge_cfg(global_cfg, s)
        rec_q = Queue(maxsize=2)
        record_cmd_queues_by_src[name] = rec_q
        p = Process(target=rtsp_worker, args=(name, url, frame_queue, stop_event, per_cfg), kwargs={
            'record_cmd_queue': rec_q,
            'clip_dir': str(outputs / 'clips')
        })
        p.daemon = True
        p.start()
        procs.append(p)
        logger.info(f'Started RTSP worker: {name}')

    # Start inference service
    p_inf = Process(target=inference_service, args=(frame_queue, alarm_queue, stop_event, global_cfg))
    p_inf.daemon = True
    p_inf.start()
    procs.append(p_inf)
    logger.info('Started inference service')

    # Start alarm handler
    p_alarm = Process(target=alarm_handler, args=(alarm_queue, stop_event), kwargs={
        'cfg': global_cfg,
        'record_cmd_queues_by_src': record_cmd_queues_by_src
    })
    p_alarm.daemon = True
    p_alarm.start()
    procs.append(p_alarm)
    logger.info('Started alarm handler')

    def shutdown(*_):
        logger.info('Shutting down...')
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        while any(p.is_alive() for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()
    finally:
        for p in procs:
            p.join(timeout=5)
        logger.info('Exited cleanly')
    return 0


if __name__ == '__main__':
    sys.exit(main())
