"""站点配置、意见反馈与用户学习统计接口。"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional
from ..models import (
    AnswerRecord,
    Exam,
    Favorite,
    Feedback,
    Membership,
    SiteConfig,
    User,
    WrongQuestion,
)

router = APIRouter(tags=["站点"])

_SITE_DEFAULTS = {
    "service_phone": "",
    "service_wechat": "",
    "service_intro": "",
}


class FeedbackRequest(BaseModel):
    """意见反馈请求。"""

    content: str


@router.get("/site-config")
def get_site_config(db: Session = Depends(get_db)) -> dict:
    """返回站点配置字典，服务联系方式缺失时返回空字符串。"""
    data = dict(_SITE_DEFAULTS)
    for item in db.query(SiteConfig).all():
        data[item.key] = item.value
    return data


@router.post("/feedback")
def create_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """提交意见反馈，登录可选。"""
    content = (payload.content or "").strip()
    if not (1 <= len(content) <= 1024):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="反馈内容需为 1~1024 字",
        )

    db.add(
        Feedback(
            user_id=current_user.id if current_user is not None else None,
            content=content,
            created_at=datetime.now(),
        )
    )
    db.commit()
    return {"ok": True}


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """返回当前用户学习统计；未登录时返回零值。"""
    if current_user is None:
        return {
            "answered_count": 0,
            "correct_count": 0,
            "correct_rate": 0.0,
            "wrong_count": 0,
            "favorite_count": 0,
            "exam_count": 0,
            "membership_expires_at": None,
        }

    answered_count = (
        db.query(AnswerRecord)
        .filter(AnswerRecord.user_id == current_user.id)
        .count()
    )
    correct_count = (
        db.query(AnswerRecord)
        .filter(
            AnswerRecord.user_id == current_user.id,
            AnswerRecord.is_correct.is_(True),
        )
        .count()
    )
    wrong_count = (
        db.query(WrongQuestion)
        .filter(
            WrongQuestion.user_id == current_user.id,
            WrongQuestion.removed.is_(False),
        )
        .count()
    )
    favorite_count = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id)
        .count()
    )
    exam_count = (
        db.query(Exam).filter(Exam.user_id == current_user.id).count()
    )
    membership = (
        db.query(Membership)
        .filter(Membership.user_id == current_user.id)
        .first()
    )
    expires_at = membership.expires_at if membership is not None else None

    return {
        "answered_count": answered_count,
        "correct_count": correct_count,
        "correct_rate": (
            round(correct_count / answered_count * 100, 1)
            if answered_count
            else 0.0
        ),
        "wrong_count": wrong_count,
        "favorite_count": favorite_count,
        "exam_count": exam_count,
        "membership_expires_at": (
            expires_at.isoformat() if expires_at is not None else None
        ),
    }
