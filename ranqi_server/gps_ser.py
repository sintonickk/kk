import serial
import time
import pynmea2
from typing import Optional
from config_manager import load_config
from logger_setup import get_logger

_logger = get_logger(__name__)
_ser: Optional[serial.Serial] = None


def start_gps() -> bool:
    """程序启动时调用：打开全局串口句柄。重复调用会复用已打开句柄。"""
    global _ser
    if _ser and getattr(_ser, "is_open", False):
        return True
    try:
        cfg = load_config()
        port = cfg.get("gps_port", "/dev/ttyUSB2") if isinstance(cfg, dict) else "/dev/ttyUSB2"
        baud = int(cfg.get("gps_baudrate", 115200)) if isinstance(cfg, dict) else 115200
        timeout = float(cfg.get("gps_timeout", 0.5)) if isinstance(cfg, dict) else 0.5
        _ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        if _ser.is_open:
            _logger.info("GPS 串口已打开: port=%s baud=%s timeout=%s", port, baud, timeout)
            return True
        _logger.warning("GPS 串口打开失败: port=%s", port)
        return False
    except Exception as e:
        _logger.warning("GPS 串口启动失败: %s", e)
        _ser = None
        return False


def stop_gps() -> None:
    """程序退出时调用：关闭全局串口句柄。"""
    global _ser
    try:
        if _ser and getattr(_ser, "is_open", False):
            _ser.close()
            _logger.info("GPS 串口已关闭")
    except Exception:
        pass
    finally:
        _ser = None


def get_gps_info(max_reads: int = 100) -> dict:
    """
    使用全局句柄读取一次定位，返回字典：
      { "latitude": float|None, "longitude": float|None, "gps_qual": int }
    若未启动或读取失败，返回默认值（lat/long=None,gps_qual=0）。
    """
    info = {"latitude": None, "longitude": None, "gps_qual": 0}
    ser = _ser
    if not ser or not getattr(ser, "is_open", False):
        _logger.warning("GPS 串口未启动，返回默认定位信息")
        return info

    for _ in range(int(max_reads)):
        try:
            if ser.in_waiting > 0:
                nmea_string = ser.readline().decode("utf-8", errors="ignore").rstrip()
                if "$GPGGA" in nmea_string:
                    try:
                        msg = pynmea2.parse(nmea_string)
                        info["latitude"] = msg.latitude
                        info["longitude"] = msg.longitude
                        info["gps_qual"] = int(getattr(msg, "gps_qual", 0) or 0)
                        if info["gps_qual"] == 1:
                            return info
                    except Exception:
                        pass
            time.sleep(0.01)
        except Exception:
            time.sleep(0.05)
    return info