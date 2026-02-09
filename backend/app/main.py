"""
Drought Analytics Microservice - FastAPI Main Application
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
import pandas as pd
import io
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ml_service import DroughtMLService
from app.services.database_service import DatabaseService
from app.models.prediction_model import (
    ManualPredictionRequest,
    PredictionResponse,
    HealthResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="Drought Insights & Analytics Microservice",
    description="Cloud-deployed microservice with REST APIs for drought data ingestion, analytics, and LSTM-based forecasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ml_service = DroughtMLService()
db_service = DatabaseService()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting Drought Analytics Microservice...")
    ml_service.load_model()
    await db_service.connect()
    print("✅ Services initialized successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await db_service.disconnect()
    print("👋 Service shutdown complete")

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and model status"""
    return {
        "status": "healthy",
        "model_loaded": ml_service.model is not None,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """API root with documentation links"""
    return {
        "message": "Drought Insights & Analytics Microservice",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "predict_manual": "/predict/manual",
            "predict_csv": "/data",
            "forecast": "/forecast",
            "summary": "/summary",
            "history": "/history"
        }
    }

# Manual prediction endpoint
@app.post("/predict/manual", response_model=PredictionResponse)
async def predict_manual(request: ManualPredictionRequest):
    """Single prediction from manual input (12 months of data)"""
    try:
        # Convert Pydantic models to dict, then DataFrame
        data_list = [item.dict() for item in request.data]
        df = pd.DataFrame(data_list)
        
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns: {df.columns.tolist()}")
        
        # Validate shape
        if len(df) != 12:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 12 months of data, got {len(df)}"
            )
        
        # Make prediction
        result = ml_service.predict(df)
        
        # Save to database (will skip if no DB)
        await db_service.save_prediction(
            prediction_type="manual",
            input_data=data_list,
            result=result,
            location=request.location
        )
        
        return result
        
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# CSV upload endpoint
@app.post("/data")
async def upload_data(file: UploadFile = File(...)):
    """Upload CSV file for batch predictions"""
    try:
        # Read CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        print(f"📊 CSV shape: {df.shape}")
        print(f"📋 Columns: {df.columns.tolist()}")
        
        # Validate columns
        required_columns = [
            'rainfall_mm', 'tmax_c', 'tmin_c', 'spei', 
            'spi', 'ndvi', 'soil_moisture'
        ]
        
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing_cols}"
            )
        
        # Generate predictions for rolling windows
        predictions = ml_service.predict_batch(df)
        
        # Save to MongoDB (will skip if no DB)
        await db_service.save_batch_predictions(
            filename=file.filename,
            predictions=predictions
        )
        
        return {
            "message": "Data processed successfully",
            "total_predictions": len(predictions),
            "predictions": predictions
        }
        
    except Exception as e:
        print(f"❌ CSV processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Forecast endpoint
@app.get("/forecast")
async def get_forecast(
    location: Optional[str] = None,
    limit: int = 10
):
    """Get recent drought forecasts"""
    try:
        forecasts = await db_service.get_recent_predictions(
            location=location,
            limit=limit
        )
        
        return {
            "total": len(forecasts),
            "forecasts": forecasts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Summary endpoint
@app.get("/summary")
async def get_summary():
    """Get system statistics and drought summary"""
    try:
        summary = await db_service.get_summary_stats()
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Prediction history endpoint
@app.get("/history")
async def get_history(
    skip: int = 0,
    limit: int = 50
):
    """Get prediction history with pagination"""
    try:
        history = await db_service.get_prediction_history(
            skip=skip,
            limit=limit
        )
        
        return {
            "total": len(history),
            "skip": skip,
            "limit": limit,
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
