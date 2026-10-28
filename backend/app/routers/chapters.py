"""章节与省份相关接口。"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user_optional
from ..models import AnswerRecord, Chapter, Question, User

router = APIRouter(tags=["章节"])

# 省份代码与名称（全量支持列表）
PROVINCES: list[tuple[str, str]] = [
    ("SC", "四川省"),
    ("BJ", "北京市"),
    ("TJ", "天津市"),
    ("HE", "河北省"),
    ("SX", "山西省"),
    ("NM", "内蒙古自治区"),
    ("LN", "辽宁省"),
    ("JL", "吉林省"),
    ("HL", "黑龙江省"),
    ("SH", "上海市"),
    ("JS", "江苏省"),
    ("ZJ", "浙江省"),
    ("AH", "安徽省"),
    ("FJ", "福建省"),
    ("JX", "江西省"),
    ("SD", "山东省"),
    ("HA", "河南省"),
    ("HB", "湖北省"),
    ("HN", "湖南省"),
    ("GD", "广东省"),
    ("GX", "广西壮族自治区"),
    ("HI", "海南省"),
    ("CQ", "重庆市"),
    ("GZ", "贵州省"),
    ("YN", "云南省"),
    ("XZ", "西藏自治区"),
    ("SN", "陕西省"),
    ("GS", "甘肃省"),
    ("QH", "青海省"),
    ("NX", "宁夏回族自治区"),
    ("XJ", "新疆维吾尔自治区"),
    ("TW", "台湾省"),
    ("HK", "香港特别行政区"),
    ("MO", "澳门特别行政区"),
]

# 当前已开放题库的省份
OPEN_PROVINCES: set[str] = {"SC"}


def _chapter_node(chapter: Chapter) -> dict:
    """构造章节树节点。"""
    return {
        "id": chapter.id,
        "name": chapter.name,
        "province_code": chapter.province_code,
        "sort_order": chapter.sort_order,
        "question_count": 0,
        "answered_count": 0,
        "children": [],
    }


def _aggregate(node: dict) -> None:
    """递归汇总子章节的题量 / 已做数到父章节。"""
    total = node["_own_question_count"]
    answered = node["_own_answered_count"]
    for child in node["children"]:
        _aggregate(child)
        total += child["question_count"]
        answered += child["answered_count"]
    node["question_count"] = total
    node["answered_count"] = answered


def _sort_tree(nodes: list[dict]) -> None:
    """按 sort_order、id 递归排序章节树。"""
    nodes.sort(key=lambda item: (item["sort_order"] or 0, item["id"]))
    for node in nodes:
        _sort_tree(node["children"])


@router.get("/chapters")
def list_chapters(
    province_code: str = Query(..., min_length=1, max_length=16, description="省份代码"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> list[dict]:
    """返回指定省份的章节树，附带题量与当前用户已做数（含子章节汇总）。"""
    chapters = (
        db.query(Chapter)
        .filter(Chapter.province_code == province_code)
        .all()
    )

    # 每章节已发布题目数
    question_rows = (
        db.query(Question.chapter_id, func.count(Question.id))
        .filter(
            Question.province_code == province_code,
            Question.status == "published",
        )
        .group_by(Question.chapter_id)
        .all()
    )
    question_counts = {chapter_id: count for chapter_id, count in question_rows}

    # 当前用户已答题数（去重）
    answered_map: dict[int, set[int]] = {}
    if current_user is not None:
        answered_rows = (
            db.query(Question.chapter_id, AnswerRecord.question_id)
            .join(Question, Question.id == AnswerRecord.question_id)
            .filter(
                AnswerRecord.user_id == current_user.id,
                Question.province_code == province_code,
            )
            .distinct()
            .all()
        )
        for chapter_id, question_id in answered_rows:
            if chapter_id is None:
                continue
            answered_map.setdefault(chapter_id, set()).add(question_id)

    nodes = {chapter.id: _chapter_node(chapter) for chapter in chapters}
    for chapter in chapters:
        node = nodes[chapter.id]
        node["_own_question_count"] = question_counts.get(chapter.id, 0)
        node["_own_answered_count"] = len(answered_map.get(chapter.id, set()))

    roots: list[dict] = []
    for chapter in chapters:
        node = nodes[chapter.id]
        parent = nodes.get(chapter.parent_id)
        if parent is None:
            # parent_id 为空，或父章节不在当前省份时作为顶级节点
            roots.append(node)
        else:
            parent["children"].append(node)

    _sort_tree(roots)
    for root in roots:
        _aggregate(root)
        _strip_internal(root)
    return roots


def _strip_internal(node: dict) -> None:
    """移除内部计算字段，避免返回给前端。"""
    node.pop("_own_question_count", None)
    node.pop("_own_answered_count", None)
    for child in node["children"]:
        _strip_internal(child)


@router.get("/provinces")
def list_provinces() -> list[dict]:
    """返回支持的省份列表及开放状态。"""
    return [
        {"code": code, "name": name, "open": code in OPEN_PROVINCES}
        for code, name in PROVINCES
    ]
