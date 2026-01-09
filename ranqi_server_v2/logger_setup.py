import logging
from pathlib import Path

def get_logger(name: str):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    out_dir = Path(__file__).resolve().parent / 'outputs'
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(str(out_dir / 'app.log'), encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
