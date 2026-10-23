"""
推荐问题配置路由
提供 /chat/api/suggested-questions 端点
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.admin import get_current_admin
from app.core.database import get_db
from app.core.time_utils import format_shanghai_display
from app.models.models import SuggestedQuestion

router = APIRouter(prefix="/suggested-questions", tags=["推荐问题"])

MAX_SUGGESTED_QUESTIONS = 3
MAX_QUESTION_LENGTH = 100


class SuggestedQuestionUpdate(BaseModel):
    questions: list[str] = Field(default_factory=list)


def _serialize(question: SuggestedQuestion) -> dict:
    return {
        "id": question.id,
        "content": question.content,
        "sortOrder": question.sort_order,
        "isActive": question.is_active,
        "createdAt": format_shanghai_display(question.created_at),
        "updatedAt": format_shanghai_display(question.updated_at),
    }


def _serialize_public(question: SuggestedQuestion) -> dict:
    return {
        "content": question.content,
    }


def _normalize_questions(values: list[str]) -> list[str]:
    normalized = [value.strip() for value in values if value and value.strip()]
    if len(normalized) > MAX_SUGGESTED_QUESTIONS:
        raise HTTPException(status_code=400, detail="推荐问题最多配置 3 个")
    for value in normalized:
        if len(value) > MAX_QUESTION_LENGTH:
            raise HTTPException(status_code=400, detail=f"推荐问题不能超过 {MAX_QUESTION_LENGTH} 个字符")
    return normalized


@router.get("/public")
async def get_public_suggested_questions(db: Session = Depends(get_db)):
    """获取启用的推荐问题，供聊天首页展示。"""
    questions = db.query(SuggestedQuestion).filter(
        SuggestedQuestion.is_active == True
    ).order_by(
        SuggestedQuestion.sort_order.asc(),
        SuggestedQuestion.id.asc(),
    ).limit(MAX_SUGGESTED_QUESTIONS).all()
    return [_serialize_public(question) for question in questions]


@router.get("")
async def get_suggested_questions(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """管理员获取推荐问题配置。"""
    questions = db.query(SuggestedQuestion).order_by(
        SuggestedQuestion.sort_order.asc(),
        SuggestedQuestion.id.asc(),
    ).all()
    return [_serialize(question) for question in questions]


@router.put("")
async def update_suggested_questions(
    data: SuggestedQuestionUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """管理员保存推荐问题；留空表示不展示。"""
    normalized = _normalize_questions(data.questions)

    db.query(SuggestedQuestion).delete(synchronize_session=False)
    for index, content in enumerate(normalized):
        db.add(SuggestedQuestion(
            content=content,
            sort_order=index,
            is_active=True,
        ))
    db.commit()

    questions = db.query(SuggestedQuestion).order_by(
        SuggestedQuestion.sort_order.asc(),
        SuggestedQuestion.id.asc(),
    ).all()
    return [_serialize(question) for question in questions]
