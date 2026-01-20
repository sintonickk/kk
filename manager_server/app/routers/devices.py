from typing import List
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import parse_auth
from ..database import get_db
from .. import schemas, crud

router = APIRouter(prefix="/api/v1/devices", tags=["devices"], dependencies=[Depends(parse_auth)])
logger = logging.getLogger(__name__)


@router.post("", response_model=schemas.DeviceRead)
def create_device(body: schemas.DeviceCreate, db: Session = Depends(get_db)):
    try:
        item = crud.create_device(db, body)
        logger.info("Device created: ip=%s id=%s", item.device_ip, item.device_id)
        return item
    except Exception as e:
        # 常见失败如唯一键冲突（device_ip 唯一），返回 400
        logger.warning("Device create failed for ip=%s: %s", getattr(body, "device_ip", None), e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[schemas.DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    items = crud.list_devices(db)
    logger.info("List devices: count=%s", len(items))
    return items


@router.get("/webrtc")
def get_webrtc_urls_by_query(device_id: int | None = None, device_ip: str | None = None, db: Session = Depends(get_db)):
    """Get placeholder WebRTC URLs by device_id or device_ip (one must be provided).
    Note: Defined before '/{device_id}' to avoid path param shadowing.
    """
    if (device_id is None and device_ip is None) or (device_id is not None and device_ip is not None):
        logger.warning("WebRTC query invalid params: device_id=%s device_ip=%s", device_id, device_ip)
        raise HTTPException(status_code=400, detail="Provide exactly one of device_id or device_ip")
    if device_id is not None:
        item = crud.get_device(db, device_id)
    else:
        item = crud.get_device_by_ip(db, device_ip)  # type: ignore[arg-type]
    if not item:
        logger.warning("WebRTC device not found: device_id=%s device_ip=%s", device_id, device_ip)
        raise HTTPException(status_code=404, detail="Device not found")
    # todo: convert item.rtsp_urls -> WebRTC URLs
    result = {
        "device_id": item.device_id,
        "webrtc_urls": [],
    }
    logger.info("WebRTC query ok: device_id=%s device_ip=%s", item.device_id, device_ip if device_ip else None)
    return result


@router.get("/{device_id}", response_model=schemas.DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    item = crud.get_device(db, device_id)
    if not item:
        logger.warning("Device not found: id=%s", device_id)
        raise HTTPException(status_code=404, detail="Device not found")
    logger.info("Get device: id=%s ip=%s", device_id, item.device_ip)
    return item


@router.put("/{device_id}", response_model=schemas.DeviceRead)
def update_device(device_id: int, body: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    try:
        item = crud.update_device(db, device_id, body)
        if not item:
            logger.warning("Update device missed: id=%s", device_id)
            raise HTTPException(status_code=404, detail="Device not found")
        logger.info("Device updated: id=%s", device_id)
        return item
    except Exception as e:
        logger.warning("Device update failed: id=%s err=%s", device_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/by-ip/{device_ip}", response_model=schemas.DeviceRead)
def update_device_by_ip(device_ip: str, body: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    # 先根据 IP 定位设备，再重用 update_device 逻辑
    item = crud.get_device_by_ip(db, device_ip)
    if not item:
        logger.warning("Device not found for update by ip: %s", device_ip)
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        updated = crud.update_device(db, item.device_id, body)
        logger.info("Device updated by ip: ip=%s id=%s", device_ip, item.device_id)
        return updated
    except Exception as e:
        logger.warning("Device update by ip failed: ip=%s err=%s", device_ip, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-ip/{device_ip}", response_model=schemas.DeviceRead)
def get_device_by_ip(device_ip: str, db: Session = Depends(get_db)):
    item = crud.get_device_by_ip(db, device_ip)
    if not item:
        logger.warning("Device not found by ip: %s", device_ip)
        raise HTTPException(status_code=404, detail="Device not found")
    logger.info("Get device by ip: ip=%s id=%s", device_ip, item.device_id)
    return item


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_device(db, device_id)
    if not ok:
        logger.warning("Delete device not found: id=%s", device_id)
        raise HTTPException(status_code=404, detail="Device not found")
    logger.info("Device deleted: id=%s", device_id)
    return {"deleted": True}


