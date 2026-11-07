"""内置题库数据包。

每个模块以纯 Python 数据结构保存一套题，由 `app.paper_importer` 负责写入数据库。
数据与逻辑分离，便于后续替换或新增套题。
"""

from typing import Iterable


def opt(*texts: str) -> list[dict]:
    """把选项文本按顺序转成 A/B/C/D... 的选项列表。

    例：opt("公开招标", "邀请招标") ->
        [{"key": "A", "text": "公开招标"}, {"key": "B", "text": "邀请招标"}]
    """
    return [{"key": chr(ord("A") + index), "text": text} for index, text in enumerate(texts)]


def judge_options() -> list[dict]:
    """判断题固定选项。"""
    return opt("正确", "错误")


__all__ = ["opt", "judge_options"]
