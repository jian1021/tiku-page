"""简单的进程内滑动窗口限流工具。

说明：计数保存在当前进程内存中，多进程部署时各进程独立计数，
适用于单机小规模部署，不依赖 Redis 等外部组件。
"""

import threading
import time

from fastapi import HTTPException, status

# key -> 最近窗口内的命中时间戳列表
_hits: dict[str, list[float]] = {}
_lock = threading.Lock()


def _prune(timestamps: list[float], window_sec: int, now: float) -> list[float]:
    """移除窗口外的旧时间戳。"""
    if window_sec <= 0:
        return []
    boundary = now - window_sec
    return [item for item in timestamps if item > boundary]


def check_rate_limit(key: str, limit: int, window_sec: int) -> None:
    """记录一次请求；超过窗口内允许次数时抛出 429。"""
    now = time.time()
    with _lock:
        timestamps = _prune(_hits.get(key, []), window_sec, now)
        if len(timestamps) >= limit:
            _hits[key] = timestamps
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="操作过于频繁，请稍后再试",
            )
        timestamps.append(now)
        _hits[key] = timestamps


def record_failure(key: str, limit: int, window_sec: int) -> int:
    """记录一次失败，返回当前窗口内的失败次数。"""
    now = time.time()
    with _lock:
        timestamps = _prune(_hits.get(key, []), window_sec, now)
        timestamps.append(now)
        _hits[key] = timestamps
        count = len(timestamps)
    if limit > 0 and count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="尝试次数过多，请稍后再试",
        )
    return count


def failure_count(key: str, window_sec: int) -> int:
    """返回当前窗口内的失败次数（不写入新记录）。"""
    now = time.time()
    with _lock:
        timestamps = _prune(_hits.get(key, []), window_sec, now)
        if timestamps:
            _hits[key] = timestamps
        else:
            _hits.pop(key, None)
        return len(timestamps)


def clear(key: str) -> None:
    """清空指定 key 的计数（例如激活成功后）。"""
    with _lock:
        _hits.pop(key, None)
