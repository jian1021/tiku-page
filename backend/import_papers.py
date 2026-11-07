"""命令行工具：把内置题库写入数据库。

在 backend 目录执行：

    python import_papers.py                 # 写入四川省题库
    python import_papers.py --dry-run       # 只统计不落库
    python import_papers.py --create-tables # 新库首次使用，先建表再导入

可重复执行：已存在的题目会跳过，不会产生重复，也不会覆盖人工修订过的题目。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.paper_importer import import_papers  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="导入内置题库")
    parser.add_argument("--province", default="SC", help="省份代码，默认 SC")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="导入前先建表（新库首次使用）",
    )
    args = parser.parse_args()

    if args.create_tables:
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        stats = import_papers(
            db,
            province_code=args.province,
            dry_run=args.dry_run,
        )
    finally:
        db.close()

    print(f"省份：{stats['province_code']}{'（试运行，未写入）' if args.dry_run else ''}")
    for detail in stats["details"]:
        print(f"  - {detail['title']}：新增 {detail['questions']} 题")
    print(
        "汇总："
        f"套题 {stats['papers']} 套，"
        f"新增章节 {stats['chapters_created']} 个，"
        f"新增题目 {stats['questions_created']} 道，"
        f"跳过已存在 {stats['questions_skipped']} 道"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
