"""应用入口：注册中间件、路由与启动事件。"""

import importlib
import importlib.util

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  确保模型注册到 Base.metadata
from .config import settings
from .database import Base, engine
from .routers import auth, chapters

app = FastAPI(title="题库后端", version="1.0.0")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 业务路由统一挂载到 /api 前缀下
app.include_router(auth.router, prefix="/api")
app.include_router(chapters.router, prefix="/api")


def _include_optional_router(module_name: str) -> None:
    """挂载后续阶段的路由模块；模块尚未创建时跳过，创建后自动生效。"""
    full_name = f"{__package__}.routers.{module_name}"
    if importlib.util.find_spec(full_name) is None:
        return
    module = importlib.import_module(full_name)
    app.include_router(module.router, prefix="/api")


# 题目、错题收藏、法规、考试、会员与站点配置路由
for _router_name in (
    "questions",
    "wrong_favorites",
    "laws",
    "exams",
    "members",
    "site",
):
    _include_optional_router(_router_name)


@app.on_event("startup")
def on_startup() -> None:
    """应用启动时自动建表。"""
    Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root() -> dict:
    """根路径：返回服务标识，便于探活与排查。"""
    return {"name": "专家库考试助手后端", "docs": "/docs"}


@app.get("/health")
def health_check() -> dict:
    """健康检查接口，供容器编排与监控使用。"""
    return {"status": "healthy"}
