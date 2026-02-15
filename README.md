# 🌊 Drought Insights & Analytics Microservice

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange.svg)](https://tensorflow.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A cloud-deployed microservice with REST APIs for drought data ingestion, analytics, and **stat-LSTM based forecasting**. Built for Final Year Project (FYP) demonstration.

## 🎯 Project Overview

This system predicts drought conditions using a **Stateful LSTM (stat-LSTM)** neural network trained on meteorological and agricultural data. It provides:

- 🔮 Real-time drought predictions (REGCDI index)
- 📊 Interactive analytics dashboard
- 🌐 RESTful API for integration
- 💾 Persistent storage (MongoDB + PostgreSQL)
- 📈 Historical trend analysis

## 🏗️ Architecture

```
┌──────────────────────────┐
│    Streamlit Dashboard    │
│    (Frontend UI)          │
└────────────┬──────────────┘
             │ REST API
┌────────────▼──────────────┐
│    FastAPI Backend         │
│  ┌──────────────────────┐ │
│  │  ML Service          │ │
│  │  (stat-LSTM)         │ │
│  └──────────────────────┘ │
│  ┌──────────────────────┐ │
│  │  Data Processing     │ │
│  └──────────────────────┘ │
└────────────┬──────────────┘
             │
    ┌────────▼────────┐
    │   Databases     │
    │ MongoDB + PG    │
    └─────────────────┘
```

## 📊 Model Details

### stat-LSTM Architecture

- **Input**: 12 months × 7 features (rolling window)
- **Output**: REGCDI (Regional Comprehensive Drought Index)
- **Sequence Length**: 12 time steps
- **Features**:
  - `rainfall_mm` - Monthly cumulative rainfall
  - `tmax_c` - Maximum temperature
  - `tmin_c` - Minimum temperature
  - `spei` - Standardized Precipitation Evapotranspiration Index
  - `spi` - Standardized Precipitation Index
  - `ndvi` - Normalized Difference Vegetation Index
  - `soil_moisture` - Surface soil moisture percentage

### Drought Categories

| REGCDI Range | Category   | Description          |
| ------------ | ---------- | -------------------- |
| ≥ 0.5        | No Drought | Normal conditions    |
| 0.0 to 0.5   | Mild       | Slight water deficit |
| -0.5 to 0.0  | Moderate   | Noticeable shortage  |
| -1.0 to -0.5 | Severe     | Major impact         |
| < -1.0       | Extreme    | Critical shortage    |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB (local or Atlas)
- Git

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/drought-prediction-system.git
cd drought-prediction-system
```

### 2. Setup Backend

```bash
cd backend
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your database credentials

# Run API server
uvicorn app.main:app --reload
```

API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### 3. Setup Frontend

```bash
cd frontend
pip install streamlit pandas plotly requests

# Run dashboard
streamlit run streamlit_app.py
```

Dashboard will open at: `http://localhost:8501`

## 📁 Project Structure

```
drought-prediction-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── models/
│   │   │   └── prediction_model.py # Pydantic schemas
│   │   └── services/
│   │       ├── ml_service.py       # LSTM model loading
│   │       └── database_service.py # DB operations
│   ├── ml_models/
│   │   ├── stat_lstm_best_model.h5 # Trained model
│   │   ├── scaler_X.pkl            # Input scaler
│   │   ├── scaler_y.pkl            # Output scaler
│   │   └── feature_config.json     # Feature definitions
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── streamlit_app.py            # Dashboard UI
├── docs/
│   ├── API_DOCUMENTATION.md
│   └── DEPLOYMENT_GUIDE.md
├── render.yaml                     # Render deployment config
└── README.md
```

## 🌐 API Endpoints

### Health Check

```bash
GET /health
```

### Manual Prediction

```bash
POST /predict/manual
Content-Type: application/json

{
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
    // ... 12 months total
  ],
  "location": "Maharashtra"
}
```

### Upload CSV

```bash
POST /data
Content-Type: multipart/form-data
file: drought_data.csv
```

### Get Forecasts

```bash
GET /forecast?limit=10
```

### System Summary

```bash
GET /summary
```

### Prediction History

```bash
GET /history?skip=0&limit=50
```

## 🎨 Dashboard Features

1. **🏠 Home** - System overview and health status
2. **📊 Manual Prediction** - Enter 12 months of data manually
3. **📁 Upload CSV** - Batch predictions from CSV files
4. **📈 Analytics** - Drought distribution and statistics
5. **📜 History** - View past predictions
6. **ℹ️ About** - System documentation

## 🚢 Deployment

### Deploy to Render (Free Tier)

1. **Fork this repository**

2. **Create Render account**: https://render.com

3. **Setup MongoDB Atlas** (Free):

   - Go to https://www.mongodb.com/cloud/atlas
   - Create free cluster
   - Get connection string

4. **Deploy Backend**:

   ```bash
   # Push to GitHub
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

   - Go to Render Dashboard → New → Web Service
   - Connect your GitHub repo
   - Use `render.yaml` configuration
   - Add environment variable: `MONGODB_URI`

5. **Deploy Frontend**:
   - Create another Web Service for Streamlit
   - Set `API_URL` environment variable to backend URL

### Deploy with Docker

```bash
# Build backend
cd backend
docker build -t drought-api .
docker run -p 8000:8000 drought-api

# Build frontend
cd frontend
docker build -t drought-dashboard .
docker run -p 8501:8501 drought-dashboard
```

## 📖 Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Model Architecture](docs/MODEL_ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)

## 🧪 Testing

```bash
cd backend
pytest tests/
```

## 📊 Model Training

The model was trained on historical weather data from:

- Google Earth Engine (GEE)
- India Meteorological Department (IMD)
- NOAA

Training notebooks are available in `notebooks/` directory.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- TensorFlow/Keras for ML framework
- FastAPI for backend framework
- Streamlit for rapid dashboard development
- MongoDB Atlas for free database hosting
- Render for free deployment


## 🐛 Known Issues

- [ ] PostgreSQL integration optional (MongoDB primary)
- [ ] Large CSV files (>1000 rows) may timeout
- [ ] Model retraining pipeline not included

## 🔮 Future Enhancements

- [ ] Multi-location support with maps
- [ ] Automated data fetching from weather APIs
- [ ] Model retraining pipeline
- [ ] Email alerts for severe droughts
- [ ] Mobile app (React Native)

---

⭐ **Star this repo** if you find it helpful!

📫 **Questions?** Open an issue or contact me directly.
