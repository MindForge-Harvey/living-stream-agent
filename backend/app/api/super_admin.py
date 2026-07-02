from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_token
from app.models.models import Admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/super-admin", tags=["超级管理员"])
security = HTTPBearer()


class SuperAdminLoginRequest(BaseModel):
    username: str
    password: str


class SuperAdminLoginResponse(BaseModel):
    success: bool
    token: str | None = None
    error: str | None = None


class CreateAdminRequest(BaseModel):
    username: str
    password: str


class UpdateAdminRequest(BaseModel):
    username: Optional[str] = None
    is_active: Optional[bool] = None


class BindUserIdRequest(BaseModel):
    bound_user_id: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class AdminResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_superadmin: bool
    created_at: str

    class Config:
        from_attributes = True


def get_current_super_admin(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> Admin:
    """获取当前登录的超级管理员"""
    token = credentials.credentials
    payload = decode_token(token)
    admin_id_str = payload.get("sub", "")

    if not admin_id_str.startswith("super_admin:"):
        raise HTTPException(status_code=401, detail="无效的超级管理员token")

    admin_id = int(admin_id_str.split(":")[1])
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    if not admin.is_active:
        raise HTTPException(status_code=401, detail="管理员账号已被禁用")
    if not admin.is_superadmin:
        raise HTTPException(status_code=403, detail="权限不足，需要超级管理员权限")
    return admin


@router.post("/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(req: SuperAdminLoginRequest, db: Session = Depends(get_db)):
    """超级管理员登录"""
    admin = db.query(Admin).filter(Admin.username == req.username).first()

    if not admin or not verify_password(req.password, admin.hashed_password):
        return SuperAdminLoginResponse(success=False, error="用户名或密码错误")

    if not admin.is_active:
        return SuperAdminLoginResponse(success=False, error="账号已被禁用")

    if not admin.is_superadmin:
        return SuperAdminLoginResponse(success=False, error="权限不足，需要超级管理员权限")

    token = create_access_token(data={"sub": f"super_admin:{admin.id}"})
    return SuperAdminLoginResponse(success=True, token=token)


@router.get("/admins")
async def list_admins(current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """获取所有管理员列表"""
    admins = db.query(Admin).all()
    result = []
    for admin in admins:
        result.append({
            "id": admin.id,
            "username": admin.username,
            "is_active": admin.is_active,
            "is_superadmin": admin.is_superadmin,
            "bound_user_id": admin.bound_user_id,
            "created_at": admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else ""
        })
    return result


@router.post("/admins")
async def create_admin(req: CreateAdminRequest, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """创建新管理员"""
    existing = db.query(Admin).filter(Admin.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    new_admin = Admin(
        username=req.username,
        hashed_password=get_password_hash(req.password),
        is_active=True,
        is_superadmin=False
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return {
        "id": new_admin.id,
        "username": new_admin.username,
        "is_active": new_admin.is_active,
        "is_superadmin": new_admin.is_superadmin,
        "bound_user_id": new_admin.bound_user_id,
        "created_at": new_admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if new_admin.created_at else ""
    }


@router.put("/admins/{admin_id}")
async def update_admin(admin_id: int, req: UpdateAdminRequest, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """更新管理员信息"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if admin.is_superadmin:
        raise HTTPException(status_code=400, detail="不能修改超级管理员信息")

    if req.username is not None:
        existing = db.query(Admin).filter(Admin.username == req.username, Admin.id != admin_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        admin.username = req.username

    if req.is_active is not None:
        admin.is_active = req.is_active

    db.commit()
    db.refresh(admin)

    return {
        "id": admin.id,
        "username": admin.username,
        "is_active": admin.is_active,
        "is_superadmin": admin.is_superadmin,
        "bound_user_id": admin.bound_user_id,
        "created_at": admin.created_at.strftime("%Y-%m-%d %H:%M:%S") if admin.created_at else ""
    }


@router.delete("/admins/{admin_id}")
async def delete_admin(admin_id: int, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """删除管理员"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if admin.is_superadmin:
        raise HTTPException(status_code=400, detail="不能删除超级管理员")

    db.delete(admin)
    db.commit()

    return {"message": "管理员已删除"}


@router.post("/admins/{admin_id}/reset-password")
async def reset_password(admin_id: int, req: ResetPasswordRequest, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """重置管理员密码"""
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if admin.is_superadmin:
        raise HTTPException(status_code=400, detail="不能重置超级管理员密码")

    admin.hashed_password = get_password_hash(req.new_password)
    db.commit()

    return {"message": "密码已重置"}


@router.put("/admins/{admin_id}/bind-user")
async def bind_user_id(admin_id: int, req: BindUserIdRequest, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """给管理员绑定/解绑平台用户ID
    
    - 传入 bound_user_id：绑定（若已被其他管理员绑定则报错）
    - 传入 null 或空字符串：解绑
    """
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="管理员不存在")

    if admin.is_superadmin:
        raise HTTPException(status_code=400, detail="不能给超级管理员绑定用户身份")

    new_uid = (req.bound_user_id or "").strip() or None

    if new_uid:
        # 检查是否已被其他管理员绑定
        existing = db.query(Admin).filter(
            Admin.bound_user_id == new_uid,
            Admin.id != admin_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"该用户ID已被管理员「{existing.username}」绑定")

    admin.bound_user_id = new_uid
    db.commit()
    db.refresh(admin)

    return {
        "id": admin.id,
        "username": admin.username,
        "bound_user_id": admin.bound_user_id,
        "message": f"已绑定用户ID：{new_uid}" if new_uid else "已解绑用户ID"
    }
