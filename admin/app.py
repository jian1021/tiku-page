"""题库管理后台（Streamlit 单文件应用）。

直接连接后端使用的数据库，通过 SQLAlchemy Core + 反射操作数据，
避免依赖 backend 包路径。所有写操作均使用显式事务。
"""

from __future__ import annotations

import hmac
import io
import json
import os
import re
import secrets
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import JSON, MetaData, case, create_engine, func, insert, or_, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------------
# 基础配置
# ---------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "app.db"

# 兼容项目根目录与 admin 目录下的 .env；已存在的环境变量优先。
for _env_file in (PROJECT_ROOT / ".env", APP_DIR / ".env"):
    if _env_file.exists():
        load_dotenv(_env_file, override=False)

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

PAGE_NAMES = [
    "数据概览",
    "题目管理",
    "法规管理",
    "激活码",
    "用户管理",
    "配置管理",
    "意见反馈",
]

REQUIRED_TABLES = [
    "users",
    "chapters",
    "questions",
    "law_documents",
    "law_articles",
    "activation_codes",
    "memberships",
    "answer_records",
    "wrong_questions",
    "favorites",
    "exams",
    "exam_configs",
    "site_configs",
    "feedbacks",
]

PROVINCES: list[tuple[str, str]] = [
    ("SC", "四川省"),
    ("BJ", "北京市"),
    ("TJ", "天津市"),
    ("HE", "河北省"),
    ("SX", "山西省"),
    ("NM", "内蒙古自治区"),
    ("LN", "辽宁省"),
    ("JL", "吉林省"),
    ("HL", "黑龙江省"),
    ("SH", "上海市"),
    ("JS", "江苏省"),
    ("ZJ", "浙江省"),
    ("AH", "安徽省"),
    ("FJ", "福建省"),
    ("JX", "江西省"),
    ("SD", "山东省"),
    ("HA", "河南省"),
    ("HB", "湖北省"),
    ("HN", "湖南省"),
    ("GD", "广东省"),
    ("GX", "广西壮族自治区"),
    ("HI", "海南省"),
    ("CQ", "重庆市"),
    ("GZ", "贵州省"),
    ("YN", "云南省"),
    ("XZ", "西藏自治区"),
    ("SN", "陕西省"),
    ("GS", "甘肃省"),
    ("QH", "青海省"),
    ("NX", "宁夏回族自治区"),
    ("XJ", "新疆维吾尔自治区"),
    ("TW", "台湾省"),
    ("HK", "香港特别行政区"),
    ("MO", "澳门特别行政区"),
]

PROVINCE_CODE_TO_NAME = dict(PROVINCES)


def _short_province_name(name: str) -> str:
    """去掉省份名称中的行政区划后缀，得到常用简称。"""
    for suffix in (
        "维吾尔自治区",
        "壮族自治区",
        "回族自治区",
        "特别行政区",
        "自治区",
        "省",
        "市",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


PROVINCE_ALIASES: dict[str, str] = {}
for _code, _name in PROVINCES:
    PROVINCE_ALIASES[_code] = _code
    PROVINCE_ALIASES[_code.lower()] = _code
    PROVINCE_ALIASES[_name] = _code
    PROVINCE_ALIASES[_short_province_name(_name)] = _code
for _alias in ("national", "NATIONAL", "National", "全国", "全国通用", "国家"):
    PROVINCE_ALIASES[_alias] = "national"


def resolve_province(raw: Any) -> str | None:
    """把中文省份名、简称或省份代码统一成数据库中的省份代码。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return PROVINCE_ALIASES.get(text) or PROVINCE_ALIASES.get(text.upper())


def province_label(code: str | None, with_code: bool = False) -> str:
    """省份代码转中文展示。"""
    if not code:
        return "未填写"
    if code == "national":
        return "全国通用（national）" if with_code else "全国通用"
    name = PROVINCE_CODE_TO_NAME.get(code, code)
    return f"{name}（{code}）" if with_code else name


def province_select_options(include_national: bool = True) -> list[str]:
    codes = [code for code, _ in PROVINCES]
    if include_national:
        codes.insert(0, "national")
    return codes


def province_select_label(code: str) -> str:
    if code == "national":
        return "national - 全国通用"
    return f"{code} - {PROVINCE_CODE_TO_NAME.get(code, code)}"


def province_filter_options() -> list[str]:
    return ["", "national"] + [code for code, _ in PROVINCES]


def province_filter_label(code: str) -> str:
    if not code:
        return "全部省份"
    return province_select_label(code)


# 题目 / 法规导入列约定
QUESTION_COLUMNS = [
    "省份",
    "章节",
    "题型",
    "题干",
    "选项A",
    "选项B",
    "选项C",
    "选项D",
    "选项E",
    "选项F",
    "答案",
    "解析",
    "难度",
    "真题年份",
    "来源说明",
    "关联条文",
    "是否免费",
]
QUESTION_REQUIRED_HEADERS = ["省份", "章节", "题型", "题干", "选项A", "答案", "是否免费"]

LAW_COLUMNS = [
    "省份",
    "法规名称",
    "分类",
    "发文单位",
    "发布日期",
    "修订日期",
    "效力状态",
    "条号",
    "条文内容",
]
LAW_REQUIRED_HEADERS = ["省份", "法规名称", "分类", "条号", "条文内容"]
LAW_CATEGORIES = ["国家法律", "行政法规", "部门规章", "地方规定"]
LAW_STATUS_LABELS = {"effective": "现行有效", "repealed": "已废止", "revised": "已修订"}
LAW_STATUS_ALIASES = {
    "现行有效": "effective",
    "有效": "effective",
    "effective": "effective",
    "已废止": "repealed",
    "废止": "repealed",
    "repealed": "repealed",
    "已修订": "revised",
    "修订": "revised",
    "revised": "revised",
}

DIFFICULTY_LABELS = {"easy": "简单", "medium": "中等", "hard": "困难"}
DIFFICULTY_ALIASES = {
    "easy": "easy",
    "简单": "easy",
    "容易": "easy",
    "medium": "medium",
    "中等": "medium",
    "一般": "medium",
    "hard": "hard",
    "困难": "hard",
    "难": "hard",
}
JUDGE_ANSWER_MAP = {
    "正确": "A",
    "对": "A",
    "是": "A",
    "TRUE": "A",
    "T": "A",
    "YES": "A",
    "Y": "A",
    "√": "A",
    "错误": "B",
    "错": "B",
    "否": "B",
    "FALSE": "B",
    "F": "B",
    "NO": "B",
    "N": "B",
    "×": "B",
}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# 密码重置依赖是可选的：管理员环境未安装时给出提示。
try:
    from passlib.context import CryptContext

    _PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:  # pragma: no cover - 兼容未安装 passlib 的环境
    _PWD_CONTEXT = None

try:
    import bcrypt as _bcrypt
except Exception:  # pragma: no cover - 兼容未安装 bcrypt 的环境
    _bcrypt = None


class AdminError(Exception):
    """管理后台中的可预期业务错误。"""


# ---------------------------------------------------------------------------
# 数据库连接与基础工具
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def get_engine(database_url: str):
    """创建（并缓存）SQLAlchemy 引擎。"""
    backend = make_url(database_url).get_backend_name()
    kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "future": True,
        "json_serializer": lambda obj: json.dumps(obj, ensure_ascii=False),
        "json_deserializer": json.loads,
    }
    if backend == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
    elif backend == "mysql":
        kwargs["connect_args"] = {"charset": "utf8mb4"}
    return create_engine(database_url, **kwargs)


@st.cache_resource(show_spinner=False)
def get_metadata(database_url: str) -> MetaData:
    """反射数据库表结构，供 Core 操作使用。"""
    metadata = MetaData()
    metadata.reflect(bind=get_engine(database_url))
    return metadata


def get_table(name: str):
    metadata = get_metadata(DATABASE_URL)
    table = metadata.tables.get(name)
    if table is None:
        raise AdminError(f"数据表 {name} 不存在，请先启动后端自动建表或执行种子脚本。")
    return table


def fetch_all(stmt) -> list[dict]:
    with get_engine(DATABASE_URL).connect() as conn:
        return [dict(row._mapping) for row in conn.execute(stmt)]


def fetch_one(stmt) -> dict | None:
    with get_engine(DATABASE_URL).connect() as conn:
        row = conn.execute(stmt).first()
        return dict(row._mapping) if row is not None else None


def fetch_scalar(stmt, default: Any = 0) -> Any:
    with get_engine(DATABASE_URL).connect() as conn:
        value = conn.execute(stmt).scalar()
    return default if value is None else value


def database_file_path(database_url: str) -> Path | None:
    """SQLite 数据库文件路径；非 SQLite 返回 None。"""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return None
    if url.database == ":memory:":
        return None
    return Path(url.database)


def safe_db_label(database_url: str) -> str:
    """隐藏密码后的数据库连接展示文本。"""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return f"SQLite：{url.database}"
    auth = url.username or ""
    if url.password:
        auth += ":***"
    if auth:
        auth += "@"
    port = f":{url.port}" if url.port else ""
    return f"{url.drivername}：{auth}{url.host or ''}{port}/{url.database or ''}"


def ensure_database_ready() -> None:
    """检查数据库文件、连接与必需表。"""
    db_path = database_file_path(DATABASE_URL)
    if db_path is not None and not db_path.exists():
        st.error(f"数据库文件不存在：{db_path}")
        st.info("请先在 backend 目录启动一次后端以自动建表，或执行 python -m app.seed 写入种子数据。")
        st.code("cd backend\npython -m app.seed")
        st.stop()

    try:
        metadata = get_metadata(DATABASE_URL)
    except Exception as exc:  # noqa: BLE001 - 管理后台需要展示具体连接错误
        st.error(f"数据库连接失败：{exc}")
        st.info("请检查 DATABASE_URL 环境变量、数据库服务状态与账号权限。")
        st.stop()

    missing = [name for name in REQUIRED_TABLES if name not in metadata.tables]
    if missing:
        st.error("数据库缺少以下数据表：" + "、".join(missing))
        st.info("请先启动一次后端（应用启动时会自动建表），或执行 backend 的种子脚本。")
        st.code("cd backend\nuvicorn app.main:app --reload")
        st.stop()


def clear_db_caches() -> None:
    get_metadata.clear()
    get_engine.clear()


def to_db_json(column, value: Any) -> Any:
    """JSON 列交给 SQLAlchemy 序列化；兼容旧库中实际为 TEXT 的列。"""
    if value is None:
        return None
    if isinstance(column.type, JSON):
        return value
    return json.dumps(value, ensure_ascii=False)


def json_load(value: Any, default: Any = None) -> Any:
    """读取 JSON 列，兼容 SQLite 返回字符串的情况。"""
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return default
    return default


def coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        text = value.strip().replace("T", " ")
        if not text or text.lower() in {"none", "null", "nan", "nat"}:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def format_dt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value.replace("T", " ")[:19]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def is_active_member(expires_at: Any) -> bool:
    moment = coerce_datetime(expires_at)
    return bool(moment and moment > datetime.now())


def parse_date_value(raw: Any) -> date | None:
    """解析 Excel/CSV 中的日期，空值返回 None，非法格式抛 ValueError。"""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw).strip()
    if not text or text.lower() in {"none", "null", "nan", "nat"}:
        return None
    text = text.replace("年", "-").replace("月", "-").replace("日", "").strip()
    text = text.replace("/", "-").replace(".", "-")
    if " " in text:
        text = text.split(" ", 1)[0]
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日期格式无法识别：{raw}")


def parse_bool_value(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and not pd.isna(raw):
        if int(raw) == 1:
            return True
        if int(raw) == 0:
            return False
        return None
    text = str(raw or "").strip().lower()
    if text in {"是", "true", "1", "y", "yes", "真", "免费"}:
        return True
    if text in {"否", "false", "0", "n", "no", "假", "收费", "付费"}:
        return False
    return None


def cell_text(row: pd.Series, column: str) -> str:
    if column not in row.index:
        return ""
    value = row[column]
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "nat", "none"} else text


def shorten(text: Any, length: int = 80) -> str:
    value = str(text or "").replace("\n", " ").strip()
    return value if len(value) <= length else value[:length] + "…"


def set_flash(message: str, level: str = "success") -> None:
    st.session_state["_admin_flash"] = (level, message)


def show_flash() -> None:
    item = st.session_state.pop("_admin_flash", None)
    if not item:
        return
    level, message = item
    if level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.success(message)


def read_uploaded_table(uploaded, csv: bool = False) -> pd.DataFrame:
    """读取上传的 xlsx/csv，所有单元格按字符串处理并去除表头空白。"""
    data = uploaded.getvalue()
    suffix = Path(uploaded.name).suffix.lower()
    if csv or suffix == ".csv":
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "gbk", "utf-8"):
            try:
                df = pd.read_csv(
                    io.BytesIO(data),
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                )
                break
            except UnicodeDecodeError as exc:  # 尝试下一种编码
                last_error = exc
        else:  # pragma: no cover - 三种编码均失败
            raise AdminError(f"CSV 编码无法识别，请另存为 UTF-8 后重试：{last_error}")
    else:
        try:
            df = pd.read_excel(io.BytesIO(data), dtype=str, keep_default_na=False)
        except Exception as exc:  # noqa: BLE001
            raise AdminError(f"Excel 读取失败：{exc}") from exc
    df.columns = [str(col).strip() for col in df.columns]
    return df


def dataframe_to_xlsx(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="导入模板")
    return buffer.getvalue()


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def check_headers(
    df: pd.DataFrame, required: list[str], all_columns: list[str]
) -> tuple[list[str], list[str]]:
    missing_required = [name for name in required if name not in df.columns]
    missing_optional = [
        name for name in all_columns if name not in required and name not in df.columns
    ]
    return missing_required, missing_optional


# ---------------------------------------------------------------------------
# 章节解析
# ---------------------------------------------------------------------------


def load_chapter_index() -> dict[str, Any]:
    chapters = get_table("chapters")
    rows = fetch_all(
        select(
            chapters.c.id,
            chapters.c.name,
            chapters.c.parent_id,
            chapters.c.province_code,
            chapters.c.sort_order,
        ).order_by(chapters.c.province_code, chapters.c.sort_order, chapters.c.id)
    )
    by_id = {row["id"]: row for row in rows}

    def build_path(row: dict) -> list[str]:
        parts: list[str] = []
        current = row
        guard: set[int] = set()
        while current is not None and current["id"] not in guard:
            guard.add(current["id"])
            parts.append(str(current["name"]))
            current = by_id.get(current["parent_id"])
        return list(reversed(parts))

    by_name: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        row["path_parts"] = build_path(row)
        row["path"] = " / ".join(row["path_parts"])
        by_name.setdefault((row["province_code"], row["name"]), []).append(row)
    return {"rows": rows, "by_id": by_id, "by_name": by_name}


def resolve_chapter(
    province_code: str, raw: str, chapter_index: dict[str, Any]
) -> tuple[dict | None, str | None]:
    """按章节 ID、名称或「父章节/子章节」路径解析章节。"""
    text = str(raw or "").strip()
    if not text:
        return None, "章节不能为空"
    if text.isdigit():
        row = chapter_index["by_id"].get(int(text))
        if row is None:
            return None, f"章节 ID 不存在：{text}"
        if row["province_code"] != province_code:
            return None, f"章节 ID {text} 不属于省份 {province_code}"
        return row, None

    separators = r"\s*[>/／]\s*"
    if re.search(separators, text):
        parts = [part.strip() for part in re.split(separators, text) if part.strip()]
        last_name = parts[-1] if parts else ""
        candidates = [
            row
            for row in chapter_index["by_name"].get((province_code, last_name), [])
            if row["path_parts"] == parts
        ]
        if len(candidates) == 1:
            return candidates[0], None
        if len(candidates) > 1:
            paths = "；".join(row["path"] for row in candidates[:5])
            return None, f"章节路径不唯一：{text}（{paths}），请改用章节 ID"
        return None, f"章节路径不存在（省份 {province_code}）：{text}"

    candidates = chapter_index["by_name"].get((province_code, text), [])
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        paths = "；".join(row["path"] for row in candidates[:5])
        return None, f"章节名在多个父章节下重复：{text}，请填写「父章节/子章节」或章节 ID（{paths}）"
    other = [
        row
        for row in chapter_index["rows"]
        if row["name"] == text and row["province_code"] != province_code
    ]
    if other:
        return None, f"章节「{text}」不属于省份 {province_code}"
    return None, f"章节不存在（省份 {province_code}）：{text}"


# ---------------------------------------------------------------------------
# 题目解析与写入
# ---------------------------------------------------------------------------


def parse_answer(raw: str, qtype: str, options: dict[str, str]) -> tuple[list[str] | None, str | None]:
    text = str(raw or "").strip()
    if not text:
        return None, "答案不能为空"
    if not options:
        return None, "没有可用选项，无法校验答案"

    # 允许直接填写选项文本
    for key, option_text in options.items():
        if text == str(option_text).strip():
            return [key], None

    if qtype == "judge":
        compact = re.sub(r"\s+", "", text).upper()
        if compact in JUDGE_ANSWER_MAP:
            key = JUDGE_ANSWER_MAP[compact]
            if key not in options:
                return None, f"答案 {key} 不在选项内"
            return [key], None

    normalized = text.upper()
    for separator in ("，", "、", "；", ";", "|", "/", "／"):
        normalized = normalized.replace(separator, ",")
    normalized = re.sub(r"\s+", ",", normalized)
    parts = [part for part in normalized.split(",") if part]
    letters: list[str] = []
    for part in parts:
        if re.fullmatch(r"[A-Z]+", part):
            letters.extend(list(part))
        elif qtype == "judge" and part in JUDGE_ANSWER_MAP:
            letters.append(JUDGE_ANSWER_MAP[part])
        else:
            return None, f"答案格式无法识别：{raw}"

    letters = list(dict.fromkeys(letters))
    missing = [letter for letter in letters if letter not in options]
    if missing:
        return None, f"答案 {','.join(missing)} 不在选项内"
    if qtype == "single" and len(letters) != 1:
        return None, "单选题答案必须且只能有一个选项"
    if qtype == "multi" and len(letters) < 2:
        return None, "多选题答案至少需要两个选项"
    if qtype == "judge" and len(letters) != 1:
        return None, "判断题答案必须且只能有一个选项"
    return sorted(letters), None


def parse_law_article_ids(raw: str) -> tuple[list[int] | None, str | None]:
    text = str(raw or "").strip()
    if not text or text.lower() in {"none", "null", "[]"}:
        return None, None
    if text.startswith("["):
        try:
            values = json.loads(text)
        except ValueError:
            return None, "关联条文应为 JSON 数组或逗号分隔的条文 ID"
        if not isinstance(values, list):
            return None, "关联条文应为 JSON 数组或逗号分隔的条文 ID"
    else:
        values = [part for part in re.split(r"[,，、;；\s]+", text) if part]
    result: list[int] = []
    for value in values:
        try:
            number = int(str(value).strip())
        except ValueError:
            return None, f"关联条文 ID 不是整数：{value}"
        if number <= 0:
            return None, f"关联条文 ID 必须为正整数：{value}"
        if number not in result:
            result.append(number)
    return (result or None), None


def parse_question_core(
    *,
    province_code: str,
    chapter_id: int | None,
    qtype: str,
    stem: str,
    raw_options: dict[str, str],
    raw_answer: str,
    explanation: str = "",
    difficulty: str = "",
    year: str = "",
    source_note: str = "",
    law_ids_raw: str = "",
    is_free_value: Any = "",
    status: str = "published",
) -> tuple[dict | None, list[str]]:
    """校验并构造一条题目记录（导入与编辑共用）。返回 (记录, 错误列表)。"""
    errors: list[str] = []

    if not province_code:
        errors.append("省份不能为空或无法识别")

    normalized_type = str(qtype or "").strip().lower()
    if normalized_type not in {"single", "multi", "judge"}:
        errors.append("题型只能是 single / multi / judge")

    normalized_stem = str(stem or "").strip()
    if not normalized_stem:
        errors.append("题干不能为空")

    clean_options: dict[str, str] = {}
    for letter in "ABCDEF":
        value = str(raw_options.get(letter, "") or "").strip()
        if value:
            clean_options[letter] = value
    if normalized_type == "judge" and not clean_options:
        clean_options = {"A": "正确", "B": "错误"}
    if normalized_type in {"single", "multi"} and len(clean_options) < 2:
        errors.append("单选题 / 多选题至少需要填写 2 个选项")
    if normalized_type == "judge" and len(clean_options) < 2:
        errors.append("判断题至少需要 2 个选项（全部留空时会自动生成「正确 / 错误」）")

    answer, answer_error = parse_answer(raw_answer, normalized_type, clean_options)
    if answer_error:
        errors.append(answer_error)

    difficulty_text = str(difficulty or "").strip()
    normalized_difficulty = "medium" if not difficulty_text else DIFFICULTY_ALIASES.get(
        difficulty_text.lower()
    )
    if normalized_difficulty is None:
        errors.append(f"难度只能是 easy / medium / hard（或简单 / 中等 / 困难）：{difficulty_text}")

    year_text = str(year or "").strip().replace("年", "")
    if year_text and not re.fullmatch(r"\d{4}", year_text):
        errors.append(f"真题年份应为 4 位数字：{year_text}")

    if isinstance(is_free_value, bool):
        is_free = is_free_value
    else:
        is_free = parse_bool_value(is_free_value)
        if is_free is None:
            errors.append(f"是否免费无法识别：{is_free_value}")

    law_ids, law_error = parse_law_article_ids(law_ids_raw)
    if law_error:
        errors.append(law_error)

    normalized_status = str(status or "published").strip().lower()
    if normalized_status not in {"published", "draft"}:
        errors.append("状态只能是 published / draft")

    if errors:
        return None, errors

    return (
        {
            "province_code": province_code,
            "chapter_id": chapter_id,
            "type": normalized_type,
            "stem": normalized_stem,
            "options": [{"key": key, "text": clean_options[key]} for key in sorted(clean_options)],
            "answer": answer,
            "explanation": str(explanation or "").strip() or None,
            "difficulty": normalized_difficulty or "medium",
            "year": year_text or None,
            "source_note": str(source_note or "").strip() or None,
            "law_article_ids": law_ids,
            "is_free": bool(is_free),
            "status": normalized_status,
        },
        [],
    )


def validate_question_dataframe(
    df: pd.DataFrame, chapter_index: dict[str, Any]
) -> tuple[list[dict], list[dict]]:
    """逐行校验题目导入数据，返回 (有效记录, 错误行)。"""
    valid: list[dict] = []
    errors: list[dict] = []
    for index, row in df.iterrows():
        excel_row = int(index) + 2
        messages: list[str] = []

        province_raw = cell_text(row, "省份")
        province_code = resolve_province(province_raw)
        if not province_code:
            messages.append(f"省份无法识别：{province_raw or '（空）'}")

        chapter_id: int | None = None
        if province_code:
            chapter, chapter_error = resolve_chapter(
                province_code, cell_text(row, "章节"), chapter_index
            )
            if chapter_error:
                messages.append(chapter_error)
            elif chapter is not None:
                chapter_id = int(chapter["id"])

        raw_options = {letter: cell_text(row, f"选项{letter}") for letter in "ABCDEF"}
        payload, core_errors = parse_question_core(
            province_code=province_code or "",
            chapter_id=chapter_id,
            qtype=cell_text(row, "题型"),
            stem=cell_text(row, "题干"),
            raw_options=raw_options,
            raw_answer=cell_text(row, "答案"),
            explanation=cell_text(row, "解析"),
            difficulty=cell_text(row, "难度"),
            year=cell_text(row, "真题年份"),
            source_note=cell_text(row, "来源说明"),
            law_ids_raw=cell_text(row, "关联条文"),
            is_free_value=cell_text(row, "是否免费"),
            status="published",
        )
        messages.extend(core_errors)
        if messages or payload is None:
            errors.append({"Excel 行号": excel_row, "错误": "；".join(messages)})
            continue
        payload["_row"] = excel_row
        valid.append(payload)
    return valid, errors


def insert_questions(records: list[dict]) -> int:
    if not records:
        return 0
    questions = get_table("questions")
    now = datetime.now()
    rows: list[dict] = []
    for record in records:
        row = {key: value for key, value in record.items() if not key.startswith("_")}
        row["options"] = to_db_json(questions.c.options, row["options"])
        row["answer"] = to_db_json(questions.c.answer, row["answer"])
        row["law_article_ids"] = to_db_json(
            questions.c.law_article_ids, row["law_article_ids"]
        )
        row["created_at"] = now
        rows.append(row)
    with get_engine(DATABASE_URL).begin() as conn:
        conn.execute(insert(questions), rows)
    return len(rows)


def fetch_question(question_id: int) -> dict | None:
    questions = get_table("questions")
    chapters = get_table("chapters")
    stmt = (
        select(questions, chapters.c.name.label("chapter_name"))
        .outerjoin(chapters, questions.c.chapter_id == chapters.c.id)
        .where(questions.c.id == question_id)
    )
    row = fetch_one(stmt)
    if row is None:
        return None
    row["options"] = json_load(row.get("options"), [])
    row["answer"] = json_load(row.get("answer"), [])
    row["law_article_ids"] = json_load(row.get("law_article_ids"), [])
    return row


# ---------------------------------------------------------------------------
# 法规解析与写入
# ---------------------------------------------------------------------------


def parse_law_status(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return "effective"
    return LAW_STATUS_ALIASES.get(text) or LAW_STATUS_ALIASES.get(text.lower())


def validate_law_dataframe(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    valid: list[dict] = []
    errors: list[dict] = []
    for index, row in df.iterrows():
        excel_row = int(index) + 2
        messages: list[str] = []

        province_raw = cell_text(row, "省份")
        province_code = resolve_province(province_raw)
        if not province_code:
            messages.append(f"省份无法识别：{province_raw or '（空）'}")

        title = cell_text(row, "法规名称")
        if not title:
            messages.append("法规名称不能为空")

        category = cell_text(row, "分类")
        if category not in LAW_CATEGORIES:
            messages.append(
                f"分类只能是：{'、'.join(LAW_CATEGORIES)}（当前：{category or '空'}）"
            )

        status = parse_law_status(cell_text(row, "效力状态"))
        if status is None:
            messages.append(f"效力状态无法识别：{cell_text(row, '效力状态')}")

        try:
            publish_date = parse_date_value(cell_text(row, "发布日期"))
        except ValueError as exc:
            publish_date = None
            messages.append(str(exc))
        try:
            revise_date = parse_date_value(cell_text(row, "修订日期"))
        except ValueError as exc:
            revise_date = None
            messages.append(str(exc))

        article_no = cell_text(row, "条号")
        if not article_no:
            messages.append("条号不能为空")
        content = cell_text(row, "条文内容")
        if not content:
            messages.append("条文内容不能为空")

        if messages or not province_code or not status:
            errors.append({"Excel 行号": excel_row, "错误": "；".join(messages)})
            continue

        valid.append(
            {
                "_row": excel_row,
                "province_code": province_code,
                "title": title,
                "category": category,
                "issuer": cell_text(row, "发文单位") or None,
                "publish_date": publish_date,
                "revise_date": revise_date,
                "status": status,
                "article_no": article_no,
                "content": content,
            }
        )
    return valid, errors


def import_law_records(records: list[dict], skip_existing: bool = True) -> dict[str, Any]:
    """按「省份 + 法规名称」归并文档并逐条写入法规条文。"""
    documents = get_table("law_documents")
    articles = get_table("law_articles")
    created_docs = 0
    inserted_articles = 0
    skipped_articles = 0

    with get_engine(DATABASE_URL).begin() as conn:
        document_rows = conn.execute(
            select(documents.c.id, documents.c.province_code, documents.c.title)
        ).all()
        doc_map = {
            (row.province_code, row.title): row.id for row in document_rows
        }
        next_sort_rows = conn.execute(
            select(articles.c.document_id, func.max(articles.c.sort_order)).group_by(
                articles.c.document_id
            )
        ).all()
        next_sort = {
            document_id: (int(max_sort or 0) + 1) for document_id, max_sort in next_sort_rows
        }

        existing_article_keys: set[tuple[int, str]] = set()
        if doc_map:
            existing_rows = conn.execute(
                select(articles.c.document_id, articles.c.article_no)
            ).all()
            existing_article_keys = {
                (int(row.document_id), str(row.article_no)) for row in existing_rows
            }

        for record in records:
            key = (record["province_code"], record["title"])
            document_id = doc_map.get(key)
            if document_id is None:
                result = conn.execute(
                    insert(documents).values(
                        province_code=record["province_code"],
                        title=record["title"],
                        category=record["category"],
                        issuer=record["issuer"],
                        publish_date=record["publish_date"],
                        revise_date=record["revise_date"],
                        status=record["status"],
                    )
                )
                document_id = int(result.inserted_primary_key[0])
                doc_map[key] = document_id
                next_sort[document_id] = 1
                created_docs += 1

            article_key = (document_id, record["article_no"])
            if skip_existing and article_key in existing_article_keys:
                skipped_articles += 1
                continue

            sort_order = next_sort.get(document_id, 1)
            conn.execute(
                insert(articles).values(
                    document_id=document_id,
                    article_no=record["article_no"],
                    chapter_title=None,
                    content=record["content"],
                    sort_order=sort_order,
                )
            )
            next_sort[document_id] = sort_order + 1
            existing_article_keys.add(article_key)
            inserted_articles += 1

    return {
        "created_docs": created_docs,
        "inserted_articles": inserted_articles,
        "skipped_articles": skipped_articles,
    }


# ---------------------------------------------------------------------------
# 激活码工具
# ---------------------------------------------------------------------------


def generate_activation_codes(
    count: int, prefix: str, existing_codes: set[str]
) -> list[str]:
    codes: list[str] = []
    total_attempts = 0
    max_attempts = max(1000, count * 200)
    while len(codes) < count:
        total_attempts += 1
        if total_attempts > max_attempts:
            raise AdminError("生成激活码时碰撞次数过多，请重试或更换前缀。")
        body = "".join(secrets.choice(CODE_ALPHABET) for _ in range(12))
        code = f"{prefix}-{body}" if prefix else body
        if code in existing_codes:
            continue
        existing_codes.add(code)
        codes.append(code)
    return codes


def hash_admin_password(password: str) -> str:
    if _PWD_CONTEXT is not None:
        return _PWD_CONTEXT.hash(password)
    if _bcrypt is not None:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
    raise AdminError(
        "当前环境缺少 passlib 与 bcrypt，无法重置密码。请安装 passlib[bcrypt] 后重试。"
    )


# ---------------------------------------------------------------------------
# 登录与侧边栏
# ---------------------------------------------------------------------------


def render_login() -> None:
    st.markdown("<h2 style='text-align:center;'>题库管理后台</h2>", unsafe_allow_html=True)
    st.caption("请使用管理员账号登录")
    left, middle, right = st.columns([1, 1.2, 1])
    with middle:
        with st.form("admin_login_form"):
            username = st.text_input("管理员账号")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
        if submitted:
            if hmac.compare_digest(
                username.strip().encode("utf-8"), ADMIN_USER.encode("utf-8")
            ) and hmac.compare_digest(
                password.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8")
            ):
                st.session_state["admin_authenticated"] = True
                st.session_state["admin_username"] = username.strip()
                st.rerun()
            else:
                st.error("账号或密码不正确")
        st.caption("默认账号 admin / admin123，可通过 ADMIN_USER / ADMIN_PASSWORD 环境变量覆盖。")


def render_sidebar() -> str:
    with st.sidebar:
        st.title("题库管理后台")
        username = st.session_state.get("admin_username", ADMIN_USER)
        st.caption(f"当前管理员：{username}")
        page = st.radio("功能导航", PAGE_NAMES)
        st.divider()
        st.caption("数据库连接")
        st.code(safe_db_label(DATABASE_URL), language=None)
        if ADMIN_PASSWORD == "admin123" and ADMIN_USER == "admin":
            st.warning("正在使用默认管理员账号密码，请尽快通过环境变量修改。")
        if st.button("刷新表结构 / 数据", use_container_width=True):
            clear_db_caches()
            st.rerun()
        if st.button("退出登录", use_container_width=True):
            st.session_state.pop("admin_authenticated", None)
            st.session_state.pop("admin_username", None)
            st.rerun()
        st.caption("提示：本工具直接读写业务数据库，操作前请备份。")
    return page


# ---------------------------------------------------------------------------
# 数据概览
# ---------------------------------------------------------------------------


def render_overview() -> None:
    st.header("数据概览")
    users = get_table("users")
    questions = get_table("questions")
    answer_records = get_table("answer_records")
    memberships = get_table("memberships")
    exams = get_table("exams")
    chapters = get_table("chapters")

    user_count = int(fetch_scalar(select(func.count()).select_from(users)))
    published_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(questions)
            .where(questions.c.status == "published")
        )
    )
    answer_count = int(fetch_scalar(select(func.count()).select_from(answer_records)))
    member_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(memberships)
            .where(memberships.c.expires_at > datetime.now())
        )
    )
    exam_count = int(fetch_scalar(select(func.count()).select_from(exams)))

    columns = st.columns(5)
    columns[0].metric("注册用户数", user_count)
    columns[1].metric("已发布题目数", published_count)
    columns[2].metric("答题记录数", answer_count)
    columns[3].metric("有效会员数", member_count)
    columns[4].metric("考试数", exam_count)

    st.divider()
    st.subheader("各章节正确率")
    correct_expr = func.sum(
        case((answer_records.c.is_correct.is_(True), 1), else_=0)
    ).label("correct_count")
    stmt = (
        select(
            questions.c.province_code,
            questions.c.chapter_id,
            chapters.c.name.label("chapter_name"),
            func.count(answer_records.c.id).label("answer_count"),
            correct_expr,
        )
        .select_from(answer_records)
        .join(questions, answer_records.c.question_id == questions.c.id)
        .outerjoin(chapters, questions.c.chapter_id == chapters.c.id)
        .group_by(questions.c.province_code, questions.c.chapter_id, chapters.c.name)
        .order_by(questions.c.province_code, chapters.c.name)
    )
    rows = fetch_all(stmt)
    if not rows:
        st.info("暂无答题记录。")
        return

    chapter_index = load_chapter_index()
    table_rows: list[dict] = []
    for row in rows:
        total = int(row["answer_count"] or 0)
        correct = int(row["correct_count"] or 0)
        chapter_id = row["chapter_id"]
        chapter = chapter_index["by_id"].get(chapter_id)
        chapter_name = chapter["path"] if chapter else (row["chapter_name"] or "未分配章节")
        table_rows.append(
            {
                "省份": province_label(row["province_code"]),
                "章节": chapter_name,
                "答题数": total,
                "正确数": correct,
                "正确率": f"{(correct / total * 100):.1f}%" if total else "0.0%",
            }
        )
    st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("正确率 = 正确答题记录数 / 答题记录总数，包含练习与考试模式。")


# ---------------------------------------------------------------------------
# 题目管理
# ---------------------------------------------------------------------------


def render_question_import(chapter_index: dict[str, Any]) -> None:
    result = st.session_state.pop("question_import_result", None)
    if result:
        st.success(
            f"导入完成：成功写入 {result['count']} 道题目（status=published）。"
        )

    st.subheader("Excel 批量导入")
    st.caption("支持 .xlsx；列名必须与模板一致。判断题的选项列留空时自动生成 A 正确 / B 错误。")
    template = pd.DataFrame(columns=QUESTION_COLUMNS)
    st.download_button(
        "下载题目导入模板",
        data=dataframe_to_xlsx(template),
        file_name="题目导入模板.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    nonce = st.session_state.setdefault("question_upload_nonce", 0)
    uploaded = st.file_uploader(
        "上传题目 Excel",
        type=["xlsx"],
        key=f"question_upload_{nonce}",
    )
    if uploaded is None:
        return

    try:
        df = read_uploaded_table(uploaded)
    except AdminError as exc:
        st.error(str(exc))
        return

    missing_required, missing_optional = check_headers(
        df, QUESTION_REQUIRED_HEADERS, QUESTION_COLUMNS
    )
    if missing_required:
        st.error("缺少必需列：" + "、".join(missing_required))
        st.info("请下载模板，按模板列名填写后重新上传。")
        return
    if missing_optional:
        st.warning("缺少可选列，将按空值处理：" + "、".join(missing_optional))

    st.caption(f"文件：{uploaded.name}，共 {len(df)} 行。以下为前 50 行预览。")
    st.dataframe(df.head(50), hide_index=True, use_container_width=True)

    if df.empty:
        st.info("文件中没有数据行。")
        return

    valid, errors = validate_question_dataframe(df, chapter_index)
    if errors:
        st.error(f"校验未通过：{len(errors)} 行存在错误，请修正后重新上传。")
        st.dataframe(pd.DataFrame(errors), hide_index=True, use_container_width=True)
    else:
        st.success(f"校验通过：{len(valid)} 行数据均可导入。")
        if valid:
            preview_rows = []
            for record in valid[:50]:
                chapter = chapter_index["by_id"].get(record["chapter_id"])
                preview_rows.append(
                    {
                        "省份": province_label(record["province_code"]),
                        "章节": chapter["path"] if chapter else "",
                        "题型": record["type"],
                        "题干": shorten(record["stem"], 60),
                        "答案": ",".join(record["answer"] or []),
                        "是否免费": "是" if record["is_free"] else "否",
                    }
                )
            st.dataframe(
                pd.DataFrame(preview_rows), hide_index=True, use_container_width=True
            )

    if errors or not valid:
        st.button("确认导入", type="primary", disabled=True)
        return

    if st.button(f"确认导入 {len(valid)} 道题目", type="primary"):
        try:
            count = insert_questions(valid)
        except SQLAlchemyError as exc:
            st.error(f"导入失败，事务已回滚：{exc}")
            return
        st.session_state["question_import_result"] = {"count": count}
        st.session_state["question_upload_nonce"] = nonce + 1
        clear_db_caches()
        st.rerun()


def render_question_edit(chapter_index: dict[str, Any]) -> None:
    st.subheader("单题编辑")
    questions = get_table("questions")

    load_col, info_col = st.columns([1, 3])
    with load_col:
        question_id = st.number_input(
            "题目 ID", min_value=1, step=1, value=1, key="question_edit_load_id"
        )
        if st.button("加载题目", type="primary", use_container_width=True):
            question = fetch_question(int(question_id))
            if question is None:
                st.session_state.pop("editing_question", None)
                st.error(f"题目 ID {question_id} 不存在")
            else:
                st.session_state["editing_question"] = question
                st.session_state["question_edit_nonce"] = (
                    st.session_state.get("question_edit_nonce", 0) + 1
                )

    question = st.session_state.get("editing_question")
    if not question:
        with info_col:
            st.info("输入题目 ID 并点击「加载题目」后即可编辑。")
        return

    qid = int(question["id"])
    nonce = st.session_state.setdefault("question_edit_nonce", 0)
    with info_col:
        st.caption(
            f"当前编辑题目 #{qid}，创建时间 {format_dt(question.get('created_at'))}；"
            "题目所属章节可为空。"
        )

    province_options = province_select_options()
    current_province = question.get("province_code") or "national"
    if current_province not in province_options:
        province_options.append(current_province)
    province_index = province_options.index(current_province)
    selected_province = st.selectbox(
        "省份",
        options=province_options,
        index=province_index,
        format_func=province_select_label,
        key=f"qe_{qid}_{nonce}_province",
    )

    province_chapters = [
        row for row in chapter_index["rows"] if row["province_code"] == selected_province
    ]
    chapter_ids: list[int | None] = [None] + [int(row["id"]) for row in province_chapters]
    current_chapter = question.get("chapter_id")
    if current_chapter not in chapter_ids:
        current_chapter = None
    chapter_index_value = chapter_ids.index(current_chapter)

    def chapter_format(chapter_id: int | None) -> str:
        if chapter_id is None:
            return "未指定章节"
        row = chapter_index["by_id"].get(chapter_id)
        return f"{chapter_id} - {row['path']}" if row else str(chapter_id)

    selected_chapter = st.selectbox(
        "章节",
        options=chapter_ids,
        index=chapter_index_value,
        format_func=chapter_format,
        key=f"qe_{qid}_{nonce}_chapter",
    )

    type_options = ["single", "multi", "judge"]
    selected_type = st.selectbox(
        "题型",
        options=type_options,
        index=type_options.index(question.get("type"))
        if question.get("type") in type_options
        else 0,
        format_func=lambda value: {
            "single": "single - 单选",
            "multi": "multi - 多选",
            "judge": "judge - 判断",
        }.get(value, value),
        key=f"qe_{qid}_{nonce}_type",
    )

    stem = st.text_area(
        "题干", value=question.get("stem") or "", height=120, key=f"qe_{qid}_{nonce}_stem"
    )

    st.markdown("**选项**")
    option_map: dict[str, str] = {}
    for option in question.get("options") or []:
        if isinstance(option, dict) and option.get("key"):
            option_map[str(option["key"]).upper()] = str(option.get("text") or "")

    raw_options: dict[str, str] = {}
    option_columns = st.columns(3)
    for position, letter in enumerate("ABCDEF"):
        with option_columns[position % 3]:
            raw_options[letter] = st.text_input(
                f"选项 {letter}",
                value=option_map.get(letter, ""),
                key=f"qe_{qid}_{nonce}_opt_{letter}",
            )
    if selected_type == "judge":
        st.caption("判断题若六个选项全部留空，保存时会自动生成 A 正确 / B 错误。")

    answer = st.text_input(
        "答案",
        value=",".join(question.get("answer") or []),
        help="单选填 A；多选填 A,B 或 AB；判断题填 A/B 或 正确/错误。",
        key=f"qe_{qid}_{nonce}_answer",
    )
    explanation = st.text_area(
        "解析",
        value=question.get("explanation") or "",
        height=100,
        key=f"qe_{qid}_{nonce}_explanation",
    )

    row1 = st.columns(3)
    difficulty_options = ["easy", "medium", "hard"]
    current_difficulty = question.get("difficulty") or "medium"
    if current_difficulty not in difficulty_options:
        current_difficulty = "medium"
    with row1[0]:
        difficulty = st.selectbox(
            "难度",
            options=difficulty_options,
            index=difficulty_options.index(current_difficulty),
            format_func=lambda value: DIFFICULTY_LABELS.get(value, value),
            key=f"qe_{qid}_{nonce}_difficulty",
        )
    with row1[1]:
        year = st.text_input(
            "真题年份",
            value=question.get("year") or "",
            key=f"qe_{qid}_{nonce}_year",
        )
    with row1[2]:
        law_ids = st.text_input(
            "关联条文 ID",
            value=",".join(str(item) for item in (question.get("law_article_ids") or [])),
            help="填 law_articles.id，多个用逗号分隔。",
            key=f"qe_{qid}_{nonce}_law_ids",
        )

    row2 = st.columns(2)
    with row2[0]:
        is_free = st.checkbox(
            "是否免费",
            value=bool(question.get("is_free")),
            key=f"qe_{qid}_{nonce}_is_free",
        )
    with row2[1]:
        status_options = ["published", "draft"]
        current_status = question.get("status") or "published"
        status = st.selectbox(
            "状态",
            options=status_options,
            index=status_options.index(current_status)
            if current_status in status_options
            else 0,
            format_func=lambda value: "published - 已发布"
            if value == "published"
            else "draft - 草稿",
            key=f"qe_{qid}_{nonce}_status",
        )

    source_note = st.text_area(
        "来源说明",
        value=question.get("source_note") or "",
        height=70,
        key=f"qe_{qid}_{nonce}_source_note",
    )

    if st.button("保存修改", type="primary", key=f"qe_{qid}_{nonce}_save"):
        payload, errors = parse_question_core(
            province_code=selected_province,
            chapter_id=int(selected_chapter) if selected_chapter is not None else None,
            qtype=selected_type,
            stem=stem,
            raw_options=raw_options,
            raw_answer=answer,
            explanation=explanation,
            difficulty=difficulty,
            year=year,
            source_note=source_note,
            law_ids_raw=law_ids,
            is_free_value=is_free,
            status=status,
        )
        if errors:
            st.error("保存失败：" + "；".join(errors))
        elif payload is not None:
            values = dict(payload)
            values["options"] = to_db_json(questions.c.options, values["options"])
            values["answer"] = to_db_json(questions.c.answer, values["answer"])
            values["law_article_ids"] = to_db_json(
                questions.c.law_article_ids, values["law_article_ids"]
            )
            with get_engine(DATABASE_URL).begin() as conn:
                result = conn.execute(
                    update(questions).where(questions.c.id == qid).values(**values)
                )
            if result.rowcount == 0:
                st.error(f"题目 ID {qid} 不存在，未发生修改。")
            else:
                st.success(f"题目 #{qid} 已保存。")
                updated = fetch_question(qid)
                if updated is not None:
                    st.session_state["editing_question"] = updated


def parse_id_list(raw: str) -> tuple[list[int], list[str]]:
    parts = [part for part in re.split(r"[,，、;；\s]+", str(raw or "").strip()) if part]
    numbers: list[int] = []
    invalid: list[str] = []
    for part in parts:
        if not part.isdigit() or int(part) <= 0:
            invalid.append(part)
        elif int(part) not in numbers:
            numbers.append(int(part))
    return numbers, invalid


def render_question_publish() -> None:
    st.subheader("发布与下架")
    questions = get_table("questions")
    st.caption("支持一次填写多个题目 ID，用逗号、空格或换行分隔。")
    raw_ids = st.text_area(
        "题目 ID 列表", placeholder="例如：12, 15, 18", key="question_publish_ids"
    )
    action = st.radio(
        "操作",
        options=["published", "draft"],
        format_func=lambda value: "发布（published）"
        if value == "published"
        else "下架（draft）",
        horizontal=True,
        key="question_publish_action",
    )
    if st.button("执行状态变更", type="primary", key="question_publish_submit"):
        ids, invalid = parse_id_list(raw_ids)
        if invalid:
            st.error("以下内容不是合法题目 ID：" + "、".join(invalid))
            return
        if not ids:
            st.warning("请至少填写一个题目 ID。")
            return
        existing = fetch_all(select(questions.c.id).where(questions.c.id.in_(ids)))
        existing_ids = {int(row["id"]) for row in existing}
        missing = sorted(set(ids) - existing_ids)
        if not existing_ids:
            st.error("所填写的题目 ID 均不存在。")
            return
        with get_engine(DATABASE_URL).begin() as conn:
            conn.execute(
                update(questions)
                .where(questions.c.id.in_(existing_ids))
                .values(status=action)
            )
        st.success(
            f"已将 {len(existing_ids)} 道题目状态改为 {action}（{'已发布' if action == 'published' else '草稿'}）。"
        )
        if missing:
            st.warning("以下 ID 不存在，已跳过：" + "、".join(str(item) for item in missing))


def render_question_list() -> None:
    st.subheader("题目列表")
    questions = get_table("questions")
    chapters = get_table("chapters")

    filter_columns = st.columns(4)
    with filter_columns[0]:
        province = st.selectbox(
            "省份",
            options=province_filter_options(),
            format_func=province_filter_label,
            key="question_list_province",
        )
    with filter_columns[1]:
        status = st.selectbox(
            "状态",
            options=["", "published", "draft"],
            format_func=lambda value: "全部状态"
            if not value
            else ("published - 已发布" if value == "published" else "draft - 草稿"),
            key="question_list_status",
        )
    with filter_columns[2]:
        qtype = st.selectbox(
            "题型",
            options=["", "single", "multi", "judge"],
            format_func=lambda value: "全部题型" if not value else value,
            key="question_list_type",
        )
    with filter_columns[3]:
        keyword = st.text_input("题干关键词", key="question_list_keyword")

    limit = st.slider("最多显示条数", min_value=50, max_value=1000, value=200, step=50)
    conditions = []
    if province:
        conditions.append(questions.c.province_code == province)
    if status:
        conditions.append(questions.c.status == status)
    if qtype:
        conditions.append(questions.c.type == qtype)
    if keyword.strip():
        conditions.append(questions.c.stem.like(f"%{keyword.strip()}%"))

    stmt = (
        select(
            questions.c.id,
            questions.c.province_code,
            chapters.c.name.label("chapter_name"),
            questions.c.chapter_id,
            questions.c.type,
            questions.c.stem,
            questions.c.options,
            questions.c.answer,
            questions.c.difficulty,
            questions.c.year,
            questions.c.is_free,
            questions.c.status,
            questions.c.created_at,
        )
        .outerjoin(chapters, questions.c.chapter_id == chapters.c.id)
        .order_by(questions.c.id.desc())
        .limit(limit)
    )
    count_stmt = select(func.count()).select_from(questions)
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(fetch_scalar(count_stmt))
    rows = fetch_all(stmt)
    st.caption(f"符合条件共 {total} 道题目，当前显示最近 {len(rows)} 道。")

    table_rows = []
    for row in rows:
        options = json_load(row["options"], [])
        answer = json_load(row["answer"], [])
        option_preview = "；".join(
            f"{item.get('key')}.{shorten(item.get('text'), 16)}"
            for item in options
            if isinstance(item, dict)
        )
        table_rows.append(
            {
                "ID": row["id"],
                "省份": province_label(row["province_code"]),
                "章节": row["chapter_name"] or "-",
                "题型": row["type"],
                "题干": shorten(row["stem"], 70),
                "选项预览": shorten(option_preview, 80),
                "答案": ",".join(str(item) for item in answer),
                "难度": DIFFICULTY_LABELS.get(row["difficulty"], row["difficulty"]),
                "年份": row["year"] or "",
                "免费": "是" if row["is_free"] else "否",
                "状态": "已发布" if row["status"] == "published" else "草稿",
                "创建时间": format_dt(row["created_at"]),
            }
        )
    if table_rows:
        st.dataframe(
            pd.DataFrame(table_rows), hide_index=True, use_container_width=True
        )
    else:
        st.info("没有符合条件的题目。")


def render_questions() -> None:
    st.header("题目管理")
    chapter_index = load_chapter_index()
    tab_import, tab_edit, tab_publish, tab_list = st.tabs(
        ["Excel 批量导入", "单题编辑", "发布与下架", "题目列表"]
    )
    with tab_import:
        render_question_import(chapter_index)
    with tab_edit:
        render_question_edit(chapter_index)
    with tab_publish:
        render_question_publish()
    with tab_list:
        render_question_list()


# ---------------------------------------------------------------------------
# 法规管理
# ---------------------------------------------------------------------------


def render_law_import() -> None:
    result = st.session_state.pop("law_import_result", None)
    if result:
        st.success(
            "导入完成："
            f"新建法规文档 {result['created_docs']} 个，"
            f"写入条文 {result['inserted_articles']} 条，"
            f"跳过重复条文 {result['skipped_articles']} 条。"
        )

    st.subheader("Excel / CSV 按条导入")
    st.caption("同一「省份 + 法规名称」视为同一法规文档；文档不存在时会自动创建。")
    template = pd.DataFrame(columns=LAW_COLUMNS)
    download_columns = st.columns(2)
    with download_columns[0]:
        st.download_button(
            "下载法规导入模板 Excel",
            data=dataframe_to_xlsx(template),
            file_name="法规导入模板.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with download_columns[1]:
        st.download_button(
            "下载法规导入模板 CSV",
            data=dataframe_to_csv(template),
            file_name="法规导入模板.csv",
            mime="text/csv",
        )

    nonce = st.session_state.setdefault("law_upload_nonce", 0)
    uploaded = st.file_uploader(
        "上传法规 Excel / CSV",
        type=["xlsx", "csv"],
        key=f"law_upload_{nonce}",
    )
    if uploaded is None:
        return

    try:
        df = read_uploaded_table(uploaded)
    except AdminError as exc:
        st.error(str(exc))
        return

    missing_required, missing_optional = check_headers(
        df, LAW_REQUIRED_HEADERS, LAW_COLUMNS
    )
    if missing_required:
        st.error("缺少必需列：" + "、".join(missing_required))
        st.info("请下载模板，按模板列名填写后重新上传。")
        return
    if missing_optional:
        st.warning("缺少可选列，将按空值处理：" + "、".join(missing_optional))

    st.caption(f"文件：{uploaded.name}，共 {len(df)} 行。以下为前 50 行预览。")
    st.dataframe(df.head(50), hide_index=True, use_container_width=True)

    if df.empty:
        st.info("文件中没有数据行。")
        return

    valid, errors = validate_law_dataframe(df)
    if errors:
        st.error(f"校验未通过：{len(errors)} 行存在错误，请修正后重新上传。")
        st.dataframe(pd.DataFrame(errors), hide_index=True, use_container_width=True)
    else:
        st.success(f"校验通过：{len(valid)} 行条文可以导入。")
        if valid:
            preview_rows = []
            for record in valid[:50]:
                preview_rows.append(
                    {
                        "省份": province_label(record["province_code"]),
                        "法规名称": record["title"],
                        "分类": record["category"],
                        "效力状态": LAW_STATUS_LABELS.get(record["status"], record["status"]),
                        "条号": record["article_no"],
                        "条文内容": shorten(record["content"], 60),
                    }
                )
            st.dataframe(
                pd.DataFrame(preview_rows), hide_index=True, use_container_width=True
            )

    if errors or not valid:
        st.button("确认导入", type="primary", disabled=True)
        return

    skip_existing = st.checkbox(
        "跳过已存在的同文档同条号（推荐）", value=True, key="law_import_skip_existing"
    )
    if st.button(f"确认导入 {len(valid)} 条条文", type="primary"):
        try:
            result = import_law_records(valid, skip_existing=skip_existing)
        except SQLAlchemyError as exc:
            st.error(f"导入失败，事务已回滚：{exc}")
            return
        st.session_state["law_import_result"] = result
        st.session_state["law_upload_nonce"] = nonce + 1
        st.rerun()


def render_law_list() -> None:
    st.subheader("法规文档与状态")
    documents = get_table("law_documents")
    articles = get_table("law_articles")

    filter_columns = st.columns(4)
    with filter_columns[0]:
        province = st.selectbox(
            "省份",
            options=province_filter_options(),
            format_func=province_filter_label,
            key="law_list_province",
        )
    with filter_columns[1]:
        category = st.selectbox(
            "分类",
            options=[""] + LAW_CATEGORIES,
            format_func=lambda value: "全部分类" if not value else value,
            key="law_list_category",
        )
    with filter_columns[2]:
        status = st.selectbox(
            "效力状态",
            options=["", "effective", "revised", "repealed"],
            format_func=lambda value: "全部状态"
            if not value
            else LAW_STATUS_LABELS.get(value, value),
            key="law_list_status",
        )
    with filter_columns[3]:
        keyword = st.text_input("法规名称关键词", key="law_list_keyword")

    conditions = []
    if province:
        conditions.append(documents.c.province_code == province)
    if category:
        conditions.append(documents.c.category == category)
    if status:
        conditions.append(documents.c.status == status)
    if keyword.strip():
        conditions.append(documents.c.title.like(f"%{keyword.strip()}%"))

    stmt = select(documents).order_by(documents.c.id.desc()).limit(500)
    if conditions:
        stmt = stmt.where(*conditions)
    rows = fetch_all(stmt)
    counts = {
        int(row["document_id"]): int(row["article_count"])
        for row in fetch_all(
            select(
                articles.c.document_id,
                func.count(articles.c.id).label("article_count"),
            ).group_by(articles.c.document_id)
        )
    }

    if not rows:
        st.info("没有符合筛选条件的法规文档。")
        return

    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "ID": row["id"],
                "省份": province_label(row["province_code"]),
                "法规名称": row["title"],
                "分类": row["category"],
                "发文单位": row["issuer"] or "",
                "发布日期": format_date(row["publish_date"]),
                "修订日期": format_date(row["revise_date"]),
                "效力状态": LAW_STATUS_LABELS.get(row["status"], row["status"]),
                "条文数": counts.get(int(row["id"]), 0),
            }
        )
    st.dataframe(
        pd.DataFrame(table_rows), hide_index=True, use_container_width=True
    )
    st.caption("仅展示最多 500 个文档。管理后台不提供删除功能，可通过修改效力状态下架法规。")

    st.divider()
    st.markdown("**修改法规效力状态**")
    document_map = {int(row["id"]): row for row in rows}
    selected_id = st.selectbox(
        "选择法规文档",
        options=list(document_map.keys()),
        format_func=lambda value: (
            f"{value} - {document_map[value]['title']}"
            f"（{province_label(document_map[value]['province_code'])}，"
            f"{LAW_STATUS_LABELS.get(document_map[value]['status'], document_map[value]['status'])}）"
        ),
        key="law_status_document",
    )
    selected_document = document_map[selected_id]
    current_status = selected_document["status"]
    status_options = ["effective", "revised", "repealed"]
    new_status = st.selectbox(
        "新的效力状态",
        options=status_options,
        index=status_options.index(current_status)
        if current_status in status_options
        else 0,
        format_func=lambda value: LAW_STATUS_LABELS.get(value, value),
        key="law_status_new",
    )
    if st.button("保存效力状态", type="primary", key="law_status_save"):
        with get_engine(DATABASE_URL).begin() as conn:
            conn.execute(
                update(documents)
                .where(documents.c.id == selected_id)
                .values(status=new_status)
            )
        set_flash(
            f"法规文档 #{selected_id} 的效力状态已改为"
            f"{LAW_STATUS_LABELS.get(new_status, new_status)}。"
        )
        st.rerun()

    with st.expander("查看所选法规的前 100 条条文"):
        article_rows = fetch_all(
            select(articles)
            .where(articles.c.document_id == selected_id)
            .order_by(articles.c.sort_order, articles.c.id)
            .limit(100)
        )
        if article_rows:
            article_table = [
                {
                    "ID": row["id"],
                    "条号": row["article_no"],
                    "章标题": row["chapter_title"] or "",
                    "排序": row["sort_order"],
                    "条文内容": shorten(row["content"], 120),
                }
                for row in article_rows
            ]
            st.dataframe(
                pd.DataFrame(article_table), hide_index=True, use_container_width=True
            )
        else:
            st.info("该文档暂无条文。")


def render_laws() -> None:
    st.header("法规管理")
    tab_import, tab_list = st.tabs(["Excel / CSV 导入", "法规列表"])
    with tab_import:
        render_law_import()
    with tab_list:
        render_law_list()


# ---------------------------------------------------------------------------
# 激活码
# ---------------------------------------------------------------------------


def render_activation_codes() -> None:
    st.header("激活码")
    activation_codes = get_table("activation_codes")
    users = get_table("users")

    st.subheader("批量生成")
    with st.form("activation_generate_form"):
        form_columns = st.columns(4)
        with form_columns[0]:
            count = st.number_input("生成数量", min_value=1, max_value=500, value=10, step=1)
        with form_columns[1]:
            duration_days = st.number_input(
                "有效天数", min_value=1, max_value=3650, value=30, step=1
            )
        with form_columns[2]:
            prefix = st.text_input("自定义前缀（可空）", placeholder="例如 VIP")
        with form_columns[3]:
            note = st.text_input("备注（可空）", placeholder="例如 双十一活动")
        submitted = st.form_submit_button("生成激活码", type="primary")

    if submitted:
        clean_prefix = prefix.strip().upper()
        if clean_prefix and not re.fullmatch(r"[A-Z0-9-]{1,20}", clean_prefix):
            st.error("前缀只能包含大写字母、数字和短横线，长度不超过 20。")
            return
        clean_prefix = clean_prefix.strip("-")
        if note and len(note) > 200:
            st.error("备注不能超过 200 个字符。")
            return
        existing_codes = {
            str(row["code"])
            for row in fetch_all(select(activation_codes.c.code))
        }
        try:
            codes = generate_activation_codes(
                int(count), clean_prefix, existing_codes
            )
        except AdminError as exc:
            st.error(str(exc))
            return
        now = datetime.now()
        rows = [
            {
                "code": code,
                "duration_days": int(duration_days),
                "status": "unused",
                "used_by": None,
                "used_at": None,
                "created_at": now,
                "note": note.strip() or None,
            }
            for code in codes
        ]
        with get_engine(DATABASE_URL).begin() as conn:
            conn.execute(insert(activation_codes), rows)
        st.session_state["generated_activation_codes"] = [
            {
                "激活码": row["code"],
                "有效天数": row["duration_days"],
                "备注": row["note"] or "",
            }
            for row in rows
        ]
        set_flash(f"已生成 {len(codes)} 个激活码。")
        st.rerun()

    generated = st.session_state.get("generated_activation_codes")
    if generated:
        generated_df = pd.DataFrame(generated)
        st.markdown("**本次生成的激活码**")
        st.dataframe(generated_df, hide_index=True, use_container_width=True)
        st.download_button(
            "下载本次生成的激活码 CSV",
            data=dataframe_to_csv(generated_df),
            file_name=f"激活码_{datetime.now():%Y%m%d_%H%M%S}.csv",
            mime="text/csv",
        )

    st.divider()
    st.subheader("激活码列表")
    filter_columns = st.columns(3)
    with filter_columns[0]:
        status = st.selectbox(
            "状态",
            options=["", "unused", "used", "disabled"],
            format_func=lambda value: "全部状态"
            if not value
            else {"unused": "未使用", "used": "已使用", "disabled": "已禁用"}.get(
                value, value
            ),
            key="activation_list_status",
        )
    with filter_columns[1]:
        keyword = st.text_input("激活码 / 备注关键词", key="activation_list_keyword")
    with filter_columns[2]:
        limit = st.number_input(
            "最多显示条数", min_value=50, max_value=2000, value=500, step=50
        )

    conditions = []
    if status:
        conditions.append(activation_codes.c.status == status)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(
            or_(activation_codes.c.code.like(like), activation_codes.c.note.like(like))
        )
    stmt = (
        select(
            activation_codes.c.id,
            activation_codes.c.code,
            activation_codes.c.duration_days,
            activation_codes.c.status,
            activation_codes.c.used_by,
            activation_codes.c.used_at,
            activation_codes.c.created_at,
            activation_codes.c.note,
            users.c.phone.label("used_phone"),
            users.c.nickname.label("used_nickname"),
        )
        .outerjoin(users, activation_codes.c.used_by == users.c.id)
        .order_by(activation_codes.c.id.desc())
        .limit(int(limit))
    )
    if conditions:
        stmt = stmt.where(*conditions)
    rows = fetch_all(stmt)

    if not rows:
        st.info("没有符合条件的激活码。")
        return

    status_labels = {"unused": "未使用", "used": "已使用", "disabled": "已禁用"}
    table_rows = []
    for row in rows:
        if row["used_phone"]:
            used_by_text = row["used_phone"]
            if row["used_nickname"]:
                used_by_text += f"（{row['used_nickname']}）"
        elif row["used_by"]:
            used_by_text = f"用户 ID {row['used_by']}"
        else:
            used_by_text = ""
        table_rows.append(
            {
                "ID": row["id"],
                "激活码": row["code"],
                "有效天数": row["duration_days"],
                "状态": status_labels.get(row["status"], row["status"]),
                "使用者": used_by_text,
                "使用时间": format_dt(row["used_at"]),
                "创建时间": format_dt(row["created_at"]),
                "备注": row["note"] or "",
            }
        )
    st.caption(f"共显示 {len(rows)} 个激活码。")
    st.dataframe(
        pd.DataFrame(table_rows), hide_index=True, use_container_width=True
    )

    row_map = {int(row["id"]): row for row in rows}
    selected_ids = st.multiselect(
        "选择激活码进行操作",
        options=list(row_map.keys()),
        format_func=lambda value: f"{value} - {row_map[value]['code']}",
        key="activation_selected_ids",
    )
    action_columns = st.columns(2)
    with action_columns[0]:
        if st.button("禁用所选", key="activation_disable"):
            if not selected_ids:
                st.warning("请先选择激活码。")
            else:
                disable_ids = [
                    item for item in selected_ids if row_map[item]["status"] != "disabled"
                ]
                if not disable_ids:
                    st.info("所选激活码均已是禁用状态。")
                else:
                    with get_engine(DATABASE_URL).begin() as conn:
                        conn.execute(
                            update(activation_codes)
                            .where(activation_codes.c.id.in_(disable_ids))
                            .values(status="disabled")
                        )
                    used_count = sum(
                        1
                        for item in disable_ids
                        if row_map[item]["status"] == "used"
                    )
                    message = f"已禁用 {len(disable_ids)} 个激活码。"
                    if used_count:
                        message += " 已使用激活码被禁用不会影响已开通的会员。"
                    set_flash(message, "warning" if used_count else "success")
                    st.rerun()
    with action_columns[1]:
        if st.button("恢复所选为未使用", key="activation_restore"):
            if not selected_ids:
                st.warning("请先选择激活码。")
            else:
                restorable = [
                    item
                    for item in selected_ids
                    if row_map[item]["status"] == "disabled"
                    and row_map[item]["used_by"] is None
                ]
                skipped = len(selected_ids) - len(restorable)
                if restorable:
                    with get_engine(DATABASE_URL).begin() as conn:
                        conn.execute(
                            update(activation_codes)
                            .where(activation_codes.c.id.in_(restorable))
                            .values(status="unused")
                        )
                if restorable:
                    message = f"已恢复 {len(restorable)} 个激活码为未使用。"
                    if skipped:
                        message += f" 跳过 {skipped} 个：仅「已禁用且从未被使用」的激活码可恢复。"
                    set_flash(message, "warning" if skipped else "success")
                    st.rerun()
                else:
                    st.warning(
                        "没有可恢复的激活码。仅「已禁用且从未被使用」的激活码可以恢复。"
                    )


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------


def render_users() -> None:
    st.header("用户管理")
    users = get_table("users")
    memberships = get_table("memberships")
    answer_records = get_table("answer_records")
    wrong_questions = get_table("wrong_questions")
    exams = get_table("exams")

    st.subheader("用户列表")
    filter_columns = st.columns(3)
    with filter_columns[0]:
        keyword = st.text_input("手机号 / 昵称关键词", key="user_list_keyword")
    with filter_columns[1]:
        roles = [
            str(row["role"])
            for row in fetch_all(select(users.c.role).distinct().order_by(users.c.role))
            if row["role"]
        ]
        role = st.selectbox(
            "角色",
            options=[""] + roles,
            format_func=lambda value: "全部角色" if not value else value,
            key="user_list_role",
        )
    with filter_columns[2]:
        limit = st.number_input(
            "最多显示条数", min_value=50, max_value=2000, value=500, step=50
        )

    conditions = []
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(users.c.phone.like(like), users.c.nickname.like(like)))
    if role:
        conditions.append(users.c.role == role)

    stmt = (
        select(
            users.c.id,
            users.c.phone,
            users.c.nickname,
            users.c.province_code,
            users.c.role,
            users.c.created_at,
            memberships.c.expires_at.label("membership_expires_at"),
        )
        .outerjoin(memberships, memberships.c.user_id == users.c.id)
        .order_by(users.c.id.desc())
        .limit(int(limit))
    )
    if conditions:
        stmt = stmt.where(*conditions)
    rows = fetch_all(stmt)

    if not rows:
        st.info("没有符合条件的用户。")
        return

    table_rows = []
    for row in rows:
        active = is_active_member(row["membership_expires_at"])
        table_rows.append(
            {
                "ID": row["id"],
                "手机号": row["phone"],
                "昵称": row["nickname"] or "",
                "省份": province_label(row["province_code"]),
                "角色": row["role"],
                "注册时间": format_dt(row["created_at"]),
                "会员到期时间": format_dt(row["membership_expires_at"])
                if row["membership_expires_at"]
                else "未开通",
                "会员状态": "有效" if active else ("已过期" if row["membership_expires_at"] else "-"),
            }
        )
    st.caption(f"共显示 {len(rows)} 个用户。")
    st.dataframe(
        pd.DataFrame(table_rows), hide_index=True, use_container_width=True
    )

    st.divider()
    st.subheader("用户答题统计")
    user_map = {int(row["id"]): row for row in rows}
    selected_id = st.selectbox(
        "选择用户",
        options=list(user_map.keys()),
        format_func=lambda value: (
            f"{value} - {user_map[value]['phone']}"
            f"（{user_map[value]['nickname'] or '无昵称'}）"
        ),
        key="user_stats_selected",
    )
    answered_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(answer_records)
            .where(answer_records.c.user_id == selected_id)
        )
    )
    correct_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(answer_records)
            .where(
                answer_records.c.user_id == selected_id,
                answer_records.c.is_correct.is_(True),
            )
        )
    )
    wrong_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(wrong_questions)
            .where(
                wrong_questions.c.user_id == selected_id,
                wrong_questions.c.removed.is_(False),
            )
        )
    )
    exam_count = int(
        fetch_scalar(
            select(func.count())
            .select_from(exams)
            .where(exams.c.user_id == selected_id)
        )
    )
    accuracy = f"{(correct_count / answered_count * 100):.1f}%" if answered_count else "0.0%"
    stat_columns = st.columns(5)
    stat_columns[0].metric("做题数", answered_count)
    stat_columns[1].metric("正确数", correct_count)
    stat_columns[2].metric("正确率", accuracy)
    stat_columns[3].metric("错题数", wrong_count)
    stat_columns[4].metric("考试数", exam_count)

    st.divider()
    st.subheader("开通 / 延长会员")
    st.caption("若会员未过期则在原到期时间上叠加；已过期或未开通则从当前时间起算。")
    with st.form("membership_form"):
        phone = st.text_input("用户手机号", placeholder="例如 13800138000")
        days = st.number_input(
            "增加天数", min_value=1, max_value=3650, value=30, step=1
        )
        membership_submitted = st.form_submit_button("开通 / 延长", type="primary")
    if membership_submitted:
        phone_text = phone.strip()
        user_row = fetch_one(select(users).where(users.c.phone == phone_text))
        if user_row is None:
            st.error(f"手机号 {phone_text} 对应的用户不存在。")
        else:
            membership = fetch_one(
                select(memberships).where(memberships.c.user_id == user_row["id"])
            )
            now = datetime.now()
            current_expire = coerce_datetime(
                membership["expires_at"] if membership else None
            )
            base = current_expire if current_expire and current_expire > now else now
            new_expire = base + timedelta(days=int(days))
            with get_engine(DATABASE_URL).begin() as conn:
                if membership:
                    conn.execute(
                        update(memberships)
                        .where(memberships.c.user_id == user_row["id"])
                        .values(expires_at=new_expire)
                    )
                else:
                    conn.execute(
                        insert(memberships).values(
                            user_id=user_row["id"], expires_at=new_expire
                        )
                    )
            st.success(
                f"用户 {phone_text} 的会员到期时间已更新为 {format_dt(new_expire)}。"
            )

    st.divider()
    st.subheader("重置用户密码")
    st.caption("密码将以 passlib bcrypt 哈希写入，与后端认证兼容；需要环境安装 passlib[bcrypt]。")
    with st.form("reset_password_form"):
        reset_phone = st.text_input("用户手机号", key="reset_password_phone")
        new_password = st.text_input(
            "新密码", type="password", key="reset_password_new"
        )
        confirm_password = st.text_input(
            "确认新密码", type="password", key="reset_password_confirm"
        )
        password_submitted = st.form_submit_button("重置密码")
    if password_submitted:
        reset_phone_text = reset_phone.strip()
        if new_password != confirm_password:
            st.error("两次输入的密码不一致。")
        elif len(new_password) < 6:
            st.error("密码长度不能少于 6 位。")
        elif len(new_password.encode("utf-8")) > 72:
            st.error("密码过长：bcrypt 最多支持 72 字节。")
        else:
            user_row = fetch_one(select(users).where(users.c.phone == reset_phone_text))
            if user_row is None:
                st.error(f"手机号 {reset_phone_text} 对应的用户不存在。")
            else:
                try:
                    password_hash = hash_admin_password(new_password)
                except AdminError as exc:
                    st.error(str(exc))
                else:
                    with get_engine(DATABASE_URL).begin() as conn:
                        conn.execute(
                            update(users)
                            .where(users.c.id == user_row["id"])
                            .values(password_hash=password_hash)
                        )
                    st.success(f"用户 {reset_phone_text} 的密码已重置。")


# ---------------------------------------------------------------------------
# 配置管理
# ---------------------------------------------------------------------------


def parse_number_text(
    raw: str, label: str, *, integer: bool, minimum: float = 0
) -> tuple[int | float | None, str | None]:
    text = str(raw or "").strip()
    if not text:
        return None, None
    try:
        value = float(text)
    except ValueError:
        return None, f"{label} 必须是数字"
    if integer:
        if not value.is_integer():
            return None, f"{label} 必须是整数"
        number: int | float = int(value)
    else:
        number = value
    if number < minimum:
        return None, f"{label} 不能小于 {minimum:g}"
    return number, None


def parse_type_distribution(raw: str) -> tuple[dict[str, int] | None, str | None]:
    text = str(raw or "").strip()
    if not text:
        return None, None
    try:
        value = json.loads(text)
    except ValueError:
        return None, "type_distribution 必须是合法 JSON"
    if not isinstance(value, dict):
        return None, "type_distribution 必须是 JSON 对象"
    allowed = {"single", "multi", "judge"}
    unknown = [key for key in value if key not in allowed]
    if unknown:
        return None, "type_distribution 仅支持键 single / multi / judge"
    result: dict[str, int] = {}
    for key, item in value.items():
        try:
            number = int(item)
        except (TypeError, ValueError):
            return None, f"type_distribution.{key} 必须是非负整数"
        if number < 0:
            return None, f"type_distribution.{key} 不能为负数"
        result[key] = number
    return result, None


def number_text(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def render_exam_config() -> None:
    st.subheader("考试参数配置")
    st.info("[待定] 数值由管理员填写，系统不预置正式值。")
    exam_configs = get_table("exam_configs")
    config_rows = fetch_all(
        select(
            exam_configs.c.province_code,
            exam_configs.c.key,
            exam_configs.c.value,
        ).order_by(exam_configs.c.province_code, exam_configs.c.key)
    )
    config_map = {
        (row["province_code"], row["key"]): row["value"] for row in config_rows
    }

    if config_rows:
        overview = [
            {
                "省份": province_label(row["province_code"]),
                "键": row["key"],
                "值": row["value"],
            }
            for row in config_rows
        ]
        st.dataframe(
            pd.DataFrame(overview), hide_index=True, use_container_width=True
        )
    else:
        st.info("尚未配置任何省份的考试参数。")

    st.markdown("**编辑所选省份**")
    province_options = sorted(
        {code for code, _ in PROVINCES} | {row["province_code"] for row in config_rows}
    )
    selected_province = st.selectbox(
        "省份",
        options=province_options,
        format_func=province_select_label,
        key="exam_config_province",
    )

    def current_value(key: str) -> str:
        return str(config_map.get((selected_province, key), "") or "")

    field_columns = st.columns(4)
    with field_columns[0]:
        question_count_raw = st.text_input(
            "题量 question_count",
            value=current_value("question_count"),
            placeholder="待定",
            key=f"exam_config_question_count_{selected_province}",
        )
    with field_columns[1]:
        duration_raw = st.text_input(
            "时长（分钟）duration_minutes",
            value=current_value("duration_minutes"),
            placeholder="待定",
            key=f"exam_config_duration_{selected_province}",
        )
    with field_columns[2]:
        pass_score_raw = st.text_input(
            "及格分 pass_score",
            value=current_value("pass_score"),
            placeholder="待定",
            key=f"exam_config_pass_{selected_province}",
        )
    with field_columns[3]:
        total_score_raw = st.text_input(
            "总分 total_score",
            value=current_value("total_score"),
            placeholder="待定",
            key=f"exam_config_total_{selected_province}",
        )
    distribution_raw = st.text_area(
        "题型分布 type_distribution（JSON）",
        value=current_value("type_distribution"),
        placeholder='{"single": 10, "multi": 4, "judge": 6}',
        height=90,
        key=f"exam_config_distribution_{selected_province}",
    )
    st.caption("留空的字段不会写入数据库，也不会覆盖已有值。")

    if st.button("保存考试参数", type="primary", key="exam_config_save"):
        errors: list[str] = []
        question_count, error = parse_number_text(
            question_count_raw, "题量", integer=True, minimum=1
        )
        if error:
            errors.append(error)
        duration_minutes, error = parse_number_text(
            duration_raw, "时长", integer=True, minimum=1
        )
        if error:
            errors.append(error)
        pass_score, error = parse_number_text(
            pass_score_raw, "及格分", integer=False, minimum=0
        )
        if error:
            errors.append(error)
        total_score, error = parse_number_text(
            total_score_raw, "总分", integer=False, minimum=0
        )
        if error:
            errors.append(error)
        distribution, error = parse_type_distribution(distribution_raw)
        if error:
            errors.append(error)
        if pass_score is not None and total_score is not None and pass_score > total_score:
            errors.append("及格分不能大于总分")

        if errors:
            st.error("保存失败：" + "；".join(errors))
            return

        updates: list[tuple[str, str]] = []
        if question_count is not None:
            updates.append(("question_count", str(int(question_count))))
        if duration_minutes is not None:
            updates.append(("duration_minutes", str(int(duration_minutes))))
        if pass_score is not None:
            updates.append(("pass_score", number_text(pass_score)))
        if total_score is not None:
            updates.append(("total_score", number_text(total_score)))
        if distribution is not None:
            updates.append(
                ("type_distribution", json.dumps(distribution, ensure_ascii=False))
            )

        if not updates:
            st.warning("没有填写任何需要保存的配置项。")
            return

        with get_engine(DATABASE_URL).begin() as conn:
            for key, value in updates:
                exists = conn.execute(
                    select(exam_configs.c.id).where(
                        exam_configs.c.province_code == selected_province,
                        exam_configs.c.key == key,
                    )
                ).first()
                if exists is None:
                    conn.execute(
                        insert(exam_configs).values(
                            province_code=selected_province, key=key, value=value
                        )
                    )
                else:
                    conn.execute(
                        update(exam_configs)
                        .where(
                            exam_configs.c.province_code == selected_province,
                            exam_configs.c.key == key,
                        )
                        .values(value=value)
                    )
        message = (
            f"已保存 {province_label(selected_province)} 的 {len(updates)} 项考试参数。"
        )
        if (
            question_count is not None
            and distribution is not None
            and sum(distribution.values()) != int(question_count)
        ):
            message += " 注意：题型分布之和与题量不一致，请复核。"
        set_flash(message)
        st.rerun()


def render_site_config() -> None:
    st.subheader("站点配置")
    site_configs = get_table("site_configs")
    rows = fetch_all(
        select(site_configs.c.key, site_configs.c.value).order_by(site_configs.c.key)
    )
    value_map = {str(row["key"]): str(row["value"] or "") for row in rows}
    fixed_keys = ["service_phone", "service_wechat", "service_intro"]
    extra_keys = sorted(key for key in value_map if key not in fixed_keys)
    labels = {
        "service_phone": "客服电话 service_phone",
        "service_wechat": "客服微信 service_wechat",
        "service_intro": "服务介绍 service_intro",
    }
    st.caption("以下三项为常用配置；保存空值也会写入空字符串，用于清空原有内容。")

    edited: dict[str, str] = {}
    for key in fixed_keys:
        if key == "service_intro":
            edited[key] = st.text_area(
                labels[key],
                value=value_map.get(key, ""),
                height=100,
                key=f"site_config_{key}",
            )
        else:
            edited[key] = st.text_input(
                labels[key],
                value=value_map.get(key, ""),
                key=f"site_config_{key}",
            )
    for key in extra_keys:
        edited[key] = st.text_input(
            f"{key}（自定义）",
            value=value_map.get(key, ""),
            key=f"site_config_{key}",
        )

    if st.button("保存站点配置", type="primary", key="site_config_save"):
        with get_engine(DATABASE_URL).begin() as conn:
            for key, value in edited.items():
                exists = conn.execute(
                    select(site_configs.c.id).where(site_configs.c.key == key)
                ).first()
                if exists is None:
                    conn.execute(
                        insert(site_configs).values(key=key, value=value)
                    )
                else:
                    conn.execute(
                        update(site_configs)
                        .where(site_configs.c.key == key)
                        .values(value=value)
                    )
        set_flash(f"已保存 {len(edited)} 项站点配置。")
        st.rerun()

    st.divider()
    st.subheader("新增自定义配置键")
    with st.form("site_config_add_form"):
        new_key = st.text_input("配置键", placeholder="仅小写字母、数字、下划线")
        new_value = st.text_area("配置值", height=80)
        add_submitted = st.form_submit_button("新增配置键", type="primary")
    if add_submitted:
        clean_key = new_key.strip()
        if not re.fullmatch(r"[a-z0-9_]{1,64}", clean_key):
            st.error("配置键只能包含小写字母、数字和下划线，长度 1~64。")
        elif clean_key in value_map:
            st.error("该配置键已存在，请在上方直接编辑后保存。")
        else:
            with get_engine(DATABASE_URL).begin() as conn:
                conn.execute(
                    insert(site_configs).values(key=clean_key, value=new_value)
                )
            set_flash(f"已新增站点配置键 {clean_key}。")
            st.rerun()


def render_configs() -> None:
    st.header("配置管理")
    tab_exam, tab_site = st.tabs(["考试参数", "站点配置"])
    with tab_exam:
        render_exam_config()
    with tab_site:
        render_site_config()


# ---------------------------------------------------------------------------
# 意见反馈
# ---------------------------------------------------------------------------


def render_feedbacks() -> None:
    st.header("意见反馈")
    feedbacks = get_table("feedbacks")
    users = get_table("users")

    filter_columns = st.columns(2)
    with filter_columns[0]:
        keyword = st.text_input("反馈内容关键词", key="feedback_keyword")
    with filter_columns[1]:
        limit = st.number_input(
            "最多显示条数", min_value=50, max_value=2000, value=500, step=50
        )

    conditions = []
    if keyword.strip():
        conditions.append(feedbacks.c.content.like(f"%{keyword.strip()}%"))
    stmt = (
        select(
            feedbacks.c.id,
            feedbacks.c.content,
            feedbacks.c.created_at,
            users.c.phone,
            users.c.nickname,
        )
        .outerjoin(users, feedbacks.c.user_id == users.c.id)
        .order_by(feedbacks.c.created_at.desc(), feedbacks.c.id.desc())
        .limit(int(limit))
    )
    if conditions:
        stmt = stmt.where(*conditions)
    rows = fetch_all(stmt)

    count_stmt = select(func.count()).select_from(feedbacks)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int(fetch_scalar(count_stmt))
    st.metric("反馈总数", total)

    if not rows:
        st.info("暂无符合条件的反馈。")
        return

    table_rows = []
    for row in rows:
        table_rows.append(
            {
                "ID": row["id"],
                "用户手机号": row["phone"] or "游客 / 用户已删除",
                "昵称": row["nickname"] or "",
                "反馈内容": row["content"],
                "提交时间": format_dt(row["created_at"]),
            }
        )
    st.caption(f"当前显示最近 {len(rows)} 条反馈。")
    st.dataframe(
        pd.DataFrame(table_rows), hide_index=True, use_container_width=True
    )


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="题库管理后台", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        div[data-testid="stMetricValue"] { font-size: 1.7rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.get("admin_authenticated"):
        render_login()
        st.stop()

    ensure_database_ready()
    page = render_sidebar()
    show_flash()

    renderers = {
        "数据概览": render_overview,
        "题目管理": render_questions,
        "法规管理": render_laws,
        "激活码": render_activation_codes,
        "用户管理": render_users,
        "配置管理": render_configs,
        "意见反馈": render_feedbacks,
    }
    try:
        renderers[page]()
    except AdminError as exc:
        st.error(str(exc))
    except SQLAlchemyError as exc:
        st.error(f"数据库操作失败：{exc}")
        with st.expander("查看错误详情"):
            st.exception(exc)
    except Exception as exc:  # noqa: BLE001 - 保证后台页面不因单页异常白屏
        st.error("页面执行失败，请查看错误详情。")
        with st.expander("查看错误详情"):
            st.exception(exc)

    st.divider()
    st.caption("题库管理后台 · 直接读写业务数据库，请谨慎操作并定期备份。")


if __name__ == "__main__":
    main()
