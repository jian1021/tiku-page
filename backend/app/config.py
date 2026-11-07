"""全局配置：支持环境变量与 .env 文件覆盖默认值。"""

import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

# pydantic v2 将 BaseSettings 拆分到了 pydantic-settings；
# 若环境未安装，则退化为普通 BaseModel，并手动读取环境变量。
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover - 兼容未安装 pydantic-settings 的环境
    BaseSettings = BaseModel
    SettingsConfigDict = dict
    _HAS_PYDANTIC_SETTINGS = False


def _env_str(name: str, default: str) -> str:
    """读取字符串类型环境变量。"""
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    """读取整数类型环境变量，非法值回退默认值。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class Settings(BaseSettings):
    """应用配置项。"""

    DATABASE_URL: str = "sqlite:///./data/app.db"
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # 允许跨域的前端来源，多个用英文逗号分隔。
    # 注意：这里刻意用 str 而不是 list[str]——pydantic-settings 对 list 字段
    # 会强制按 JSON 解析，逗号分隔的写法（.env 里最自然的形式）会直接报错。
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://localhost:4173,"
        "http://localhost:8080,http://localhost"
    )

    # 允许跨域的来源正则，用于 Cloudflare Pages 预览域名这类动态子域。
    # 例如：https://.*\.tiku-page\.pages\.dev    留空则不启用。
    CORS_ORIGIN_REGEX: str = ""

    if _HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的来源串解析为列表。"""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    def model_post_init(self, __context) -> None:
        """未安装 pydantic-settings 时，从环境变量手动加载配置。"""
        if _HAS_PYDANTIC_SETTINGS:
            return
        self.DATABASE_URL = _env_str("DATABASE_URL", self.DATABASE_URL)
        self.SECRET_KEY = _env_str("SECRET_KEY", self.SECRET_KEY)
        self.ALGORITHM = _env_str("ALGORITHM", self.ALGORITHM)
        self.ACCESS_TOKEN_EXPIRE_MINUTES = _env_int(
            "ACCESS_TOKEN_EXPIRE_MINUTES", self.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self.CORS_ORIGINS = _env_str("CORS_ORIGINS", self.CORS_ORIGINS)
        self.CORS_ORIGIN_REGEX = _env_str("CORS_ORIGIN_REGEX", self.CORS_ORIGIN_REGEX)


settings = Settings()
