"""Калькулятор личной матрицы судьбы"""
from datetime import date
from typing import Dict, List
from .models import MatrixData, MatrixResult
from .interpretations import get_interpretation


class MatrixCalculator:
    """Класс для расчета личной матрицы судьбы"""
    
    # Кармические числа
    KARMIC_NUMBERS = [13, 14, 16, 19]
    
    def __init__(self):
        self.interpretations = get_interpretation()
    
    def reduce_number(self, number: int) -> int:
        """Редуцирует число до однозначного (кроме мастер-чисел 11, 22)"""
        while number > 9 and number not in [11, 22]:
            number = sum(int(digit) for digit in str(number))
        return number
    
    def calculate_name_numbers(self, name: str) -> Dict[str, int]:
        """Вычисляет числа имени"""
        # Русский алфавит с нумерологическими значениями
        # А=1, Б=2, В=6, Г=3, Д=4, Е=5, Ё=5, Ж=2, З=7, И=1, Й=1, К=2, Л=3, М=4, Н=5, О=7, П=8, Р=2, С=3, Т=4, У=6, Ф=8, Х=5, Ц=3, Ч=7, Ш=2, Щ=9, Ъ=1, Ы=1, Ь=1, Э=6, Ю=7, Я=2
        
        # Упрощенная версия - используем стандартную нумерологию
        name_upper = name.upper().replace(' ', '')
        
        # Гласные: А, Е, Ё, И, О, У, Ы, Э, Ю, Я
        vowels = 'АЕЁИОУЫЭЮЯ'
        # Согласные: все остальные
        consonants = 'БВГДЖЗЙКЛМНПРСТФХЦЧШЩ'
        
        soul_sum = sum(self._char_to_number(char) for char in name_upper if char in vowels)
        personality_sum = sum(self._char_to_number(char) for char in name_upper if char in consonants)
        
        return {
            'soul': self.reduce_number(soul_sum),
            'personality': self.reduce_number(personality_sum)
        }
    
    def _char_to_number(self, char: str) -> int:
        """Преобразует символ в число по нумерологии"""
        # Русская нумерология
        mapping = {
            'А': 1, 'Б': 2, 'В': 6, 'Г': 3, 'Д': 4, 'Е': 5, 'Ё': 5, 'Ж': 2, 'З': 7,
            'И': 1, 'Й': 1, 'К': 2, 'Л': 3, 'М': 4, 'Н': 5, 'О': 7, 'П': 8, 'Р': 2,
            'С': 3, 'Т': 4, 'У': 6, 'Ф': 8, 'Х': 5, 'Ц': 3, 'Ч': 7, 'Ш': 2, 'Щ': 9,
            'Ъ': 1, 'Ы': 1, 'Ь': 1, 'Э': 6, 'Ю': 7, 'Я': 2
        }
        return mapping.get(char, 0)
    
    def calculate_matrix(self, data: MatrixData) -> MatrixResult:
        """Основной метод расчета матрицы"""
        birth_date = data.birth_date
        
        # Базовые числа
        day = birth_date.day
        month = birth_date.month
        year = birth_date.year
        year_reduced = self.reduce_number(year)
        
        # Личное число (день + месяц)
        personal_number = self.reduce_number(day + month)
        
        # Число судьбы (сумма всех цифр даты)
        date_sum = sum(int(d) for d in str(day) + str(month) + str(year))
        destiny_number = self.reduce_number(date_sum)
        
        # Числа имени
        name_numbers = self.calculate_name_numbers(data.name)
        soul_number = name_numbers['soul']
        personality_number = name_numbers['personality']
        
        # Путь жизни (сумма дня, месяца, года)
        life_path = self.reduce_number(day + month + year_reduced)
        
        # Выражение (сумма всех чисел имени)
        name_sum = sum(self._char_to_number(char) for char in data.name.upper().replace(' ', ''))
        expression = self.reduce_number(name_sum)
        
        # Построение матрицы 3x3
        matrix = self._build_matrix(
            day, month, year_reduced, 
            personal_number, destiny_number,
            soul_number, personality_number,
            life_path, expression
        )
        
        # Кармические числа
        karmic_numbers = self._find_karmic_numbers(
            day, month, year, personal_number, destiny_number
        )
        
        # Интерпретации
        interpretations = self._get_interpretations(
            personal_number, destiny_number, soul_number,
            personality_number, life_path, expression, matrix
        )
        
        return MatrixResult(
            day=day,
            month=month,
            year=year,
            year_reduced=year_reduced,
            personal_number=personal_number,
            destiny_number=destiny_number,
            soul_number=soul_number,
            personality_number=personality_number,
            matrix=matrix,
            karmic_numbers=karmic_numbers,
            life_path=life_path,
            expression=expression,
            interpretations=interpretations
        )
    
    def _build_matrix(self, day: int, month: int, year_reduced: int,
                     personal: int, destiny: int,
                     soul: int, personality: int,
                     life_path: int, expression: int) -> Dict[str, int]:
        """Строит матрицу 3x3"""
        # Матрица судьбы: квадрат с диагоналями
        # Верхний ряд: день, месяц, год
        # Средний ряд: личное число, число судьбы, выражение
        # Нижний ряд: душа, личность, путь жизни
        
        return {
            'top_left': self.reduce_number(day),
            'top_center': self.reduce_number(month),
            'top_right': self.reduce_number(year_reduced),
            'middle_left': personal,
            'center': destiny,
            'middle_right': expression,
            'bottom_left': soul,
            'bottom_center': personality,
            'bottom_right': life_path
        }
    
    def _find_karmic_numbers(self, day: int, month: int, year: int,
                            personal: int, destiny: int) -> List[int]:
        """Находит кармические числа в расчетах"""
        found = []
        numbers_to_check = [day, month, year, personal, destiny]
        
        for num in numbers_to_check:
            if num in self.KARMIC_NUMBERS:
                found.append(num)
        
        return list(set(found))
    
    def _get_interpretations(self, personal: int, destiny: int, soul: int,
                           personality: int, life_path: int, expression: int,
                           matrix: Dict[str, int]) -> Dict[str, str]:
        """Получает интерпретации для всех чисел"""
        return {
            'personal_number': self.interpretations.get(f'number_{personal}', ''),
            'destiny_number': self.interpretations.get(f'number_{destiny}', ''),
            'soul_number': self.interpretations.get(f'number_{soul}', ''),
            'personality_number': self.interpretations.get(f'number_{personality}', ''),
            'life_path': self.interpretations.get(f'number_{life_path}', ''),
            'expression': self.interpretations.get(f'number_{expression}', ''),
            'matrix_center': self.interpretations.get(f'number_{matrix["center"]}', ''),
        }
