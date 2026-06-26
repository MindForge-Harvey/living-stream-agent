"""
直播话术生成智能体服务
功能：
1. 生成直播脚本
2. 对直播脚本进行打分
3. 根据打分情况进行订正
4. 流式返回每一步的结果
"""

import json
import asyncio
import logging
import time
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.forbidden_word_service import forbidden_word_service
from app.services.memory_service import memory_service, MEMORY_EXTRACT_PROMPT

logger = logging.getLogger(__name__)


def get_scoring_prompt():
    """从数据库获取打分提示模板，如果没有则使用默认值"""
    db = SessionLocal()
    try:
        from app.models.models import ScoringConfig
        config = db.query(ScoringConfig).filter(ScoringConfig.is_default == True).first()
        if config and config.prompt_template:
            return config.prompt_template
    except Exception as e:
        logger.warning(f"获取打分配置失败: {e}")
    finally:
        db.close()
    
    # 返回默认值
    return SCRIPT_SCORING_PROMPT

# System Prompts
SCRIPT_GENERATION_PROMPT = """你是一位专业的直播脚本编剧。请根据用户提供的产品信息和需求，生成完整的直播脚本。

要求：
1. 包含开场白、产品介绍、互动环节、促单话术、结尾
2. 话术要口语化、有感染力
3. 包含产品卖点强调
4. 包含与观众互动的设计

直接输出脚本内容，不要多余的解释。"""

SCRIPT_SCORING_PROMPT = """你是一位专业的直播话术评审专家。请对用户提供的直播话术进行严格评分。

## 评分维度（每项1-10分）

### 1. 吸引力（Attention）
- **9-10分**：开场即抓住注意力，有强烈好奇心驱动，用户停留意愿极高
- **7-8分**：开场较吸引人，有一定好奇心，用户愿意继续观看
- **5-6分**：开场普通，缺乏亮点，用户可能继续观看但容易流失
- **3-4分**：开场平淡，缺乏吸引力，用户容易划走
- **1-2分**：开场无趣，完全无法吸引用户

### 2. 逻辑性（Logic）
- **9-10分**：产品介绍层次分明，卖点递进清晰，从痛点→方案→证据→行动完美衔接
- **7-8分**：逻辑较清晰，卖点有条理，过渡自然
- **5-6分**：逻辑基本通顺，但部分衔接生硬
- **3-4分**：逻辑混乱，卖点堆砌，缺乏条理
- **1-2分**：完全没有逻辑，东一句西一句

### 3. 感染力（Emotion）
- **9-10分**：情感充沛，能引发强烈共鸣，让用户产生"我也想要"的冲动
- **7-8分**：有一定情感表达，能打动部分用户
- **5-6分**：情感表达一般，缺乏感染力
- **3-4分**：语气平淡，像念稿，缺乏情感
- **1-2分**：完全无感情，机械式朗读

### 4. 专业性（Professional）
- **9-10分**：产品知识准确，数据详实，有权威背书，用户信任度极高
- **7-8分**：产品介绍较专业，有一定数据支撑
- **5-6分**：产品介绍基本准确，但缺乏深度
- **3-4分**：产品介绍有明显错误或夸大
- **1-2分**：产品介绍错误百出，完全不专业

## 输出格式

请严格按照以下格式输出评分结果：

### 评分总览
| 维度 | 分数 | 评语 |
|------|------|------|
| 吸引力 | X/10 | 一句话评语 |
| 逻辑性 | X/10 | 一句话评语 |
| 感染力 | X/10 | 一句话评语 |
| 专业性 | X/10 | 一句话评语 |
| **综合** | **X/10** | - |

### 优点
- 列出2-3个具体优点

### 待改进
- 列出2-3个具体改进建议

### 优化方向
- 给出1-2个最关键的优化方向

直接给出评分结果，不要多余的解释。"""

SCRIPT_REVISION_PROMPT = """你是一位专业的直播话术编辑专家。请对用户提供的直播话术进行订正优化。

要求：
1. 修正不当表达
2. 优化话术的流畅度和感染力
3. 保持原意不变
4. 适当增加互动元素

直接输出优化后的完整话术。"""

INTENT_RECOGNITION_PROMPT = """判断用户意图，返回一个或多个意图（用逗号分隔）。

可选意图：
- generate_script：生成直播脚本
- score_script：对脚本打分评价
- revise_script：订正优化脚本
- analyze_script：分析脚本结构
- save_memory：用户明确要求记住、保存某些信息（如"帮我记住xxx"、"请记住我的偏好"）
- general_chat：普通对话、提问

示例：
- "帮我写个直播脚本" → generate_script
- "帮我写个脚本并打分" → generate_script,score_script
- "帮我写个脚本并订正" → generate_script,revise_script
- "帮我记住我卖的是美妆产品" → save_memory
- "直播话术怎么写" → general_chat
- "打分" → score_script
- "评分" → score_script
- "评价" → score_script
- "评估" → score_script
- "订正" → revise_script
- "优化" → revise_script
- "修改" → revise_script
- "改进" → revise_script
- "分析" → analyze_script
- "结构分析" → analyze_script

只返回意图，不要其他内容。"""

PRODUCT_INFO_EXTRACTION_PROMPT = """请从用户的输入中提取产品相关信息，包括：
1. 产品名称
2. 产品类型/类别
3. 产品特点/卖点
4. 目标受众
5. 价格信息（如果有）
6. 促销信息（如果有）
7. 其他相关信息

请以JSON格式返回提取的信息，如果没有相关信息则返回空值。"""

MEMORY_AUTO_EXTRACT_PROMPT = """分析以下对话内容，判断是否有值得长期记忆的信息。

值得记忆的信息包括：
- 用户的产品偏好（如"我卖的是美妆产品"）
- 用户的直播风格偏好（如"我喜欢轻松幽默的风格"）
- 用户的常用话术或技巧
- 用户提到的重要产品信息
- 用户的工作习惯或流程

不值得记忆的信息：
- 普通的问答对话
- 临时性的请求
- 已经过时的信息

如果有值得记忆的信息，请简洁地总结出来（一句话）。
如果没有值得记忆的信息，请只回复"无"。

注意：只回复总结内容或"无"，不要有其他内容。"""

# 直播话术助手通用对话提示
GENERAL_CHAT_PROMPT = """你是一个专业的直播话术助手，可以帮助用户：
1. 生成直播脚本 - 提供产品信息即可自动生成完整的直播脚本
2. 对直播话术进行打分评价 - 从吸引力、逻辑性、感染力、专业性等维度评分
3. 对直播话术进行订正优化 - 修正错误、优化表达、增加互动
4. 分析直播脚本结构 - 检查脚本完整性，给出改进方向

你还具备以下能力：
- 回答关于直播技巧的问题
- 提供直播话术的写作建议
- 分析优秀直播案例
- 根据不同产品类型提供定制化建议

请用友好专业的语气回答用户的问题。如果用户提到产品信息或直播需求，可以主动询问是否需要生成直播脚本。"""

SCRIPT_ANALYSIS_PROMPT = """你是一位专业的直播脚本结构分析师。请对用户提供的直播脚本进行结构分析，包括：

1. **结构完整性检查**：
   - 是否包含开场白
   - 是否有产品介绍
   - 是否有互动环节
   - 是否有促单话术
   - 是否有结尾

2. **时间节奏分析**：
   - 各部分时长是否合理
   - 是否有节奏拖沓或过快的地方

3. **话术技巧分析**：
   - 是否有吸引力的开头
   - 卖点是否突出
   - 互动设计是否充分
   - 逼单话术是否到位

4. **改进建议**：
   - 给出具体的优化方向
   - 提供可参考的话术模板

请输出详细的分析报告。"""


class LLMService:
    """直播话术生成智能体服务"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """初始化OpenAI客户端"""
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
            )
            logger.info(f"OpenAI客户端已初始化，模型: {settings.OPENAI_MODEL}")
        else:
            logger.warning("未配置OPENAI_API_KEY，直播话术智能体功能不可用")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None

    async def _call_llm(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True
    ) -> AsyncGenerator[str, None] | str:
        """调用大模型API"""
        if not self.client:
            raise Exception("OpenAI客户端未初始化，请配置OPENAI_API_KEY")

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        if stream:
            return self._stream_llm_call(full_messages, temperature, max_tokens)
        else:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return response.choices[0].message.content

    async def _stream_llm_call(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """流式调用大模型"""
        try:
            stream = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            yield f"\n\n[错误] 大模型调用失败: {str(e)}"

    async def recognize_intent(self, user_message: str, file_content: str = None) -> list[str]:
        """识别用户意图，返回意图列表"""
        try:
            # 构建完整的消息内容，包含文件信息
            full_message = user_message
            if file_content:
                # 只取文件内容的前500字符用于意图识别，避免token浪费
                file_preview = file_content[:500]
                full_message = f"{user_message}\n\n[文件内容预览]:\n{file_preview}"
            
            response = await self._call_llm(
                INTENT_RECOGNITION_PROMPT,
                [{"role": "user", "content": full_message}],
                temperature=0.1,
                max_tokens=100,
                stream=False
            )
            intents = [i.strip().lower() for i in response.strip().split(",")]
            valid_intents = ["generate_script", "score_script", "revise_script", "analyze_script", "save_memory", "general_chat"]
            valid_result = [i for i in intents if i in valid_intents]
            return valid_result if valid_result else ["general_chat"]
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return ["general_chat"]

    async def extract_product_info(self, user_message: str) -> dict:
        """提取产品信息"""
        try:
            response = await self._call_llm(
                PRODUCT_INFO_EXTRACTION_PROMPT,
                [{"role": "user", "content": user_message}],
                temperature=0.1,
                max_tokens=1000,
                stream=False
            )
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"raw_info": response}
        except Exception as e:
            logger.error(f"产品信息提取失败: {e}")
            return {}

    def _build_context_messages(
        self,
        current_message: str,
        history: list[dict] = None,
        max_history: int = 10
    ) -> list[dict]:
        """构建带上下文的消息列表"""
        messages = []
        if history:
            recent_history = history[-max_history:]
            for msg in recent_history:
                content = msg.get("content", "")
                # 如果历史消息包含 file_content，将其拼接到内容中
                file_content = msg.get("file_content")
                if file_content:
                    content = f"{content}\n\n[文件内容]:\n{file_content}"
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })
        messages.append({"role": "user", "content": current_message})
        return messages

    async def generate_script_stream(
        self,
        user_message: str,
        file_content: str = None,
        history: list[dict] = None,
        memory_prompt: str = "",
        full_process: bool = True
    ) -> AsyncGenerator[str, None]:
        """生成直播脚本（流式）
        
        Args:
            full_process: 是否执行完整三步流程（生成→打分→订正）
        """
        enhanced_message = user_message
        if file_content:
            enhanced_message = f"用户上传的文件内容：\n{file_content}\n\n用户需求：{user_message}"

        # 提取产品信息（用于增强脚本生成质量）
        product_info = None
        try:
            product_info = await self.extract_product_info(enhanced_message)
            if product_info and not product_info.get("raw_info"):
                # 将提取的产品信息附加到消息中
                info_str = "\n".join([f"- {k}: {v}" for k, v in product_info.items() if v])
                if info_str:
                    enhanced_message = f"{enhanced_message}\n\n【提取的产品信息】\n{info_str}"
        except Exception as e:
            logger.warning(f"产品信息提取失败，继续生成: {e}")

        messages = self._build_context_messages(enhanced_message, history)

        fw_prompt = forbidden_word_service.build_forbidden_word_prompt()
        system_prompt = SCRIPT_GENERATION_PROMPT + fw_prompt + memory_prompt

        # 第一步：生成脚本
        yield "正在根据您的需求生成直播脚本，请稍候...\n\n"

        script_content = ""
        has_error = False
        try:
            async for chunk in self._stream_llm_call(
                [{"role": "system", "content": system_prompt}] + messages,
                temperature=0.8,
                max_tokens=4096
            ):
                if "[错误]" in chunk:
                    has_error = True
                script_content += chunk
                yield chunk
        except Exception as e:
            has_error = True
            yield f"\n\n[错误] 脚本生成失败: {str(e)}"

        # 如果生成失败或不需要完整流程，直接返回
        if has_error or not full_process:
            if not full_process:
                yield "\n\n---\n\n## ✅ 完成\n\n直播脚本生成完毕！"
                yield "\n\n💡 **下一步建议：**\n"
                yield "- 想对脚本进行质量评估？回复「**打分**」即可获取详细评分\n"
                yield "- 想优化脚本内容？回复「**订正**」即可获取优化版本"
            return

        yield "\n\n---\n\n"

        # 第二步：打分（注入违禁词和记忆，传入原始需求）
        yield "## ⭐ 第二步：脚本质量评估\n\n"
        yield "正在对生成的脚本进行质量评估...\n\n"

        score_system_prompt = get_scoring_prompt() + fw_prompt + memory_prompt
        score_content = ""
        try:
            async for chunk in self._stream_llm_call(
                [
                    {"role": "system", "content": score_system_prompt},
                    {"role": "user", "content": f"用户原始需求：{enhanced_message}\n\n请对以下直播脚本进行打分：\n\n{script_content}"}
                ],
                temperature=0.3,
                max_tokens=2048
            ):
                score_content += chunk
                yield chunk
        except Exception as e:
            yield f"\n\n[错误] 脚本打分失败: {str(e)}"

        yield "\n\n---\n\n"

        # 第三步：订正（传入原始需求）
        yield "## ✨ 第三步：脚本优化订正\n\n"
        yield "正在根据评估结果对脚本进行优化...\n\n"

        revision_prompt = SCRIPT_REVISION_PROMPT + fw_prompt + memory_prompt
        try:
            async for chunk in self._stream_llm_call(
                [
                    {"role": "system", "content": revision_prompt},
                    {"role": "user", "content": f"用户原始需求：{enhanced_message}\n\n请对以下直播脚本进行订正优化：\n\n原始脚本：\n{script_content}\n\n评估报告：\n{score_content}"}
                ],
                temperature=0.7,
                max_tokens=4096
            ):
                yield chunk
        except Exception as e:
            yield f"\n\n[错误] 脚本订正失败: {str(e)}"

        yield "\n\n---\n\n## ✅ 完成\n\n直播脚本生成完毕！您可以根据需要继续优化或提出修改意见。"

    async def score_script_stream(
        self,
        script_content: str,
        history: list[dict] = None,
        memory_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """对直播脚本进行打分（流式）"""
        yield "## ⭐ 脚本质量评估\n\n"
        yield "正在对您提供的直播脚本进行质量评估...\n\n"

        fw_prompt = forbidden_word_service.build_forbidden_word_prompt()
        system_prompt = get_scoring_prompt() + fw_prompt + memory_prompt

        # 使用对话历史构建上下文
        user_message = f"请对以下直播脚本进行打分：\n\n{script_content}"
        messages = self._build_context_messages(user_message, history)

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        async for chunk in self._stream_llm_call(full_messages, temperature=0.3, max_tokens=2048):
            yield chunk

        yield "\n\n---\n\n评估完成！如需订正优化，请告诉我。"

    async def revise_script_stream(
        self,
        script_content: str,
        history: list[dict] = None,
        memory_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """订正直播脚本（流式）"""
        yield "## ✨ 脚本优化订正\n\n"
        yield "正在对您提供的直播脚本进行优化订正...\n\n"

        fw_prompt = forbidden_word_service.build_forbidden_word_prompt()
        system_prompt = SCRIPT_REVISION_PROMPT + fw_prompt + memory_prompt

        # 使用对话历史构建上下文
        user_message = f"请对以下直播脚本进行订正优化：\n\n{script_content}"
        messages = self._build_context_messages(user_message, history)

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        async for chunk in self._stream_llm_call(full_messages, temperature=0.7, max_tokens=4096):
            yield chunk

        yield "\n\n---\n\n订正完成！如需进一步调整，请告诉我。"

    async def analyze_script_stream(
        self,
        script_content: str,
        history: list[dict] = None
    ) -> AsyncGenerator[str, None]:
        """分析直播脚本结构（流式）"""
        yield "## 🔍 脚本结构分析\n\n"
        yield "正在分析您的直播脚本结构...\n\n"

        # 使用对话历史构建上下文
        user_message = f"请对以下直播脚本进行结构分析：\n\n{script_content}"
        messages = self._build_context_messages(user_message, history)

        full_messages = [{"role": "system", "content": SCRIPT_ANALYSIS_PROMPT}] + messages

        async for chunk in self._stream_llm_call(full_messages, temperature=0.3, max_tokens=2048):
            yield chunk

        yield "\n\n---\n\n分析完成！如需根据分析结果优化脚本，请告诉我。"

    async def general_chat_stream(
        self,
        user_message: str,
        history: list[dict] = None,
        memory_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """普通对话（流式）"""
        messages = self._build_context_messages(user_message, history)
        system_prompt = GENERAL_CHAT_PROMPT + memory_prompt

        async for chunk in self._stream_llm_call(
            [{"role": "system", "content": system_prompt}] + messages,
            temperature=0.7,
            max_tokens=2048
        ):
            yield chunk

        # 记忆自动提取：检查对话中是否有值得记忆的信息
        try:
            memory_content = await self._auto_extract_memory(user_message, history)
            if memory_content:
                # 使用JSON格式传递记忆内容
                memory_data = json.dumps({"type": "memory_save", "content": memory_content}, ensure_ascii=False)
                yield f"\n\n__MEMORY_DATA__:{memory_data}:__END__"
        except Exception as e:
            logger.warning(f"自动记忆提取失败: {e}")

    async def _auto_extract_memory(self, user_message: str, history: list[dict] = None) -> str:
        """自动提取值得记忆的信息"""
        # 构建上下文
        context_messages = []
        if history:
            recent_history = history[-5:]  # 只看最近5条消息
            for msg in recent_history:
                context_messages.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")
        context_messages.append(f"user: {user_message}")
        context = "\n".join(context_messages)
        
        # 使用LLM判断是否有值得记忆的信息
        try:
            response = await self._call_llm(
                MEMORY_AUTO_EXTRACT_PROMPT,
                [{"role": "user", "content": context}],
                temperature=0.1,
                max_tokens=200,
                stream=False
            )
            
            response = response.strip()
            
            # 如果返回"无"或空，则不记忆
            if not response or response == "无" or "无" in response[:5]:
                return None
            
            return response
        except Exception as e:
            logger.warning(f"记忆自动提取LLM调用失败: {e}")
            return None

    async def save_memory_stream(
        self,
        user_message: str,
        history: list[dict] = None
    ) -> AsyncGenerator[str, None]:
        """提取并保存用户记忆（流式）"""
        messages = self._build_context_messages(user_message, history)

        # 用 LLM 提取记忆要点
        extracted = await self._call_llm(
            MEMORY_EXTRACT_PROMPT,
            messages,
            temperature=0.1,
            max_tokens=500,
            stream=False
        )
        extracted = extracted.strip()

        if not extracted:
            yield "没有检测到需要记忆的信息。请明确告诉我您希望我记住什么内容。"
            return

        yield "已为您记住以下内容：\n\n"
        yield extracted
        yield "\n\n---\n\n✅ 记忆已保存！下次对话时我会参考这些信息。您可以随时在「记忆」中查看和管理。"

        # 使用JSON格式传递记忆内容，更安全
        memory_data = json.dumps({"type": "memory_save", "content": extracted}, ensure_ascii=False)
        yield f"\n\n__MEMORY_DATA__:{memory_data}:__END__"

    async def process_message(
        self,
        user_message: str,
        file_content: str = None,
        history: list[dict] = None,
        force_intent: str = None,
        user_id: str = None,
        user_memories: list = None,
        full_process: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        处理用户消息的主入口
        - 自动识别意图（支持多意图）
        - 根据意图调用相应功能
        - 流式返回结果
        
        Args:
            full_process: 是否执行完整三步流程
        """
        memory_prompt = memory_service.build_memory_prompt(user_memories) if user_memories else ""

        if force_intent:
            intents = [force_intent]
        else:
            intents = await self.recognize_intent(user_message, file_content)
            logger.info(f"识别到用户意图: {intents}")

        # 处理save_memory意图（独立处理，可能与其他意图并存）
        if "save_memory" in intents:
            async for chunk in self.save_memory_stream(user_message, history):
                yield chunk
            # 如果只有save_memory意图，直接返回
            if len(intents) == 1:
                return

        # 返回检测到的意图给调用方（用于版本保存）
        yield f"__INTENT_DATA__:{json.dumps({'intents': intents})}:__END__"

        # 处理生成脚本意图
        if "generate_script" in intents:
            # 根据意图动态决定是否执行完整流程
            # 只有当用户明确要求打分或订正时，才执行完整流程
            should_full_process = "score_script" in intents or "revise_script" in intents
            async for chunk in self.generate_script_stream(
                user_message, file_content, history, memory_prompt, should_full_process
            ):
                yield chunk
            return

        # 处理打分意图
        if "score_script" in intents:
            script = file_content if file_content else user_message
            async for chunk in self.score_script_stream(script, history, memory_prompt):
                yield chunk
            return

        # 处理订正意图
        if "revise_script" in intents:
            script = file_content if file_content else user_message
            async for chunk in self.revise_script_stream(script, history, memory_prompt):
                yield chunk
            return

        # 处理分析意图
        if "analyze_script" in intents:
            script = file_content if file_content else user_message
            async for chunk in self.analyze_script_stream(script, history):
                yield chunk
            return

        # 普通对话
        async for chunk in self.general_chat_stream(user_message, history, memory_prompt):
            yield chunk


# 全局实例
llm_service = LLMService()
