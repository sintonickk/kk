from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, LargeBinary, Float, Numeric
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
from sqlalchemy.sql import func
from .database import Base


# PostgreSQL ENUM types pre-exist in DB, so we reference them without creating
device_status_enum = PG_ENUM(
    "online", "offline", "fault", "maintenance",
    name="device_status",
    create_type=False,
)

user_status_enum = PG_ENUM(
    "enabled", "disabled",
    name="user_status",
    create_type=False,
)

alarm_process_status_enum = PG_ENUM(
    "unprocessed", "processing", "closed", "ignore",
    name="alarm_process_status",
    create_type=False,
)

file_format_enum = PG_ENUM(
    "gps", "txt", "json",
    name="file_format",
    create_type=False,
)


class Device(Base):
    __tablename__ = "t_device"

    device_id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(64), unique=True, nullable=False)
    device_ip = Column(String(15), unique=True, nullable=False)
    rtsp_urls = Column(JSONB, nullable=True)
    note = Column(Text, nullable=True)
    device_config = Column(JSONB, nullable=True)
    device_info = Column(JSONB, nullable=True)
    status = Column(device_status_enum, nullable=False, server_default="offline")
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AlarmInfo(Base):
    __tablename__ = "t_alarm_info"

    alarm_id = Column(Integer, primary_key=True, index=True)
    alarm_time = Column(DateTime(timezone=True), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    latitude = Column(Numeric(10, 7), nullable=False)
    alarm_type = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, nullable=True)
    process_opinion = Column(Text, nullable=True)
    process_opinion_person = Column(Integer, nullable=True)
    process_status = Column(alarm_process_status_enum, nullable=False, server_default="unprocessed")
    process_feedback = Column(Text, nullable=True)
    process_feedback_person = Column(Integer, nullable=True)
    image_url = Column(String(1024), nullable=False)
    device_ip = Column(String(15), ForeignKey("t_device.device_ip", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    # align with existing DB: use user_code (string) instead of user_id
    user_code = Column(String(64), ForeignKey("t_user.user_code", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConfigKV(Base):
    __tablename__ = "config_kv"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)


class User(Base):
    __tablename__ = "t_user"

    user_id = Column(Integer, primary_key=True, index=True)
    user_code = Column(String(64), nullable=False, unique=True)
    user_name = Column(String(64), nullable=False)
    user_account = Column(String(64), nullable=False, unique=True)
    user_password = Column(LargeBinary, nullable=False)
    user_phone = Column(String(20), nullable=True)
    user_email = Column(String(128), nullable=True)
    user_role = Column(String(32), nullable=True)
    user_dept = Column(String(64), nullable=True)
    status = Column(user_status_enum, nullable=False, server_default="enabled")
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ext_info = Column(JSONB, nullable=True)


class Route(Base):
    __tablename__ = "t_route"

    route_id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String(128), nullable=False)
    route_file_path = Column(String(1024), nullable=False, unique=True)
    upload_user_code = Column(String(64), ForeignKey("t_user.user_code", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    route_desc = Column(Text, nullable=True)
    route_format = Column(file_format_enum, nullable=False, server_default="gps")
    create_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    update_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
