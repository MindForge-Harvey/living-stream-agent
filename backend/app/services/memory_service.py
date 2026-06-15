import logging
from sqlalchemy.orm import Session

from app.models.models import UserMemory

logger = logging.getLogger(__name__)

MEMORY_EXTRACT_PROMPT = """请从用户的输入中提取需要长期记忆的信息要点，直接输出精炼后的记忆内容。

要求：
1. 只提取有价值的信息（如偏好、习惯、身份信息、重要约定等）
2. 用简洁的陈述句表达
3. 如果用户输入不包含值得记忆的内容，返回空字符串
4. 如果包含多条信息，每条一行，用 "- " 开头

直接输出记忆内容，不要解释。"""


def build_memory_prompt(memories: list[UserMemory]) -> str:
    """构建用户记忆提示段落，注入到 LLM system prompt"""
    if not memories:
        return ""

    lines = []
    for m in memories:
        lines.append(f"- {m.content}")

    return (
        "\n\n【用户长期记忆】\n"
        "以下是该用户之前要求你记住的信息，在对话中请参考这些记忆：\n"
        + "\n".join(lines)
    )


memory_service = type("MemoryService", (), {
    "build_memory_prompt": staticmethod(build_memory_prompt),
    "MEMORY_EXTRACT_PROMPT": MEMORY_EXTRACT_PROMPT,
})()
