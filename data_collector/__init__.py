"""Модуль для сбора и обработки данных с веб-сайтов"""
from .web_scraper import WebScraper
from .text_processor import TextProcessor
from .image_processor import ImageProcessor
from .config import MATRIX_SOURCES, MATRIX_KEYWORDS, PROCESSING_CONFIG

__all__ = [
    'WebScraper', 
    'TextProcessor', 
    'ImageProcessor', 
    'MATRIX_SOURCES',
    'MATRIX_KEYWORDS',
    'PROCESSING_CONFIG'
]
