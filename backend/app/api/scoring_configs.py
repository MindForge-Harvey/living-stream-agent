"""
打分配置路由
提供 /chat/api/scoring-configs 端点
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.models.models import ScoringConfig
from app.api.admin import get_current_admin

router = APIRouter(prefix="/scoring-configs", tags=["打分配置"])


class ScoringConfigCreate(BaseModel):
    name: str
    dimensions: List[dict]
    prompt_template: str
    is_default: bool = False


class ScoringConfigUpdate(BaseModel):
    name: Optional[str] = None
    dimensions: Optional[List[dict]] = None
    prompt_template: Optional[str] = None
    is_default: Optional[bool] = None


@router.get("")
async def get_scoring_configs(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """获取所有打分配置"""
    configs = db.query(ScoringConfig).order_by(ScoringConfig.created_at.desc()).all()
    return [{
        "id": c.id,
        "name": c.name,
        "dimensions": c.dimensions,
        "prompt_template": c.prompt_template,
        "is_default": c.is_default,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
        "updated_at": c.updated_at.strftime("%Y-%m-%d %H:%M:%S") if c.updated_at else ""
    } for c in configs]


@router.get("/default")
async def get_default_scoring_config(db: Session = Depends(get_db)):
    """获取默认打分配置（无需认证）"""
    config = db.query(ScoringConfig).filter(ScoringConfig.is_default == True).first()
    if not config:
        return None
    return {
        "id": config.id,
        "name": config.name,
        "dimensions": config.dimensions,
        "prompt_template": config.prompt_template,
        "is_default": config.is_default
    }


@router.post("")
async def create_scoring_config(
    data: ScoringConfigCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """创建打分配置"""
    # 如果设置为默认，先取消其他默认配置
    if data.is_default:
        db.query(ScoringConfig).filter(ScoringConfig.is_default == True).update({"is_default": False})
    
    config = ScoringConfig(
        name=data.name,
        dimensions=data.dimensions,
        prompt_template=data.prompt_template,
        is_default=data.is_default
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "name": config.name,
        "dimensions": config.dimensions,
        "prompt_template": config.prompt_template,
        "is_default": config.is_default
    }


@router.put("/{config_id}")
async def update_scoring_config(
    config_id: int,
    data: ScoringConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """更新打分配置"""
    config = db.query(ScoringConfig).filter(ScoringConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 如果设置为默认，先取消其他默认配置
    if data.is_default and not config.is_default:
        db.query(ScoringConfig).filter(ScoringConfig.is_default == True).update({"is_default": False})
    
    if data.name is not None:
        config.name = data.name
    if data.dimensions is not None:
        config.dimensions = data.dimensions
    if data.prompt_template is not None:
        config.prompt_template = data.prompt_template
    if data.is_default is not None:
        config.is_default = data.is_default
    
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "name": config.name,
        "dimensions": config.dimensions,
        "prompt_template": config.prompt_template,
        "is_default": config.is_default
    }


@router.delete("/{config_id}")
async def delete_scoring_config(
    config_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin)
):
    """删除打分配置"""
    config = db.query(ScoringConfig).filter(ScoringConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    if config.is_default:
        raise HTTPException(status_code=400, detail="不能删除默认配置")
    
    db.delete(config)
    db.commit()
    
    return {"message": "配置已删除"}
