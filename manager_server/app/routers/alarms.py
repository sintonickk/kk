from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import uuid

from ..database import get_db
from ..config import get_settings
from .. import schemas, crud
from ..deps import parse_auth

router = APIRouter(prefix="/api/v1/alarms", tags=["alarms"], dependencies=[Depends(parse_auth)]) 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
settings = get_settings()
UPLOAD_DIR = os.path.join(settings.upload_dir, "alarms")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("", response_model=schemas.AlarmRead)
async def create_alarm(
    alarm_time: str = Form(...),  # ISO8601 string
    longitude: float = Form(...),
    latitude: float = Form(...),
    alarm_type: str = Form(...),
    device_ip: str = Form(...),
    confidence: Optional[float] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    #todo 需要加上去重的处理
    image_url: Optional[str] = None
    if image is not None:
        ext = os.path.splitext(image.filename)[1] or ".bin"
        file_name = f"{uuid.uuid4().hex}{ext}"
        dst_path = os.path.join(UPLOAD_DIR, file_name)
        with open(dst_path, "wb") as f:
            f.write(await image.read())
        # store url as relative to save_path root (e.g., 'alarms/<file>')
        image_url = os.path.join("alarms", file_name).replace("\\", "/")

    from datetime import datetime
    alarm_dt = datetime.fromisoformat(alarm_time)

    alarm_in = schemas.AlarmCreate(
        alarm_time=alarm_dt,
        longitude=longitude,
        latitude=latitude,
        alarm_type=alarm_type,
        confidence=confidence,
        device_ip=device_ip,
        image_url=image_url,
    )
    new_alarm = crud.create_alarm(db, alarm_in, image_url=image_url)
    return new_alarm


@router.get("/{alarm_id}", response_model=schemas.AlarmRead)
def get_alarm(alarm_id: int, db: Session = Depends(get_db), request: Request = None):
    alarm = crud.get_alarm(db, alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return alarm


@router.get("", response_model=List[schemas.AlarmRead])
def list_alarms(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    alarm_type: Optional[str] = None,
    process_status: Optional[str] = None,
    user_code: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    request: Request = None,
):
    from datetime import datetime

    # prefer header user_code over query param
    try:
        header_uc = getattr(getattr(request, "state", None), "auth", {}).get("user_code") if request else None
        if header_uc:
            user_code = header_uc
    except Exception:
        pass

    st = datetime.fromisoformat(start_time) if start_time else None
    et = datetime.fromisoformat(end_time) if end_time else None
    items = crud.query_alarms(db, st, et, alarm_type, process_status, user_code, skip, min(limit, 200))
    return items

@router.put("/{alarm_id}/process", response_model=schemas.AlarmRead)
def update_alarm_process(
    alarm_id: int,
    body: schemas.AlarmProcessUpdate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    # extract header user_code and pass to CRUD to update alarm.user_code
    try:
        header_user_code = getattr(getattr(request, "state", None), "auth", {}).get("user_code") if request else None
    except Exception:
        header_user_code = None
    updated = crud.update_alarm_process(db, alarm_id, body, header_user_code=header_user_code)
    if not updated:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return updated


@router.get("/stats/today-hourly")
def stats_today_hourly(db: Session = Depends(get_db), request: Request = None):
    rows = crud.stats_today_hourly(db)
    # format as list of {"time": "HH:00", "count": n}
    result = []
    for hour_dt, cnt in rows:
        # hour_dt from PG may be datetime; format to HH:MM
        try:
            label = hour_dt.strftime("%H:00")
        except Exception:
            label = str(hour_dt)
        result.append({"time": label, "count": int(cnt)})
    return result


def _remove_local_images(image_urls: List[str]):
    for rel in image_urls:
        # stored image_url is relative to save_path; resolve under settings.upload_dir
        abs_path = os.path.normpath(os.path.join(settings.upload_dir, rel))
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            # ignore individual file errors
            pass


@router.delete("/{alarm_id}")
def delete_alarm(alarm_id: int, db: Session = Depends(get_db), request: Request = None):
    image_urls = crud.get_alarm_image_urls_by_ids(db, [alarm_id])
    deleted = crud.delete_alarms_by_ids(db, [alarm_id])
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Alarm not found")
    _remove_local_images(image_urls)
    return {"deleted": deleted}


@router.delete("")
def delete_alarms(ids: List[int], db: Session = Depends(get_db), request: Request = None):
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")
    image_urls = crud.get_alarm_image_urls_by_ids(db, ids)
    deleted = crud.delete_alarms_by_ids(db, ids)
    _remove_local_images(image_urls)
    return {"deleted": deleted}
