from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.models import PlatformUser, User, utc_now

router = APIRouter(prefix="/auth", tags=["认证"])


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TestTokenRequest(BaseModel):
    userId: str
    platformToken: str = ""
    lanName: str = ""
    regionName: str = ""
    staffCode: str = ""
    staffName: str = ""
    staffPosType: str = ""


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


@router.post("/login", response_model=UserLoginResponse)
async def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """用户登录（用户名+密码）"""
    user = db.query(User).filter(User.username == req.username).first()

    if not user:
        return UserLoginResponse(success=False, error="用户不存在")

    if not user.hashed_password:
        return UserLoginResponse(success=False, error="该账号未设置密码")

    if not verify_password(req.password, user.hashed_password):
        return UserLoginResponse(success=False, error="密码错误")

    if not user.is_active:
        return UserLoginResponse(success=False, error="账号已被禁用")

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
async def issue_test_token(req: TestTokenRequest, db: Session = Depends(get_db)):
    """测试平台模式下签发普通用户 token。"""
    if req.platformToken != settings.PLATFORM_ENTRY_TOKEN:
        raise HTTPException(status_code=404, detail="接口不存在")

    user_id = req.userId.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="userId 不能为空")

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
