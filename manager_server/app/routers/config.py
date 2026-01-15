from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import schemas, crud

router = APIRouter(prefix="/api/v1/config", tags=["config"]) 


@router.get("", response_model=List[schemas.ConfigItemRead])
def list_config(db: Session = Depends(get_db)):
    return crud.list_configs(db)


@router.get("/{key}", response_model=schemas.ConfigItemRead)
def get_config(key: str, db: Session = Depends(get_db)):
    item = crud.get_config(db, key)
    if not item:
        raise HTTPException(status_code=404, detail="Config not found")
    return item


@router.put("/{key}", response_model=schemas.ConfigItemRead)
def put_config(key: str, body: schemas.ConfigItem, db: Session = Depends(get_db)):
    if key != body.key:
        raise HTTPException(status_code=400, detail="Key mismatch")
    return crud.upsert_config(db, key=body.key, value=body.value)
