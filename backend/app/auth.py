"""认证工具：密码哈希与 JWT 令牌。"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """生成密码哈希。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> str:
    """签发访问令牌，sub 中保存用户 ID。"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """解析访问令牌，成功返回用户 ID，失败返回 None。"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            return None
        return int(subject)
    except (JWTError, ValueError, TypeError):
        return None
