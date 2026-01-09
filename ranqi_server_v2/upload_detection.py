import requests
import base64
import cv2
import numpy as np
from config_manager import load_config
import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

_CFG = load_config()
_BASE_URL = _CFG.get("backend_base_url", "http://127.0.0.1:5000").rstrip("/")
BACKEND_UPLOAD_URL = f"{_BASE_URL}/api/upload"

def upload_numpy_image(numpy_image, category="未知", location="未知位置"):
    try:
        if numpy_image is None:
            raise ValueError("空图像")
        if numpy_image.dtype != np.uint8:
            numpy_image = numpy_image.astype(np.uint8)
        success, buffer = cv2.imencode('.jpg', numpy_image)
        if not success:
            raise ValueError("图像编码失败")
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        payload = {
            "image_base64": image_base64,
            "category": category,
            "location": location
        }
        response = requests.post(BACKEND_UPLOAD_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('success'):
            logger.debug(f"检测结果上传成功，ID: {result.get('id')}")
            return True
        else:
            logger.error(f"上传失败: {result.get('error', '未知错误')}")
            return False
    except Exception as e:
        logger.exception(f"上传过程中发生错误: {e}")
        return False
