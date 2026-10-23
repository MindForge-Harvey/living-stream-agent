import logging
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("security.audit")

GENERIC_AUTH_ERROR = "凭证无效或请求过于频繁"

_failures: dict[str, deque[float]] = defaultdict(deque)
_locks: dict[str, float] = {}


def get_client_ip(request: Request) -> str:
    """获取客户端 IP，兼容反向代理传入的 X-Forwarded-For。"""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def ensure_not_limited(action: str, identifier: str, ip: str) -> None:
    """按 action + IP + 账号维度检查失败锁定状态。"""
    now = time.time()
    for key in _rate_keys(action, identifier, ip):
        _prune_attempts(key, now)
        locked_until = _locks.get(key, 0)
        if locked_until > now:
            audit_auth_event(action, identifier, ip, False, "locked")
            raise HTTPException(status_code=429, detail=GENERIC_AUTH_ERROR)
        if locked_until and locked_until <= now:
            _locks.pop(key, None)


def record_auth_success(action: str, identifier: str, ip: str) -> None:
    """登录成功后清理相关失败计数。"""
    for key in _rate_keys(action, identifier, ip):
        _failures.pop(key, None)
        _locks.pop(key, None)
    audit_auth_event(action, identifier, ip, True)


def record_auth_failure(action: str, identifier: str, ip: str, reason: str = "invalid") -> None:
    """记录失败并在超过阈值后锁定。"""
    now = time.time()
    for key in _rate_keys(action, identifier, ip):
        attempts = _prune_attempts(key, now)
        attempts.append(now)
        if len(attempts) >= settings.AUTH_RATE_LIMIT_MAX_FAILURES:
            _locks[key] = now + settings.AUTH_LOCK_SECONDS
    audit_auth_event(action, identifier, ip, False, reason)


def reject_auth_failure(action: str, identifier: str, ip: str, reason: str = "invalid") -> None:
    record_auth_failure(action, identifier, ip, reason)
    raise HTTPException(
        status_code=401,
        detail={"msg": GENERIC_AUTH_ERROR, "reason": reason},
    )


def audit_auth_event(action: str, identifier: str, ip: str, success: bool, reason: str = "") -> None:
    result = "success" if success else "failure"
    logger.info(
        "auth_event action=%s identifier=%s ip=%s result=%s reason=%s",
        action,
        identifier or "-",
        ip,
        result,
        reason or "-",
    )


def _prune_attempts(key: str, now: float) -> deque[float]:
    attempts = _failures[key]
    cutoff = now - settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def _rate_keys(action: str, identifier: str, ip: str) -> tuple[str, str]:
    normalized_identifier = (identifier or "-").strip().lower()
    normalized_ip = ip or "unknown"
    return (
        f"{action}:ip:{normalized_ip}",
        f"{action}:user:{normalized_identifier}",
    )
