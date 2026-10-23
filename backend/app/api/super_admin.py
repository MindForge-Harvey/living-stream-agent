from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.rate_limit import (
    GENERIC_AUTH_ERROR,
    ensure_not_limited,
    get_client_ip,
    record_auth_failure,
    record_auth_success,
)
from app.core.security import verify_password, create_access_token, decode_token
from app.core.time_utils import format_shanghai_display
from app.models.models import Admin, PlatformUser
from app.api.dialogs import (
    export_user_stats_response,
    get_overview_stats_payload,
    get_stats_filter_options_payload,
    get_user_stats_payload,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/super-admin", tags=["超级管理员"])
security = HTTPBearer()
MIN_USER_SEARCH_KEYWORD_LENGTH = 2
MAX_USER_SEARCH_KEYWORD_LENGTH = 50
MAX_BOUND_USER_ID_LENGTH = 100


class SuperAdminLoginRequest(BaseModel):
    username: str
    password: str


class SuperAdminLoginResponse(BaseModel):
    success: bool
    token: str | None = None
    error: str | None = None


class CreateAdminRequest(BaseModel):
    bound_user_id: str


class UpdateAdminRequest(BaseModel):
    is_active: Optional[bool] = None


class BindUserIdRequest(BaseModel):
    bound_user_id: Optional[str] = None


class AdminResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_superadmin: bool
    created_at: str

    class Config:
        from_attributes = True


def serialize_platform_user(user: PlatformUser | None) -> dict | None:
    """序列化平台用户名片信息。"""
    if not user:
        return None

    return {
        "platform_user_id": user.platform_user_id,
        "staff_name": user.staff_name or "",
        "staff_code": user.staff_code or "",
        "staff_pos_type": user.staff_pos_type or "",
        "lan_name": user.lan_name or "",
        "region_name": user.region_name or "",
    }


def get_current_super_admin(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> Admin:
    """获取当前登录的超级管理员"""
    token = credentials.credentials
    payload = decode_token(token)
    admin_id_str = payload.get("sub", "")

    if not admin_id_str.startswith("super_admin:"):
        raise HTTPException(status_code=401, detail="无效的超级管理员token")

    try:
        admin_id = int(admin_id_str.split(":", 1)[1])
    except (IndexError, ValueError):
        raise HTTPException(status_code=401, detail="无效的超级管理员token")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    if not admin.is_active:
        raise HTTPException(status_code=401, detail="管理员账号已被禁用")
    if not admin.is_superadmin:
        raise HTTPException(status_code=403, detail="权限不足，需要超级管理员权限")
    return admin


@router.post("/login", response_model=SuperAdminLoginResponse)
async def super_admin_login(req: SuperAdminLoginRequest, request: Request, db: Session = Depends(get_db)):
    """超级管理员登录"""
    ip = get_client_ip(request)
    identifier = req.username.strip()
    ensure_not_limited("super_admin_login", identifier, ip)

    admin = db.query(Admin).filter(Admin.username == req.username).first()

    if not admin or not verify_password(req.password, admin.hashed_password):
        record_auth_failure("super_admin_login", identifier, ip, "invalid_credentials")
        return SuperAdminLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    if not admin.is_active:
        record_auth_failure("super_admin_login", identifier, ip, "inactive")
        return SuperAdminLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    if not admin.is_superadmin:
        record_auth_failure("super_admin_login", identifier, ip, "not_super_admin")
        return SuperAdminLoginResponse(success=False, error=GENERIC_AUTH_ERROR)

    record_auth_success("super_admin_login", identifier, ip)
    token = create_access_token(data={"sub": f"super_admin:{admin.id}"})
    return SuperAdminLoginResponse(success=True, token=token)


@router.get("/admins")
async def list_admins(current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """获取所有管理员列表"""
    admins = db.query(Admin).all()
    bound_user_ids = [admin.bound_user_id for admin in admins if admin.bound_user_id]
    users = []
    if bound_user_ids:
        users = db.query(PlatformUser).filter(PlatformUser.platform_user_id.in_(bound_user_ids)).all()
    user_map = {user.platform_user_id: user for user in users}

    result = []
    for admin in admins:
        result.append({
            "id": admin.id,
            "username": admin.username,
            "is_active": admin.is_active,
            "is_superadmin": admin.is_superadmin,
            "bound_user_id": admin.bound_user_id,
            "bound_user": serialize_platform_user(user_map.get(admin.bound_user_id)) if admin.bound_user_id else None,
            "created_at": format_shanghai_display(admin.created_at),
        })
    return result


@router.get("/platform-users/search")
async def search_platform_users(
    q: str = "",
    current_admin: Admin = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """按用户ID、工号、姓名搜索平台用户。"""
    keyword = q.strip()
    if not keyword:
        return []
    if len(keyword) < MIN_USER_SEARCH_KEYWORD_LENGTH:
        raise HTTPException(status_code=400, detail="搜索关键字至少需要2个字符")
    if len(keyword) > MAX_USER_SEARCH_KEYWORD_LENGTH:
        raise HTTPException(status_code=400, detail="搜索关键字过长")

    users = (
        db.query(PlatformUser)
        .filter(
            or_(
                PlatformUser.platform_user_id.contains(keyword, autoescape=True),
                PlatformUser.staff_code.contains(keyword, autoescape=True),
                PlatformUser.staff_name.contains(keyword, autoescape=True),
            )
        )
        .order_by(PlatformUser.updated_at.desc(), PlatformUser.id.desc())
        .limit(20)
        .all()
    )

    return [serialize_platform_user(user) for user in users]


@router.get("/conversations/stats/overview")
async def get_super_admin_overview_stats(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """超级管理员获取用户使用总览统计。"""
    return get_overview_stats_payload(db)


@router.get("/conversations/stats/users")
async def get_super_admin_user_stats(
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/工号/用户ID）"),
    lanName: Optional[str] = Query(None, description="地市筛选"),
    regionName: Optional[str] = Query(None, description="区县筛选"),
    staffPosType: Optional[str] = Query(None, description="岗位筛选"),
    sortBy: Optional[str] = Query(None, description="排序字段"),
    sortOrder: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """超级管理员获取用户使用统计。"""
    return get_user_stats_payload(db, keyword, lanName, regionName, staffPosType, sortBy, sortOrder, page, pageSize)


@router.get("/conversations/stats/users/export")
async def export_super_admin_user_stats(
    keyword: Optional[str] = Query(None),
    lanName: Optional[str] = Query(None),
    regionName: Optional[str] = Query(None),
    staffPosType: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: Optional[str] = Query("desc"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """超级管理员导出用户使用统计 CSV。"""
    return export_user_stats_response(db, keyword, lanName, regionName, staffPosType, sortBy, sortOrder)


@router.get("/conversations/stats/filters")
async def get_super_admin_stats_filter_options(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_super_admin),
):
    """超级管理员获取统计筛选下拉选项。"""
    return get_stats_filter_options_payload(db)


@router.post("/admins")
async def create_admin(req: CreateAdminRequest, current_admin: Admin = Depends(get_current_super_admin), db: Session = Depends(get_db)):
    """创建绑定 userId 的普通管理员。"""
    bound_user_id = req.bound_user_id.strip()
    if not bound_user_id:
        raise HTTPException(status_code=400, detail="绑定用户ID不能为空")
    if len(bound_user_id) > MAX_BOUND_USER_ID_LENGTH:
        raise HTTPException(status_code=400, detail="绑定用户ID过长")

    platform_user = db.query(PlatformUser).filter(PlatformUser.platform_user_id == bound_user_id).first()
    if not platform_user:
        raise HTTPException(status_code=400, detail="只能选择已有平台用户创建管理员")

    existing_bound = db.query(Admin).filter(Admin.bound_user_id == bound_user_id).first()
    if existing_bound:
        raise HTTPException(status_code=400, detail=f"该用户ID已被管理员「{existing_bound.username}」绑定")

    username = f"admin_{bound_user_id}"
    existing = db.query(Admin).filter(Admin.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户ID对应的管理员已存在")

    new_admin = Admin(
        username=username,
        hashed_password="",
        is_active=True,
        is_superadmin=False,
        bound_user_id=bound_user_id
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
        "bound_user": serialize_platform_user(platform_user),
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
        "bound_user": serialize_platform_user(
            db.query(PlatformUser).filter(PlatformUser.platform_user_id == admin.bound_user_id).first()
        ) if admin.bound_user_id else None,
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
        if len(new_uid) > MAX_BOUND_USER_ID_LENGTH:
            raise HTTPException(status_code=400, detail="绑定用户ID过长")

        platform_user = db.query(PlatformUser).filter(PlatformUser.platform_user_id == new_uid).first()
        if not platform_user:
            raise HTTPException(status_code=400, detail="只能绑定已有平台用户")

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
        "bound_user": serialize_platform_user(
            db.query(PlatformUser).filter(PlatformUser.platform_user_id == admin.bound_user_id).first()
        ) if admin.bound_user_id else None,
        "message": f"已绑定用户ID：{new_uid}" if new_uid else "已解绑用户ID"
    }
