"""FastAPI 依赖：数据库会话、当前用户与权限校验。"""

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import get_db
from .models import Membership, User

# auto_error=False：未携带令牌时交由依赖自行处理，便于区分必选/可选登录
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_user(
    db: Session, credentials: Optional[HTTPAuthorizationCredentials]
) -> Optional[User]:
    """根据 Bearer 令牌查找用户，失败返回 None。"""
    if credentials is None or not credentials.credentials:
        return None
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        return None
    return db.get(User, user_id)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """必须登录：令牌缺失、无效或用户不存在时返回 401。"""
    user = _extract_user(db, credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选登录：未登录或令牌无效时返回 None。"""
    return _extract_user(db, credentials)


def require_member(db: Session, current_user: Optional[User]) -> User:
    """会员校验：管理员直接放行，普通用户需会员未过期。"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该内容仅会员可访问",
        )
    if current_user.role == "admin":
        return current_user

    membership = (
        db.query(Membership).filter(Membership.user_id == current_user.id).first()
    )
    if (
        membership is None
        or membership.expires_at is None
        or membership.expires_at <= datetime.now()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该内容仅会员可访问",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员校验：要求当前用户 role 为 admin。"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无管理员权限",
        )
    return current_user
