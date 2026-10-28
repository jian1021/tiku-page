"""题目浏览与答题接口。"""

import random
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional
from ..models import AnswerRecord, Chapter, Favorite, Membership, Question, User, WrongQuestion
from ..ratelimit import check_rate_limit
from ..serializers import question_public

router = APIRouter(tags=["题目"])


class AnswerSubmitRequest(BaseModel):
    """练习答题请求。"""

    selected: list[str] = Field(default_factory=list)
    mode: str = "practice"


def _is_member(db: Session, user: Optional[User]) -> bool:
    """判断用户是否为有效会员（管理员直接视为会员）。"""
    if user is None:
        return False
    if user.role == "admin":
        return True
    membership = (
        db.query(Membership).filter(Membership.user_id == user.id).first()
    )
    return (
        membership is not None
        and membership.expires_at is not None
        and membership.expires_at > datetime.now()
    )


def _chapter_map(db: Session, province_code: str) -> dict[int, Chapter]:
    """读取某省全部章节，便于递归取子孙章节并补充分章名称。"""
    chapters = (
        db.query(Chapter).filter(Chapter.province_code == province_code).all()
    )
    return {chapter.id: chapter for chapter in chapters}


def _descendant_ids(chapters: dict[int, Chapter], root_id: int) -> set[int]:
    """递归收集指定章节及其全部子孙章节 ID。"""
    if root_id not in chapters:
        return {root_id}
    children: dict[Optional[int], list[int]] = {}
    for chapter in chapters.values():
        children.setdefault(chapter.parent_id, []).append(chapter.id)

    result: set[int] = set()
    stack = [root_id]
    while stack:
        current = stack.pop()
        if current in result:
            continue
        result.add(current)
        stack.extend(children.get(current, []))
    return result


def _favorite_question_ids(db: Session, user: Optional[User], ids: list[int]) -> set[int]:
    """查询当前用户收藏的题目 ID 集合。"""
    if user is None or not ids:
        return set()
    target_ids = {str(item) for item in ids}
    rows = (
        db.query(Favorite.target_id)
        .filter(
            Favorite.user_id == user.id,
            Favorite.target_type == "question",
            Favorite.target_id.in_(target_ids),
        )
        .all()
    )
    result: set[int] = set()
    for (target_id,) in rows:
        try:
            result.add(int(target_id))
        except (TypeError, ValueError):
            continue
    return result


def _require_rate_limit(request: Request, user: Optional[User]) -> None:
    """题目列表限流：登录用户按用户，游客按 IP。"""
    if user is not None:
        key = f"q:{user.id}"
    else:
        client_host = request.client.host if request.client else "unknown"
        key = f"ip:{client_host}"
    check_rate_limit(key, 120, 60)


@router.get("/questions")
def list_questions(
    request: Request,
    chapter_id: Optional[int] = Query(None, description="章节 ID，包含子孙章节"),
    mode: Optional[str] = Query(None, description="practice 普通模式 / random 随机模式"),
    year_only: bool = Query(False, description="仅显示带年份的题目"),
    province_code: Optional[str] = Query(None, max_length=16),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """按省份、章节获取已发布题目；非会员仅能看到免费题目。"""
    _require_rate_limit(request, current_user)

    # 省份优先级：查询参数 > 当前用户设置的省份
    resolved_province = (province_code or "").strip() or (
        current_user.province_code if current_user is not None else None
    )
    if not resolved_province:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先选择省份",
        )

    is_member = _is_member(db, current_user)
    chapters = _chapter_map(db, resolved_province)

    query = (
        db.query(Question)
        .outerjoin(Chapter, Chapter.id == Question.chapter_id)
        .filter(
            Question.province_code == resolved_province,
            Question.status == "published",
        )
    )
    if not is_member:
        query = query.filter(Question.is_free.is_(True))
    if chapter_id is not None:
        query = query.filter(
            Question.chapter_id.in_(_descendant_ids(chapters, chapter_id))
        )
    if year_only:
        query = query.filter(
            Question.year.isnot(None),
            Question.year != "",
        )

    questions = query.order_by(
        sa.func.coalesce(Chapter.sort_order, 0),
        Question.id,
    ).all()

    if mode == "random":
        # 以「用户+章节+省份」为种子打乱：同一场练习多次请求顺序稳定，
        # 避免答题页与答题卡取到不同顺序导致跳题错位。
        seed = (
            f"random:{current_user.id if current_user is not None else 'anonymous'}"
            f":{chapter_id}:{resolved_province}"
        )
        random.Random(seed).shuffle(questions)

    favorite_ids = _favorite_question_ids(
        db, current_user, [question.id for question in questions]
    )
    items = [
        question_public(
            question,
            chapter_name=(
                chapters[question.chapter_id].name
                if question.chapter_id in chapters
                else None
            ),
            is_favorited=question.id in favorite_ids,
        )
        for question in questions
    ]
    return {"items": items, "count": len(items)}


@router.post("/questions/{question_id}/answer")
def submit_practice_answer(
    question_id: int,
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """练习答题判分；登录用户写入答题记录，答错时更新错题本。"""
    question = db.get(Question, question_id)
    if question is None or question.status != "published":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="题目不存在",
        )

    if not _is_member(db, current_user) and not question.is_free:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该题目为会员专享，请先激活会员",
        )

    # 校验选项 key 是否合法
    option_keys = {
        str(option.get("key"))
        for option in (question.options or [])
        if isinstance(option, dict) and option.get("key") is not None
    }
    selected = [str(item) for item in payload.selected]
    if any(item not in option_keys for item in selected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="选项不合法",
        )

    answer_keys = {str(item) for item in (question.answer or [])}
    is_correct = set(selected) == answer_keys

    if current_user is not None:
        now = datetime.now()
        db.add(
            AnswerRecord(
                user_id=current_user.id,
                question_id=question.id,
                selected=selected,
                is_correct=is_correct,
                mode="practice",
                created_at=now,
            )
        )
        if not is_correct:
            wrong = (
                db.query(WrongQuestion)
                .filter(
                    WrongQuestion.user_id == current_user.id,
                    WrongQuestion.question_id == question.id,
                )
                .first()
            )
            if wrong is None:
                db.add(
                    WrongQuestion(
                        user_id=current_user.id,
                        question_id=question.id,
                        wrong_count=1,
                        last_wrong_at=now,
                        removed=False,
                    )
                )
            else:
                wrong.wrong_count = (wrong.wrong_count or 0) + 1
                wrong.last_wrong_at = now
                wrong.removed = False
        db.commit()

    chapter = db.get(Chapter, question.chapter_id) if question.chapter_id else None
    return {
        "question_id": question.id,
        "is_correct": is_correct,
        "selected": selected,
        "correct_answer": question.answer or [],
        "explanation": question.explanation,
        "chapter_name": chapter.name if chapter is not None else None,
    }
