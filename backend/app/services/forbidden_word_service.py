import time
import logging
from collections import deque
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
        self._automaton = None
        self._automaton_words_key = ()

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
            self._cache_multi = [
                (w.word, w.replacement or "***")
                for w in words
                if (w.level or "multi") == "multi" and w.word
            ]
            self._cache_single = [w.word for w in words if (w.level or "multi") == "single"]
            self._cache_time = current_time
            self._automaton = None
            self._automaton_words_key = ()
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
        """替换多字违禁词，单字只记录告警不做直接替换"""
        return self.process_text(text, db)["processed"]

    def process_text(self, text: str, db: Session = None) -> dict:
        """检测并替换文本中的违禁词。

        规则：
        - 单字违禁词只检测不替换；
        - 多字违禁词使用 Aho-Corasick 单次扫描；
        - 扫描完成后按词长降序选择替换，已替换区间不再覆盖。
        """
        if not text:
            return {
                "original": text,
                "processed": text,
                "foundForbiddenWords": [],
                "hasForbiddenWords": False,
            }

        words = self.get_all_forbidden_words(db)
        all_matches = self._find_matches(text, words)
        multi_matches = [match for match in all_matches if match["level"] == "multi"]
        replacements = self._select_non_overlapping_matches(multi_matches)
        processed = self._apply_replacements(text, replacements)

        found_words = []
        seen = set()
        for match in all_matches:
            if match["level"] == "single":
                logger.warning(f"检测到单字违禁词「{match['word']}」，按规则不做直接替换")
            key = (match["word"], match["start"], match["end"], match["level"])
            if key in seen:
                continue
            seen.add(key)
            found_words.append(match)

        found_words.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))

        return {
            "original": text,
            "processed": processed,
            "foundForbiddenWords": found_words,
            "hasForbiddenWords": bool(found_words),
        }

    def _find_matches(self, text: str, words: list[tuple[str, str, str]]) -> list[dict]:
        """使用 Aho-Corasick 自动机单次扫描所有违禁词。"""
        if not words:
            return []

        root = self._get_automaton(words)
        node = root
        matches = []

        for index, char in enumerate(text):
            while node is not root and char not in node["next"]:
                node = node["fail"]
            node = node["next"].get(char, root)

            for word, replacement, level in node["outputs"]:
                start = index - len(word) + 1
                matches.append({
                    "word": word,
                    "replacement": replacement if level == "multi" else None,
                    "level": level,
                    "start": start,
                    "end": index + 1,
                    "replaced": False,
                })

        return matches

    def _get_automaton(self, words: list[tuple[str, str, str]]) -> dict:
        """构建或复用违禁词自动机。"""
        words_key = tuple(sorted((word, replacement or "***", level or "multi") for word, replacement, level in words if word))
        if self._automaton is not None and words_key == self._automaton_words_key:
            return self._automaton

        root = {"next": {}, "fail": None, "outputs": []}
        root["fail"] = root

        for word, replacement, level in words:
            if not word:
                continue
            normalized_level = level or "multi"
            normalized_replacement = replacement or "***"
            node = root
            for char in word:
                node = node["next"].setdefault(char, {"next": {}, "fail": root, "outputs": []})
            node["outputs"].append((word, normalized_replacement, normalized_level))

        queue = deque()
        for child in root["next"].values():
            child["fail"] = root
            queue.append(child)

        while queue:
            current = queue.popleft()
            for char, child in current["next"].items():
                fail_node = current["fail"]
                while fail_node is not root and char not in fail_node["next"]:
                    fail_node = fail_node["fail"]
                child["fail"] = fail_node["next"].get(char, root)
                child["outputs"].extend(child["fail"]["outputs"])
                queue.append(child)

        self._automaton = root
        self._automaton_words_key = words_key
        return root

    def _select_non_overlapping_matches(self, matches: list[dict]) -> list[dict]:
        """按词长降序选择替换区间，已替换区间不再覆盖。"""
        selected = []
        occupied_ranges = []

        sorted_matches = sorted(
            matches,
            key=lambda item: (-(item["end"] - item["start"]), item["start"])
        )

        for match in sorted_matches:
            start = match["start"]
            end = match["end"]
            if any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied_ranges):
                continue
            match["replaced"] = True
            selected.append(match)
            occupied_ranges.append((start, end))

        selected.sort(key=lambda item: item["start"])
        return selected

    def _apply_replacements(self, text: str, replacements: list[dict]) -> str:
        """根据已选区间一次性重建文本。"""
        if not replacements:
            return text

        parts = []
        cursor = 0
        for item in replacements:
            parts.append(text[cursor:item["start"]])
            parts.append(item["replacement"])
            cursor = item["end"]
        parts.append(text[cursor:])
        return "".join(parts)

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
        self._automaton = None
        self._automaton_words_key = ()


forbidden_word_service = ForbiddenWordService()
