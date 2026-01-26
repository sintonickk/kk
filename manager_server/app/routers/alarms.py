from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import uuid
from imagededup.methods import WHash  # type: ignore
_whash = WHash()
import logging

from ..database import get_db
from ..config import get_settings
from .. import schemas, crud
from ..deps import parse_auth

router = APIRouter(prefix="/api/v1/alarms", tags=["alarms"], dependencies=[Depends(parse_auth)]) 
logger = logging.getLogger(__name__)

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
    """
    创建报警记录
    时间格式：ISO8601字符串，例：2025-10-15T10:30:00+08:00
    """
    image_url: Optional[str] = None
    image_hash: Optional[str] = None
    if image is not None:
        ext = os.path.splitext(image.filename)[1] or ".bin"
        file_name = f"{uuid.uuid4().hex}{ext}"
        dst_path = os.path.join(UPLOAD_DIR, file_name)
        # save file first
        content = await image.read()
        with open(dst_path, "wb") as f:
            f.write(content)
        # compute hash: use WHash; 
        image_hash = _whash.encode_image(dst_path)
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
        image_hash=image_hash or "",
    )
    # Similarity check: if similar to ignored ones, mark as ignore before insert
    try:
        if crud.need_alarm(db, alarm_in):
            alarm_in.process_status = "auto_ignore"
            logger.info("Alarm marked ignore by similarity: device_ip=%s type=%s", device_ip, alarm_type)
    except Exception:
        logger.exception("need_alarm check failed; proceeding without ignore")
    new_alarm = crud.create_alarm(db, alarm_in, image_url=image_url)
    logger.info("Alarm created: id=%s device_ip=%s type=%s", getattr(new_alarm, "alarm_id", None), device_ip, alarm_type)
    return new_alarm


@router.get("/today-events")
def list_today_events(db: Session = Depends(get_db)):
    """Return today's alarms with:
    - items: list of AlarmRead objects
    - summary: {total, processed, feedback_confirmed, ignored, auto_ignored, unprocessed}
    """
    from datetime import datetime
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    items = crud.query_alarms(db, start, now, None, None, None, 0, 1000)
    resp = []
    # counters
    total = 0
    processed = 0  # processing + closed
    feedback_confirmed = 0  # closed
    ignored = 0  # ignore
    auto_ignored = 0  # auto_ignore
    for it in items:
        total += 1
        status = str(getattr(it, "process_status", ""))
        if status in ("processing", "closed"):
            processed += 1
        if status == "closed":
            feedback_confirmed += 1
        if status == "ignore":
            ignored += 1
        if status == "auto_ignore":
            auto_ignored += 1
        alarm_read = schemas.AlarmRead(
            alarm_id=getattr(it, "alarm_id", None),
            alarm_time=getattr(it, "alarm_time", None),
            longitude=getattr(it, "longitude", None),
            latitude=getattr(it, "latitude", None),
            alarm_type=getattr(it, "alarm_type", None),
            confidence=getattr(it, "confidence", None),
            device_ip=getattr(it, "device_ip", None),
            image_url=getattr(it, "image_url", None),
            image_hash=getattr(it, "image_hash", None),
            process_status=getattr(it, "process_status", None),
            process_opinion_person=getattr(it, "process_opinion_person", None),
            process_feedback_person=getattr(it, "process_feedback_person", None),
            process_time=getattr(it, "process_time", None),
            process_note=getattr(it, "process_note", None)
        )
        resp.append(alarm_read)
    summary = {
        "total": total,
        "processed": processed,
        "feedback_confirmed": feedback_confirmed,
        "ignored": ignored,
        "auto_ignored": auto_ignored,
        "unprocessed": total - processed,
    }
    logger.info("Today events retrieved: count=%s, summary=%s", len(resp), summary)
    return {"summary": summary, "items": resp}


@router.get("/stats/today-hourly")
def stats_today_hourly(db: Session = Depends(get_db), request: Request = None):
    rows = crud.stats_today_hourly(db)
    # Build a map: hour (0-23) -> count
    counts_by_hour: dict[int, int] = {}
    for hour_dt, cnt in rows:
        h = None
        try:
            # hour_dt likely a datetime
            h = int(getattr(hour_dt, "hour"))
        except Exception:
            h = None
        if h is None:
            # fallback: try to parse from string like '2026-01-16 10:00:00'
            try:
                s = str(hour_dt)
                # find HH at positions 11-13 or 0-2 if only hour
                if len(s) >= 13 and s[11:13].isdigit():
                    h = int(s[11:13])
                elif len(s) >= 2 and s[0:2].isdigit():
                    h = int(s[0:2])
            except Exception:
                h = None
        if h is not None and 0 <= h <= 23:
            counts_by_hour[h] = int(cnt)
    # Produce full 24 hours
    result = [{"time": f"{h:02d}:00", "count": counts_by_hour.get(h, 0)} for h in range(0, 24)]
    return result


@router.get("/by-process-status", response_model=List[schemas.AlarmRead])
def list_alarms_by_process_status(
    process_status: str = "unprocessed",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    List alarms by process status.
    process_status: unprocessed, processing, closed, ignore
    """
    # prefer header user_code over query param
    try:
        header_uc = getattr(getattr(request, "state", None), "auth", {}).get("user_code") if request else None
        if header_uc:
            user_code = header_uc
    except Exception:
        pass

    items = crud.query_alarms_by_process_status(db, user_code, process_status, skip, min(limit, 200))
    logger.info("List alarms by status: status=%s count=%s", process_status, len(items))
    return items


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
    logger.info("List alarms: count=%s process_status=%s type=%s", len(items), process_status, alarm_type)
    return items


@router.get("/{alarm_id}", response_model=schemas.AlarmRead)
def get_alarm(alarm_id: int, db: Session = Depends(get_db), request: Request = None):
    alarm = crud.get_alarm(db, alarm_id)
    if not alarm:
        logger.warning("Alarm not found: id=%s", alarm_id)
        raise HTTPException(status_code=404, detail="Alarm not found")
    logger.info("Get alarm: id=%s type=%s", alarm_id, getattr(alarm, "alarm_type", None))
    return alarm


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
        logger.warning("Update alarm process failed: id=%s", alarm_id)
        raise HTTPException(status_code=404, detail="Alarm not found")
    logger.info("Alarm process updated: id=%s status=%s", alarm_id, getattr(updated, "process_status", None))
    return updated



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
        logger.warning("Delete alarm not found: id=%s", alarm_id)
        raise HTTPException(status_code=404, detail="Alarm not found")
    _remove_local_images(image_urls)
    logger.info("Alarm deleted: id=%s", alarm_id)
    return {"deleted": deleted}


@router.delete("")
def delete_alarms(ids: List[int], db: Session = Depends(get_db), request: Request = None):
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")
    image_urls = crud.get_alarm_image_urls_by_ids(db, ids)
    deleted = crud.delete_alarms_by_ids(db, ids)
    _remove_local_images(image_urls)
    logger.info("Alarms batch deleted: ids=%s deleted=%s", ids, deleted)
    return {"deleted": deleted}
