from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_token, get_current_user
from app.models.models import Admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/admin", tags=["管理员"])
security = HTTPBearer()


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


@router.get("/auth-by-user")
async def auth_by_user_id(
    user_id: str = Query(..., description="平台用户ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """根据绑定的 userId 免密登录管理员后台
    
    超管在后台给管理员绑定了 userId 后，平台用户点击「后台管理」时
    调用此接口，若 userId 命中则直接签发 admin token，无需再次登录。
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    if current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权使用其他用户身份登录后台")
    
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


@router.get("/me-by-user")
async def get_admin_by_user(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """检查当前普通用户是否绑定了后台管理员身份。"""
    admin = db.query(Admin).filter(Admin.bound_user_id == current_user["user_id"]).first()
    if not admin or not admin.is_active:
        return {"isAdmin": False}
    return {
        "isAdmin": True,
        "username": admin.username,
        "is_superadmin": admin.is_superadmin,
    }
