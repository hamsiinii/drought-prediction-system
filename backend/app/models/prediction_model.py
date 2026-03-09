"""
Pydantic models - 19 features matching Vidarbha GEE training data
Target: NDVI (raw GEE pixel sum, range ~1900-7348)
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class MonthlyDataPoint(BaseModel):
    """One month of Vidarbha climate/vegetation data — exact training feature order"""
    EVI:          float = Field(..., description="Enhanced Vegetation Index (GEE pixel sum ~1100-5200)")
    LST:          float = Field(..., description="Land Surface Temperature day (°C ~26-50)")
    LST_Night:    float = Field(..., description="Land Surface Temperature night (°C ~12-29)")
    Rainfall:     float = Field(..., ge=0.0, description="Monthly rainfall mm (~0-18)")
    Soil_Moisture:float = Field(..., description="Soil moisture fraction (0.20-0.46)")
    SPI:          float = Field(..., description="Standardized Precipitation Index (-3 to 3)")
    PET:          float = Field(..., description="Potential Evapotranspiration mm (~70-262)")
    SPEI:         float = Field(..., description="Standardized Precip Evapotranspiration Index")
    NDVI_min:     float = Field(..., description="NDVI min pixel sum reference (~1900-3560)")
    NDVI_max:     float = Field(..., description="NDVI max pixel sum reference (~3822-7348)")
    VCI:          float = Field(..., ge=0.0, le=100.0, description="Vegetation Condition Index %")
    LST_min:      float = Field(..., description="LST minimum reference °C")
    LST_max:      float = Field(..., description="LST maximum reference °C")
    TCI:          float = Field(..., ge=0.0, le=100.0, description="Temperature Condition Index %")
    SM_min:       float = Field(..., description="Soil Moisture minimum reference")
    SM_max:       float = Field(..., description="Soil Moisture maximum reference")
    SMCI:         float = Field(..., ge=0.0, le=100.0, description="Soil Moisture Condition Index %")
    VHI:          float = Field(..., ge=0.0, le=100.0, description="Vegetation Health Index %")
    SIWSI:        float = Field(..., description="Shortwave Infrared Water Stress Index (0.16-0.74)")


class ManualPredictionRequest(BaseModel):
    data:     List[MonthlyDataPoint] = Field(..., min_length=12, max_length=12)
    location: Optional[str] = None


class PredictionResponse(BaseModel):
    regcdi_value:     float
    drought_category: str
    severity_level:   str
    confidence_score: float
    model_version:    str
    prediction_date:  str


class HealthResponse(BaseModel):
    status:       str
    model_loaded: bool
    timestamp:    str
    version:      str