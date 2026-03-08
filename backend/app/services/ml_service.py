"""
ML Service for Drought Analytics — Vidarbha Region
Model: stat-LSTM | Target: NDVI (GEE pixel sum) | Features: 19
"""

import os
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from typing import List, Dict

# EXACT feature order from training notebook Cell 7
FEATURE_COLS = [
    "EVI", "LST", "LST_Night", "Rainfall", "Soil_Moisture",
    "SPI", "PET", "SPEI",
    "NDVI_min", "NDVI_max", "VCI",
    "LST_min", "LST_max", "TCI",
    "SM_min", "SM_max", "SMCI", "VHI", "SIWSI"
]

# NDVI range observed in Vidarbha dataset (raw GEE pixel sums)
NDVI_MIN = 1899.86
NDVI_MAX = 7348.72
NDVI_MEAN = 4590.97

MODEL_DIR = "/home/hamsi/drought-prediction-system/backend/ml_models"

def ndvi_to_drought(ndvi_value: float) -> tuple:
    """
    Map predicted NDVI (GEE pixel sum) to drought category.
    Higher NDVI = more vegetation = less drought.
    Thresholds derived from Vidarbha data distribution.
    """
    # Normalize to 0-1 for comparison
    ndvi_norm = (ndvi_value - NDVI_MIN) / (NDVI_MAX - NDVI_MIN)
    ndvi_norm = max(0.0, min(1.0, ndvi_norm))

    if ndvi_norm >= 0.65:
        return "No Drought", "none"
    elif ndvi_norm >= 0.45:
        return "Mild Drought", "mild"
    elif ndvi_norm >= 0.30:
        return "Moderate Drought", "moderate"
    elif ndvi_norm >= 0.15:
        return "Severe Drought", "severe"
    else:
        return "Extreme Drought", "extreme"


def ndvi_to_regcdi(ndvi_value: float) -> float:
    """
    Convert NDVI pixel sum to a REGCDI-like index (-2 to +2).
    Scaled so average NDVI = 0, extremes = ±2.
    """
    ndvi_norm = (ndvi_value - NDVI_MEAN) / (NDVI_MAX - NDVI_MIN)
    return round(float(np.clip(ndvi_norm * 4, -2.0, 2.0)), 4)


class DroughtMLService:
    def __init__(self):
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.model_version = "stat-LSTM-v1.0-vidarbha"

    def load_model(self):
        """Load LSTM model and both scalers"""
        try:
            import tensorflow as tf

            model_path    = os.path.join(MODEL_DIR, "stat_lstm_best_model.h5")
            scaler_x_path = os.path.join(MODEL_DIR, "scaler_X.pkl")
            scaler_y_path = os.path.join(MODEL_DIR, "scaler_y.pkl")

            self.model = tf.keras.models.load_model(
                model_path,
                custom_objects={"mse": tf.keras.losses.MeanSquaredError()}
            )

            with open(scaler_x_path, "rb") as f:
                self.scaler_X = pickle.load(f)
            with open(scaler_y_path, "rb") as f:
                self.scaler_y = pickle.load(f)

            print(f"✅ stat-LSTM loaded — {self.scaler_X.n_features_in_} features, target=NDVI")

        except Exception as e:
            print(f"❌ Model load failed: {e}")
            self.model = None

    def _df_from_request(self, data_list: List[Dict]) -> pd.DataFrame:
        """Convert API request dicts to correctly-ordered DataFrame"""
        df = pd.DataFrame(data_list)
        missing = [c for c in FEATURE_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        return df[FEATURE_COLS]

    def predict(self, df: pd.DataFrame) -> Dict:
        """Run single 12-month prediction"""
        if self.model is None:
            raise RuntimeError("Model not loaded")

        X_scaled = self.scaler_X.transform(df[FEATURE_COLS].values)
        X_seq    = X_scaled.reshape(1, 12, len(FEATURE_COLS))

        y_scaled = self.model.predict(X_seq, verbose=0)
        ndvi_pred = float(self.scaler_y.inverse_transform(y_scaled)[0][0])

        category, severity = ndvi_to_drought(ndvi_pred)
        regcdi             = ndvi_to_regcdi(ndvi_pred)

        # Confidence: based on how far from category boundary
        ndvi_norm  = (ndvi_pred - NDVI_MIN) / (NDVI_MAX - NDVI_MIN)
        confidence = min(0.97, max(0.55, 0.70 + abs(ndvi_norm - 0.5) * 0.5))

        return {
            "regcdi_value":     regcdi,
            "drought_category": category,
            "severity_level":   severity,
            "confidence_score": round(confidence, 4),
            "model_version":    self.model_version,
            "prediction_date":  datetime.utcnow().isoformat(),
            "ndvi_predicted":   round(ndvi_pred, 2),
        }

    def predict_batch(self, df: pd.DataFrame) -> List[Dict]:
        """Sliding 12-month window predictions"""
        if self.model is None:
            raise RuntimeError("Model not loaded")

        results = []
        for i in range(len(df) - 11):
            window = df.iloc[i: i + 12]
            try:
                result = self.predict(window)
                result["window_start"] = i
                result["window_end"]   = i + 11
                results.append(result)
            except Exception as e:
                print(f"⚠️ Window {i} skipped: {e}")
        return results