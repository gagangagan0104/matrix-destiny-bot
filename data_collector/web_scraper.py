"""Модуль для сбора информации с веб-сайтов"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)


class WebScraper:
    """Класс для сбора информации с веб-сайтов"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Получает HTML страницы"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Ошибка получения страницы {url}: статус {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении страницы {url}: {e}")
            return None
    
    def extract_text_from_html(self, html: str, selectors: List[str] = None) -> str:
        """Извлекает текст из HTML используя селекторы"""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Если указаны селекторы, используем их
        if selectors:
            text_parts = []
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        
        # Иначе извлекаем весь основной текст
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            return main_content.get_text(separator='\n', strip=True)
        
        return soup.get_text(separator='\n', strip=True)
    
    def extract_images(self, html: str, base_url: str) -> List[str]:
        """Извлекает URL изображений из HTML"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                # Преобразуем относительные URL в абсолютные
                full_url = urljoin(base_url, src)
                images.append(full_url)
        
        return images
    
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов и форматирует"""
        if not text:
            return ""
        
        # Удаляем множественные пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Удаляем лишние символы
        text = text.strip()
        
        return text
    
    async def scrape_site(self, url: str, selectors: List[str] = None) -> Dict[str, any]:
        """Собирает информацию с сайта"""
        logger.info(f"Начинаю сбор информации с {url}")
        
        html = await self.fetch_page(url)
        if not html:
            return {
                'url': url,
                'text': '',
                'images': [],
                'success': False
            }
        
        text = self.extract_text_from_html(html, selectors)
        text = self.clean_text(text)
        images = self.extract_images(html, url)
        
        return {
            'url': url,
            'text': text,
            'images': images,
            'success': True
        }
    
    async def scrape_multiple_sites(self, urls: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Собирает информацию с нескольких сайтов параллельно"""
        tasks = []
        for site_config in urls:
            url = site_config.get('url')
            selectors = site_config.get('selectors')
            task = self.scrape_site(url, selectors)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при сборе с сайта {urls[i].get('url')}: {result}")
                processed_results.append({
                    'url': urls[i].get('url'),
                    'text': '',
                    'images': [],
                    'success': False
                })
            else:
                processed_results.append(result)
        
        return processed_results


# Импортируем конфигурацию
from .config import MATRIX_SOURCES
