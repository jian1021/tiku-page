"""幂等种子数据脚本。

在 backend 目录执行：

    python seed.py

说明：
- 可重复执行，已存在的数据不会重复写入。
- 会创建管理员、示例考生（含一个已激活会员）、章节、示例题目、
  示例法规、激活码、站点配置与考试参数。
- exam_configs 中的题量 20、时长 120、及格分 60、总分 100 以及题型分布
  均为占位示例值，需由管理员在管理后台确认后修改为正式配置。
"""

from datetime import datetime, timedelta
from typing import Optional

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 只用 app 包这一套模型，避免误用旧版扁平模块（backend/models.py）建出另一套元数据
from app.auth import hash_password, verify_password
from app.database import Base, SessionLocal, engine
from app.models import (
    ActivationCode,
    Chapter,
    ExamConfig,
    LawArticle,
    LawDocument,
    Membership,
    Question,
    SiteConfig,
    User,
)

SOURCE_NOTE = "示例题目，仅用于系统联调，不代表真实考试内容"
EXPLANATION = "本题为系统示例题目，仅用于功能联调，不代表真实考试内容。"
LAW_PLACEHOLDER = (
    "【示例条文】本条为系统联调占位内容，非真实法规条文，"
    "仅用于展示法规检索、详情与收藏功能。"
)

# 章节结构：key -> (名称, 父级 key, sort_order)
CHAPTERS = [
    ("ch1", "第一章 政府采购基础", None, 1),
    ("ch1_1", "第一节 基本概念", "ch1", 2),
    ("ch1_2", "第二节 采购方式", "ch1", 3),
    ("ch2", "第二章 政府采购实务", None, 4),
    ("ch2_1", "第一节 程序与文件", "ch2", 5),
    ("ch2_2", "第二节 评审与监督", "ch2", 6),
]

QUESTIONS = [
    {
        "chapter": "ch1_1",
        "type": "single",
        "stem": "政府采购应当遵循的基本原则不包括下列哪一项？",
        "options": [
            {"key": "A", "text": "公开透明"},
            {"key": "B", "text": "公平竞争"},
            {"key": "C", "text": "任意指定供应商"},
            {"key": "D", "text": "诚实信用"},
        ],
        "answer": ["C"],
        "difficulty": "easy",
        "is_free": True,
    },
    {
        "chapter": "ch1_1",
        "type": "judge",
        "stem": "政府采购只能采用公开招标一种方式。",
        "options": [
            {"key": "A", "text": "正确"},
            {"key": "B", "text": "错误"},
        ],
        "answer": ["B"],
        "difficulty": "easy",
        "is_free": True,
    },
    {
        "chapter": "ch1_1",
        "type": "multi",
        "stem": "政府采购通常应当遵循的原则包括哪些？",
        "options": [
            {"key": "A", "text": "公开透明"},
            {"key": "B", "text": "公平竞争"},
            {"key": "C", "text": "公正"},
            {"key": "D", "text": "诚实信用"},
        ],
        "answer": ["A", "B", "C", "D"],
        "difficulty": "medium",
        "is_free": False,
    },
    {
        "chapter": "ch1_2",
        "type": "single",
        "stem": "下列哪一项属于政府采购方式？",
        "options": [
            {"key": "A", "text": "公开招标"},
            {"key": "B", "text": "私下议价"},
            {"key": "C", "text": "任意采购"},
            {"key": "D", "text": "口头委托"},
        ],
        "answer": ["A"],
        "difficulty": "easy",
        "is_free": True,
    },
    {
        "chapter": "ch1_2",
        "type": "multi",
        "stem": "政府采购常用的采购方式包括哪些？",
        "options": [
            {"key": "A", "text": "公开招标"},
            {"key": "B", "text": "邀请招标"},
            {"key": "C", "text": "竞争性谈判"},
            {"key": "D", "text": "单一来源采购"},
        ],
        "answer": ["A", "B", "C", "D"],
        "difficulty": "medium",
        "is_free": False,
    },
    {
        "chapter": "ch2_1",
        "type": "single",
        "stem": "采购人编制采购文件时，首先应当明确的是哪项内容？",
        "options": [
            {"key": "A", "text": "采购需求"},
            {"key": "B", "text": "供应商名单"},
            {"key": "C", "text": "评审专家"},
            {"key": "D", "text": "合同金额"},
        ],
        "answer": ["A"],
        "difficulty": "medium",
        "is_free": False,
    },
    {
        "chapter": "ch2_1",
        "type": "multi",
        "stem": "采购文件通常应当包含哪些内容？",
        "options": [
            {"key": "A", "text": "采购需求"},
            {"key": "B", "text": "评审标准"},
            {"key": "C", "text": "合同主要条款"},
            {"key": "D", "text": "供应商内部财务资料"},
        ],
        "answer": ["A", "B", "C"],
        "difficulty": "medium",
        "is_free": False,
    },
    {
        "chapter": "ch2_2",
        "type": "single",
        "stem": "评审活动应当遵循的基本要求是？",
        "options": [
            {"key": "A", "text": "客观公正"},
            {"key": "B", "text": "随意打分"},
            {"key": "C", "text": "泄露评审情况"},
            {"key": "D", "text": "私下接触供应商"},
        ],
        "answer": ["A"],
        "difficulty": "easy",
        "is_free": False,
    },
    {
        "chapter": "ch2_2",
        "type": "judge",
        "stem": "评审专家应当独立、客观、公正地履行评审职责。",
        "options": [
            {"key": "A", "text": "正确"},
            {"key": "B", "text": "错误"},
        ],
        "answer": ["A"],
        "difficulty": "easy",
        "is_free": False,
    },
]

LAW_DOCUMENTS = [
    {
        "title": "示例：政府采购法（联调数据）",
        "province_code": "national",
        "category": "国家法律",
        "status": "effective",
        "articles": [
            ("第一条", "第一章 总则（示例）"),
            ("第二条", "第一章 总则（示例）"),
            ("第三条", "第二章 示例条款（示例）"),
        ],
    },
    {
        "title": "示例：四川省政府采购实施办法（联调数据）",
        "province_code": "SC",
        "category": "地方规定",
        "status": "repealed",
        "articles": [
            ("第一条", "第一章 总则（示例）"),
            ("第二条", "第二章 示例条款（示例）"),
        ],
    },
    {
        "title": "示例：政府采购法实施条例（联调数据）",
        "province_code": "national",
        "category": "行政法规",
        "status": "revised",
        "articles": [
            ("第一条", "第一章 总则（示例）"),
            ("第二条", "第二章 示例条款（示例）"),
            ("第三条", "第三章 示例条款（示例）"),
        ],
    },
]


def _ensure_user(
    db,
    phone: str,
    password: str,
    nickname: Optional[str] = None,
    role: str = "user",
    province_code: Optional[str] = None,
) -> User:
    """按手机号创建或更新用户。"""
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = User(
            phone=phone,
            password_hash=hash_password(password),
            nickname=nickname,
            province_code=province_code,
            settings={},
            role=role,
        )
        db.add(user)
        db.flush()
        return user

    # 已存在时仅补齐必要字段，避免覆盖用户已修改的资料
    if not verify_password(password, user.password_hash):
        user.password_hash = hash_password(password)
    if role and user.role != role:
        user.role = role
    if nickname is not None:
        user.nickname = nickname
    if province_code is not None:
        user.province_code = province_code
    if user.settings is None:
        user.settings = {}
    return user


def _ensure_membership(db, user: User, days: int) -> None:
    """确保用户拥有至少 days 天的有效会员（已有效则不缩短）。"""
    now = datetime.now()
    membership = (
        db.query(Membership).filter(Membership.user_id == user.id).first()
    )
    if membership is None:
        membership = Membership(
            user_id=user.id,
            expires_at=now + timedelta(days=days),
        )
        db.add(membership)
        return
    if membership.expires_at is None or membership.expires_at <= now:
        membership.expires_at = now + timedelta(days=days)


def _ensure_chapter(
    db,
    key: str,
    name: str,
    parent_id: Optional[int],
    sort_order: int,
    chapter_map: dict[str, Chapter],
) -> Chapter:
    """按省份、父级与名称查找或创建章节。"""
    query = db.query(Chapter).filter(
        Chapter.province_code == "SC",
        Chapter.name == name,
    )
    if parent_id is None:
        query = query.filter(Chapter.parent_id.is_(None))
    else:
        query = query.filter(Chapter.parent_id == parent_id)
    chapter = query.first()
    if chapter is None:
        chapter = Chapter(
            name=name,
            parent_id=parent_id,
            province_code="SC",
            sort_order=sort_order,
        )
        db.add(chapter)
        db.flush()
    chapter_map[key] = chapter
    return chapter


def _seed_chapters(db) -> dict[str, Chapter]:
    """写入四川省示例章节树。"""
    chapter_map: dict[str, Chapter] = {}
    for key, name, parent_key, sort_order in CHAPTERS:
        parent_id = (
            chapter_map[parent_key].id if parent_key is not None else None
        )
        _ensure_chapter(
            db,
            key=key,
            name=name,
            parent_id=parent_id,
            sort_order=sort_order,
            chapter_map=chapter_map,
        )
    return chapter_map


def _seed_questions(db, chapter_map: dict[str, Chapter]) -> None:
    """写入示例题目，按题干判重。"""
    for item in QUESTIONS:
        exists = (
            db.query(Question)
            .filter(
                Question.province_code == "SC",
                Question.stem == item["stem"],
            )
            .first()
        )
        if exists is not None:
            continue
        db.add(
            Question(
                province_code="SC",
                chapter_id=chapter_map[item["chapter"]].id,
                type=item["type"],
                stem=item["stem"],
                options=item["options"],
                answer=item["answer"],
                explanation=EXPLANATION,
                difficulty=item["difficulty"],
                year=None,
                source_note=SOURCE_NOTE,
                law_article_ids=None,
                is_free=item["is_free"],
                status="published",
            )
        )


def _seed_laws(db) -> None:
    """写入示例法规与占位条文。"""
    for document_data in LAW_DOCUMENTS:
        document = (
            db.query(LawDocument)
            .filter(LawDocument.title == document_data["title"])
            .first()
        )
        if document is None:
            document = LawDocument(
                title=document_data["title"],
                province_code=document_data["province_code"],
                category=document_data["category"],
                issuer="示例单位",
                publish_date=None,
                revise_date=None,
                status=document_data["status"],
            )
            db.add(document)
            db.flush()

        for index, (article_no, chapter_title) in enumerate(
            document_data["articles"], start=1
        ):
            exists = (
                db.query(LawArticle)
                .filter(
                    LawArticle.document_id == document.id,
                    LawArticle.article_no == article_no,
                )
                .first()
            )
            if exists is not None:
                continue
            db.add(
                LawArticle(
                    document_id=document.id,
                    article_no=article_no,
                    chapter_title=chapter_title,
                    content=f"{LAW_PLACEHOLDER}（占位条文{index}）",
                    sort_order=index,
                )
            )


def _seed_activation_codes(db) -> None:
    """写入示例激活码；已存在时不重置使用状态。"""
    codes = [
        ("DEMO-30D-0001", 30, "unused"),
        ("DEMO-7D-0001", 7, "unused"),
        ("DEMO-DISABLED", 30, "disabled"),
    ]
    for code, days, code_status in codes:
        exists = (
            db.query(ActivationCode)
            .filter(ActivationCode.code == code)
            .first()
        )
        if exists is not None:
            continue
        db.add(
            ActivationCode(
                code=code,
                duration_days=days,
                status=code_status,
                note="示例激活码",
            )
        )


def _seed_site_configs(db) -> None:
    """写入站点配置默认值，不覆盖管理员已配置内容。"""
    defaults = {
        "service_phone": "",
        "service_wechat": "",
        "service_intro": (
            "标书审查与招标文件咨询服务（示例介绍，请管理员在后台配置正式内容）。"
        ),
    }
    for key, value in defaults.items():
        exists = db.query(SiteConfig).filter(SiteConfig.key == key).first()
        if exists is None:
            db.add(SiteConfig(key=key, value=value))


def _seed_exam_configs(db) -> None:
    """写入 SC 省考试配置占位值，不覆盖管理员已配置内容。"""
    # 以下数值均为待管理员确认的占位示例值
    values = {
        "question_count": "20",
        "duration_minutes": "120",
        "pass_score": "60",
        "total_score": "100",
        "type_distribution": '{"single": 10, "multi": 4, "judge": 6}',
    }
    for key, value in values.items():
        exists = (
            db.query(ExamConfig)
            .filter(
                ExamConfig.province_code == "SC",
                ExamConfig.key == key,
            )
            .first()
        )
        if exists is None:
            db.add(
                ExamConfig(
                    province_code="SC",
                    key=key,
                    value=value,
                )
            )


def seed() -> None:
    """执行幂等种子写入。"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = _ensure_user(
            db,
            phone="admin",
            password="admin123",
            nickname="系统管理员",
            role="admin",
        )
        _ensure_user(
            db,
            phone="13800138000",
            password="test1234",
            nickname="示例考生（未激活）",
            role="user",
            province_code="SC",
        )
        member = _ensure_user(
            db,
            phone="13900139000",
            password="test1234",
            nickname="示例考生（已激活）",
            role="user",
            province_code="SC",
        )
        _ensure_membership(db, member, 30)

        chapter_map = _seed_chapters(db)
        _seed_questions(db, chapter_map)
        _seed_laws(db)
        _seed_activation_codes(db)
        _seed_site_configs(db)
        _seed_exam_configs(db)

        db.commit()
        print("种子数据写入完成。")
        print(f"管理员账号：{admin.phone} / admin123")
        print("测试账号：13800138000 / test1234（未激活）")
        print("测试账号：13900139000 / test1234（已开通 30 天会员）")
        print("示例激活码：DEMO-30D-0001、DEMO-7D-0001、DEMO-DISABLED")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
