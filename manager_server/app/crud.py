from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from datetime import datetime
from . import models, schemas
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_alarm(db: Session, alarm: schemas.AlarmCreate, image_url: Optional[str]) -> models.AlarmInfo:
    db_alarm = models.AlarmInfo(
        alarm_time=alarm.alarm_time,
        longitude=alarm.longitude,
        latitude=alarm.latitude,
        alarm_type=alarm.alarm_type,
        confidence=alarm.confidence,
        process_opinion=alarm.process_opinion,
        process_person=alarm.process_person,
        process_status=alarm.process_status,
        process_feedback=alarm.process_feedback,
        image_url=image_url,
        device_ip=alarm.device_ip,
        user_code=alarm.user_code,
    )
    db.add(db_alarm)
    db.commit()
    db.refresh(db_alarm)
    return db_alarm


def get_alarm(db: Session, alarm_id: int) -> Optional[models.AlarmInfo]:
    return db.get(models.AlarmInfo, alarm_id)


def query_alarms(
    db: Session,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    alarm_type: Optional[str],
    process_status: Optional[str],
    user_code: Optional[str],
    skip: int,
    limit: int,
) -> List[models.AlarmInfo]:
    stmt = select(models.AlarmInfo)
    conditions = []
    if start_time:
        conditions.append(models.AlarmInfo.alarm_time >= start_time)
    if end_time:
        conditions.append(models.AlarmInfo.alarm_time <= end_time)
    if alarm_type:
        conditions.append(models.AlarmInfo.alarm_type == alarm_type)
    if process_status:
        conditions.append(models.AlarmInfo.process_status == process_status)
    if user_code:
        conditions.append(models.AlarmInfo.user_code == user_code)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(models.AlarmInfo.alarm_time.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def update_alarm_process(db: Session, alarm_id: int, body: schemas.AlarmProcessUpdate, header_user_code: Optional[str] = None) -> Optional[models.AlarmInfo]:
    alarm = db.get(models.AlarmInfo, alarm_id)
    if not alarm:
        return None
    if body.process_status is not None:
        alarm.process_status = body.process_status
    if body.process_opinion is not None:
        alarm.process_opinion = body.process_opinion
    if body.process_feedback is not None:
        alarm.process_feedback = body.process_feedback
    if body.process_person is not None:
        alarm.process_person = body.process_person
    # If header user_code is provided, update it onto the alarm record
    if header_user_code:
        alarm.user_code = header_user_code
    db.add(alarm)
    db.commit()
    db.refresh(alarm)
    return alarm


def query_device_id_by_ip(db: Session, device_ip: str) -> Optional[int]:
    stmt = select(models.Device.device_id).where(models.Device.device_ip == device_ip)
    return db.execute(stmt).scalars().first()


def upsert_config(db: Session, key: str, value: Optional[str]) -> models.ConfigKV:
    stmt = select(models.ConfigKV).where(models.ConfigKV.key == key)
    existing = db.execute(stmt).scalars().first()
    if existing:
        existing.value = value
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    new_item = models.ConfigKV(key=key, value=value)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


def stats_today_hourly(db: Session) -> list[tuple]:
    """Return list of tuples (hour_dt, count) for today up to now, grouped per hour.
    hour_dt is a timezone-aware datetime truncated to hour from the database.
    """
    hour_col = func.date_trunc('hour', models.AlarmInfo.alarm_time).label('h')
    stmt = (
        select(hour_col, func.count())
        .where(models.AlarmInfo.alarm_time >= func.date_trunc('day', func.now()))
        .where(models.AlarmInfo.alarm_time <= func.now())
        .group_by(hour_col)
        .order_by(hour_col.asc())
    )
    rows = db.execute(stmt).all()
    return rows


def get_config(db: Session, key: str) -> Optional[models.ConfigKV]:
    stmt = select(models.ConfigKV).where(models.ConfigKV.key == key)
    return db.execute(stmt).scalars().first()


def list_configs(db: Session) -> List[models.ConfigKV]:
    stmt = select(models.ConfigKV).order_by(models.ConfigKV.key.asc())
    return list(db.execute(stmt).scalars().all())


def get_alarm_image_urls_by_ids(db: Session, ids: List[int]) -> List[str]:
    if not ids:
        return []
    stmt = select(models.AlarmInfo.image_url).where(models.AlarmInfo.alarm_id.in_(ids))
    return [row[0] for row in db.execute(stmt).all() if row[0]]


def delete_alarms_by_ids(db: Session, ids: List[int]) -> int:
    if not ids:
        return 0
    # Use ORM load then delete to respect session, or execute delete where in_
    # Simpler: load primary keys then delete individually
    stmt = select(models.AlarmInfo).where(models.AlarmInfo.alarm_id.in_(ids))
    items = list(db.execute(stmt).scalars().all())
    for it in items:
        db.delete(it)
    db.commit()
    return len(items)


# Route related CRUD
def create_route(db: Session, body: schemas.RouteCreate, route_file_path: str) -> models.Route:
    item = models.Route(
        route_name=body.route_name,
        route_file_path=route_file_path,
        upload_user_code=body.upload_user_code,
        route_desc=body.route_desc,
        route_format=body.route_format or "gps",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_route(db: Session, route_id: int) -> Optional[models.Route]:
    return db.get(models.Route, route_id)


def list_routes(db: Session) -> List[models.Route]:
    stmt = select(models.Route).order_by(models.Route.create_time.desc())
    return list(db.execute(stmt).scalars().all())


def update_route(db: Session, route_id: int, body: schemas.RouteUpdate, new_file_path: Optional[str] = None) -> Optional[models.Route]:
    item = db.get(models.Route, route_id)
    if not item:
        return None
    if body.route_name is not None:
        item.route_name = body.route_name
    if body.upload_user_code is not None:
        item.upload_user_code = body.upload_user_code
    if body.route_desc is not None:
        item.route_desc = body.route_desc
    if body.route_format is not None:
        item.route_format = body.route_format
    if new_file_path is not None:
        item.route_file_path = new_file_path
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_route_file_paths_by_ids(db: Session, ids: List[int]) -> List[str]:
    if not ids:
        return []
    stmt = select(models.Route.route_file_path).where(models.Route.route_id.in_(ids))
    return [row[0] for row in db.execute(stmt).all() if row[0]]


def delete_routes_by_ids(db: Session, ids: List[int]) -> int:
    if not ids:
        return 0
    stmt = select(models.Route).where(models.Route.route_id.in_(ids))
    items = list(db.execute(stmt).scalars().all())
    for it in items:
        db.delete(it)
    db.commit()
    return len(items)


# User related CRUD
def create_user(db: Session, body: schemas.UserCreate) -> models.User:
    hashed = pwd_ctx.hash(body.password)
    ext_info = None if (body.ext_info == "") else body.ext_info
    user_code = generate_unique_user_code(db)
    user = models.User(
        user_code=user_code,
        user_name=body.user_name,
        user_account=body.user_account,
        user_password=hashed.encode("utf-8") if isinstance(hashed, str) else hashed,
        user_phone=body.user_phone,
        user_email=body.user_email,
        user_role=body.user_role,
        user_dept=body.user_dept,
        status=body.status,
        ext_info=ext_info,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_account(db: Session, user_account: str) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.user_account == user_account)
    return db.execute(stmt).scalars().first()


def verify_login(db: Session, user_account: str, password: str) -> Optional[models.User]:
    user = get_user_by_account(db, user_account)
    if not user:
        return None
    stored = bytes(user.user_password) if isinstance(user.user_password, (bytes, bytearray)) else str(user.user_password).encode("utf-8")
    if pwd_ctx.verify(password, stored.decode("utf-8")):
        return user
    return None


def update_user(db: Session, user_id: int, body: schemas.UserUpdate) -> Optional[models.User]:
    user = db.get(models.User, user_id)
    if not user:
        return None
    if body.user_name is not None:
        user.user_name = body.user_name
    if body.password is not None:
        hashed = pwd_ctx.hash(body.password)
        user.user_password = hashed.encode("utf-8")
    if body.user_phone is not None:
        user.user_phone = body.user_phone
    if body.user_email is not None:
        user.user_email = body.user_email
    if body.user_role is not None:
        user.user_role = body.user_role
    if body.user_dept is not None:
        user.user_dept = body.user_dept
    if body.status is not None:
        user.status = body.status
    if body.ext_info is not None:
        user.ext_info = None if (body.ext_info == "") else body.ext_info
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(models.User, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


# Helpers for user_code generation
def _user_code_exists(db: Session, code: str) -> bool:
    stmt = select(models.User.user_id).where(models.User.user_code == code)
    return db.execute(stmt).first() is not None


def _generate_user_code() -> str:
    # pattern: U + yymmdd + random 4 hex
    from datetime import datetime as _dt
    import secrets
    return f"U{_dt.now().strftime('%y%m%d')}{secrets.token_hex(2).upper()}"


def generate_unique_user_code(db: Session, max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        code = _generate_user_code()
        if not _user_code_exists(db, code):
            return code
    raise RuntimeError("Failed to generate unique user_code after multiple attempts")


# Device related CRUD and helpers
def _device_code_exists(db: Session, code: str) -> bool:
    stmt = select(models.Device.device_id).where(models.Device.device_code == code)
    return db.execute(stmt).first() is not None


def _generate_device_code() -> str:
    # pattern: D + yymmdd + random 4 hex
    from datetime import datetime as _dt
    import secrets
    return f"D{_dt.now().strftime('%y%m%d')}{secrets.token_hex(2).upper()}"


def generate_unique_device_code(db: Session, max_attempts: int = 10) -> str:
    for _ in range(max_attempts):
        code = _generate_device_code()
        if not _device_code_exists(db, code):
            return code
    raise RuntimeError("Failed to generate unique device_code after multiple attempts")


def create_device(db: Session, body: schemas.DeviceCreate) -> models.Device:
    code = generate_unique_device_code(db)
    item = models.Device(
        device_code=code,
        device_ip=body.device_ip,
        rtsp_urls=body.rtsp_urls,
        note=body.note,
        device_config=body.device_config,
        device_info=body.device_info,
        status=body.status or "offline",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_device(db: Session, device_id: int) -> Optional[models.Device]:
    return db.get(models.Device, device_id)


def list_devices(db: Session) -> List[models.Device]:
    stmt = select(models.Device).order_by(models.Device.create_time.desc())
    return list(db.execute(stmt).scalars().all())


def get_device_by_ip(db: Session, device_ip: str) -> Optional[models.Device]:
    stmt = select(models.Device).where(models.Device.device_ip == device_ip)
    return db.execute(stmt).scalars().first()


def update_device(db: Session, device_id: int, body: schemas.DeviceUpdate) -> Optional[models.Device]:
    item = db.get(models.Device, device_id)
    if not item:
        return None
    if body.device_ip is not None:
        item.device_ip = body.device_ip
    if body.rtsp_urls is not None:
        item.rtsp_urls = body.rtsp_urls
    if body.note is not None:
        item.note = body.note
    if body.device_config is not None:
        item.device_config = body.device_config
    if body.device_info is not None:
        item.device_info = body.device_info
    if body.status is not None:
        item.status = body.status
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_device(db: Session, device_id: int) -> bool:
    item = db.get(models.Device, device_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
