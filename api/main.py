"""FastAPI приложение"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from pydantic import BaseModel

from config import settings
from database.database import get_db, init_db
from database.models import Client, MatrixCalculation
from matrix_calculator import MatrixCalculator, MatrixData
from reports import ReportGenerator
import io

app = FastAPI(
    title="Личная Матрица Судьбы API",
    description="API для расчета личной матрицы судьбы",
    version="1.0.0"
)

# Инициализация
calculator = MatrixCalculator()
report_generator = ReportGenerator()

# Инициализация БД при старте
@app.on_event("startup")
async def startup_event():
    init_db()


# Модели запросов
class MatrixRequest(BaseModel):
    name: str
    birth_date: date
    gender: Optional[str] = None


class ClientCreate(BaseModel):
    name: str
    birth_date: date
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


# API endpoints
@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Личная Матрица Судьбы API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.post("/api/calculate")
async def calculate_matrix(request: MatrixRequest):
    """Расчет матрицы судьбы"""
    try:
        matrix_data = MatrixData(
            birth_date=request.birth_date,
            name=request.name,
            gender=request.gender
        )
        
        result = calculator.calculate_matrix(matrix_data)
        
        return {
            "success": True,
            "data": result.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/calculate/report")
async def calculate_matrix_report(request: MatrixRequest):
    """Расчет матрицы с текстовым отчетом"""
    try:
        matrix_data = MatrixData(
            birth_date=request.birth_date,
            name=request.name,
            gender=request.gender
        )
        
        result = calculator.calculate_matrix(matrix_data)
        report = report_generator.generate_text_report(matrix_data, result)
        
        return {
            "success": True,
            "report": report,
            "data": result.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/calculate/visual")
async def calculate_matrix_visual(
    name: str,
    birth_date: date,
    gender: Optional[str] = None
):
    """Расчет матрицы с визуализацией"""
    try:
        matrix_data = MatrixData(
            birth_date=birth_date,
            name=name,
            gender=gender
        )
        
        result = calculator.calculate_matrix(matrix_data)
        visual = report_generator.generate_visual_matrix(result)
        
        return StreamingResponse(
            io.BytesIO(visual),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=matrix.png"}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/clients")
async def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Создание нового клиента"""
    try:
        db_client = Client(
            name=client.name,
            birth_date=client.birth_date,
            gender=client.gender,
            phone=client.phone,
            email=client.email,
            notes=client.notes
        )
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        
        return {
            "success": True,
            "client_id": db_client.id,
            "data": {
                "id": db_client.id,
                "name": db_client.name,
                "birth_date": str(db_client.birth_date),
                "created_at": str(db_client.created_at)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/clients")
async def get_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Получение списка клиентов"""
    clients = db.query(Client).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "count": len(clients),
        "data": [
            {
                "id": c.id,
                "name": c.name,
                "birth_date": str(c.birth_date),
                "gender": c.gender,
                "created_at": str(c.created_at)
            }
            for c in clients
        ]
    }


@app.get("/api/clients/{client_id}")
async def get_client(client_id: int, db: Session = Depends(get_db)):
    """Получение клиента по ID"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "success": True,
        "data": {
            "id": client.id,
            "name": client.name,
            "birth_date": str(client.birth_date),
            "gender": client.gender,
            "phone": client.phone,
            "email": client.email,
            "notes": client.notes,
            "created_at": str(client.created_at),
            "calculations_count": len(client.calculations)
        }
    }


@app.post("/api/clients/{client_id}/calculate")
async def calculate_for_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Расчет матрицы для существующего клиента"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    try:
        matrix_data = MatrixData(
            birth_date=client.birth_date,
            name=client.name,
            gender=client.gender
        )
        
        result = calculator.calculate_matrix(matrix_data)
        
        # Сохраняем расчет
        calculation = MatrixCalculation(
            client_id=client.id,
            result_data=result.model_dump()
        )
        db.add(calculation)
        db.commit()
        db.refresh(calculation)
        
        return {
            "success": True,
            "calculation_id": calculation.id,
            "data": result.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/clients/{client_id}/calculations")
async def get_client_calculations(client_id: int, db: Session = Depends(get_db)):
    """Получение всех расчетов клиента"""
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "success": True,
        "count": len(client.calculations),
        "data": [
            {
                "id": calc.id,
                "created_at": str(calc.created_at),
                "result": calc.result_data
            }
            for calc in client.calculations
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
