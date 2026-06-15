from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, verify_password
from app.models.models import User

router = APIRouter(prefix="/auth", tags=["认证"])


class UserLoginRequest(BaseModel):
    username: str
    password: str


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


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user
