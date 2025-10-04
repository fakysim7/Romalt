import asyncio
from typing import List, Dict
from services.web_search import WebSearch
import logging
import re
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self, always_enabled: bool = True):
        self.web_search = WebSearch()
        self.context_window = 4000
        self.always_enabled = always_enabled
        self.cache = {}  # кэш

    def _cache_key(self, query: str):
        return hashlib.md5(query.encode('utf-8')).hexdigest()

    async def get_relevant_context(self, query: str) -> str:
        """Всегда актуальный контекст"""
        try:
            current_year = datetime.now().year
            search_query = self._build_search_query(query) + f" {current_year}"
            results = await self.web_search.search_and_extract(search_query, num_results=5)
            context = self._format_context(results, query)
            return context
        except Exception as e:
            logger.error(f"RAG error: {e}")
            return f"Не удалось получить актуальные данные для запроса: {query}"

    def _build_search_query(self, original_query: str) -> str:
        stop_words = {'как', 'что', 'где', 'когда', 'почему', 'зачем', 'мне', 'ты', 'вы', 'свой'}
        words = original_query.lower().split()
        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        if filtered:
            return ' '.join(filtered) + ' актуальная информация'
        return original_query + ' информация'

    def _format_context(self, results: List[Dict], original_query: str) -> str:
        if not results:
            return f"По запросу '{original_query}' не найдено информации."
        parts = [f"🔍 Информация по '{original_query}':", "="*50]
        valid = 0
        for i, r in enumerate(results, 1):
            if r['content'] and len(r['content']) > 50:
                domain = self._extract_domain(r['url'])
                parts.append(f"Источник {i} | {domain}:\n{self._clean_content(r['content'])}")
                parts.append("-"*40)
                valid += 1
        if valid == 0:
            return f"По запросу '{original_query}' найдено мало релевантной информации."
        parts.append(f"Всего источников: {valid}")
        full = "\n".join(parts)
        return full[:self.context_window] + ("\n[...информация обрезана...]" if len(full) > self.context_window else "")

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace('www.', '')

    def _clean_content(self, content: str) -> str:
        # убираем лишние пробелы и переносы
        content = re.sub(r'\s+', ' ', content)
        # убираем markdown-заголовки ###, ##, #
        content = re.sub(r'#{1,6}\s*', '', content)
        # убираем жирный/курсивный (**текст**, *текст*, _текст_, __текст__)
        content = re.sub(r'(\*\*|__)(.*?)\1', r'\2', content)  # жирный
        content = re.sub(r'(\*|_)(.*?)\1', r'\2', content)     # курсив
        # убираем ссылки [текст](url)
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', content)
        # убираем явные http/https ссылки
        content = re.sub(r'https?://\S+', '', content)
        # убираем начальные маркеры списков (-, *, •, >)
        content = re.sub(r'^[\s>*•-]+', '', content, flags=re.MULTILINE)
        # убираем повторяющиеся дефисы/равенства (---, ===)
        content = re.sub(r'[-=]{3,}', ' ', content)
        # убираем лишние markdown-символы (остатки `~`, `>`, '`')
        content = re.sub(r'[~`>]', '', content)
        # финальная нормализация пробелов
        content = re.sub(r'\s{2,}', ' ', content)
        cleaned = content.strip()
        return cleaned[:800] + '...' if len(cleaned) > 800 else cleaned

    async def close(self):
        await self.web_search.close()

