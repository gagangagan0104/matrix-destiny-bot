"""Настройки администраторов"""
from typing import List

# Список Telegram ID администраторов
# Получить свой ID можно через бота @userinfobot
ADMIN_IDS: List[int] = []

# Можно также указать через переменную окружения
# ADMIN_IDS=123456789,987654321

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    if not ADMIN_IDS:
        # Если список пуст, можно загрузить из переменных окружения
        import os
        admin_str = os.getenv("ADMIN_IDS", "")
        if admin_str:
            return int(user_id) in [int(x.strip()) for x in admin_str.split(",")]
    return user_id in ADMIN_IDS
