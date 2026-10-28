"""数据库连接与会话管理。"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# SQLite 需要关闭同线程检查；同时确保数据文件所在目录存在。
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

if _is_sqlite:
    _db_path = settings.DATABASE_URL.split("sqlite:///", 1)[-1]
    if _db_path and not _db_path.startswith(":memory:"):
        Path(_db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 依赖：提供数据库会话并在请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
