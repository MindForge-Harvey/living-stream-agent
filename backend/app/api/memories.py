from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import UserMemory
from app.schemas.schemas import MemoryCreate, MemoryUpdate, MemoryResponse

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=List[MemoryResponse])
async def get_user_memories(user_id: str = Query(..., description="用户ID，必传"), db: Session = Depends(get_db)):
    """获取用户的所有记忆"""
    memories = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id)
        .order_by(UserMemory.created_at.desc())
        .all()
    )
    return memories


@router.post("", response_model=MemoryResponse)
async def create_memory(data: MemoryCreate, db: Session = Depends(get_db)):
    """创建记忆"""
    if not data.user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    memory = UserMemory(user_id=data.user_id, content=data.content)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: int, data: MemoryUpdate, user_id: str = Query(..., description="用户ID，必传"), db: Session = Depends(get_db)
):
    """更新记忆"""
    memory = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    if memory.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权修改此记忆")
    memory.content = data.content
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}")
async def delete_memory(memory_id: int, user_id: str = Query(..., description="用户ID，必传"), db: Session = Depends(get_db)):
    """删除记忆"""
    memory = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")
    if memory.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权删除此记忆")
    db.delete(memory)
    db.commit()
    return {"success": True}
