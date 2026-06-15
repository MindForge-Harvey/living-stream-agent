"""
直播话术生成智能体路由
提供 /chat/api/agent 端点
"""

import json
import logging
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from markitdown import MarkItDown

from app.core.database import get_db
from app.services.llm_service import llm_service
from app.services.forbidden_word_service import forbidden_word_service
from app.services.memory_service import memory_service
from app.models.models import DialogMessage, UserMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["直播话术智能体"])

markitdown_converter = MarkItDown()


async def parse_upload_file(file: UploadFile) -> str:
    """解析上传的文件内容（使用 MarkItDown）"""
    if not file:
        return None

    try:
        content = await file.read()
        filename = file.filename.lower()

        if filename.endswith('.txt'):
            return content.decode('utf-8')

        suffix = os.path.splitext(filename)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = markitdown_converter.convert(tmp_path)
            return result.text_content
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        return f"[文件解析失败: {str(e)}]"


@router.get("/status")
async def get_status():
    """获取智能体状态"""
    return {
        "available": llm_service.is_available(),
        "agent_id": "living-stream-agent",
        "name": "直播话术生成智能体",
        "capabilities": [
            "generate_script",   # 生成直播脚本
            "score_script",      # 脚本打分评价
            "revise_script",     # 脚本订正优化
            "analyze_script",    # 脚本结构分析
            "save_memory",       # 保存用户记忆
            "general_chat"       # 普通对话
        ],
        "features": [
            "上下文对话关联",
            "文件上传解析",
            "违禁词过滤",
            "用户长期记忆",
            "流式输出"
        ]
    }


@router.post("")
async def agent_endpoint(request: Request, db: Session = Depends(get_db)):
    """
    直播话术生成智能体主端点

    请求格式：multipart/form-data
    - message: 用户消息（必填）
    - dialogId: 对话ID（可选，用于关联对话历史）
    - userId: 用户ID（可选）
    - intent: 意图（可选，强制指定意图）
    - file: 上传的文件（可选）
    """
    if not llm_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="直播话术智能体服务不可用，请配置OPENAI_API_KEY"
        )

    try:
        form = await request.form()
        message = form.get("message", "")
        dialog_id = form.get("dialogId")
        user_id = form.get("userId")
        intent = form.get("intent")
        file = form.get("file")

        if not message and not file:
            raise HTTPException(status_code=400, detail="消息内容不能为空")

        file_content = None
        if file and hasattr(file, 'filename') and file.filename:
            file_content = await parse_upload_file(file)
            logger.info(f"已解析文件: {file.filename}")

        history = []
        if dialog_id:
            msgs = db.query(DialogMessage).filter(
                DialogMessage.dialog_id == dialog_id
            ).order_by(DialogMessage.created_at).all()

            for msg in msgs[-20:]:
                history.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # 加载用户记忆
        user_memories = []
        if user_id:
            user_memories = db.query(UserMemory).filter(
                UserMemory.user_id == user_id
            ).order_by(UserMemory.created_at.desc()).all()

        async def generate_stream():
            memory_to_save = None
            async for chunk in llm_service.process_message(
                user_message=message,
                file_content=file_content,
                history=history,
                force_intent=intent,
                user_id=user_id,
                user_memories=user_memories
            ):
                # 检测记忆保存信号
                if chunk.startswith("\n\n__MEMORY_SAVE__:"):
                    memory_to_save = chunk.split(":", 1)[1].strip()
                    continue
                # 违禁词过滤
                filtered_chunk = forbidden_word_service.replace_forbidden_words(chunk, db)
                yield f"data: {json.dumps({'content': filtered_chunk}, ensure_ascii=False)}\n\n"

            # 异步保存记忆到数据库
            if memory_to_save and user_id:
                try:
                    memory = UserMemory(user_id=user_id, content=memory_to_save)
                    db.add(memory)
                    db.commit()
                    logger.info(f"已保存用户记忆: user_id={user_id}, content={memory_to_save[:50]}...")
                except Exception as e:
                    logger.error(f"保存记忆失败: {e}")

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/generate")
async def generate_script(request: Request, db: Session = Depends(get_db)):
    """直接生成直播脚本（快捷接口）"""
    form = await request.form()
    message = form.get("message", "")
    file = form.get("file")

    file_content = None
    if file and hasattr(file, 'filename') and file.filename:
        file_content = await parse_upload_file(file)

    if not message and not file_content:
        raise HTTPException(status_code=400, detail="请提供产品信息或上传相关文件")

    async def generate_stream():
        async for chunk in llm_service.generate_script_stream(
            user_message=message,
            file_content=file_content
        ):
            filtered_chunk = forbidden_word_service.replace_forbidden_words(chunk, db)
            yield f"data: {json.dumps({'content': filtered_chunk}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/score")
async def score_script(request: Request, db: Session = Depends(get_db)):
    """对直播脚本进行打分"""
    form = await request.form()
    script = form.get("script", "")

    if not script:
        raise HTTPException(status_code=400, detail="请提供要评分的直播脚本")

    async def score_stream():
        async for chunk in llm_service.score_script_stream(script):
            filtered_chunk = forbidden_word_service.replace_forbidden_words(chunk, db)
            yield f"data: {json.dumps({'content': filtered_chunk}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        score_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/revise")
async def revise_script(request: Request, db: Session = Depends(get_db)):
    """订正直播脚本"""
    form = await request.form()
    script = form.get("script", "")

    if not script:
        raise HTTPException(status_code=400, detail="请提供要订正的直播脚本")

    async def revise_stream():
        async for chunk in llm_service.revise_script_stream(script):
            filtered_chunk = forbidden_word_service.replace_forbidden_words(chunk, db)
            yield f"data: {json.dumps({'content': filtered_chunk}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        revise_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )
