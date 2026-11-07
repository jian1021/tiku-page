"""内置题库清单。

每个套餐（PAPERS）包含：章节树、题目列表、来源说明。
`app.paper_importer` 按此结构写入数据库，题面按省份 + 题干判重，可重复执行。
"""

from typing import Callable, Iterable

from . import paper_2026_case, paper_2026_judge, paper_2026_multi, paper_2026_single
from . import paper_renew_2026b


def _attach(
    questions: Iterable[dict],
    chapter: str,
    is_free: Callable[[dict], bool],
) -> list[dict]:
    """给题目补上所属章节与是否免费。"""
    items = []
    for question in questions:
        data = dict(question)
        data["chapter"] = chapter
        data["is_free"] = bool(is_free(question))
        items.append(data)
    return items


PAPERS = [
    {
        "key": "paper_2026",
        "title": "2026 年备考练习题",
        "sort_order": 10,
        "year": "2026",
        "source_note": (
            "《四川省政府采购评审专家考试备考练习题（2026）》，"
            "来源：微信公众号「周芳的极简财务思维」2026-10-26"
        ),
        "chapters": [
            ("single", "第一部分 单项选择题", 11),
            ("multi", "第二部分 多项选择题", 12),
            ("judge", "第三部分 判断题", 13),
            ("case", "第四部分 案例分析题", 14),
        ],
        "questions": (
            _attach(paper_2026_single.QUESTIONS, "single", lambda q: q["no"] <= 10)
            + _attach(paper_2026_multi.QUESTIONS, "multi", lambda q: q["no"] <= 5)
            + _attach(paper_2026_judge.QUESTIONS, "judge", lambda q: True)
            + _attach(paper_2026_case.QUESTIONS, "case", lambda q: False)
        ),
    },
    {
        "key": "renew_2026b",
        "title": "2026 续聘真题模拟（二）",
        "sort_order": 20,
        "year": "2026",
        "source_note": (
            "《2026年度四川省政府采购评审专家库续聘真题模拟（二）》，"
            "来源：微信公众号「风行评标采购」2026-10-16"
        ),
        "chapters": [
            ("single", "一、单项选择题（题号 16-25）", 21),
            ("multi", "二、多项选择题（题号 26-30）", 22),
        ],
        "questions": (
            _attach(
                [q for q in paper_renew_2026b.QUESTIONS if q["type"] == "single"],
                "single",
                lambda q: q["no"] <= 20,
            )
            + _attach(
                [q for q in paper_renew_2026b.QUESTIONS if q["type"] == "multi"],
                "multi",
                lambda q: q["no"] <= 27,
            )
        ),
    },
]


__all__ = ["PAPERS"]
