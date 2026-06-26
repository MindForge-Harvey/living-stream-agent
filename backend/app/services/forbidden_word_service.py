import time
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import ForbiddenWord

logger = logging.getLogger(__name__)


class ForbiddenWordService:
    """违禁词服务（带缓存，区分单字/多字）"""

    def __init__(self):
        self._cache_all = []
        self._cache_multi = []
        self._cache_single = []
        self._cache_time = 0
        self._cache_ttl = 60

    def _load_words(self, db: Session = None):
        """加载违禁词到缓存"""
        current_time = time.time()
        if current_time - self._cache_time <= self._cache_ttl:
            return

        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            words = db.query(ForbiddenWord).all()
            self._cache_all = [(w.word, w.replacement, w.level or "multi") for w in words]
            self._cache_multi = [(w.word, w.replacement) for w in words if (w.level or "multi") == "multi"]
            self._cache_single = [w.word for w in words if (w.level or "multi") == "single"]
            self._cache_time = current_time
        finally:
            if close_db:
                db.close()

    def get_all_forbidden_words(self, db: Session = None) -> list:
        """获取所有违禁词（含 level），用于 prompt 注入"""
        self._load_words(db)
        return self._cache_all

    def get_multi_forbidden_words(self, db: Session = None) -> list:
        """获取多字违禁词，用于规则替换"""
        self._load_words(db)
        return self._cache_multi

    def get_single_forbidden_words(self, db: Session = None) -> list:
        """获取单字违禁词，用于检测告警"""
        self._load_words(db)
        return self._cache_single

    def replace_forbidden_words(self, text: str, db: Session = None) -> str:
        """替换多字违禁词，并检测单字违禁词"""
        words_multi = self.get_multi_forbidden_words(db)
        words_single = self.get_single_forbidden_words(db)
        result = text
        
        # 替换多字违禁词
        for word, replacement in words_multi:
            result = result.replace(word, replacement)
        
        # 检测并替换单字违禁词（使用替换词或默认用*替代）
        for word in words_single:
            if word in result:
                logger.warning(f"检测到单字违禁词「{word}」，已自动替换")
                # 查找该单字违禁词的替换词
                replacement = self._get_single_word_replacement(word, db)
                result = result.replace(word, replacement)
        
        return result

    def _get_single_word_replacement(self, word: str, db: Session = None) -> str:
        """获取单字违禁词的替换词"""
        self._load_words(db)
        for w, replacement, level in self._cache_all:
            if w == word and level == "single":
                return replacement if replacement and replacement != "***" else "*"
        return "*"

    def build_forbidden_word_prompt(self, db: Session = None) -> str:
        """构建违禁词提示段落，注入到 LLM system prompt"""
        words = self.get_all_forbidden_words(db)
        if not words:
            return ""

        lines = []
        for word, replacement, level in words:
            if level == "single":
                lines.append(f"- 「{word}」（单字，需用其他表述替代，不要直接使用）")
            else:
                lines.append(f"- 「{word}」→ 替换为「{replacement}」")

        return (
            "\n\n【违禁词要求】\n"
            "以下词汇在直播话术中禁止使用，请在生成/订正时严格遵守：\n"
            + "\n".join(lines)
        )

    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_time = 0


forbidden_word_service = ForbiddenWordService()
