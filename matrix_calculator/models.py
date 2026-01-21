"""Модели данных для матрицы"""
from pydantic import BaseModel
from datetime import date
from typing import Dict, List, Optional


class MatrixData(BaseModel):
    """Входные данные для расчета матрицы"""
    birth_date: date
    name: str
    gender: Optional[str] = None  # 'male' или 'female'


class MatrixResult(BaseModel):
    """Результат расчета матрицы"""
    # Основные числа
    day: int
    month: int
    year: int
    year_reduced: int
    
    # Ключевые числа матрицы
    personal_number: int  # Сумма дня и месяца
    destiny_number: int   # Сумма всех цифр даты
    soul_number: int      # Сумма гласных имени
    personality_number: int  # Сумма согласных имени
    
    # Позиции матрицы (квадрат 3x3)
    matrix: Dict[str, int]  # Позиции: top_left, top_center, top_right, etc.
    
    # Кармические числа
    karmic_numbers: List[int]
    
    # Дополнительные расчеты
    life_path: int
    expression: int
    
    # Интерпретации
    interpretations: Dict[str, str]
