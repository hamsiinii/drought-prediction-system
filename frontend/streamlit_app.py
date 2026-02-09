"""
Drought Analytics Dashboard - Streamlit Frontend
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="Drought Analytics Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .drought-extreme { background-color: #8B0000; color: white; }
    .drought-severe { background-color: #FF4500; color: white; }
    .drought-moderate { background-color: #FFA500; }
    .drought-mild { background-color: #FFD700; }
    .drought-none { background-color: #32CD32; color: white; }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🌊 Drought Analytics")
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "📊 Manual Prediction", "📁 Upload CSV", "📈 Analytics", "📜 History", "ℹ️ About"]
)

# Helper functions
def get_drought_color(category):
    """Return color based on drought category"""
    colors = {
        "No Drought": "#32CD32",
        "Mild Drought": "#FFD700",
        "Moderate Drought": "#FFA500",
        "Severe Drought": "#FF4500",
        "Extreme Drought": "#8B0000"
    }
    return colors.get(category, "#808080")

def create_gauge_chart(regcdi_value):
    """Create gauge chart for REGCDI value"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=regcdi_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "REGCDI Value", 'font': {'size': 24}},
        delta={'reference': 0},
        gauge={
            'axis': {'range': [-2, 2], 'tickwidth': 1},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [-2, -1], 'color': '#8B0000'},
                {'range': [-1, -0.5], 'color': '#FF4500'},
                {'range': [-0.5, 0], 'color': '#FFA500'},
                {'range': [0, 0.5], 'color': '#FFD700'},
                {'range': [0.5, 2], 'color': '#32CD32'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': regcdi_value
            }
        }
    ))
    
    fig.update_layout(height=300)
    return fig

# PAGE 1: HOME
if page == "🏠 Home":
    st.markdown('<h1 class="main-header">🌊 Drought Analytics Microservice</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ### Welcome to the Drought Insights & Analytics Platform
    
    This system uses **stat-LSTM deep learning** to predict drought conditions using:
    - 🌧️ Meteorological data (rainfall, temperature)
    - 📊 Drought indices (SPEI, SPI)
    - 🌱 Agricultural indicators (NDVI, soil moisture)
    
    **Prediction Output**: REGCDI (Regional Comprehensive Drought Index)
    """)
    
    # System health check
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("System Status", "🟢 Healthy" if health["status"] == "healthy" else "🔴 Down")
            with col2:
                st.metric("Model Status", "✅ Loaded" if health["model_loaded"] else "❌ Not Loaded")
            with col3:
                st.metric("Version", health["version"])
        else:
            st.error("⚠️ Backend API is not responding")
    except:
        st.warning("⚠️ Cannot connect to backend. Make sure the API is running.")
    
    # Quick stats
    try:
        summary = requests.get(f"{API_URL}/summary").json()
        
        st.markdown("### 📊 System Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Predictions", summary.get("total_predictions", 0))
        with col2:
            st.metric("Average REGCDI", f"{summary.get('average_regcdi', 0):.3f}")
        with col3:
            drought_dist = summary.get("drought_distribution", {})
            severe_count = drought_dist.get("severe", 0) + drought_dist.get("extreme", 0)
            st.metric("Severe/Extreme Events", severe_count)
        with col4:
            last_date = summary.get("last_prediction_date", "N/A")
            if last_date != "N/A":
                last_date = datetime.fromisoformat(last_date).strftime("%Y-%m-%d")
            st.metric("Last Prediction", last_date)
    except:
        pass

# PAGE 2: MANUAL PREDICTION
elif page == "📊 Manual Prediction":
    st.title("📊 Manual Drought Prediction")
    st.markdown("Enter 12 months of weather data to get drought prediction")
    
    # Feature descriptions
    with st.expander("ℹ️ Feature Descriptions"):
        st.markdown("""
        - **Rainfall (mm)**: Monthly cumulative rainfall
        - **Max Temp (°C)**: Maximum temperature
        - **Min Temp (°C)**: Minimum temperature
        - **SPEI**: Standardized Precipitation Evapotranspiration Index
        - **SPI**: Standardized Precipitation Index
        - **NDVI**: Normalized Difference Vegetation Index (0-1)
        - **Soil Moisture (%)**: Surface soil moisture percentage
        """)
    
    # Create input form
    st.markdown("### Enter Monthly Data (12 Months Required)")
    
    data_entries = []
    
    # Use tabs for better UX
    tabs = st.tabs([f"Month {i+1}" for i in range(12)])
    
    for i, tab in enumerate(tabs):
        with tab:
            col1, col2 = st.columns(2)
            
            with col1:
                rainfall = st.number_input(f"Rainfall (mm)", key=f"rain_{i}", value=85.0, min_value=0.0)
                tmax = st.number_input(f"Max Temp (°C)", key=f"tmax_{i}", value=32.0)
                tmin = st.number_input(f"Min Temp (°C)", key=f"tmin_{i}", value=18.0)
                spei = st.number_input(f"SPEI", key=f"spei_{i}", value=-0.5, min_value=-3.0, max_value=3.0)
            
            with col2:
                spi = st.number_input(f"SPI", key=f"spi_{i}", value=-0.3, min_value=-3.0, max_value=3.0)
                ndvi = st.number_input(f"NDVI", key=f"ndvi_{i}", value=0.65, min_value=0.0, max_value=1.0)
                soil = st.number_input(f"Soil Moisture (%)", key=f"soil_{i}", value=45.0, min_value=0.0, max_value=100.0)
            
            data_entries.append({
                "rainfall_mm": rainfall,
                "tmax_c": tmax,
                "tmin_c": tmin,
                "spei": spei,
                "spi": spi,
                "ndvi": ndvi,
                "soil_moisture": soil
            })
    
    # Location input
    location = st.text_input("Location (optional)", placeholder="e.g., Maharashtra")
    
    # Predict button
    if st.button("🔮 Predict Drought Conditions", type="primary"):
        with st.spinner("Making prediction..."):
            try:
                payload = {
                    "data": data_entries,
                    "location": location if location else None
                }
                
                response = requests.post(
                    f"{API_URL}/predict/manual",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    st.success("✅ Prediction Complete!")
                    
                    # Display results
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.markdown("### Prediction Results")
                        
                        category = result["drought_category"]
                        color = get_drought_color(category)
                        
                        st.markdown(f"""
                        <div style="background-color: {color}; padding: 1rem; border-radius: 0.5rem; text-align: center; color: white;">
                            <h2>{category}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.metric("REGCDI Value", f"{result['regcdi_value']:.3f}")
                        st.metric("Confidence Score", f"{result['confidence_score']:.2%}")
                        st.metric("Model Version", result["model_version"])
                    
                    with col2:
                        # Gauge chart
                        fig = create_gauge_chart(result["regcdi_value"])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Severity explanation
                    st.info(f"""
                    **Severity Level**: {result['severity_level'].upper()}
                    
                    This prediction indicates **{category.lower()}** conditions based on the analysis of 
                    12 months of meteorological and agricultural data.
                    """)
                    
                else:
                    st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
            
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

# PAGE 3: CSV UPLOAD
elif page == "📁 Upload CSV":
    st.title("📁 Upload CSV for Batch Predictions")
    
    st.markdown("""
    Upload a CSV file with historical weather data for batch drought predictions.
    
    **Required columns**: `rainfall_mm`, `tmax_c`, `tmin_c`, `spei`, `spi`, `ndvi`, `soil_moisture`
    
    The system will create predictions for every 12-month rolling window in your data.
    """)
    
    # Sample CSV download
    sample_data = pd.DataFrame({
        'rainfall_mm': [85.5, 92.3, 78.1, 65.2, 45.8, 32.1, 28.5, 35.2, 42.8, 55.3, 68.7, 82.4] * 3,
        'tmax_c': [32.4, 33.1, 34.2, 35.8, 36.5, 37.2, 36.8, 35.9, 34.5, 33.2, 32.1, 31.8] * 3,
        'tmin_c': [18.2, 19.5, 20.8, 22.1, 23.5, 24.2, 23.8, 22.9, 21.5, 20.2, 19.1, 18.5] * 3,
        'spei': [-0.5, -0.3, -0.2, -0.1, 0.1, 0.3, 0.2, 0.0, -0.2, -0.4, -0.5, -0.6] * 3,
        'spi': [-0.3, -0.2, 0.0, 0.1, 0.2, 0.3, 0.2, 0.1, -0.1, -0.3, -0.4, -0.5] * 3,
        'ndvi': [0.65, 0.68, 0.72, 0.75, 0.73, 0.70, 0.68, 0.66, 0.64, 0.62, 0.63, 0.65] * 3,
        'soil_moisture': [45.0, 48.2, 52.1, 55.3, 53.8, 50.2, 47.5, 45.8, 43.2, 42.5, 43.8, 45.2] * 3
    })
    
    st.download_button(
        label="📥 Download Sample CSV",
        data=sample_data.to_csv(index=False),
        file_name="sample_drought_data.csv",
        mime="text/csv"
    )
    
    # File upload
    uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
    
    if uploaded_file is not None:
        # Preview data
        df = pd.read_csv(uploaded_file)
        st.markdown("### Data Preview")
        st.dataframe(df.head(20), use_container_width=True)
        
        st.markdown(f"**Total rows**: {len(df)}")
        st.markdown(f"**Possible predictions**: {max(0, len(df) - 11)} (12-month windows)")
        
        # Upload button
        if st.button("🚀 Upload and Predict", type="primary"):
            with st.spinner("Processing... This may take a minute..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    response = requests.post(
                        f"{API_URL}/data",
                        files=files,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        st.success(f"✅ Successfully processed {result['total_predictions']} predictions!")
                        
                        # Display predictions
                        predictions = result['predictions']
                        pred_df = pd.DataFrame(predictions)
                        
                        st.markdown("### Prediction Results")
                        st.dataframe(pred_df, use_container_width=True)
                        
                        # Download results
                        st.download_button(
                            label="📥 Download Results",
                            data=pred_df.to_csv(index=False),
                            file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                        
                        # Visualization
                        st.markdown("### Prediction Timeline")
                        fig = px.line(
                            pred_df,
                            x=pred_df.index,
                            y='regcdi_value',
                            title='REGCDI Values Over Time',
                            labels={'x': 'Window Index', 'regcdi_value': 'REGCDI Value'}
                        )
                        fig.add_hline(y=0, line_dash="dash", line_color="gray")
                        st.plotly_chart(fig, use_container_width=True)
                        
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Upload failed')}")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# PAGE 4: ANALYTICS
elif page == "📈 Analytics":
    st.title("📈 System Analytics")
    
    try:
        # Get summary stats
        summary = requests.get(f"{API_URL}/summary").json()
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Predictions", summary.get("total_predictions", 0))
        with col2:
            st.metric("Avg REGCDI", f"{summary.get('average_regcdi', 0):.3f}")
        with col3:
            last_date = summary.get("last_prediction_date", "N/A")
            if last_date != "N/A":
                last_date = datetime.fromisoformat(last_date).strftime("%m/%d")
            st.metric("Last Prediction", last_date)
        with col4:
            drought_dist = summary.get("drought_distribution", {})
            total_drought = sum(v for k, v in drought_dist.items() if k != "no_drought")
            st.metric("Drought Events", total_drought)
        
        # Drought distribution
        st.markdown("### Drought Category Distribution")
        
        if summary.get("drought_distribution"):
            dist = summary["drought_distribution"]
            
            # Pie chart
            labels = [k.replace("_", " ").title() for k in dist.keys()]
            values = list(dist.values())
            colors = ['#32CD32', '#FFD700', '#FFA500', '#FF4500', '#8B0000']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors[:len(labels)])
            )])
            fig.update_layout(title="Drought Severity Distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No predictions yet. Start by uploading data or making manual predictions.")
            
    except Exception as e:
        st.error(f"Could not load analytics: {str(e)}")

# PAGE 5: HISTORY
elif page == "📜 History":
    st.title("📜 Prediction History")
    
    # Pagination
    page_size = st.selectbox("Results per page", [10, 25, 50, 100], index=1)
    page_num = st.number_input("Page", min_value=1, value=1)
    
    try:
        skip = (page_num - 1) * page_size
        response = requests.get(f"{API_URL}/history?skip={skip}&limit={page_size}")
        
        if response.status_code == 200:
            data = response.json()
            history = data["history"]
            
            if history:
                st.markdown(f"**Showing {len(history)} results**")
                
                # Display as cards
                for item in history:
                    with st.expander(f"🔍 {item['drought_category']} - {item.get('location', 'Unknown')} - {item['created_at'][:10]}"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("REGCDI", f"{item['regcdi_value']:.3f}")
                        with col2:
                            st.metric("Confidence", f"{item['confidence_score']:.2%}")
                        with col3:
                            st.metric("Type", item['prediction_type'].title())
                        
                        st.markdown(f"**Category**: {item['drought_category']}")
                        st.markdown(f"**Model**: {item.get('model_version', 'N/A')}")
            else:
                st.info("No prediction history found.")
        else:
            st.error("Could not load history")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

# PAGE 6: ABOUT
elif page == "ℹ️ About":
    st.title("ℹ️ About This System")
    
    st.markdown("""
    ## Drought Insights & Analytics Microservice
    
    ### 🎯 Project Overview
    This system provides real-time drought prediction and analytics using advanced machine learning techniques.
    
    ### 🧠 Technology Stack
    - **Backend**: FastAPI (Python)
    - **ML Model**: stat-LSTM (Stateful LSTM Neural Network)
    - **Databases**: MongoDB (NoSQL) + PostgreSQL (Relational)
    - **Frontend**: Streamlit
    - **Deployment**: Render / Docker
    
    ### 📊 Model Architecture
    - **Input**: 12 months × 7 features (rolling window)
    - **Output**: REGCDI (Regional Comprehensive Drought Index)
    - **Features Used**:
      - Rainfall (mm)
      - Max/Min Temperature (°C)
      - SPEI (Standardized Precipitation Evapotranspiration Index)
      - SPI (Standardized Precipitation Index)
      - NDVI (Normalized Difference Vegetation Index)
      - Soil Moisture (%)
    
    ### 🌟 Key Features
    - ✅ Manual single predictions
    - ✅ Batch CSV processing
    - ✅ Real-time analytics dashboard
    - ✅ Prediction history tracking
    - ✅ RESTful API endpoints
    - ✅ Persistent data storage
    
    ### 📈 Drought Categories
    | REGCDI Range | Category |
    |--------------|----------|
    | ≥ 0.5 | No Drought |
    | 0.0 to 0.5 | Mild Drought |
    | -0.5 to 0.0 | Moderate Drought |
    | -1.0 to -0.5 | Severe Drought |
    | < -1.0 | Extreme Drought |
    
    ### 🔗 API Endpoints
    - `GET /health` - System health check
    - `POST /predict/manual` - Single prediction
    - `POST /data` - Upload CSV for batch predictions
    - `GET /forecast` - Recent forecasts
    - `GET /summary` - System statistics
    - `GET /history` - Prediction history
    
    ### 👨‍💻 Developer
    **Your Name** | [GitHub](https://github.com/yourusername) | [LinkedIn](https://linkedin.com/in/yourprofile)
    
    ### 📄 License
    MIT License - Open Source
    
    ---
    
    **Version**: 1.0.0  
    **Last Updated**: January 2025
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.info("""
**Drought Analytics v1.0**

Built with ❤️ using FastAPI + Streamlit

[📚 Documentation](#) | [🐛 Report Issue](#)
""")