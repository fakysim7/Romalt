import aiohttp
import asyncio
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebSearch:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def search_google_async(self, query: str, num_results: int = 5) -> List[str]:
        """
        Ищет ссылки в Google (через HTML-страницу).
        ⚠️ Лучше использовать API (SerpAPI, Serper и т.п.), но пока сделаем базово.
        """
        session = await self._get_session()
        url = f"https://www.google.com/search?q={query}&num={num_results}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }

        async with session.get(url, headers=headers) as resp:
            text = await resp.text()

        soup = BeautifulSoup(text, "html.parser")
        links = []

        for g in soup.select("a"):
            href = g.get("href")
            if href and href.startswith("http") and "google" not in href:
                links.append(href)
        return links[:num_results]

    async def fetch_page(self, url: str) -> str:
        """Скачивание и очистка текста страницы"""
        try:
            session = await self._get_session()
            async with session.get(url, timeout=10) as resp:
                html = await resp.text()
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            return ""

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text(" ", strip=True)
        return text[:2000]  # ограничим размер

    async def search_and_extract(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Выполняет поиск и возвращает список словарей:
        [{url: ..., content: ...}, ...]
        """
        urls = await self.search_google_async(query, num_results)
        tasks = [self.fetch_page(u) for u in urls]
        contents = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for u, c in zip(urls, contents):
            if isinstance(c, Exception):
                logger.error(f"Ошибка при обработке {u}: {c}")
                continue
            results.append({"url": u, "content": c})
        return results

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
