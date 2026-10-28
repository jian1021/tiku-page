"""认证相关接口：注册、登录、当前用户与个人设置。"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..deps import get_current_user
from ..models import Membership, User

router = APIRouter(tags=["认证"])


class RegisterRequest(BaseModel):
    """注册请求。"""

    phone: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)
    nickname: Optional[str] = Field(None, max_length=64)


class LoginRequest(BaseModel):
    """登录请求。"""

    phone: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)


class UpdateSettingsRequest(BaseModel):
    """更新个人设置请求，字段均可选。"""

    province_code: Optional[str] = Field(None, max_length=16)
    nickname: Optional[str] = Field(None, max_length=64)
    settings: Optional[dict[str, Any]] = None


def _public_user(user: User, db: Session) -> dict:
    """输出用户公开字段（含会员到期时间，便于前端判断权限）。"""
    membership = (
        db.query(Membership).filter(Membership.user_id == user.id).first()
    )
    expires_at = membership.expires_at if membership is not None else None
    return {
        "id": user.id,
        "phone": user.phone,
        "nickname": user.nickname,
        "province_code": user.province_code,
        "settings": user.settings or {},
        "role": user.role,
        "membership_expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at,
    }


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    """注册新用户并直接返回登录令牌。"""
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号不能为空",
        )

    exists = db.query(User).filter(User.phone == phone).first()
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已注册",
        )

    user = User(
        phone=phone,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname.strip() if payload.nickname else None,
        settings={},
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册时唯一约束兜底
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已注册",
        )
    db.refresh(user)

    return {"token": create_access_token(user.id), "user": _public_user(user, db)}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    """手机号 + 密码登录。"""
    phone = payload.phone.strip()
    user = db.query(User).filter(User.phone == phone).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    return {"token": create_access_token(user.id), "user": _public_user(user, db)}


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取当前登录用户信息。"""
    return _public_user(current_user, db)


@router.put("/me/settings")
def update_me_settings(
    payload: UpdateSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """更新当前用户的省份、昵称与个人设置。"""
    data = payload.model_dump(exclude_unset=True)

    if "province_code" in data:
        current_user.province_code = data["province_code"]
    if "nickname" in data:
        current_user.nickname = data["nickname"].strip() if data["nickname"] else None
    if "settings" in data:
        # settings 为 JSON 字典，与已有设置合并，避免覆盖其他开关
        merged = dict(current_user.settings or {})
        merged.update(data["settings"] or {})
        current_user.settings = merged

    db.commit()
    db.refresh(current_user)
    return _public_user(current_user, db)
