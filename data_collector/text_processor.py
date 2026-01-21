"""Модуль для обработки и объединения текста из разных источников"""
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TextProcessor:
    """Класс для обработки и объединения текста"""
    
    def __init__(self):
        pass
    
    def remove_duplicates(self, texts: List[str]) -> List[str]:
        """Удаляет дублирующиеся фрагменты текста"""
        unique_texts = []
        seen_sentences = set()
        
        for text in texts:
            if not text:
                continue
            
            # Разбиваем на предложения
            sentences = re.split(r'[.!?]\s+', text)
            unique_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Создаем ключ для проверки дубликатов (первые 50 символов)
                key = sentence[:50].lower()
                if key not in seen_sentences:
                    seen_sentences.add(key)
                    unique_sentences.append(sentence)
            
            if unique_sentences:
                unique_texts.append('. '.join(unique_sentences) + '.')
        
        return unique_texts
    
    def extract_key_information(self, text: str, keywords: List[str]) -> str:
        """Извлекает ключевую информацию по ключевым словам"""
        if not text:
            return ""
        
        sentences = re.split(r'[.!?]\s+', text)
        relevant_sentences = []
        
        text_lower = text.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower:
                # Находим предложения с ключевым словом
                for sentence in sentences:
                    if keyword_lower in sentence.lower():
                        relevant_sentences.append(sentence.strip())
        
        return '. '.join(relevant_sentences) + '.' if relevant_sentences else ""
    
    def merge_texts(self, texts: List[str], max_length: int = 5000) -> str:
        """Объединяет тексты в один, удаляя дубликаты"""
        # Удаляем дубликаты
        unique_texts = self.remove_duplicates(texts)
        
        # Объединяем
        merged = "\n\n".join(unique_texts)
        
        # Ограничиваем длину
        if len(merged) > max_length:
            merged = merged[:max_length] + "..."
        
        return merged
    
    def format_for_report(self, text: str, title: str = "Дополнительная информация") -> str:
        """Форматирует текст для отчета"""
        if not text:
            return ""
        
        # Разбиваем на абзацы
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        formatted = f"\n{'─' * 40}\n"
        formatted += f"📚 {title}\n"
        formatted += f"{'─' * 40}\n\n"
        
        for i, paragraph in enumerate(paragraphs[:10], 1):  # Ограничиваем 10 абзацами
            if len(paragraph) > 200:
                paragraph = paragraph[:200] + "..."
            formatted += f"{paragraph}\n\n"
        
        return formatted
    
    def create_summary(self, texts: List[str], focus_keywords: List[str] = None) -> str:
        """Создает краткое резюме из нескольких текстов"""
        if not texts:
            return ""
        
        # Извлекаем ключевую информацию
        if focus_keywords:
            key_info = []
            for text in texts:
                extracted = self.extract_key_information(text, focus_keywords)
                if extracted:
                    key_info.append(extracted)
            
            if key_info:
                return self.merge_texts(key_info, max_length=1000)
        
        # Если ключевых слов нет, берем первые предложения из каждого текста
        summary_parts = []
        for text in texts:
            if text:
                sentences = re.split(r'[.!?]\s+', text)
                if sentences:
                    summary_parts.append(sentences[0] + '.')
        
        return ' '.join(summary_parts[:5])  # Первые 5 предложений
    
    def process_matrix_data(self, scraped_data: List[Dict], matrix_result, keywords: List[str] = None) -> Dict[str, str]:
        """Обрабатывает собранные данные для матрицы судьбы"""
        # Используем переданные ключевые слова или значения по умолчанию
        if keywords is None:
            from .config import MATRIX_KEYWORDS
            keywords = MATRIX_KEYWORDS
        
        # Извлекаем тексты из успешных запросов
        texts = [data['text'] for data in scraped_data if data.get('success') and data.get('text')]
        
        if not texts:
            return {
                'summary': '',
                'detailed_info': '',
                'images': []
            }
        
        # Создаем резюме
        summary = self.create_summary(texts, keywords)
        
        # Объединяем детальную информацию
        detailed = self.merge_texts(texts, max_length=3000)
        detailed_formatted = self.format_for_report(detailed, "Информация из источников")
        
        # Собираем изображения
        images = []
        for data in scraped_data:
            if data.get('images'):
                images.extend(data['images'][:3])  # Берем первые 3 изображения с каждого сайта
        
        return {
            'summary': summary,
            'detailed_info': detailed_formatted,
            'images': images[:5]  # Максимум 5 изображений
        }
