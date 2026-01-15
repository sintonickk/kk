from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from .. import schemas, crud, models

router = APIRouter(prefix="/api/v1/users", tags=["users"]) 


@router.post("/login", response_model=schemas.LoginResponse)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.verify_login(db, body.user_account, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="User disabled")
    return schemas.LoginResponse(
        user_id=user.user_id,
        user_code=user.user_code,
        user_name=user.user_name,
        user_account=user.user_account,
        user_role=user.user_role,
        status=user.status,
    )


@router.post("", response_model=schemas.UserRead)
def create_user(body: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_account(db, body.user_account)
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists")
    user = crud.create_user(db, body)
    return user


@router.put("/{user_id}", response_model=schemas.UserRead)
def update_user(user_id: int, body: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = crud.update_user(db, user_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}
