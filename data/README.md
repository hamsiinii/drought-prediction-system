# Dataset Information

## Vidarbha Drought Dataset

This folder contains sample data from the **Vidarbha region** (Maharashtra, India) used for drought prediction model training and testing.

### Dataset Overview

- **Region**: Vidarbha, Maharashtra, India
- **Time Period**: [Add your date range, e.g., 2010-2023]
- **Frequency**: Monthly observations
- **Total Records**: [Number of rows in your CSV]
- **Source**: Google Earth Engine (GEE), IMD, NOAA

### Features

| Column Name     | Description                                         | Unit       | Range    |
| --------------- | --------------------------------------------------- | ---------- | -------- |
| `date`          | Observation date                                    | YYYY-MM-DD | -        |
| `rainfall_mm`   | Monthly cumulative rainfall                         | mm         | 0-500+   |
| `tmax_c`        | Maximum temperature                                 | °C         | 20-45    |
| `tmin_c`        | Minimum temperature                                 | °C         | 10-30    |
| `spei`          | Standardized Precipitation Evapotranspiration Index | index      | -3 to +3 |
| `spi`           | Standardized Precipitation Index                    | index      | -3 to +3 |
| `ndvi`          | Normalized Difference Vegetation Index              | index      | 0-1      |
| `soil_moisture` | Surface soil moisture                               | %          | 0-100    |

### Files

- **`vidarbha_drought_data.csv`** - Full dataset used for model training
- **`vidarbha_sample.csv`** - Sample subset (200 rows) for quick testing
- **`sample_input.json`** - Example API request format

### Usage

#### For CSV Upload (Dashboard)

1. Go to "📁 Upload CSV" page in dashboard
2. Upload `vidarbha_sample.csv`
3. System will generate predictions for all 12-month windows

#### For API Testing

```bash
# Upload CSV via API
curl -X POST http://localhost:8000/data \
  -F "file=@vidarbha_sample.csv"
```

### Data Quality

- ✅ No missing values (preprocessed)
- ✅ Outliers handled using IQR method
- ✅ Features normalized using StandardScaler
- ✅ Time-series validated for continuity

### Citation

If you use this dataset, please cite:

```
Vidarbha Drought Dataset (2010-2023)
Data Sources: Google Earth Engine, India Meteorological Department
Preprocessed for stat-LSTM drought prediction model
```

### Notes

- This is **real data** from the drought-prone Vidarbha region
- Data has been preprocessed and cleaned
- Original raw data available in `notebooks/` folder
- For full dataset access, contact: [your.email@example.com]
