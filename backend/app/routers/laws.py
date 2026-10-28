"""法规列表、详情与检索接口。"""

from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional
from ..models import Favorite, LawArticle, LawDocument, User

router = APIRouter(tags=["法规"])

# 排序权重：现行有效 > 已修订 > 已废止
_STATUS_ORDER = sa.case(
    (LawDocument.status == "effective", 0),
    (LawDocument.status == "revised", 1),
    (LawDocument.status == "repealed", 2),
    else_=3,
)


def _visibility_filter(province_code: Optional[str]):
    """构造法规可见范围条件：指定省份时包含全国法规。"""
    province = (province_code or "").strip()
    if province:
        return sa.or_(
            LawDocument.province_code == province,
            LawDocument.province_code == "national",
        )
    return LawDocument.province_code == "national"


def _iso_date(value) -> Optional[str]:
    """日期转 isoformat 字符串。"""
    return value.isoformat() if value is not None else None


def _document_dict(document: LawDocument, article_count: Optional[int] = None) -> dict:
    """法规文档公开字段。"""
    data = {
        "id": document.id,
        "title": document.title,
        "category": document.category,
        "issuer": document.issuer,
        "publish_date": _iso_date(document.publish_date),
        "revise_date": _iso_date(document.revise_date),
        "status": document.status,
        "province_code": document.province_code,
    }
    if article_count is not None:
        data["article_count"] = article_count
    return data


def _article_dict(article: LawArticle) -> dict:
    """法规条文公开字段。"""
    return {
        "id": article.id,
        "article_no": article.article_no,
        "chapter_title": article.chapter_title,
        "content": article.content,
        "sort_order": article.sort_order,
    }


def _find_positions(content: Optional[str], keyword: str) -> list[int]:
    """不区分大小写地扫描关键词在文本中的所有起始下标。"""
    if not content or not keyword:
        return []
    lowered = content.lower()
    needle = keyword.lower()
    positions: list[int] = []
    index = lowered.find(needle)
    while index != -1:
        positions.append(index)
        index = lowered.find(needle, index + max(1, len(needle)))
    return positions


def _favorite_article_ids(
    db: Session, current_user: Optional[User], article_ids: list[int]
) -> set[int]:
    """当前用户收藏的法规条文 ID 集合。"""
    if current_user is None or not article_ids:
        return set()
    rows = (
        db.query(Favorite.target_id)
        .filter(
            Favorite.user_id == current_user.id,
            Favorite.target_type == "law_article",
            Favorite.target_id.in_({str(item) for item in article_ids}),
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


@router.get("/laws")
def list_laws(
    province_code: Optional[str] = Query(None, max_length=16),
    category: Optional[str] = Query(None, max_length=32),
    status_filter: Optional[str] = Query(None, alias="status", max_length=16),
    db: Session = Depends(get_db),
) -> dict:
    """返回可见法规列表，自动按生效状态排序。"""
    count_subquery = (
        db.query(
            LawArticle.document_id.label("document_id"),
            sa.func.count(LawArticle.id).label("article_count"),
        )
        .group_by(LawArticle.document_id)
        .subquery()
    )

    query = (
        db.query(
            LawDocument,
            sa.func.coalesce(count_subquery.c.article_count, 0),
        )
        .outerjoin(
            count_subquery,
            count_subquery.c.document_id == LawDocument.id,
        )
        .filter(_visibility_filter(province_code))
    )
    if category:
        query = query.filter(LawDocument.category == category)
    if status_filter:
        query = query.filter(LawDocument.status == status_filter)

    rows = query.order_by(_STATUS_ORDER, LawDocument.id).all()
    items = [
        _document_dict(document, int(article_count or 0))
        for document, article_count in rows
    ]
    return {"items": items}


# 注意：/laws/search 必须注册在 /laws/{document_id} 之前
@router.get("/laws/search")
def search_laws(
    q: str = Query(..., min_length=1, max_length=128),
    province_code: Optional[str] = Query(None, max_length=16),
    db: Session = Depends(get_db),
) -> dict:
    """在法规标题与条文中模糊检索。"""
    keyword = q.strip()
    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="搜索关键词不能为空",
        )

    pattern = f"%{keyword.lower()}%"
    rows = (
        db.query(LawArticle, LawDocument)
        .join(LawDocument, LawDocument.id == LawArticle.document_id)
        .filter(_visibility_filter(province_code))
        .filter(
            sa.or_(
                sa.func.lower(LawArticle.content).like(pattern),
                sa.func.lower(LawDocument.title).like(pattern),
            )
        )
        .order_by(
            _STATUS_ORDER,
            LawDocument.id,
            LawArticle.sort_order,
            LawArticle.id,
        )
        .all()
    )

    # 批量统计文档条数，避免逐条查询
    document_ids = {document.id for _, document in rows}
    count_map: dict[int, int] = {}
    if document_ids:
        count_rows = (
            db.query(LawArticle.document_id, sa.func.count(LawArticle.id))
            .filter(LawArticle.document_id.in_(document_ids))
            .group_by(LawArticle.document_id)
            .all()
        )
        count_map = {document_id: count for document_id, count in count_rows}

    hits = []
    lowered_keyword = keyword.lower()
    for article, document in rows:
        hits.append(
            {
                "document": _document_dict(
                    document, count_map.get(document.id, 0)
                ),
                "article": _article_dict(article),
                "positions": _find_positions(article.content, keyword),
                "title_hit": lowered_keyword in (document.title or "").lower(),
            }
        )
    return {"q": keyword, "total": len(hits), "hits": hits}


@router.get("/laws/{document_id}")
def get_law(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """返回法规详情及全部条文，登录用户标记收藏状态。"""
    document = db.get(LawDocument, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="法规不存在",
        )

    articles = (
        db.query(LawArticle)
        .filter(LawArticle.document_id == document.id)
        .order_by(LawArticle.sort_order, LawArticle.id)
        .all()
    )
    favorite_ids = _favorite_article_ids(
        db, current_user, [article.id for article in articles]
    )

    article_items = []
    for article in articles:
        item = _article_dict(article)
        item["is_favorited"] = article.id in favorite_ids
        article_items.append(item)

    return {
        "document": _document_dict(document, len(articles)),
        "articles": article_items,
    }
