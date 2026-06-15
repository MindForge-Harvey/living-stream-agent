import uuid
import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.time_utils import format_shanghai_iso, format_shanghai_display, shanghai_now
from app.models.models import Dialog, DialogMessage, PlatformUser
from app.api.admin import get_current_admin

router = APIRouter(prefix="/dialogs", tags=["对话"])


def utc_now():
    return datetime.now(timezone.utc)


def generate_dialog_id():
    """生成唯一 dialogId"""
    return uuid.uuid4().hex


def generate_request_id():
    """生成唯一 requestId"""
    return uuid.uuid4().hex


class CreateDialogRequest(BaseModel):
    userId: str
    toolId: str = "living-stream-agent"
    toolName: str = "直播话术生成智能体"
    title: str = "新对话"
    lanName: str = ""
    regionName: str = ""
    staffCode: str = ""
    staffName: str = ""
    staffPosType: str = ""


class SendMessageRequest(BaseModel):
    dialogId: str
    userId: str
    role: str
    content: str


# ==================== 对话基础接口 ====================

@router.post("")
async def create_dialog(req: CreateDialogRequest, db: Session = Depends(get_db)):
    """创建新对话"""
    if req.userId:
        platform_user = db.query(PlatformUser).filter(PlatformUser.platform_user_id == req.userId).first()
        if not platform_user:
            platform_user = PlatformUser(
                platform_user_id=req.userId,
                lan_name=req.lanName,
                region_name=req.regionName,
                staff_code=req.staffCode,
                staff_name=req.staffName,
                staff_pos_type=req.staffPosType,
            )
            db.add(platform_user)
        else:
            if req.lanName:
                platform_user.lan_name = req.lanName
            if req.regionName:
                platform_user.region_name = req.regionName
            if req.staffCode:
                platform_user.staff_code = req.staffCode
            if req.staffName:
                platform_user.staff_name = req.staffName
            if req.staffPosType:
                platform_user.staff_pos_type = req.staffPosType
            platform_user.updated_at = utc_now()

    dialog_id = generate_dialog_id()
    dialog = Dialog(
        id=dialog_id,
        user_id=req.userId,
        tool_id=req.toolId,
        tool_name=req.toolName,
        title=req.title,
    )
    db.add(dialog)
    db.commit()
    db.refresh(dialog)
    return {
        "id": dialog.id,
        "userId": dialog.user_id,
        "toolId": dialog.tool_id,
        "toolName": dialog.tool_name,
        "title": dialog.title,
        "createdAt": format_shanghai_iso(dialog.created_at),
        "updatedAt": format_shanghai_iso(dialog.updated_at),
    }


@router.get("")
async def list_dialogs(userId: str = None, page: int = 1, pageSize: int = 50, db: Session = Depends(get_db)):
    """获取对话列表（支持分页）"""
    query = db.query(Dialog)
    if userId:
        query = query.filter(Dialog.user_id == userId)

    total = query.count()
    dialogs = query.order_by(Dialog.updated_at.desc()).offset((page - 1) * pageSize).limit(pageSize).all()

    return {
        "items": [
            {
                "id": d.id,
                "userId": d.user_id,
                "toolId": d.tool_id,
                "toolName": d.tool_name,
                "title": d.title,
                "requestCount": d.request_count,
                "createdAt": format_shanghai_iso(d.created_at),
                "updatedAt": format_shanghai_iso(d.updated_at),
            }
            for d in dialogs
        ],
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "totalPages": (total + pageSize - 1) // pageSize
    }


@router.post("/message")
async def save_message(req: SendMessageRequest, db: Session = Depends(get_db)):
    """保存消息"""
    dialog = db.query(Dialog).filter(Dialog.id == req.dialogId).first()
    if not dialog:
        raise HTTPException(status_code=404, detail="对话不存在")

    if req.userId and dialog.user_id != req.userId:
        raise HTTPException(status_code=403, detail="无权操作此对话")

    request_id = generate_request_id()
    message = DialogMessage(
        dialog_id=req.dialogId,
        request_id=request_id,
        role=req.role,
        content=req.content,
    )
    db.add(message)

    dialog.request_count += 1
    dialog.updated_at = datetime.now(timezone.utc)

    if req.role == "user" and dialog.title == "新对话":
        dialog.title = req.content[:20] + ("..." if len(req.content) > 20 else "")

    db.commit()
    return {
        "id": message.id,
        "requestId": request_id,
        "dialogId": message.dialog_id,
        "role": message.role,
        "content": message.content,
        "createdAt": format_shanghai_iso(message.created_at),
    }


# ==================== 统计接口 ====================

def _build_user_stats_query(db, keyword, lan_name, region_name, staff_pos_type):
    """构建用户统计查询（共用逻辑）"""
    stats_subq = db.query(
        Dialog.user_id,
        func.count(Dialog.id).label("dialog_count"),
        func.sum(Dialog.request_count).label("total_requests"),
        func.min(Dialog.created_at).label("first_used"),
        func.max(Dialog.updated_at).label("last_used"),
    ).group_by(Dialog.user_id).subquery()

    query = db.query(
        stats_subq.c.user_id,
        stats_subq.c.dialog_count,
        stats_subq.c.total_requests,
        stats_subq.c.first_used,
        stats_subq.c.last_used,
        PlatformUser.staff_name,
        PlatformUser.staff_code,
        PlatformUser.staff_pos_type,
        PlatformUser.lan_name,
        PlatformUser.region_name,
    ).outerjoin(
        PlatformUser, PlatformUser.platform_user_id == stats_subq.c.user_id
    )

    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                PlatformUser.staff_name.like(like_pattern),
                PlatformUser.staff_code.like(like_pattern),
                stats_subq.c.user_id.like(like_pattern),
            )
        )
    if lan_name:
        query = query.filter(PlatformUser.lan_name == lan_name)
    if region_name:
        query = query.filter(PlatformUser.region_name == region_name)
    if staff_pos_type:
        query = query.filter(PlatformUser.staff_pos_type == staff_pos_type)

    return query, stats_subq


def _format_user_stat(row):
    return {
        "userId": row.user_id,
        "dialogCount": row.dialog_count,
        "totalRequests": row.total_requests or 0,
        "firstUsed": format_shanghai_iso(row.first_used),
        "lastUsed": format_shanghai_iso(row.last_used),
        "staffName": row.staff_name or "",
        "staffCode": row.staff_code or "",
        "staffPosType": row.staff_pos_type or "",
        "lanName": row.lan_name or "",
        "regionName": row.region_name or "",
    }


@router.get("/stats/users")
async def get_user_stats(
    keyword: Optional[str] = Query(None, description="搜索关键词（姓名/工号/用户ID）"),
    lanName: Optional[str] = Query(None, description="地市筛选"),
    regionName: Optional[str] = Query(None, description="区县筛选"),
    staffPosType: Optional[str] = Query(None, description="岗位筛选"),
    sortBy: Optional[str] = Query(None, description="排序字段"),
    sortOrder: Optional[str] = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=200, description="每页条数"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """获取用户使用统计（支持筛选、排序、分页）"""
    query, stats_subq = _build_user_stats_query(db, keyword, lanName, regionName, staffPosType)

    sort_map = {
        "dialogCount": stats_subq.c.dialog_count,
        "totalRequests": stats_subq.c.total_requests,
        "firstUsed": stats_subq.c.first_used,
        "lastUsed": stats_subq.c.last_used,
        "staffName": PlatformUser.staff_name,
        "lanName": PlatformUser.lan_name,
        "regionName": PlatformUser.region_name,
    }
    sort_col = sort_map.get(sortBy, stats_subq.c.dialog_count)
    order = sort_col.desc() if sortOrder == "desc" else sort_col.asc()
    query = query.order_by(order)

    total = query.count()
    rows = query.offset((page - 1) * pageSize).limit(pageSize).all()

    return {
        "items": [_format_user_stat(row) for row in rows],
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "totalPages": (total + pageSize - 1) // pageSize,
    }


@router.get("/stats/users/export")
async def export_user_stats(
    keyword: Optional[str] = Query(None),
    lanName: Optional[str] = Query(None),
    regionName: Optional[str] = Query(None),
    staffPosType: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: Optional[str] = Query("desc"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """导出用户使用统计为 CSV"""
    query, stats_subq = _build_user_stats_query(db, keyword, lanName, regionName, staffPosType)

    sort_map = {
        "dialogCount": stats_subq.c.dialog_count,
        "totalRequests": stats_subq.c.total_requests,
        "firstUsed": stats_subq.c.first_used,
        "lastUsed": stats_subq.c.last_used,
        "staffName": PlatformUser.staff_name,
        "lanName": PlatformUser.lan_name,
        "regionName": PlatformUser.region_name,
    }
    sort_col = sort_map.get(sortBy, stats_subq.c.dialog_count)
    order = sort_col.desc() if sortOrder == "desc" else sort_col.asc()
    rows = query.order_by(order).all()

    def generate():
        buffer = io.StringIO()
        buffer.write('\ufeff')
        writer = csv.writer(buffer)
        writer.writerow(["用户ID", "姓名", "工号", "岗位", "地市", "区县", "对话数", "消息数", "首次使用", "最近使用"])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for row in rows:
            writer.writerow([
                row.user_id,
                row.staff_name or "",
                row.staff_code or "",
                row.staff_pos_type or "",
                row.lan_name or "",
                row.region_name or "",
                row.dialog_count,
                row.total_requests or 0,
                format_shanghai_display(row.first_used) if row.first_used else "",
                format_shanghai_display(row.last_used) if row.last_used else "",
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = f"用户使用统计_{shanghai_now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/stats/filters")
async def get_stats_filter_options(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """获取筛选下拉选项"""
    lan_names = [r[0] for r in db.query(PlatformUser.lan_name).distinct().filter(PlatformUser.lan_name != "").all()]
    region_names = [r[0] for r in db.query(PlatformUser.region_name).distinct().filter(PlatformUser.region_name != "").all()]
    staff_pos_types = [r[0] for r in db.query(PlatformUser.staff_pos_type).distinct().filter(PlatformUser.staff_pos_type != "").all()]
    return {
        "lanNames": sorted(lan_names),
        "regionNames": sorted(region_names),
        "staffPosTypes": sorted(staff_pos_types),
    }


@router.get("/stats/overview")
async def get_overview_stats(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """获取总览统计"""
    total_dialogs = db.query(func.count(Dialog.id)).scalar() or 0
    total_messages = db.query(func.sum(Dialog.request_count)).scalar() or 0
    total_users = db.query(func.count(func.distinct(Dialog.user_id))).scalar() or 0

    return {
        "totalDialogs": total_dialogs,
        "totalMessages": total_messages,
        "totalUsers": total_users,
    }


# ==================== 对话详情接口 ====================

@router.get("/{dialog_id}")
async def get_dialog(dialog_id: str, db: Session = Depends(get_db)):
    """获取对话详情"""
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if not dialog:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {
        "id": dialog.id,
        "userId": dialog.user_id,
        "toolId": dialog.tool_id,
        "toolName": dialog.tool_name,
        "title": dialog.title,
        "requestCount": dialog.request_count,
        "createdAt": format_shanghai_iso(dialog.created_at),
        "updatedAt": format_shanghai_iso(dialog.updated_at),
    }


@router.delete("/{dialog_id}")
async def delete_dialog(dialog_id: str, userId: str = Query(..., description="用户ID，必传"), db: Session = Depends(get_db)):
    """删除对话"""
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if not dialog:
        raise HTTPException(status_code=404, detail="对话不存在")

    if dialog.user_id != userId:
        raise HTTPException(status_code=403, detail="无权删除此对话")

    db.query(DialogMessage).filter(DialogMessage.dialog_id == dialog_id).delete()
    db.delete(dialog)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{dialog_id}/messages")
async def get_dialog_messages(dialog_id: str, db: Session = Depends(get_db)):
    """获取对话消息"""
    dialog = db.query(Dialog).filter(Dialog.id == dialog_id).first()
    if not dialog:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.query(DialogMessage).filter(
        DialogMessage.dialog_id == dialog_id
    ).order_by(DialogMessage.created_at).all()

    return [
        {
            "id": m.id,
            "requestId": m.request_id,
            "role": m.role,
            "content": m.content,
            "createdAt": format_shanghai_iso(m.created_at),
        }
        for m in messages
    ]
