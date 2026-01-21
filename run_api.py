#!/usr/bin/env python3
"""Скрипт запуска API"""
import uvicorn
from config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
