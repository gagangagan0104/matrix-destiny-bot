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
    
    # Railway/Production
    railway_environment: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Application
    debug: bool = False
    
    class Config:
        env_file = ".env" if not os.getenv("RAILWAY_ENVIRONMENT") else None
        case_sensitive = False


settings = Settings()
