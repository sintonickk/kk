import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_INITIALIZED = False


def get_logger(name: str = "gas_project") -> logging.Logger:
    global _LOGGER_INITIALIZED
    logger = logging.getLogger(name)

    if not _LOGGER_INITIALIZED:
        # 初始化 root logger 并添加文件 handler（仅一次）
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        base_dir = Path(__file__).resolve().parent / "outputs"
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        log_path = base_dir / "app.log"

        file_handler = RotatingFileHandler(str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        _LOGGER_INITIALIZED = True

    # 模块 logger 只设置级别并且让日志向上冒泡到 root
    logger.setLevel(logging.INFO)
    logger.propagate = True
    return logger
