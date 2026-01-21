"""Конфигурация приложения"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Telegram
    telegram_bot_token: str
    
    # Database
    database_url: str = "sqlite:///./matrix.db"
    
    # Railway/Production (Railway устанавливает это как строку 'production')
    railway_environment: Optional[str] = None
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Application
    debug: bool = False
    
    @property
    def is_railway(self) -> bool:
        """Проверяет, запущено ли на Railway"""
        return self.railway_environment is not None or os.getenv("RAILWAY_ENVIRONMENT") is not None
    
    class Config:
        # Для Railway используем переменные окружения напрямую
        env_file = ".env" if not os.getenv("RAILWAY_ENVIRONMENT") else None
        case_sensitive = False
        # Игнорируем неизвестные поля из окружения Railway
        extra = "ignore"


settings = Settings()
