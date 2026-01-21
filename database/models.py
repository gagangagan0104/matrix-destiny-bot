"""Модели базы данных"""
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Client(Base):
    """Модель клиента"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связь с расчетами
    calculations = relationship("MatrixCalculation", back_populates="client")
    feedbacks = relationship("Feedback", back_populates="client")


class MatrixCalculation(Base):
    """Модель расчета матрицы"""
    __tablename__ = "matrix_calculations"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    
    # Результаты расчета (JSON)
    result_data = Column(JSON, nullable=False)
    
    # Дополнительная информация
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с клиентом
    client = relationship("Client", back_populates="calculations")


class Feedback(Base):
    """Модель обратной связи от клиентов"""
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    calculation_id = Column(Integer, ForeignKey("matrix_calculations.id"), nullable=True)
    
    # Оценка (1-5)
    rating = Column(Integer, nullable=False)
    
    # Комментарий
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    client = relationship("Client", back_populates="feedbacks")
