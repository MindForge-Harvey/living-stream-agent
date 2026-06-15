import time
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.models import ForbiddenWord

logger = logging.getLogger(__name__)


class ForbiddenWordService:
    """违禁词服务（带缓存）"""

    def __init__(self):
        self._cache = []
        self._cache_time = 0
        self._cache_ttl = 60  # 缓存60秒

    def get_forbidden_words(self, db: Session = None) -> list:
        """获取违禁词列表（带缓存）"""
        current_time = time.time()
        if current_time - self._cache_time > self._cache_ttl:
            if db is None:
                db = SessionLocal()
                try:
                    words = db.query(ForbiddenWord).all()
                    self._cache = [(w.word, w.replacement) for w in words]
                    self._cache_time = current_time
                finally:
                    db.close()
            else:
                words = db.query(ForbiddenWord).all()
                self._cache = [(w.word, w.replacement) for w in words]
                self._cache_time = current_time
        return self._cache

    def replace_forbidden_words(self, text: str, db: Session = None) -> str:
        """替换文本中的违禁词"""
        words = self.get_forbidden_words(db)
        result = text
        for word, replacement in words:
            result = result.replace(word, replacement)
        return result

    def invalidate_cache(self):
        """使缓存失效"""
        self._cache_time = 0


forbidden_word_service = ForbiddenWordService()
