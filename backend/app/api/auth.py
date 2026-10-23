import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx

logger = logging.getLogger("security.audit")
from sqlalchemy.orm import Session
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import (
    GENERIC_AUTH_ERROR,
    ensure_not_limited,
    get_client_ip,
    record_auth_failure,
    record_auth_success,
    reject_auth_failure,
)
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.models import PlatformUser, User, utc_now

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/check")
async def check_portal_session(request: Request):
    from app.core.portal import portal_identity
    await portal_identity(request)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/session")
async def get_session(request: Request, db: Session = Depends(get_db)):
    if not settings.PORTAL_AUTH_URL:
        return {"mode": "platform"}
    from app.core.portal import portal_identity
    identity = await portal_identity(request)
    uid = identity["uid"]
    user = db.query(PlatformUser).filter(PlatformUser.platform_user_id == uid).first()
    if not user:
        user = PlatformUser(platform_user_id=uid)
        db.add(user)
    user.staff_name = identity.get("displayName") or identity.get("username") or uid
    user.staff_code = identity.get("username") or ""
    db.commit()
    return {"mode": "portal", "authenticated": True, "userInfo": {
        "platformUserId": uid, "authMode": "portal", "platformToken": "",
        "staffName": user.staff_name, "staffCode": user.staff_code,
    }}


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TestTokenRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    userId: str
    platformToken: str = ""
    lanName: str = Field(default="", validation_alias=AliasChoices("lanName", "lan_name"))
    regionName: str = Field(default="", validation_alias=AliasChoices("regionName", "region_name"))
    staffCode: str = Field(default="", validation_alias=AliasChoices("staffCode", "staff_code"))
    staffName: str = Field(default="", validation_alias=AliasChoices("staffName", "staff_name"))
    staffPosType: str = Field(default="", validation_alias=AliasChoices("staffPosType", "staff_pos_type"))
    staffCodeBoss: str = Field(default="", validation_alias=AliasChoices("staffCodeBoss", "staff_code_boss"))


class UserLoginResponse(BaseModel):
    success: bool
    token: str | None = None
    userId: str | None = None
    lan_name: str | None = None
    region_name: str | None = None
    staff_code: str | None = None
    staff_name: str | None = None
    staff_pos_type: str | None = None
    error: str | None = None


def _clean_code(value) -> str:
    """Normalize IAM/user code values for exact business-code comparison."""
    return str(value or "").strip()


def _extract_iam_staff_code_candidates(data: dict) -> set[str]:
    """Extract possible staff-code fields from IAM response.

    The mobile IAM document mentions staff_code, while the sample response
    exposes acctNo/subAcctNo. Keep the parser tolerant so deployment-side
    field naming differences do not require a code change.
    """
    if not isinstance(data, dict):
        return set()

    candidates = {
        data.get("staff_code"),
        data.get("staffCode"),
        data.get("staff_code_boss"),
        data.get("staffCodeBoss"),
        data.get("acctNo"),
        data.get("subAcctNo"),
    }
    return {_clean_code(value) for value in candidates if _clean_code(value)}


async def _verify_mobile_ticket(req: TestTokenRequest, request: Request) -> None:
    """Validate mobile IAM ticket and compare returned code with BOSS code."""
    ip = get_client_ip(request)
    user_id = req.userId.strip()
    ticket = req.platformToken.strip()
    staff_code_boss = req.staffCodeBoss.strip()

    logger.info(
        "IAM_VERIFY request ip=%s userId=%s ticket_len=%d ticket_head=%s staffCodeBoss=%s "
        "lanName=%s regionName=%s staffCode=%s staffName=%s staffPosType=%s",
        ip,
        user_id,
        len(ticket),
        ticket[:16],
        staff_code_boss,
        req.lanName,
        req.regionName,
        req.staffCode,
        req.staffName,
        req.staffPosType,
    )

    if not ticket:
        reject_auth_failure("platform_token", user_id, ip, "empty_ticket")
    if not staff_code_boss:
        reject_auth_failure("platform_token", user_id, ip, "empty_staff_code_boss")

    payload = {
        "ticket": ticket,
        "appCode": settings.IAM_APP_CODE,
    }
    logger.info(
        "IAM_VERIFY calling url=%s payload(appCode=%s ticket_len=%d)",
        settings.IAM_CHECK_TICKET_URL,
        payload["appCode"],
        len(payload["ticket"]),
    )

    body = None
    try:
        async with httpx.AsyncClient(timeout=settings.IAM_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.IAM_CHECK_TICKET_URL, json=payload)
            logger.info(
                "IAM_VERIFY http_status=%s content_type=%s body=%s",
                getattr(response, "status_code", None),
                response.headers.get("content-type"),
                response.text,
            )
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        logger.info(
            "IAM_VERIFY exception type=%s msg=%s",
            type(exc).__name__,
            str(exc),
        )
        reject_auth_failure("platform_token", user_id, ip, "iam_check_failed")

    logger.info(
        "IAM_VERIFY parsed body code=%s msg=%s data=%s",
        body.get("code") if isinstance(body, dict) else None,
        (body.get("msg") if isinstance(body, dict) else None),
        (body.get("data") if isinstance(body, dict) else None),
    )

    if body.get("code") != "000000":
        reject_auth_failure("platform_token", user_id, ip, "iam_rejected_ticket")

    iam_data = body.get("data") or {}
    iam_staff_codes = _extract_iam_staff_code_candidates(iam_data)
    logger.info(
        "IAM_VERIFY extracted staff_codes=%s staffCodeBoss=%s match=%s",
        iam_staff_codes,
        staff_code_boss,
        staff_code_boss in iam_staff_codes,
    )
    if staff_code_boss not in iam_staff_codes:
        reject_auth_failure("platform_token", user_id, ip, "staff_code_boss_mismatch")


@router.post("/login", response_model=UserLoginResponse)
async def login(req: UserLoginRequest, request: Request, db: Session = Depends(get_db)):
    """用户登录（用户名+密码）"""
    ip = get_client_ip(request)
    identifier = req.username.strip()
    ensure_not_limited("user_login", identifier, ip)

    user = db.query(User).filter(User.username == req.username).first()

    if not user:
        record_auth_failure("user_login", identifier, ip, "not_found")
        return UserLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    if not user.hashed_password:
        record_auth_failure("user_login", identifier, ip, "password_unset")
        return UserLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    if not verify_password(req.password, user.hashed_password):
        record_auth_failure("user_login", identifier, ip, "bad_password")
        return UserLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    if not user.is_active:
        record_auth_failure("user_login", identifier, ip, "inactive")
        return UserLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    record_auth_success("user_login", identifier, ip)
    token = create_access_token(data={"sub": user.id})
    return UserLoginResponse(
        success=True,
        token=token,
        userId=user.id,
        lan_name=user.lan_name or "",
        region_name=user.region_name or "",
        staff_code=user.staff_code or "",
        staff_name=user.staff_name or "",
        staff_pos_type=user.staff_pos_type or ""
    )


@router.post("/test-token", response_model=UserLoginResponse)
async def issue_test_token(req: TestTokenRequest, request: Request, db: Session = Depends(get_db)):
    """测试平台模式下签发普通用户 token。"""
    if settings.PORTAL_AUTH_URL:
        raise HTTPException(404, "门户模式不提供平台 Token 登录")
    ip = get_client_ip(request)
    user_id = req.userId.strip()
    ensure_not_limited("platform_token", user_id, ip)

    if not user_id:
        reject_auth_failure("platform_token", user_id, ip, "empty_user")

    legacy_platform_token_ok = (
        bool(settings.PLATFORM_ENTRY_TOKEN)
        and secrets.compare_digest(req.platformToken, settings.PLATFORM_ENTRY_TOKEN)
    )
    if not legacy_platform_token_ok:
        await _verify_mobile_ticket(req, request)

    platform_user = db.query(PlatformUser).filter(PlatformUser.platform_user_id == user_id).first()
    if not platform_user:
        platform_user = PlatformUser(
            platform_user_id=user_id,
            lan_name=req.lanName,
            region_name=req.regionName,
            staff_code=req.staffCode,
            staff_name=req.staffName,
            staff_pos_type=req.staffPosType,
        )
        db.add(platform_user)
    else:
        platform_user.lan_name = req.lanName or platform_user.lan_name
        platform_user.region_name = req.regionName or platform_user.region_name
        platform_user.staff_code = req.staffCode or platform_user.staff_code
        platform_user.staff_name = req.staffName or platform_user.staff_name
        platform_user.staff_pos_type = req.staffPosType or platform_user.staff_pos_type
        platform_user.updated_at = utc_now()
    db.commit()
    record_auth_success("platform_token", user_id, ip)

    token = create_access_token(data={"sub": user_id})
    return UserLoginResponse(
        success=True,
        token=token,
        userId=user_id,
        lan_name=platform_user.lan_name or "",
        region_name=platform_user.region_name or "",
        staff_code=platform_user.staff_code or "",
        staff_name=platform_user.staff_name or "",
        staff_pos_type=platform_user.staff_pos_type or "",
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user
