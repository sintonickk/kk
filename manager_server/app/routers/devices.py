from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import parse_auth
from ..database import get_db
from .. import schemas, crud

router = APIRouter(prefix="/api/v1/devices", tags=["devices"], dependencies=[Depends(parse_auth)])


@router.post("", response_model=schemas.DeviceRead)
def create_device(body: schemas.DeviceCreate, db: Session = Depends(get_db)):
    try:
        item = crud.create_device(db, body)
        return item
    except Exception as e:
        # 常见失败如唯一键冲突（device_ip 唯一），返回 400
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[schemas.DeviceRead])
def list_devices(db: Session = Depends(get_db)):
    return crud.list_devices(db)


@router.get("/{device_id}", response_model=schemas.DeviceRead)
def get_device(device_id: int, db: Session = Depends(get_db)):
    item = crud.get_device(db, device_id)
    if not item:
        raise HTTPException(status_code=404, detail="Device not found")
    return item


@router.put("/{device_id}", response_model=schemas.DeviceRead)
def update_device(device_id: int, body: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    try:
        item = crud.update_device(db, device_id, body)
        if not item:
            raise HTTPException(status_code=404, detail="Device not found")
        return item
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/by-ip/{device_ip}", response_model=schemas.DeviceRead)
def update_device_by_ip(device_ip: str, body: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    # 先根据 IP 定位设备，再重用 update_device 逻辑
    item = crud.get_device_by_ip(db, device_ip)
    if not item:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        updated = crud.update_device(db, item.device_id, body)
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_device(db, device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"deleted": True}
