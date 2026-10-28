"""SQLAlchemy 数据模型（兼容 SQLite / MySQL）。"""

import sqlalchemy as sa

from .database import Base


class User(Base):
    """用户表。"""

    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    phone = sa.Column(sa.String(32), unique=True, nullable=False, index=True)
    password_hash = sa.Column(sa.String(255), nullable=False)
    nickname = sa.Column(sa.String(64), nullable=True)
    province_code = sa.Column(sa.String(16), nullable=True)
    settings = sa.Column(sa.JSON, nullable=True)
    role = sa.Column(sa.String(16), nullable=False, default="user")
    created_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())


class Chapter(Base):
    """省份下的章节（支持多层树形结构）。"""

    __tablename__ = "chapters"
    __table_args__ = (
        sa.UniqueConstraint("province_code", "parent_id", "name", name="uq_chapter_province_parent_name"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String(128), nullable=False)
    parent_id = sa.Column(sa.Integer, sa.ForeignKey("chapters.id"), nullable=True)
    province_code = sa.Column(sa.String(16), nullable=False, index=True)
    sort_order = sa.Column(sa.Integer, nullable=False, default=0)


class Question(Base):
    """题目表。"""

    __tablename__ = "questions"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    province_code = sa.Column(sa.String(16), nullable=False, index=True)
    chapter_id = sa.Column(sa.Integer, sa.ForeignKey("chapters.id"), nullable=True, index=True)
    # 题型：single 单选 / multi 多选 / judge 判断
    type = sa.Column(sa.String(16), nullable=False)
    stem = sa.Column(sa.Text, nullable=False)
    options = sa.Column(sa.JSON, nullable=True)
    answer = sa.Column(sa.JSON, nullable=True)
    explanation = sa.Column(sa.Text, nullable=True)
    difficulty = sa.Column(sa.String(16), nullable=False, default="medium")
    year = sa.Column(sa.String(16), nullable=True)
    source_note = sa.Column(sa.Text, nullable=True)
    law_article_ids = sa.Column(sa.JSON, nullable=True)
    is_free = sa.Column(sa.Boolean, nullable=False, default=False)
    status = sa.Column(sa.String(16), nullable=False, default="published")
    created_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())


class LawDocument(Base):
    """法规文件表。"""

    __tablename__ = "law_documents"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    province_code = sa.Column(sa.String(16), nullable=False, default="national", index=True)
    title = sa.Column(sa.String(255), nullable=False)
    category = sa.Column(sa.String(32), nullable=False)
    issuer = sa.Column(sa.String(255), nullable=True)
    publish_date = sa.Column(sa.Date, nullable=True)
    revise_date = sa.Column(sa.Date, nullable=True)
    # 状态：effective 现行有效 / repealed 已废止 / revised 已修订
    status = sa.Column(sa.String(16), nullable=False, default="effective")


class LawArticle(Base):
    """法规条文表。"""

    __tablename__ = "law_articles"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    document_id = sa.Column(
        sa.Integer, sa.ForeignKey("law_documents.id"), nullable=False, index=True
    )
    article_no = sa.Column(sa.String(32), nullable=False)
    chapter_title = sa.Column(sa.String(128), nullable=True)
    content = sa.Column(sa.Text, nullable=False)
    sort_order = sa.Column(sa.Integer, nullable=False, default=0)


class ActivationCode(Base):
    """会员激活码表。"""

    __tablename__ = "activation_codes"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    code = sa.Column(sa.String(64), unique=True, nullable=False, index=True)
    duration_days = sa.Column(sa.Integer, nullable=False)
    # 状态：unused 未使用 / used 已使用 / disabled 已禁用
    status = sa.Column(sa.String(16), nullable=False, default="unused")
    used_by = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=True)
    used_at = sa.Column(sa.DateTime, nullable=True)
    created_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())
    note = sa.Column(sa.Text, nullable=True)


class Membership(Base):
    """用户会员有效期表。"""

    __tablename__ = "memberships"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), unique=True, nullable=False)
    expires_at = sa.Column(sa.DateTime, nullable=False)


class AnswerRecord(Base):
    """答题记录表。"""

    __tablename__ = "answer_records"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    question_id = sa.Column(sa.Integer, sa.ForeignKey("questions.id"), nullable=False, index=True)
    selected = sa.Column(sa.JSON, nullable=True)
    is_correct = sa.Column(sa.Boolean, nullable=True)
    # 模式：practice 练习 / exam 考试
    mode = sa.Column(sa.String(16), nullable=False, default="practice")
    created_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())


class WrongQuestion(Base):
    """错题本表。"""

    __tablename__ = "wrong_questions"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "question_id", name="uq_wrong_user_question"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    question_id = sa.Column(sa.Integer, sa.ForeignKey("questions.id"), nullable=False, index=True)
    wrong_count = sa.Column(sa.Integer, nullable=False, default=1)
    last_wrong_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())
    removed = sa.Column(sa.Boolean, nullable=False, default=False)


class Favorite(Base):
    """收藏表（可收藏题目、法规等不同对象）。"""

    __tablename__ = "favorites"
    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "target_type", "target_id", name="uq_favorite_user_target"
        ),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    target_type = sa.Column(sa.String(16), nullable=False)
    target_id = sa.Column(sa.String(64), nullable=False)


class Exam(Base):
    """模拟考试表。"""

    __tablename__ = "exams"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True)
    started_at = sa.Column(sa.DateTime, nullable=False)
    submitted_at = sa.Column(sa.DateTime, nullable=True)
    duration_limit_sec = sa.Column(sa.Integer, nullable=False)
    total = sa.Column(sa.Integer, nullable=False)
    score = sa.Column(sa.Float, nullable=True)
    passed = sa.Column(sa.Boolean, nullable=False, default=False)
    question_ids = sa.Column(sa.JSON, nullable=False)
    answers = sa.Column(sa.JSON, nullable=False)


class ExamConfig(Base):
    """省份考试配置表。"""

    __tablename__ = "exam_configs"
    __table_args__ = (
        sa.UniqueConstraint("province_code", "key", name="uq_exam_config_province_key"),
    )

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    province_code = sa.Column(sa.String(16), nullable=False, index=True)
    key = sa.Column(sa.String(64), nullable=False)
    value = sa.Column(sa.String(64), nullable=False)


class SiteConfig(Base):
    """站点配置表。"""

    __tablename__ = "site_configs"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    key = sa.Column(sa.String(64), unique=True, nullable=False, index=True)
    value = sa.Column(sa.Text, nullable=False)


class Feedback(Base):
    """用户反馈表。"""

    __tablename__ = "feedbacks"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=True)
    content = sa.Column(sa.String(1024), nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())
