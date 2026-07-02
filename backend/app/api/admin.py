from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.models.models import Admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/admin", tags=["管理员"])
security = HTTPBearer()


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    success: bool
    token: str | None = None
    error: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> Admin:
    """获取当前登录的管理员"""
    token = credentials.credentials
    payload = decode_token(token)
    admin_id_str = payload.get("sub", "")

    if not admin_id_str.startswith("admin:"):
        raise HTTPException(status_code=401, detail="无效的管理员token")

    admin_id = int(admin_id_str.split(":")[1])
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    if not admin.is_active:
        raise HTTPException(status_code=401, detail="管理员账号已被禁用")
    return admin


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(req: AdminLoginRequest, db: Session = Depends(get_db)):
    """管理员登录"""
    admin = db.query(Admin).filter(Admin.username == req.username).first()

    if not admin or not verify_password(req.password, admin.hashed_password):
        return AdminLoginResponse(success=False, error="用户名或密码错误")

    if not admin.is_active:
        return AdminLoginResponse(success=False, error="账号已被禁用")

    token = create_access_token(data={"sub": f"admin:{admin.id}"})
    return AdminLoginResponse(success=True, token=token)


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, current_admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """修改管理员密码"""
    if not verify_password(req.old_password, current_admin.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")

    current_admin.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "密码修改成功"}


@router.get("/auth-by-user")
async def auth_by_user_id(
    user_id: str = Query(..., description="平台用户ID"),
    db: Session = Depends(get_db)
):
    """根据绑定的 userId 免密登录管理员后台
    
    超管在后台给管理员绑定了 userId 后，平台用户点击「后台管理」时
    调用此接口，若 userId 命中则直接签发 admin token，无需再次登录。
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    
    admin = db.query(Admin).filter(Admin.bound_user_id == user_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="该用户未绑定管理员账号")
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="管理员账号已被禁用")
    
    token = create_access_token(data={"sub": f"admin:{admin.id}"})
    return {
        "success": True,
        "token": token,
        "username": admin.username,
        "is_superadmin": admin.is_superadmin
    }
