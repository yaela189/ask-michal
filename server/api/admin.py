# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from server.auth.jwt import require_admin
from server.database import get_db
from server.models import User
from server.api.schemas import UserResponse, ReloadQuotaRequest

router = APIRouter(prefix="/admin", tags=["admin"])

MSG_USER_NOT_FOUND = "משתמש לא נמצא"
MSG_CANNOT_CHANGE_SELF = "לא ניתן לשנות הרשאות עצמיות"


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(User).all()


@router.post("/users/{user_id}/reload")
async def reload_quota(
    user_id: int,
    body: ReloadQuotaRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=MSG_USER_NOT_FOUND)

    user.queries_remaining += body.amount
    db.commit()

    return {
        "message": f"נטענו {body.amount} שאילתות למשתמש {user.email}",
        "new_balance": user.queries_remaining,
    }


@router.post("/users/{user_id}/set-admin")
async def toggle_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=MSG_USER_NOT_FOUND)

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail=MSG_CANNOT_CHANGE_SELF)

    user.is_admin = not user.is_admin
    db.commit()

    return {
        "message": f"הרשאת מנהל עודכנה ל-{user.is_admin}",
        "is_admin": user.is_admin,
    }
