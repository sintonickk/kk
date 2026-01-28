from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_ip: str = Field(max_length=15)
    device_code: str
    rtsp_urls: Optional[List[str]] = Field(default=None)
    note: Optional[str] = None
    device_config: Optional[Any] = None
    device_info: Optional[Any] = None
    status: Optional[Literal["online", "offline", "fault", "maintenance"]] = "offline"


class DeviceRead(BaseModel):
    device_id: int
    device_code: str
    device_ip: str
    rtsp_urls: Optional[List[str]]
    note: Optional[str]
    device_config: Optional[Any]
    device_info: Optional[Any]
    status: Literal["online", "offline", "fault", "maintenance"]
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    device_ip: Optional[str] = Field(default=None, max_length=15)
    rtsp_urls: Optional[List[str]] = None
    note: Optional[str] = None
    device_config: Optional[Any] = None
    device_info: Optional[Any] = None
    status: Optional[Literal["online", "offline", "fault", "maintenance"]] = None


class AlarmCreate(BaseModel):
    alarm_time: datetime
    longitude: float
    latitude: float
    alarm_type: str = Field(max_length=64)
    confidence: Optional[float] = None
    process_opinion: Optional[str] = None
    process_opinion_person: Optional[int] = None
    process_status: Optional[Literal["unprocessed", "processing", "closed", "ignore", "auto_ignore"]] = "unprocessed"
    process_feedback: Optional[str] = None
    process_feedback_person: Optional[int] = None
    device_ip: str
    user_code: Optional[str] = None
    image_url: Optional[str]
    image_hash: str


class AlarmRead(BaseModel):
    alarm_id: int
    alarm_time: datetime
    longitude: float
    latitude: float
    alarm_type: str
    confidence: Optional[float]
    process_opinion: Optional[str]
    process_opinion_person: Optional[int]
    process_status: Literal["unprocessed", "processing", "closed", "ignore", "auto_ignore"]
    process_feedback: Optional[str]
    process_feedback_person: Optional[int]
    image_url: Optional[str]
    image_hash: str
    device_ip: str
    user_code: Optional[str]
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class AlarmQuery(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    alarm_type: Optional[str] = None
    process_status: Optional[Literal["unprocessed", "processing", "closed", "ignore", "auto_ignore"]] = None
    device_ip: Optional[str] = None
    skip: int = 0
    limit: int = 50


class AlarmProcessUpdate(BaseModel):
    process_status: Optional[Literal["unprocessed", "processing", "closed", "ignore", "auto_ignore"]] = None
    process_opinion: Optional[str] = None
    process_feedback: Optional[str] = None
    process_opinion_person: Optional[int] = None
    process_feedback_person: Optional[int] = None


class ConfigItem(BaseModel):
    key: str
    value: Optional[str] = None


class ConfigItemRead(ConfigItem):
    id: int

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    user_name: str = Field(max_length=64)
    user_account: str = Field(max_length=64)
    password: str = Field(min_length=6, max_length=128)
    user_phone: Optional[str] = Field(default=None, max_length=20)
    user_email: Optional[str] = Field(default=None, max_length=128)
    user_role: Optional[str] = Field(default=None, max_length=32)
    user_dept: Optional[str] = Field(default=None, max_length=64)
    status: Optional[Literal["enabled", "disabled"]] = "enabled"
    ext_info: Optional[Any] = None


class UsersBaseInfo(BaseModel):
    user_id: int
    user_code: str
    user_name: str


class UserRead(BaseModel):
    user_id: int
    user_code: str
    user_name: str
    user_account: str
    user_phone: Optional[str]
    user_email: Optional[str]
    user_role: Optional[str]
    user_dept: Optional[str]
    status: Literal["enabled", "disabled"]
    create_time: datetime
    update_time: datetime
    ext_info: Optional[Any]

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    user_name: Optional[str] = Field(default=None, max_length=64)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    user_phone: Optional[str] = Field(default=None, max_length=20)
    user_email: Optional[str] = Field(default=None, max_length=128)
    user_role: Optional[str] = Field(default=None, max_length=32)
    user_dept: Optional[str] = Field(default=None, max_length=64)
    status: Optional[Literal["enabled", "disabled"]] = None
    ext_info: Optional[Any] = None


class LoginRequest(BaseModel):
    user_account: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    user_code: str
    user_name: str
    user_account: str
    user_role: Optional[str]
    status: Literal["enabled", "disabled"]


# Route schemas
class RouteCreate(BaseModel):
    route_name: str = Field(max_length=128)
    upload_user_code: Optional[str] = None
    route_desc: Optional[str] = None
    route_format: Optional[Literal["gps", "txt", "json"]] = "gps"


class RouteRead(BaseModel):
    route_id: int
    route_name: str
    route_file_path: str
    upload_user_code: Optional[str]
    route_desc: Optional[str]
    route_format: Literal["gps", "txt", "json"]
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class RouteUpdate(BaseModel):
    route_name: Optional[str] = Field(default=None, max_length=128)
    upload_user_code: Optional[str] = None
    route_desc: Optional[str] = None
    route_format: Optional[Literal["gps", "txt", "json"]] = None
