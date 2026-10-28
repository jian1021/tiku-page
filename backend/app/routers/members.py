"""会员激活接口。"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ActivationCode, Membership, User
from ..ratelimit import clear, failure_count, record_failure

router = APIRouter(tags=["会员"])

# 激活码失败限频：10 分钟内最多 5 次
_ACTIVATE_FAIL_LIMIT = 5
_ACTIVATE_FAIL_WINDOW = 600


class ActivateRequest(BaseModel):
    """激活码请求。"""

    code: str = Field(..., max_length=64)


@router.post("/activate")
def activate_membership(
    payload: ActivateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """使用激活码开通或续期会员。"""
    client_host = request.client.host if request.client else "unknown"
    failure_key = f"activate_fail:{current_user.id}:{client_host}"

    if failure_count(failure_key, _ACTIVATE_FAIL_WINDOW) >= _ACTIVATE_FAIL_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="尝试次数过多，请稍后再试",
        )

    def fail(status_code: int, detail: str) -> None:
        """记录失败次数后抛出错误。"""
        record_failure(
            failure_key, _ACTIVATE_FAIL_LIMIT, _ACTIVATE_FAIL_WINDOW
        )
        raise HTTPException(status_code=status_code, detail=detail)

    code_value = (payload.code or "").strip()
    activation = (
        db.query(ActivationCode)
        .filter(ActivationCode.code == code_value)
        .first()
    )
    if activation is None:
        fail(status.HTTP_404_NOT_FOUND, "激活码不存在")
    if activation.status == "disabled":
        fail(status.HTTP_400_BAD_REQUEST, "激活码已被禁用")
    if activation.status == "used":
        fail(status.HTTP_400_BAD_REQUEST, "激活码已被使用")
    if activation.duration_days is None or activation.duration_days <= 0:
        fail(status.HTTP_400_BAD_REQUEST, "激活码配置有误")

    now = datetime.now()
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id)
        .first()
    )
    # 未过期则从现有到期时间叠加，否则从现在开始计算
    base_time = (
        membership.expires_at
        if membership is not None
        and membership.expires_at is not None
        and membership.expires_at > now
        else now
    )
    expires_at = base_time + timedelta(days=activation.duration_days)

    activation.status = "used"
    activation.used_by = current_user.id
    activation.used_at = now

    if membership is None:
        db.add(
            Membership(user_id=current_user.id, expires_at=expires_at)
        )
    else:
        membership.expires_at = expires_at

    db.commit()
    clear(failure_key)

    return {
        "ok": True,
        "expires_at": expires_at.isoformat(),
        "duration_days": activation.duration_days,
    }
