"""
ML Service - Model Loading and Prediction Logic
"""

import numpy as np
import pandas as pd
import pickle
import json
import os
from typing import Dict, List, Any
from datetime import datetime

class DroughtMLService:
    def __init__(self):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.feature_config = None
        self.model_path = "ml_models/"
        
    def load_model(self):
        """Load trained LSTM model and scalers"""
        try:
            import tensorflow as tf
            from tensorflow import keras
            
            # Suppress TensorFlow warnings
            import logging
            logging.getLogger('tensorflow').setLevel(logging.ERROR)
            
            # Load model with compatibility fix
            model_file = os.path.join(self.model_path, "stat_lstm_best_model.h5")
            
            # Load without compiling to avoid serialization issues
            self.model = keras.models.load_model(model_file, compile=False)
            
            # Recompile with current Keras
            self.model.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            
            print(f"✅ Model loaded from {model_file}")
            
            # Load scalers
            with open(os.path.join(self.model_path, "scaler_X.pkl"), "rb") as f:
                self.scaler_X = pickle.load(f)
            
            with open(os.path.join(self.model_path, "scaler_y.pkl"), "rb") as f:
                self.scaler_y = pickle.load(f)
            
            print("✅ Scalers loaded successfully")
            
            # Load feature config
            config_file = os.path.join(self.model_path, "feature_config.json")
            with open(config_file, "r") as f:
                self.feature_config = json.load(f)
            
            print("✅ Feature configuration loaded")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def preprocess_data(self, df: pd.DataFrame) -> np.ndarray:
        """Preprocess input data for model"""
        # Ensure correct column order
        feature_names = [f["name"] for f in self.feature_config["features"]]
        df = df[feature_names]
        
        # Convert to numpy
        data = df.values
        
        # Reshape for scaler
        original_shape = data.shape
        data_flat = data.reshape(-1, 1)
        
        # Scale
        data_scaled = self.scaler_X.transform(data_flat)
        data_scaled = data_scaled.reshape(original_shape)
        
        # Add batch dimension
        data_scaled = np.expand_dims(data_scaled, axis=0)
        
        return data_scaled
    
    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Make single prediction"""
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        # Preprocess
        X = self.preprocess_data(df)
        
        # Predict
        y_pred_scaled = self.model.predict(X, verbose=0)
        
        # Inverse transform
        regcdi_value = self.scaler_y.inverse_transform(y_pred_scaled)[0][0]
        
        # Categorize drought
        category = self.categorize_drought(regcdi_value)
        
        # Create response
        result = {
            "regcdi_value": float(regcdi_value),
            "drought_category": category["label"],
            "severity_level": category["level"],
            "confidence_score": self._calculate_confidence(regcdi_value),
            "prediction_date": datetime.utcnow().isoformat(),
            "model_version": "stat-LSTM-v1.0"
        }
        
        return result
    
    def predict_batch(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Make predictions for rolling windows in CSV data"""
        predictions = []
        
        # Generate rolling windows of 12 months
        for i in range(len(df) - 11):
            window = df.iloc[i:i+12]
            
            try:
                result = self.predict(window)
                result["window_start"] = i
                result["window_end"] = i + 11
                predictions.append(result)
            except Exception as e:
                print(f"Error predicting window {i}: {e}")
                continue
        
        return predictions
    
    def categorize_drought(self, regcdi: float) -> Dict[str, Any]:
        """Categorize REGCDI value into drought severity"""
        categories = self.feature_config["drought_categories"]
        
        if regcdi >= 0.5:
            level = "no_drought"
        elif regcdi >= 0.0:
            level = "mild"
        elif regcdi >= -0.5:
            level = "moderate"
        elif regcdi >= -1.0:
            level = "severe"
        else:
            level = "extreme"
        
        return {
            "level": level,
            "label": categories[level]["label"],
            "description": self._get_severity_description(level)
        }
    
    def _get_severity_description(self, level: str) -> str:
        """Get human-readable description of drought severity"""
        descriptions = {
            "no_drought": "Normal conditions with adequate water availability",
            "mild": "Slight water deficit, minimal impact on agriculture",
            "moderate": "Noticeable water shortage, crop stress beginning",
            "severe": "Significant water scarcity, major agricultural impact",
            "extreme": "Critical water shortage, widespread agricultural failure"
        }
        return descriptions.get(level, "Unknown severity")
    
    def _calculate_confidence(self, regcdi: float) -> float:
        """Calculate confidence score based on REGCDI value"""
        boundaries = [-1.0, -0.5, 0.0, 0.5]
        distances = [abs(regcdi - b) for b in boundaries]
        min_distance = min(distances)
        
        confidence = 0.5 + (min_distance * 0.25)
        return min(confidence, 1.0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata"""
        if self.model is None:
            return {"error": "Model not loaded"}
        
        return {
            "model_type": "stat-LSTM",
            "sequence_length": 12,
            "num_features": 7,
            "output": "REGCDI",
            "feature_config": self.feature_config
        }