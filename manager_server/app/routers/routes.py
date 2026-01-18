from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import uuid

from ..database import get_db
from ..config import get_settings
from .. import schemas, crud
from ..deps import parse_auth

router = APIRouter(prefix="/api/v1/routes", tags=["routes"], dependencies=[Depends(parse_auth)]) 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
settings = get_settings()
ROUTE_DIR = os.path.join(settings.upload_dir, "routes")
os.makedirs(ROUTE_DIR, exist_ok=True)


def _save_uploaded_file(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1]
    name = f"{uuid.uuid4().hex}{ext or ''}"
    abs_path = os.path.join(ROUTE_DIR, name)
    with open(abs_path, "wb") as f:
        f.write(file.file.read())
    # store as path relative to save_path
    rel_path = os.path.join("routes", name).replace("\\", "/")
    return rel_path


def _remove_files(paths: List[str]):
    for rel in paths:
        abs_path = os.path.normpath(os.path.join(settings.upload_dir, rel))
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            pass


@router.post("", response_model=schemas.RouteRead)
def create_route(
    route_name: str = Form(...),
    route_format: Optional[str] = Form("gps"),
    upload_user_code: Optional[str] = Form(None),
    route_desc: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    rel_path = _save_uploaded_file(file)
    body = schemas.RouteCreate(
        route_name=route_name,
        route_format=route_format,  # validated by schema default
        upload_user_code=upload_user_code,
        route_desc=route_desc,
    )
    item = crud.create_route(db, body, rel_path)
    return item


@router.get("", response_model=List[schemas.RouteRead])
def list_routes(db: Session = Depends(get_db)):
    return crud.list_routes(db)


#todo 后期增加对各个路径文件的解析，返回list点位数据
@router.get("/{route_id}", response_model=schemas.RouteRead)
def get_route(route_id: int, db: Session = Depends(get_db)):
    item = crud.get_route(db, route_id)
    if not item:
        raise HTTPException(status_code=404, detail="Route not found")
    return item


@router.put("/{route_id}", response_model=schemas.RouteRead)
def update_route(
    route_id: int,
    route_name: Optional[str] = Form(None),
    route_format: Optional[str] = Form(None),
    upload_user_code: Optional[str] = Form(None),
    route_desc: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    new_rel_path: Optional[str] = None
    if file is not None:
        new_rel_path = _save_uploaded_file(file)
    body = schemas.RouteUpdate(
        route_name=route_name,
        route_format=route_format,
        upload_user_code=upload_user_code,
        route_desc=route_desc,
    )
    # If replacing file, consider removing old one
    old = crud.get_route(db, route_id)
    item = crud.update_route(db, route_id, body, new_rel_path)
    if not item:
        if new_rel_path:
            _remove_files([new_rel_path])  # cleanup newly saved file if route missing
        raise HTTPException(status_code=404, detail="Route not found")
    if new_rel_path and old and old.route_file_path and old.route_file_path != new_rel_path:
        _remove_files([old.route_file_path])
    return item


@router.get("/{route_id}/download")
def download_route(route_id: int, db: Session = Depends(get_db)):
    item = crud.get_route(db, route_id)
    if not item or not item.route_file_path:
        raise HTTPException(status_code=404, detail="Route not found")
    abs_path = os.path.normpath(os.path.join(settings.upload_dir, item.route_file_path))
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Route file missing")
    # derive a friendly filename
    _, ext = os.path.splitext(abs_path)
    download_name = f"{item.route_name}{ext or ''}"
    return FileResponse(abs_path, media_type="application/octet-stream", filename=download_name)


@router.delete("/{route_id}")
def delete_route(route_id: int, db: Session = Depends(get_db)):
    files = crud.get_route_file_paths_by_ids(db, [route_id])
    deleted = crud.delete_routes_by_ids(db, [route_id])
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Route not found")
    _remove_files(files)
    return {"deleted": deleted}


@router.delete("")
def delete_routes(ids: List[int], db: Session = Depends(get_db)):
    if not ids:
        raise HTTPException(status_code=400, detail="ids is required")
    files = crud.get_route_file_paths_by_ids(db, ids)
    deleted = crud.delete_routes_by_ids(db, ids)
    _remove_files(files)
    return {"deleted": deleted}
