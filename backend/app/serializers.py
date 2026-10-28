"""题目序列化工具：统一公开题目与含答案题目的输出结构。"""

from typing import Optional

from .models import Question


def question_public(
    q: Question,
    chapter_name: Optional[str] = None,
    is_favorited: bool = False,
) -> dict:
    """输出题目的公开字段（不含答案与解析）。"""
    return {
        "id": q.id,
        "province_code": q.province_code,
        "chapter_id": q.chapter_id,
        "chapter_name": chapter_name,
        "type": q.type,
        "stem": q.stem,
        "options": q.options or [],
        "difficulty": q.difficulty,
        "year": q.year,
        "source_note": q.source_note,
        "is_free": bool(q.is_free),
        "is_favorited": bool(is_favorited),
    }


def question_with_answer(
    q: Question,
    chapter_name: Optional[str] = None,
    is_favorited: bool = False,
) -> dict:
    """在公开字段基础上补充正确答案与解析。"""
    data = question_public(q, chapter_name=chapter_name, is_favorited=is_favorited)
    data["correct_answer"] = q.answer or []
    data["explanation"] = q.explanation
    return data
