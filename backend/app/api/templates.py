"""
脚本模板路由
提供 /chat/api/templates 端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.time_utils import format_shanghai_display
from app.models.models import ScriptTemplate
from app.api.admin import get_current_admin

router = APIRouter(prefix="/templates", tags=["脚本模板"])


class TemplateCreate(BaseModel):
    name: str
    category: str = "custom"
    product_type: Optional[str] = None
    template_content: str
    description: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    product_type: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# 预置模板
PRESET_TEMPLATES = [
    {
        "name": "移动宽带套餐直播脚本",
        "category": "preset",
        "product_type": "通信",
        "description": "适用于移动宽带套餐推广的直播脚本模板",
        "template_content": """## 开场白（30秒）
"家人们，宽带选得好，上网没烦恼！今天给大家带来移动宽带超值套餐，网速快、价格低、服务好！"

## 产品介绍（2分钟）
1. **套餐内容**
   - 带宽：[100M/200M/500M/1000M]
   - 流量：[是否含手机流量]
   - 通话：[是否含通话时长]

2. **核心卖点**
   - 网速稳定：光纤入户，玩游戏不卡顿
   - 价格实惠：月费低至[X]元，比营业厅更优惠
   - 安装便捷：预约后[X]天内上门安装

3. **适用场景**
   - 家庭上网：看视频、刷抖音不缓冲
   - 居家办公：视频会议流畅稳定
   - 游戏娱乐：低延迟，团战不掉线

## 互动环节（1分钟）
"家里宽带到期的扣1，想换宽带的扣2！"
"觉得网速重要还是价格重要的？网速扣A，价格扣B"

## 促单话术（1分钟）
"今天直播间下单，首年月费只要[X]元，还送[路由器/话费]！"
"名额有限，只有[X]个名额，抢完恢复原价！"
"现在下单，明天就能安排上门安装！"

## 结尾（30秒）
"宽带选移动，生活更轻松！赶紧下单，享受飞一般的网速体验！记得关注我们，更多优惠等着你！"
"""
    }
]


@router.get("")
async def get_templates(
    category: Optional[str] = None,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """获取模板列表"""
    query = db.query(ScriptTemplate).filter(ScriptTemplate.is_active == True)

    if category:
        query = query.filter(ScriptTemplate.category == category)
    if product_type:
        query = query.filter(ScriptTemplate.product_type == product_type)

    templates = query.order_by(ScriptTemplate.created_at.desc()).all()

    return [{
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "product_type": t.product_type,
        "template_content": t.template_content,
        "description": t.description,
        "created_at": format_shanghai_display(t.created_at),
    } for t in templates]


def _format_public_template(t: ScriptTemplate, user_id: Optional[str] = None) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "product_type": t.product_type,
        "template_content": t.template_content,
        "description": t.description,
        "user_id": t.user_id,
        "is_mine": bool(t.user_id) and t.user_id == user_id if user_id else False
    }


@router.get("/public")
async def get_public_templates(
    category: Optional[str] = None,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取公开模板列表（无需认证，只返回全局模板）。"""
    query = db.query(ScriptTemplate).filter(
        ScriptTemplate.is_active == True,
        ScriptTemplate.user_id.is_(None),
    )

    if category:
        query = query.filter(ScriptTemplate.category == category)
    if product_type:
        query = query.filter(ScriptTemplate.product_type == product_type)

    templates = query.order_by(ScriptTemplate.created_at.desc()).all()
    
    return [_format_public_template(t) for t in templates]


@router.get("/mine")
async def get_my_templates(
    category: Optional[str] = None,
    product_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取全局模板和当前用户私有模板。"""
    user_id = current_user["user_id"]
    query = db.query(ScriptTemplate).filter(
        ScriptTemplate.is_active == True,
        or_(ScriptTemplate.user_id.is_(None), ScriptTemplate.user_id == user_id),
    )
    
    if category:
        query = query.filter(ScriptTemplate.category == category)
    if product_type:
        query = query.filter(ScriptTemplate.product_type == product_type)
    
    templates = query.order_by(ScriptTemplate.created_at.desc()).all()
    return [_format_public_template(t, user_id) for t in templates]


@router.post("")
async def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """创建新模板"""
    template = ScriptTemplate(
        name=data.name,
        category=data.category,
        product_type=data.product_type,
        template_content=data.template_content,
        description=data.description
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "product_type": template.product_type,
        "template_content": template.template_content,
        "description": template.description
    }


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """更新模板"""
    template = db.query(ScriptTemplate).filter(ScriptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    if data.name is not None:
        template.name = data.name
    if data.category is not None:
        template.category = data.category
    if data.product_type is not None:
        template.product_type = data.product_type
    if data.template_content is not None:
        template.template_content = data.template_content
    if data.description is not None:
        template.description = data.description
    if data.is_active is not None:
        template.is_active = data.is_active
    
    db.commit()
    db.refresh(template)
    
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "product_type": template.product_type,
        "template_content": template.template_content,
        "description": template.description,
        "is_active": template.is_active
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """删除模板"""
    template = db.query(ScriptTemplate).filter(ScriptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    db.delete(template)
    db.commit()
    
    return {"message": "模板已删除"}


@router.post("/init-presets")
async def init_preset_templates(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """初始化预置模板"""
    created_count = 0
    
    for preset in PRESET_TEMPLATES:
        existing = db.query(ScriptTemplate).filter(
            ScriptTemplate.name == preset["name"],
            ScriptTemplate.category == "preset"
        ).first()
        
        if not existing:
            template = ScriptTemplate(
                name=preset["name"],
                category=preset["category"],
                product_type=preset["product_type"],
                template_content=preset["template_content"],
                description=preset["description"]
            )
            db.add(template)
            created_count += 1
    
    db.commit()
    
    return {"message": f"已初始化 {created_count} 个预置模板", "created": created_count}


# ===== 用户级模板接口（普通用户认证，通过 token 校验归属） =====

class UserTemplateCreate(BaseModel):
    name: str
    product_type: Optional[str] = None
    template_content: str
    description: Optional[str] = None


class UserTemplateUpdate(BaseModel):
    name: Optional[str] = None
    product_type: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None


@router.post("/my")
async def create_user_template(
    data: UserTemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """用户创建自己的私有模板"""
    user_id = current_user["user_id"]
    template = ScriptTemplate(
        name=data.name,
        category="custom",
        product_type=data.product_type,
        template_content=data.template_content,
        description=data.description,
        user_id=user_id
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "product_type": template.product_type,
        "template_content": template.template_content,
        "description": template.description,
        "user_id": template.user_id,
        "is_mine": True
    }


@router.put("/my/{template_id}")
async def update_user_template(
    template_id: int,
    data: UserTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """用户更新自己的私有模板"""
    template = db.query(ScriptTemplate).filter(ScriptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权修改此模板")
    
    if data.name is not None:
        template.name = data.name
    if data.product_type is not None:
        template.product_type = data.product_type
    if data.template_content is not None:
        template.template_content = data.template_content
    if data.description is not None:
        template.description = data.description
    
    db.commit()
    db.refresh(template)
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "product_type": template.product_type,
        "template_content": template.template_content,
        "description": template.description,
        "user_id": template.user_id,
        "is_mine": True
    }


@router.delete("/my/{template_id}")
async def delete_user_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """用户删除自己的私有模板"""
    template = db.query(ScriptTemplate).filter(ScriptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权删除此模板")
    
    db.delete(template)
    db.commit()
    return {"message": "模板已删除"}
