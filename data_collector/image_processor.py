"""Модуль для обработки и генерации изображений"""
import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Tuple
import io
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Класс для обработки и генерации изображений"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Скачивает изображение по URL"""
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.warning(f"Не удалось скачать изображение {url}: статус {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка при скачивании изображения {url}: {e}")
            return None
    
    def resize_image(self, image_bytes: bytes, max_size: Tuple[int, int] = (800, 600)) -> Optional[bytes]:
        """Изменяет размер изображения"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Сохраняем пропорции
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Конвертируем в RGB если нужно
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Сохраняем в bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при изменении размера изображения: {e}")
            return None
    
    def create_info_image(self, title: str, text: str, width: int = 800, height: int = 600) -> bytes:
        """Создает информационное изображение с текстом"""
        try:
            # Создаем изображение
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Пытаемся найти шрифт
            font_large = None
            font_small = None
            
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
            
            for path in font_paths:
                try:
                    if os.path.exists(path):
                        font_large = ImageFont.truetype(path, 32)
                        font_small = ImageFont.truetype(path, 18)
                        break
                except:
                    continue
            
            if font_large is None:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            # Рисуем заголовок
            y_position = 30
            draw.text((width // 2, y_position), title, fill=(0, 0, 0), 
                     font=font_large, anchor="mm")
            
            # Рисуем текст (разбиваем на строки)
            y_position = 100
            words = text.split()
            line = ""
            line_height = 30
            
            for word in words:
                test_line = line + word + " "
                bbox = draw.textbbox((0, 0), test_line, font=font_small)
                text_width = bbox[2] - bbox[0]
                
                if text_width > width - 60:
                    if line:
                        draw.text((30, y_position), line, fill=(50, 50, 50), 
                                 font=font_small)
                        y_position += line_height
                    line = word + " "
                else:
                    line = test_line
                
                if y_position > height - 50:
                    break
            
            if line and y_position < height - 50:
                draw.text((30, y_position), line, fill=(50, 50, 50), font=font_small)
            
            # Сохраняем в bytes
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при создании изображения: {e}")
            return None
    
    async def process_images(self, image_urls: List[str], max_images: int = 5) -> List[bytes]:
        """Обрабатывает список изображений"""
        processed_images = []
        
        for url in image_urls[:max_images]:
            try:
                # Скачиваем изображение
                image_bytes = await self.download_image(url)
                if image_bytes:
                    # Изменяем размер
                    resized = self.resize_image(image_bytes)
                    if resized:
                        processed_images.append(resized)
            except Exception as e:
                logger.error(f"Ошибка при обработке изображения {url}: {e}")
                continue
        
        return processed_images
    
    def combine_images(self, images: List[bytes], layout: str = 'vertical') -> Optional[bytes]:
        """Объединяет несколько изображений в одно"""
        if not images:
            return None
        
        try:
            opened_images = [Image.open(io.BytesIO(img)) for img in images]
            
            if layout == 'vertical':
                # Вертикальная компоновка
                total_width = max(img.width for img in opened_images)
                total_height = sum(img.height for img in opened_images)
                
                combined = Image.new('RGB', (total_width, total_height), color='white')
                y_offset = 0
                
                for img in opened_images:
                    x_offset = (total_width - img.width) // 2
                    combined.paste(img, (x_offset, y_offset))
                    y_offset += img.height
            else:
                # Горизонтальная компоновка
                total_width = sum(img.width for img in opened_images)
                total_height = max(img.height for img in opened_images)
                
                combined = Image.new('RGB', (total_width, total_height), color='white')
                x_offset = 0
                
                for img in opened_images:
                    y_offset = (total_height - img.height) // 2
                    combined.paste(img, (x_offset, y_offset))
                    x_offset += img.width
            
            # Сохраняем в bytes
            output = io.BytesIO()
            combined.save(output, format='PNG')
            output.seek(0)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Ошибка при объединении изображений: {e}")
            return None
