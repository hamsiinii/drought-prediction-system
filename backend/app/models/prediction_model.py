"""
Pydantic Models for Request/Response Validation
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class DroughtCategory(str, Enum):
    """Drought severity categories"""
    NO_DROUGHT = "No Drought"
    MILD = "Mild Drought"
    MODERATE = "Moderate Drought"
    SEVERE = "Severe Drought"
    EXTREME = "Extreme Drought"

class MonthlyFeatures(BaseModel):
    """Single month's feature data"""
    rainfall_mm: float = Field(..., description="Monthly cumulative rainfall (mm)")
    tmax_c: float = Field(..., description="Maximum temperature (°C)")
    tmin_c: float = Field(..., description="Minimum temperature (°C)")
    spei: float = Field(..., description="Standardized Precipitation Evapotranspiration Index")
    spi: float = Field(..., description="Standardized Precipitation Index")
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index", ge=0, le=1)
    soil_moisture: float = Field(..., description="Soil moisture (%)", ge=0, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "rainfall_mm": 85.5,
                "tmax_c": 32.4,
                "tmin_c": 18.2,
                "spei": -0.5,
                "spi": -0.3,
                "ndvi": 0.65,
                "soil_moisture": 45.0
            }
        }

class ManualPredictionRequest(BaseModel):
    """Request for manual prediction (12 months of data)"""
    data: List[MonthlyFeatures] = Field(..., min_length=12, max_length=12)
    location: Optional[str] = Field(None, description="Location identifier")
    
    @validator('data')
    def validate_data_length(cls, v):
        if len(v) != 12:
            raise ValueError('Exactly 12 months of data required')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "rainfall_mm": 85.5,
                        "tmax_c": 32.4,
                        "tmin_c": 18.2,
                        "spei": -0.5,
                        "spi": -0.3,
                        "ndvi": 0.65,
                        "soil_moisture": 45.0
                    }
                    # ... repeat for 12 months
                ],
                "location": "Maharashtra"
            }
        }

class PredictionResponse(BaseModel):
    """Response from prediction endpoint"""
    regcdi_value: float = Field(..., description="Predicted REGCDI value")
    drought_category: str = Field(..., description="Drought severity category")
    severity_level: str = Field(..., description="Severity level (no_drought, mild, moderate, severe, extreme)")
    confidence_score: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    prediction_date: str = Field(..., description="Timestamp of prediction")
    model_version: str = Field(..., description="Model version used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "regcdi_value": -0.65,
                "drought_category": "Moderate Drought",
                "severity_level": "moderate",
                "confidence_score": 0.82,
                "prediction_date": "2025-01-15T10:30:00Z",
                "model_version": "stat-LSTM-v1.0"
            }
        }

class BatchPredictionResponse(BaseModel):
    """Response for batch predictions"""
    total_predictions: int
    predictions: List[PredictionResponse]
    filename: Optional[str] = None
    uploaded_at: str

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether ML model is loaded")
    timestamp: str = Field(..., description="Current server timestamp")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "model_loaded": True,
                "timestamp": "2025-01-15T10:30:00Z",
                "version": "1.0.0"
            }
        }

class SummaryStats(BaseModel):
    """System summary statistics"""
    total_predictions: int
    drought_distribution: Dict[str, int]
    average_regcdi: float
    last_prediction_date: Optional[str]
    
class PredictionHistory(BaseModel):
    """Historical prediction record"""
    id: str
    prediction_type: str  # 'manual' or 'batch'
    regcdi_value: float
    drought_category: str
    location: Optional[str]
    created_at: str
    input_summary: Optional[Dict[str, Any]]