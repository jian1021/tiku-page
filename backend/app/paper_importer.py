"""把内置题库（app/fixtures/papers.py）写入数据库。

特点：
- 幂等：章节按「省份 + 父级 + 名称」判重，题目按「省份 + 题干」判重，
  重复执行不会产生副本，也不会覆盖管理员已修改的题目。
- 事务：整批写入，任一步失败整体回滚。

用法（在 backend 目录）：

    python import_papers.py            # 默认写入 SC（四川省）
    python import_papers.py --dry-run  # 只统计，不写库
"""

from typing import Optional

from sqlalchemy.orm import Session

from .fixtures.papers import PAPERS
from .models import Chapter, Question

DEFAULT_PROVINCE = "SC"


def _ensure_chapter(
    db: Session,
    province_code: str,
    name: str,
    parent_id: Optional[int],
    sort_order: int,
    created: list[str],
) -> Chapter:
    """按省份 + 父级 + 名称查找章节，不存在则创建。"""
    query = db.query(Chapter).filter(
        Chapter.province_code == province_code,
        Chapter.name == name,
    )
    query = (
        query.filter(Chapter.parent_id.is_(None))
        if parent_id is None
        else query.filter(Chapter.parent_id == parent_id)
    )
    chapter = query.first()
    if chapter is not None:
        return chapter

    chapter = Chapter(
        name=name,
        parent_id=parent_id,
        province_code=province_code,
        sort_order=sort_order,
    )
    db.add(chapter)
    db.flush()
    created.append(name)
    return chapter


def import_papers(
    db: Session,
    province_code: str = DEFAULT_PROVINCE,
    dry_run: bool = False,
) -> dict:
    """导入全部内置套题，返回统计结果。"""
    stats = {
        "province_code": province_code,
        "papers": 0,
        "chapters_created": 0,
        "questions_created": 0,
        "questions_skipped": 0,
        "details": [],
    }

    created_chapters: list[str] = []

    for paper in PAPERS:
        root = _ensure_chapter(
            db,
            province_code=province_code,
            name=paper["title"],
            parent_id=None,
            sort_order=paper["sort_order"],
            created=created_chapters,
        )

        chapter_map = {"__root__": root}
        for key, name, sort_order in paper["chapters"]:
            chapter_map[key] = _ensure_chapter(
                db,
                province_code=province_code,
                name=name,
                parent_id=root.id,
                sort_order=sort_order,
                created=created_chapters,
            )

        paper_created = 0
        for item in paper["questions"]:
            exists = (
                db.query(Question.id)
                .filter(
                    Question.province_code == province_code,
                    Question.stem == item["stem"],
                )
                .first()
            )
            if exists is not None:
                stats["questions_skipped"] += 1
                continue

            db.add(
                Question(
                    province_code=province_code,
                    chapter_id=chapter_map[item["chapter"]].id,
                    type=item["type"],
                    stem=item["stem"],
                    options=item["options"],
                    answer=item["answer"],
                    explanation=item.get("explain"),
                    difficulty=item.get("difficulty", "medium"),
                    year=paper["year"],
                    source_note=item.get("source_note") or paper["source_note"],
                    is_free=item.get("is_free", False),
                    status="published",
                )
            )
            paper_created += 1

        stats["papers"] += 1
        stats["questions_created"] += paper_created
        stats["details"].append(
            {
                "key": paper["key"],
                "title": paper["title"],
                "questions": paper_created,
            }
        )

    stats["chapters_created"] = len(created_chapters)

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return stats
