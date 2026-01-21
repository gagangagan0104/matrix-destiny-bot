"""Генератор отчетов с интеграцией сбора данных с веб-сайтов"""
from typing import Dict, List, Optional
from matrix_calculator.models import MatrixResult, MatrixData
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
import asyncio

from data_collector import (
    WebScraper, 
    TextProcessor, 
    ImageProcessor, 
    MATRIX_SOURCES,
    MATRIX_KEYWORDS
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Генератор текстовых и визуальных отчетов с расширенной информацией"""
    
    def __init__(self, enable_web_scraping: bool = True):
        """
        Инициализация генератора отчетов
        
        Args:
            enable_web_scraping: Включить ли сбор информации с веб-сайтов
        """
        self.enable_web_scraping = enable_web_scraping
        self.text_processor = TextProcessor()
    
    async def _collect_additional_info(self, result: MatrixResult) -> Dict[str, any]:
        """Собирает дополнительную информацию с веб-сайтов"""
        if not self.enable_web_scraping:
            return {
                'summary': '',
                'detailed_info': '',
                'images': []
            }
        
        try:
            # Подготавливаем конфигурацию источников
            sources_config = [
                {
                    'url': source['url'],
                    'selectors': source.get('selectors')
                }
                for source in MATRIX_SOURCES
            ]
            
            # Собираем информацию с сайтов
            async with WebScraper() as scraper:
                scraped_data = await scraper.scrape_multiple_sites(sources_config)
            
            # Обрабатываем собранные данные
            processed_data = self.text_processor.process_matrix_data(
                scraped_data, 
                result, 
                keywords=MATRIX_KEYWORDS
            )
            
            return processed_data
        except Exception as e:
            logger.error(f"Ошибка при сборе дополнительной информации: {e}")
            return {
                'summary': '',
                'detailed_info': '',
                'images': []
            }
    
    def generate_text_report(self, data: MatrixData, result: MatrixResult, 
                           additional_info: Optional[Dict] = None) -> str:
        """Генерирует текстовый отчет"""
        # Базовый отчет
        report = f"""
╔════════════════════════════════════════╗
║     ЛИЧНАЯ МАТРИЦА СУДЬБЫ              ║
╚════════════════════════════════════════╝

👤 КЛИЕНТ: {data.name}
📅 ДАТА РОЖДЕНИЯ: {data.birth_date.strftime('%d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 ОСНОВНЫЕ ЧИСЛА:

• День рождения: {result.day}
• Месяц рождения: {result.month}
• Год рождения: {result.year} (редуцировано: {result.year_reduced})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔢 КЛЮЧЕВЫЕ ЧИСЛА:

• Личное число: {result.personal_number}
  {result.interpretations.get('personal_number', '')[:200]}...

• Число судьбы: {result.destiny_number}
  {result.interpretations.get('destiny_number', '')[:200]}...

• Число души: {result.soul_number}
  {result.interpretations.get('soul_number', '')[:200]}...

• Число личности: {result.personality_number}
  {result.interpretations.get('personality_number', '')[:200]}...

• Путь жизни: {result.life_path}
  {result.interpretations.get('life_path', '')[:200]}...

• Выражение: {result.expression}
  {result.interpretations.get('expression', '')[:200]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 МАТРИЦА СУДЬБЫ:

        {result.matrix['top_left']}  |  {result.matrix['top_center']}  |  {result.matrix['top_right']}
      ─────┼─────┼─────
        {result.matrix['middle_left']}  |  {result.matrix['center']}  |  {result.matrix['middle_right']}
      ─────┼─────┼─────
        {result.matrix['bottom_left']}  |  {result.matrix['bottom_center']}  |  {result.matrix['bottom_right']}

Центр матрицы (Число судьбы): {result.matrix['center']}
{result.interpretations.get('matrix_center', '')[:300]}...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ КАРМИЧЕСКИЕ ЧИСЛА: {', '.join(map(str, result.karmic_numbers)) if result.karmic_numbers else 'Не обнаружено'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 ПОЛНЫЕ ИНТЕРПРЕТАЦИИ:

{self._format_interpretations(result.interpretations)}
"""
        
        # Добавляем дополнительную информацию, если есть
        if additional_info:
            if additional_info.get('summary'):
                report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                report += f"📚 КРАТКОЕ РЕЗЮМЕ ИЗ ИСТОЧНИКОВ:\n\n"
                report += f"{additional_info['summary'][:500]}...\n"
            
            if additional_info.get('detailed_info'):
                report += additional_info['detailed_info']
        
        report += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"✨ Отчет сгенерирован автоматически\n"
        
        return report
    
    async def generate_enhanced_report(self, data: MatrixData, result: MatrixResult) -> Dict[str, any]:
        """Генерирует расширенный отчет с информацией с веб-сайтов"""
        # Собираем дополнительную информацию
        additional_info = await self._collect_additional_info(result)
        
        # Генерируем текстовый отчет
        text_report = self.generate_text_report(data, result, additional_info)
        
        # Генерируем визуализацию матрицы
        visual_matrix = self.generate_visual_matrix(result)
        
        # Обрабатываем изображения с сайтов
        processed_images = []
        if additional_info.get('images'):
            try:
                async with ImageProcessor() as img_processor:
                    processed_images = await img_processor.process_images(
                        additional_info['images'],
                        max_images=3
                    )
            except Exception as e:
                logger.error(f"Ошибка при обработке изображений: {e}")
        
        return {
            'text_report': text_report,
            'visual_matrix': visual_matrix,
            'additional_images': processed_images,
            'summary': additional_info.get('summary', '')
        }
    
    def _format_interpretations(self, interpretations: Dict[str, str]) -> str:
        """Форматирует интерпретации"""
        text = ""
        for key, value in interpretations.items():
            if value:
                title = key.replace('_', ' ').title()
                text += f"\n{title}:\n{value.strip()}\n"
        return text
    
    def generate_visual_matrix(self, result: MatrixResult) -> bytes:
        """Генерирует визуальное изображение матрицы"""
        # Создаем изображение
        img_size = 600
        img = Image.new('RGB', (img_size, img_size), color='white')
        draw = ImageDraw.Draw(img)
        
        # Параметры
        cell_size = img_size // 3
        border_width = 3
        
        # Цвета
        bg_color = (255, 255, 255)
        border_color = (0, 0, 0)
        center_color = (255, 215, 0)  # Золотой для центра
        
        # Рисуем сетку
        for i in range(4):
            x = i * cell_size
            y = i * cell_size
            # Вертикальные линии
            draw.rectangle([x, 0, x + border_width, img_size], fill=border_color)
            # Горизонтальные линии
            draw.rectangle([0, y, img_size, y + border_width], fill=border_color)
        
        # Заполняем ячейки
        positions = {
            'top_left': (0, 0),
            'top_center': (1, 0),
            'top_right': (2, 0),
            'middle_left': (0, 1),
            'center': (1, 1),
            'middle_right': (2, 1),
            'bottom_left': (0, 2),
            'bottom_center': (1, 2),
            'bottom_right': (2, 2),
        }
        
        # Рисуем числа в ячейках
        # Пытаемся найти подходящий шрифт
        font = None
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "C:/Windows/Fonts/arial.ttf",  # Windows
        ]
        
        for path in font_paths:
            try:
                if os.path.exists(path):
                    font = ImageFont.truetype(path, 60)
                    break
            except:
                continue
        
        if font is None:
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
        
        for key, (col, row) in positions.items():
            x = col * cell_size + cell_size // 2
            y = row * cell_size + cell_size // 2
            
            # Выделяем центр
            if key == 'center':
                margin = 10
                draw.rectangle(
                    [col * cell_size + margin, row * cell_size + margin,
                     (col + 1) * cell_size - margin, (row + 1) * cell_size - margin],
                    fill=center_color, outline=border_color, width=2
                )
            
            # Рисуем число
            number = str(result.matrix[key])
            bbox = draw.textbbox((0, 0), number, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            draw.text(
                (x - text_width // 2, y - text_height // 2),
                number,
                fill=(0, 0, 0),
                font=font
            )
        
        # Добавляем подпись
        try:
            if font != ImageFont.load_default() and font_paths:
                label_font = ImageFont.truetype(font_paths[0], 20)
            else:
                label_font = ImageFont.load_default()
        except:
            label_font = ImageFont.load_default()
        
        # Расширяем изображение для подписи
        label_height = 40
        new_img = Image.new('RGB', (img_size, img_size + label_height), color='white')
        new_img.paste(img, (0, 0))
        
        draw = ImageDraw.Draw(new_img)
        label_text = "Матрица судьбы"
        bbox = draw.textbbox((0, 0), label_text, font=label_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((img_size - text_width) // 2, img_size + 10),
            label_text,
            fill=(0, 0, 0),
            font=label_font
        )
        
        # Сохраняем в bytes
        img_bytes = io.BytesIO()
        new_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
