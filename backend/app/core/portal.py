"""Validate the existing CAS-backed portal cookie without sharing its secret."""

from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request

from app.core.config import settings


async def portal_identity(request: Request) -> dict:
    """Return a trusted stable uid; client headers never establish identity."""
    cached = getattr(request.state, "portal_identity", None)
    if cached is not None:
        return cached
    if not settings.PORTAL_AUTH_URL:
        raise HTTPException(503, "门户认证服务未配置")
    try:
        async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
            response = await client.get(
                settings.PORTAL_AUTH_URL.rstrip("/") + "/api/auth/me",
                headers={"Cookie": request.headers.get("cookie", "")},
            )
        if response.status_code == 401:
            raise HTTPException(401, "请先从门户登录")
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "门户认证服务暂不可用") from None
    if not isinstance(payload, dict):
        raise HTTPException(503, "门户身份响应无效")
    identity = payload.get("user") or {}
    if not isinstance(identity, dict):
        raise HTTPException(503, "门户身份响应无效")
    uid = identity.get("uid")
    if payload.get("authenticated") is not True or not isinstance(uid, str) or not uid or len(uid) > 100:
        raise HTTPException(401, "请先从门户登录")
    if request.headers.get("x-portal-user") not in (None, "", uid):
        raise HTTPException(401, "登录账号已切换，请刷新后继续")
    request.state.portal_identity = identity
    return identity


def check_write_origin(request: Request) -> None:
    """Cookie-authenticated writes require the app marker and same Origin."""
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    public = urlsplit(settings.APP_PUBLIC_URL)
    origin = f"{public.scheme}://{public.netloc}"
    if request.headers.get("x-living-stream-request") != "1" or request.headers.get("origin") != origin:
        raise HTTPException(403, "请求来源无效")
