"""Конфигурация источников данных для матрицы судьбы"""
from typing import List, Dict

# Список источников для сбора информации о матрице судьбы
MATRIX_SOURCES: List[Dict[str, any]] = [
    {
        'name': 'gadalkindom',
        'url': 'https://gadalkindom.ru/matritsa-sudby',
        'selectors': [
            'article',
            '.content',
            'main',
            'p',
            'h1', 'h2', 'h3'
        ],
        'enabled': True
    },
    # Добавьте другие источники здесь:
    # {
    #     'name': 'source2',
    #     'url': 'https://example.com/matrix',
    #     'selectors': ['article', 'main'],
    #     'enabled': True
    # }
]

# Ключевые слова для поиска релевантной информации
MATRIX_KEYWORDS = [
    'матрица судьбы',
    'нумерология',
    'аркан',
    'кармическая задача',
    'число судьбы',
    'личное число',
    'путь жизни',
    'выражение',
    'душа',
    'личность',
    'кармические числа',
    'мастер-число'
]

# Настройки обработки
PROCESSING_CONFIG = {
    'max_text_length': 5000,
    'max_summary_length': 1000,
    'max_images': 5,
    'image_max_size': (800, 600),
    'request_timeout': 30
}
