"""错题本与收藏接口。"""

from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Chapter, Favorite, LawArticle, LawDocument, Question, User, WrongQuestion
from ..serializers import question_public

router = APIRouter(tags=["错题与收藏"])

FAVORITE_TYPES = {"question", "law_article"}


class FavoriteCreateRequest(BaseModel):
    """新增收藏请求。"""

    target_type: str = Field(..., max_length=16)
    target_id: str = Field(..., max_length=64)


def _chapter_map(db: Session) -> dict[int, Chapter]:
    """读取章节名称映射。"""
    return {chapter.id: chapter for chapter in db.query(Chapter).all()}


def _parse_target_id(raw: str) -> Optional[int]:
    """将收藏目标 ID 转为整数，非法返回 None。"""
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _validate_target_type(target_type: str) -> str:
    """校验收藏类型。"""
    value = (target_type or "").strip()
    if value not in FAVORITE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="收藏类型不合法",
        )
    return value


@router.get("/wrong")
def list_wrong_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """按章节分组返回当前用户未移除的错题。"""
    rows = (
        db.query(WrongQuestion, Question, Chapter)
        .join(Question, Question.id == WrongQuestion.question_id)
        .outerjoin(Chapter, Chapter.id == Question.chapter_id)
        .filter(
            WrongQuestion.user_id == current_user.id,
            WrongQuestion.removed.is_(False),
        )
        .order_by(
            sa.func.coalesce(Chapter.sort_order, 0),
            Question.id,
        )
        .all()
    )

    question_ids = [question.id for _, question, _ in rows]
    favorite_ids: set[int] = set()
    if question_ids:
        favorite_rows = (
            db.query(Favorite.target_id)
            .filter(
                Favorite.user_id == current_user.id,
                Favorite.target_type == "question",
                Favorite.target_id.in_({str(item) for item in question_ids}),
            )
            .all()
        )
        for (target_id,) in favorite_rows:
            try:
                favorite_ids.add(int(target_id))
            except (TypeError, ValueError):
                continue

    groups: dict[Optional[int], dict] = {}
    for wrong, question, chapter in rows:
        group = groups.get(question.chapter_id)
        if group is None:
            group = {
                "chapter_id": question.chapter_id,
                "chapter_name": chapter.name if chapter is not None else "未分类",
                "items": [],
            }
            groups[question.chapter_id] = group
        group["items"].append(
            {
                "question": question_public(
                    question,
                    chapter_name=chapter.name if chapter is not None else None,
                    is_favorited=question.id in favorite_ids,
                ),
                "wrong_count": wrong.wrong_count,
                "last_wrong_at": (
                    wrong.last_wrong_at.isoformat() if wrong.last_wrong_at else None
                ),
            }
        )

    return {"total": len(rows), "groups": list(groups.values())}


@router.delete("/wrong/{question_id}")
def remove_wrong_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """将错题标记为已移除（不物理删除记录）。"""
    wrong = (
        db.query(WrongQuestion)
        .filter(
            WrongQuestion.user_id == current_user.id,
            WrongQuestion.question_id == question_id,
        )
        .first()
    )
    if wrong is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="错题不存在",
        )
    wrong.removed = True
    db.commit()
    return {"ok": True}


@router.get("/favorites")
def list_favorites(
    target_type: Optional[str] = Query(None, max_length=16),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """返回当前用户的收藏列表，可按类型筛选。"""
    cleaned_type = (target_type or "").strip()
    if cleaned_type:
        cleaned_type = _validate_target_type(cleaned_type)

    query = db.query(Favorite).filter(Favorite.user_id == current_user.id)
    if cleaned_type:
        query = query.filter(Favorite.target_type == cleaned_type)
    favorites = query.order_by(Favorite.id.desc()).all()

    question_ids: list[int] = []
    article_ids: list[int] = []
    for favorite in favorites:
        target_id = _parse_target_id(favorite.target_id)
        if target_id is None:
            continue
        if favorite.target_type == "question":
            question_ids.append(target_id)
        elif favorite.target_type == "law_article":
            article_ids.append(target_id)

    questions = (
        db.query(Question).filter(Question.id.in_(set(question_ids))).all()
        if question_ids
        else []
    )
    question_map = {question.id: question for question in questions}
    chapters = _chapter_map(db)

    articles = (
        db.query(LawArticle, LawDocument)
        .join(LawDocument, LawDocument.id == LawArticle.document_id)
        .filter(LawArticle.id.in_(set(article_ids)))
        .all()
        if article_ids
        else []
    )
    article_map = {
        article.id: (article, document) for article, document in articles
    }

    items: list[dict] = []
    for favorite in favorites:
        target_id = _parse_target_id(favorite.target_id)
        if target_id is None:
            continue
        base = {
            "id": favorite.id,
            "target_type": favorite.target_type,
            "target_id": favorite.target_id,
        }
        if favorite.target_type == "question":
            question = question_map.get(target_id)
            if question is None:
                continue
            chapter = chapters.get(question.chapter_id)
            base["question"] = question_public(
                question,
                chapter_name=chapter.name if chapter is not None else None,
                is_favorited=True,
            )
        elif favorite.target_type == "law_article":
            pair = article_map.get(target_id)
            if pair is None:
                continue
            article, document = pair
            base["law_article"] = {
                "id": article.id,
                "article_no": article.article_no,
                "chapter_title": article.chapter_title,
                "content": article.content,
            }
            base["law_document"] = {
                "id": document.id,
                "title": document.title,
                "status": document.status,
                "category": document.category,
                "issuer": document.issuer,
                "province_code": document.province_code,
                "publish_date": (
                    document.publish_date.isoformat()
                    if document.publish_date is not None
                    else None
                ),
            }
        else:
            continue
        items.append(base)

    return {"items": items}


@router.post("/favorites")
def create_favorite(
    payload: FavoriteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """新增收藏；已收藏时幂等返回。"""
    target_type = _validate_target_type(payload.target_type)
    target_id = _parse_target_id(payload.target_id)
    if target_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏目标不存在",
        )

    if target_type == "question":
        exists = db.get(Question, target_id)
    else:
        exists = db.get(LawArticle, target_id)
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏目标不存在",
        )

    normalized_id = str(target_id)
    favorite = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user.id,
            Favorite.target_type == target_type,
            Favorite.target_id == normalized_id,
        )
        .first()
    )
    if favorite is not None:
        return {"ok": True, "created": False}

    db.add(
        Favorite(
            user_id=current_user.id,
            target_type=target_type,
            target_id=normalized_id,
        )
    )
    db.commit()
    return {"ok": True, "created": True}


@router.delete("/favorites/{target_type}/{target_id}")
def delete_favorite(
    target_type: str,
    target_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """取消收藏。"""
    cleaned_type = _validate_target_type(target_type)
    parsed_id = _parse_target_id(target_id)
    if parsed_id is None:
        return {"ok": True}

    favorite = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user.id,
            Favorite.target_type == cleaned_type,
            Favorite.target_id == str(parsed_id),
        )
        .first()
    )
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return {"ok": True}
