from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ml_service import ml_service
from app.services.database_service import save_prediction
from typing import List, Dict

router = APIRouter()

class PredictionRequest(BaseModel):
    features: List[Dict[str, float]]  # 12 or 6 months of data
    model_type: str = "stat_lstm"

class PredictionResponse(BaseModel):
    prediction: float
    model_used: str
    confidence: float
    drought_category: str

@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    try:
        # Make prediction
        prediction = ml_service.predict(
            features=request.features,
            model_type=request.model_type
        )
        
        # Classify drought severity
        category = classify_drought(prediction)
        
        # Save to database
        await save_prediction(prediction, request.model_type, category)
        
        return PredictionResponse(
            prediction=prediction,
            model_used=request.model_type,
            confidence=0.85,  # Calculate based on model uncertainty
            drought_category=category
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def classify_drought(ndvi_value: float) -> str:
    if ndvi_value > 6000:
        return "No Drought"
    elif ndvi_value > 5000:
        return "Mild Drought"
    elif ndvi_value > 4000:
        return "Moderate Drought"
    else:
        return "Severe Drought"