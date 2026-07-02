"""
直播话术生成智能体路由
提供 /chat/api/agent 端点
"""

import json
import logging
import tempfile
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from markitdown import MarkItDown

from app.core.database import get_db, SessionLocal
from app.services.llm_service import llm_service
from app.services.forbidden_word_service import forbidden_word_service
from app.services.memory_service import memory_service
from app.models.models import DialogMessage, UserMemory, ScriptVersion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["直播话术智能体"])

markitdown_converter = MarkItDown()


async def parse_upload_file(file: UploadFile) -> tuple[str, str]:
    """解析上传的文件内容（使用 MarkItDown），返回 (file_content, filename)"""
    if not file:
        return None, None

    # 获取文件名，确保不为 None
    filename = file.filename or "unknown"
    
    try:
        content = await file.read()
        filename_lower = filename.lower()

        if filename_lower.endswith('.txt'):
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    text = content.decode('gbk')
                except UnicodeDecodeError:
                    text = content.decode('latin-1')
            return _truncate_content(text), filename

        suffix = os.path.splitext(filename_lower)[1]
        if not suffix:
            suffix = ".tmp"
            
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Excel 文件特殊处理：使用 pandas 读取并处理合并单元格
            if filename_lower.endswith(('.xlsx', '.xls')):
                result = _parse_excel_with_merged_cells(tmp_path)
            else:
                result = markitdown_converter.convert(tmp_path)
                result = result.text_content
            
            return _truncate_content(result), filename
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # 临时文件删除失败不影响主流程

    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        return f"[文件解析失败: {str(e)}]", filename


# 文件内容最大字符数（约100k）
MAX_CONTENT_LENGTH = 100000


def _truncate_content(text: str) -> str:
    """截断文件内容，超过最大长度时保留头尾并提示"""
    if not text or len(text) <= MAX_CONTENT_LENGTH:
        return text
    
    # 保留前面大部分内容 + 尾部提示
    truncated = text[:MAX_CONTENT_LENGTH]
    truncated += f"\n\n[文件内容过长，已截断。原始长度：{len(text)} 字符，已保留前 {MAX_CONTENT_LENGTH} 字符]"
    return truncated


def _parse_excel_with_merged_cells(file_path: str) -> str:
    """解析 Excel 文件，处理合并单元格（只对第一列进行 forward fill）"""
    import pandas as pd
    
    try:
        # 读取所有工作表
        dfs = pd.read_excel(file_path, sheet_name=None, header=0)
        
        all_sheets = []
        for sheet_name, df in dfs.items():
            # 只对第一列进行 forward fill（处理合并单元格）
            df_filled = df.copy()
            first_col = df_filled.columns[0]
            df_filled[first_col] = df_filled[first_col].ffill()
            
            # 转换为 Markdown 表格
            lines = [f"## {sheet_name}", ""]
            
            # 表头
            headers = df_filled.columns.tolist()
            lines.append("| " + " | ".join(str(h) for h in headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            # 数据行
            for _, row in df_filled.iterrows():
                row_data = []
                for val in row:
                    if pd.isna(val):
                        row_data.append("")
                    else:
                        # 清理换行符，避免破坏表格格式
                        cell = str(val).replace('\n', ' ').replace('\r', '')
                        row_data.append(cell)
                lines.append("| " + " | ".join(row_data) + " |")
            
            all_sheets.append("\n".join(lines))
        
        return "\n\n".join(all_sheets)
        
    except Exception as e:
        logger.error(f"Excel 解析失败: {e}")
        # 降级到 markitdown
        result = markitdown_converter.convert(file_path)
        return result.text_content


def _build_history_with_metadata(msgs: list) -> list:
    """构建包含文件元数据的历史消息"""
    history = []
    for msg in msgs:
        entry = {
            "role": msg.role,
            "content": msg.content
        }
        # 如果有文件元数据，添加到历史中
        if msg.metadata_json:
            try:
                metadata = json.loads(msg.metadata_json)
                if metadata.get("file_content"):
                    entry["file_content"] = metadata["file_content"]
                    entry["file_name"] = metadata.get("file_name", "")
            except json.JSONDecodeError:
                pass
        history.append(entry)
    return history


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
        file_name = None
        if file and hasattr(file, 'filename') and file.filename:
            file_content, file_name = await parse_upload_file(file)
            logger.info(f"已解析文件: {file.filename}")

        history = []
        if dialog_id:
            msgs = db.query(DialogMessage).filter(
                DialogMessage.dialog_id == dialog_id
            ).order_by(DialogMessage.created_at).all()

            history = _build_history_with_metadata(msgs[-20:])

        # 加载用户记忆
        user_memories = []
        if user_id:
            user_memories = db.query(UserMemory).filter(
                UserMemory.user_id == user_id
            ).order_by(UserMemory.created_at.desc()).all()

        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 构建文件元数据
        file_metadata = None
        if file_content:
            file_metadata = json.dumps({
                "file_content": file_content,
                "file_name": file_name
            }, ensure_ascii=False)

        async def generate_stream():
            gen_db = SessionLocal()
            try:
                memory_to_save = None
                detected_intent = None
                accumulated_content = ""
                save_interval = 500  # 每500个字符保存一次中间结果
                last_saved_length = 0
                
                async for chunk in llm_service.process_message(
                    user_message=message,
                    file_content=file_content,
                    history=history,
                    force_intent=intent,
                    user_id=user_id,
                    user_memories=user_memories
                ):
                     # 解析记忆保存标记（使用JSON格式）
                    if "__MEMORY_DATA__:" in chunk and ":__END__" in chunk:
                        try:
                            start = chunk.index("__MEMORY_DATA__:") + len("__MEMORY_DATA__:")
                            end = chunk.index(":__END__")
                            memory_json = chunk[start:end]
                            memory_data = json.loads(memory_json)
                            if memory_data.get("type") == "memory_save":
                                memory_to_save = memory_data.get("content")
                                # 移除标记，不输出给用户
                                chunk = chunk[:chunk.index("__MEMORY_DATA__:")] + chunk[chunk.index(":__END__") + len(":__END__"):]
                                if not chunk.strip():
                                    continue
                        except (json.JSONDecodeError, ValueError):
                            pass  # 解析失败则正常输出
                    
                    # 解析意图标记
                    if "__INTENT_DATA__:" in chunk and ":__END__" in chunk:
                        try:
                            start = chunk.index("__INTENT_DATA__:") + len("__INTENT_DATA__:")
                            end = chunk.index(":__END__")
                            intent_json = chunk[start:end]
                            intent_data = json.loads(intent_json)
                            intents = intent_data.get("intents", [])
                            if intents:
                                detected_intent = intents[0]  # 取第一个意图
                                logger.info(f"检测到意图: {detected_intent}")
                            # 移除标记，不输出给用户
                            chunk = chunk[:chunk.index("__INTENT_DATA__:")] + chunk[chunk.index(":__END__") + len(":__END__"):]
                            if not chunk.strip():
                                continue
                        except (json.JSONDecodeError, ValueError):
                            pass  # 解析失败则正常输出
                    
                    # 流式输出原始内容（不进行违禁词替换）
                    accumulated_content += chunk
                    
                    # 定期保存中间结果（对话历史完整性）
                    if len(accumulated_content) - last_saved_length >= save_interval:
                        _save_intermediate_result(gen_db, dialog_id, request_id, "assistant", accumulated_content, file_metadata)
                        last_saved_length = len(accumulated_content)
                    
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

                # 结束后一次性替换违禁词
                if accumulated_content:
                    filtered_content = forbidden_word_service.replace_forbidden_words(accumulated_content, gen_db)
                    # 如果内容有变化，发送替换后的内容
                    if filtered_content != accumulated_content:
                        yield f"data: {json.dumps({'content': '[内容已过滤]', 'replace_all': True, 'final_content': filtered_content}, ensure_ascii=False)}\n\n"
                    
                    # 保存最终结果（使用过滤后的内容）
                    _save_message(gen_db, dialog_id, request_id, "assistant", filtered_content, file_metadata)
                    
                    # 保存脚本版本（使用检测到的意图）
                    _save_script_version(gen_db, dialog_id, request_id, filtered_content, detected_intent)

                if memory_to_save and user_id:
                    try:
                        memory = UserMemory(user_id=user_id, content=memory_to_save)
                        gen_db.add(memory)
                        gen_db.commit()
                        logger.info(f"已保存用户记忆: user_id={user_id}, content={memory_to_save[:50]}...")
                    except Exception as e:
                        gen_db.rollback()
                        logger.error(f"保存记忆失败: {e}")
            finally:
                gen_db.close()

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


def _save_message(db: Session, dialog_id: str, request_id: str, role: str, content: str, metadata: str = None):
    """保存消息到数据库（如果已存在则更新）"""
    if not dialog_id:
        return
    
    try:
        # 检查是否已有该 request_id 的消息（由 _save_intermediate_result 创建）
        existing = db.query(DialogMessage).filter(
            DialogMessage.dialog_id == dialog_id,
            DialogMessage.request_id == request_id,
            DialogMessage.role == role
        ).first()
        
        if existing:
            existing.content = content
            if metadata:
                existing.metadata_json = metadata
        else:
            msg = DialogMessage(
                dialog_id=dialog_id,
                request_id=request_id,
                role=role,
                content=content,
                metadata_json=metadata
            )
            db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"保存消息失败: {e}")


def _save_intermediate_result(db: Session, dialog_id: str, request_id: str, role: str, content: str, metadata: str = None):
    """保存中间结果（更新或插入）"""
    if not dialog_id:
        return
    
    try:
        # 查找是否已有该request_id的消息
        existing = db.query(DialogMessage).filter(
            DialogMessage.dialog_id == dialog_id,
            DialogMessage.request_id == request_id,
            DialogMessage.role == role
        ).first()
        
        if existing:
            existing.content = content
            if metadata:
                existing.metadata_json = metadata
        else:
            msg = DialogMessage(
                dialog_id=dialog_id,
                request_id=request_id,
                role=role,
                content=content,
                metadata_json=metadata
            )
            db.add(msg)
        
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"保存中间结果失败: {e}")


def _save_script_version(db: Session, dialog_id: str, request_id: str, content: str, intent: str = None):
    """保存脚本版本（只保存直播脚本相关的内容）"""
    if not dialog_id:
        return
    
    # 只保存直播脚本相关的版本，过滤掉普通对话
    script_intents = ["generate_script", "score_script", "revise_script", "analyze_script"]
    if intent and intent not in script_intents:
        return  # 非脚本相关意图，不保存版本
    
    try:
        # 根据意图判断版本类型
        version_type = "generated"
        if intent:
            if intent == "score_script":
                version_type = "scored"
            elif intent == "revise_script":
                version_type = "revised"
            elif intent == "analyze_script":
                version_type = "analyzed"
        
        version = ScriptVersion(
            dialog_id=dialog_id,
            request_id=request_id,
            version_type=version_type,
            content=content
        )
        db.add(version)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"保存脚本版本失败: {e}")


@router.get("/versions/{dialog_id}")
async def get_script_versions(dialog_id: str, db: Session = Depends(get_db)):
    """获取对话的脚本版本历史"""
    versions = db.query(ScriptVersion).filter(
        ScriptVersion.dialog_id == dialog_id
    ).order_by(ScriptVersion.created_at).all()
    
    return [{
        "id": v.id,
        "dialog_id": v.dialog_id,
        "request_id": v.request_id,
        "version_type": v.version_type,
        "content": v.content,
        "score_data": v.score_data,
        "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else ""
    } for v in versions]


@router.post("/generate")
async def generate_script(request: Request, db: Session = Depends(get_db)):
    """直接生成直播脚本（快捷接口）"""
    form = await request.form()
    message = form.get("message", "")
    dialog_id = form.get("dialogId")
    user_id = form.get("userId")
    file = form.get("file")

    file_content = None
    file_name = None
    if file and hasattr(file, 'filename') and file.filename:
        file_content, file_name = await parse_upload_file(file)

    if not message and not file_content:
        raise HTTPException(status_code=400, detail="请提供产品信息或上传相关文件")

    # 加载对话历史
    history = []
    if dialog_id:
        msgs = db.query(DialogMessage).filter(
            DialogMessage.dialog_id == dialog_id
        ).order_by(DialogMessage.created_at).all()
        history = _build_history_with_metadata(msgs[-20:])

    # 加载用户记忆
    user_memories = []
    if user_id:
        user_memories = db.query(UserMemory).filter(
            UserMemory.user_id == user_id
        ).order_by(UserMemory.created_at.desc()).all()

    # 生成请求ID
    request_id = str(uuid.uuid4())[:8]
    
    # 构建文件元数据
    file_metadata = None
    if file_content:
        file_metadata = json.dumps({
            "file_content": file_content,
            "file_name": file_name
        }, ensure_ascii=False)

    async def generate_stream():
        gen_db = SessionLocal()
        try:
            accumulated_content = ""
            
            async for chunk in llm_service.generate_script_stream(
                user_message=message,
                file_content=file_content,
                history=history,
                memory_prompt=memory_service.build_memory_prompt(user_memories) if user_memories else ""
            ):
                accumulated_content += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 结束后一次性替换违禁词
            if accumulated_content:
                filtered_content = forbidden_word_service.replace_forbidden_words(accumulated_content, gen_db)
                # 如果内容有变化，发送替换后的内容
                if filtered_content != accumulated_content:
                    yield f"data: {json.dumps({'content': '[内容已过滤]', 'replace_all': True, 'final_content': filtered_content}, ensure_ascii=False)}\n\n"
                
                # 保存消息
                _save_message(gen_db, dialog_id, request_id, "assistant", filtered_content, file_metadata)
                # 保存脚本版本
                _save_script_version(gen_db, dialog_id, request_id, filtered_content, "generate_script")
        finally:
            gen_db.close()

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
    dialog_id = form.get("dialogId")
    user_id = form.get("userId")

    if not script:
        raise HTTPException(status_code=400, detail="请提供要评分的直播脚本")

    # 加载对话历史
    history = []
    if dialog_id:
        msgs = db.query(DialogMessage).filter(
            DialogMessage.dialog_id == dialog_id
        ).order_by(DialogMessage.created_at).all()
        history = _build_history_with_metadata(msgs[-20:])

    # 加载用户记忆
    user_memories = []
    if user_id:
        user_memories = db.query(UserMemory).filter(
            UserMemory.user_id == user_id
        ).order_by(UserMemory.created_at.desc()).all()

    # 生成请求ID
    request_id = str(uuid.uuid4())[:8]

    async def score_stream():
        gen_db = SessionLocal()
        try:
            accumulated_content = ""
            
            async for chunk in llm_service.score_script_stream(
                script_content=script,
                history=history,
                memory_prompt=memory_service.build_memory_prompt(user_memories) if user_memories else ""
            ):
                accumulated_content += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 结束后一次性替换违禁词
            if accumulated_content:
                filtered_content = forbidden_word_service.replace_forbidden_words(accumulated_content, gen_db)
                if filtered_content != accumulated_content:
                    yield f"data: {json.dumps({'content': '[内容已过滤]', 'replace_all': True, 'final_content': filtered_content}, ensure_ascii=False)}\n\n"
                
                # 保存消息
                _save_message(gen_db, dialog_id, request_id, "assistant", filtered_content)
                # 保存脚本版本
                _save_script_version(gen_db, dialog_id, request_id, filtered_content, "score_script")
        finally:
            gen_db.close()

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
    dialog_id = form.get("dialogId")
    user_id = form.get("userId")

    if not script:
        raise HTTPException(status_code=400, detail="请提供要订正的直播脚本")

    # 加载对话历史
    history = []
    if dialog_id:
        msgs = db.query(DialogMessage).filter(
            DialogMessage.dialog_id == dialog_id
        ).order_by(DialogMessage.created_at).all()
        history = _build_history_with_metadata(msgs[-20:])

    # 加载用户记忆
    user_memories = []
    if user_id:
        user_memories = db.query(UserMemory).filter(
            UserMemory.user_id == user_id
        ).order_by(UserMemory.created_at.desc()).all()

    # 生成请求ID
    request_id = str(uuid.uuid4())[:8]

    async def revise_stream():
        gen_db = SessionLocal()
        try:
            accumulated_content = ""
            
            async for chunk in llm_service.revise_script_stream(
                script_content=script,
                history=history,
                memory_prompt=memory_service.build_memory_prompt(user_memories) if user_memories else ""
            ):
                accumulated_content += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 结束后一次性替换违禁词
            if accumulated_content:
                filtered_content = forbidden_word_service.replace_forbidden_words(accumulated_content, gen_db)
                if filtered_content != accumulated_content:
                    yield f"data: {json.dumps({'content': '[内容已过滤]', 'replace_all': True, 'final_content': filtered_content}, ensure_ascii=False)}\n\n"
                
                # 保存消息
                _save_message(gen_db, dialog_id, request_id, "assistant", filtered_content)
                # 保存脚本版本
                _save_script_version(gen_db, dialog_id, request_id, filtered_content, "revise_script")
        finally:
            gen_db.close()

    return StreamingResponse(
        revise_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )
