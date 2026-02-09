"""
Database Service - MongoDB & PostgreSQL Integration
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List, Dict, Optional, Any

class DatabaseService:
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.postgres_pool = None
        
        self.mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.postgres_uri = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/droughtdb")
    
    async def connect(self):
        """Initialize database connections"""
        try:
            self.mongo_client = AsyncIOMotorClient(self.mongo_uri)
            self.mongo_db = self.mongo_client.drought_analytics
            await self.mongo_client.admin.command('ping')
            print("✅ MongoDB connected")
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            print("   Running without database persistence...")
    
    async def disconnect(self):
        """Close database connections"""
        if self.mongo_client:
            self.mongo_client.close()
    
    async def save_prediction(self, prediction_type: str, input_data: Any, result: Dict[str, Any], location: Optional[str] = None):
        """Save prediction to MongoDB"""
        if not self.mongo_db:
            return None
        
        try:
            document = {
                "prediction_type": prediction_type,
                "regcdi_value": result["regcdi_value"],
                "drought_category": result["drought_category"],
                "severity_level": result["severity_level"],
                "confidence_score": result["confidence_score"],
                "location": location,
                "input_data": input_data,
                "created_at": datetime.utcnow(),
                "model_version": result["model_version"]
            }
            
            collection = self.mongo_db.predictions
            insert_result = await collection.insert_one(document)
            return str(insert_result.inserted_id)
            
        except Exception as e:
            print(f"Error saving prediction: {e}")
            return None
    
    async def save_batch_predictions(self, filename: str, predictions: List[Dict[str, Any]]):
        """Save batch predictions to MongoDB"""
        if not self.mongo_db:
            return None
        
        try:
            document = {
                "filename": filename,
                "total_predictions": len(predictions),
                "predictions": predictions,
                "uploaded_at": datetime.utcnow()
            }
            
            collection = self.mongo_db.batch_uploads
            insert_result = await collection.insert_one(document)
            return str(insert_result.inserted_id)
            
        except Exception as e:
            print(f"Error saving batch: {e}")
            return None
    
    async def get_recent_predictions(self, location: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent predictions with optional location filter"""
        if not self.mongo_db:
            return []
        
        try:
            collection = self.mongo_db.predictions
            query = {}
            if location:
                query["location"] = location
            
            cursor = collection.find(query).sort("created_at", -1).limit(limit)
            predictions = await cursor.to_list(length=limit)
            
            for pred in predictions:
                pred["_id"] = str(pred["_id"])
                pred.pop("input_data", None)
            
            return predictions
            
        except Exception as e:
            print(f"Error fetching predictions: {e}")
            return []
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.mongo_db:
            return {
                "total_predictions": 0,
                "message": "Database not connected"
            }
        
        try:
            collection = self.mongo_db.predictions
            total = await collection.count_documents({})
            
            return {
                "total_predictions": total,
                "drought_distribution": {},
                "average_regcdi": 0.0,
                "last_prediction_date": None
            }
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {"error": str(e)}
    
    async def get_prediction_history(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get paginated prediction history"""
        if not self.mongo_db:
            return []
        
        try:
            collection = self.mongo_db.predictions
            cursor = collection.find({}).sort("created_at", -1).skip(skip).limit(limit)
            history = await cursor.to_list(length=limit)
            
            for item in history:
                item["id"] = str(item.pop("_id"))
                item["created_at"] = item["created_at"].isoformat()
                item.pop("input_data", None)
            
            return history
            
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []
    
    async def get_prediction_by_id(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Get single prediction by ID"""
        if not self.mongo_db:
            return None
        
        try:
            from bson import ObjectId
            collection = self.mongo_db.predictions
            prediction = await collection.find_one({"_id": ObjectId(prediction_id)})
            
            if prediction:
                prediction["_id"] = str(prediction["_id"])
                prediction["created_at"] = prediction["created_at"].isoformat()
            
            return prediction
            
        except Exception as e:
            print(f"Error fetching prediction: {e}")
            return None
