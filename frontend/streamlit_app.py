"""
Drought Analytics Dashboard - Upgraded Streamlit Frontend
DynamoDB-backed | Real predictions | Severity map | Live graphs
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import boto3
from decimal import Decimal
import os

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Drought Analytics",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "http://localhost:8000")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
DYNAMO_TABLE = "drought_predictions"

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    .main { background: #0a0f1e; }
    .block-container { padding-top: 1.5rem; }

    .dash-header {
        font-family: 'Space Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -1px;
        background: linear-gradient(90deg, #00d4ff, #0066ff, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding: 0.5rem 0;
    }
    .kpi-box {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.4rem;
        font-family: 'Space Mono', monospace;
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #f9fafb;
        font-family: 'Space Mono', monospace;
    }
    .severity-extreme { color: #ef4444 !important; }
    .severity-severe  { color: #f97316 !important; }
    .severity-moderate{ color: #eab308 !important; }
    .severity-mild    { color: #84cc16 !important; }
    .severity-none    { color: #22c55e !important; }

    .pred-card {
        background: #111827;
        border-radius: 12px;
        border: 1px solid #1f2937;
        padding: 1rem 1.4rem;
        margin-bottom: 0.6rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #0066ff, #7c3aed);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.4rem;
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
DROUGHT_COLORS = {
    "No Drought":       "#22c55e",
    "Mild Drought":     "#84cc16",
    "Moderate Drought": "#eab308",
    "Severe Drought":   "#f97316",
    "Extreme Drought":  "#ef4444",
}

def category_color(cat):
    return DROUGHT_COLORS.get(cat, "#6b7280")

def severity_css(cat):
    mapping = {
        "No Drought": "none",
        "Mild Drought": "mild",
        "Moderate Drought": "moderate",
        "Severe Drought": "severe",
        "Extreme Drought": "extreme",
    }
    return mapping.get(cat, "none")


def gauge_chart(value, title="REGCDI"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 36, "color": "#f9fafb", "family": "Space Mono"}},
        title={"text": title, "font": {"size": 14, "color": "#9ca3af", "family": "Space Mono"}},
        gauge={
            "axis": {"range": [-2, 2], "tickcolor": "#6b7280", "tickfont": {"color": "#9ca3af"}},
            "bar": {"color": "#0066ff", "thickness": 0.25},
            "bgcolor": "#1f2937",
            "bordercolor": "#374151",
            "steps": [
                {"range": [-2,   -1],  "color": "#7f1d1d"},
                {"range": [-1,  -0.5], "color": "#9a3412"},
                {"range": [-0.5, 0.0], "color": "#78350f"},
                {"range": [0.0,  0.5], "color": "#365314"},
                {"range": [0.5,  2.0], "color": "#14532d"},
            ],
        }
    ))
    fig.update_layout(
        height=260,
        paper_bgcolor="#0a0f1e",
        plot_bgcolor="#0a0f1e",
        margin=dict(t=40, b=10, l=20, r=20),
        font={"color": "#f9fafb"}
    )
    return fig


def health_check():
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def get_summary():
    try:
        r = requests.get(f"{API_URL}/summary", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}


def get_history(skip=0, limit=50):
    try:
        r = requests.get(f"{API_URL}/history?skip={skip}&limit={limit}", timeout=5)
        return r.json() if r.status_code == 200 else {"history": [], "total": 0}
    except:
        return {"history": [], "total": 0}


# ── DynamoDB direct read (for richer table display) ───────────────────────────
@st.cache_data(ttl=30)
def fetch_dynamo_history(limit=200):
    """Pull raw records from DynamoDB for dashboard display"""
    try:
        dynamo = boto3.resource(
            "dynamodb",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
        )
        table = dynamo.Table(DYNAMO_TABLE)
        resp = table.scan(Limit=limit)
        items = resp.get("Items", [])

        # Convert Decimal
        def conv(o):
            if isinstance(o, Decimal): return float(o)
            if isinstance(o, dict): return {k: conv(v) for k, v in o.items()}
            if isinstance(o, list): return [conv(i) for i in o]
            return o

        items = [conv(i) for i in items]
        for i in items:
            i["regcdi_value"]    = float(i.get("regcdi_value", 0))
            i["confidence_score"] = float(i.get("confidence_score", 0))

        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items
    except Exception as e:
        return []


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown('<div class="dash-header">🌊 DROUGHT<br>ANALYTICS</div>', unsafe_allow_html=True)
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["🏠 Dashboard", "🔮 Predict", "📁 Upload CSV", "📋 DynamoDB Table", "🗺️ Severity Map", "ℹ️ About"],
    label_visibility="collapsed"
)

health = health_check()
if health:
    st.sidebar.success(f"✅ API Online — Model {'loaded' if health.get('model_loaded') else 'not loaded'}")
else:
    st.sidebar.error("❌ API Offline")

st.sidebar.markdown("---")
st.sidebar.caption(f"Region: `{AWS_REGION}` | Table: `{DYNAMO_TABLE}`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<div class="dash-header">🌊 Drought Intelligence Platform</div>', unsafe_allow_html=True)
    st.caption("stat-LSTM · REGCDI · DynamoDB · ap-south-1")
    st.markdown("---")

    summary = get_summary()
    total   = summary.get("total_predictions", 0)
    avg_reg = summary.get("average_regcdi", 0.0)
    dist    = summary.get("drought_distribution", {})
    severe  = dist.get("severe_drought", 0) + dist.get("extreme_drought", 0)
    last_dt = summary.get("last_prediction_date", "N/A")
    if last_dt != "N/A":
        try: last_dt = datetime.fromisoformat(last_dt).strftime("%d %b %Y")
        except: pass

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value in [
        (c1, "TOTAL PREDICTIONS", total),
        (c2, "AVG REGCDI",        f"{avg_reg:.3f}"),
        (c3, "SEVERE / EXTREME",  severe),
        (c4, "LAST PREDICTION",   last_dt),
    ]:
        col.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Drought Distribution")
        if dist:
            labels = [k.replace("_", " ").title() for k in dist]
            values = list(dist.values())
            colors = [category_color(l) for l in labels]
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors, line=dict(color="#0a0f1e", width=2)),
                hole=0.55,
                textfont=dict(family="Space Mono", size=11, color="white"),
            ))
            fig.update_layout(
                paper_bgcolor="#0a0f1e", plot_bgcolor="#0a0f1e",
                font=dict(color="#9ca3af"),
                showlegend=True,
                legend=dict(font=dict(size=11, color="#d1d5db")),
                height=280, margin=dict(t=10, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No predictions yet. Run a prediction to see data here.")

    with col_right:
        st.markdown("#### REGCDI Trend")
        dynamo_items = fetch_dynamo_history(50)
        if dynamo_items:
            df_trend = pd.DataFrame(dynamo_items)[["created_at", "regcdi_value", "drought_category"]].head(30)
            df_trend = df_trend.sort_values("created_at")
            df_trend["ts"] = df_trend["created_at"].str[:16]

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_trend["ts"], y=df_trend["regcdi_value"],
                mode="lines+markers",
                line=dict(color="#0066ff", width=2),
                marker=dict(
                    color=[category_color(c) for c in df_trend["drought_category"]],
                    size=8, line=dict(color="#0a0f1e", width=1)
                ),
                hovertemplate="<b>%{x}</b><br>REGCDI: %{y:.3f}<extra></extra>"
            ))
            fig2.add_hline(y=0, line_dash="dot", line_color="#4b5563")
            fig2.update_layout(
                paper_bgcolor="#0a0f1e", plot_bgcolor="#111827",
                xaxis=dict(tickfont=dict(size=9, color="#6b7280"), gridcolor="#1f2937", showgrid=True),
                yaxis=dict(tickfont=dict(size=10, color="#9ca3af"), gridcolor="#1f2937"),
                height=280, margin=dict(t=10, b=30, l=40, r=10),
                font=dict(color="#9ca3af")
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No trend data yet.")

    # Recent 5 predictions
    st.markdown("#### Recent Predictions")
    if dynamo_items:
        for item in dynamo_items[:5]:
            cat   = item.get("drought_category", "Unknown")
            loc   = item.get("location", "Unknown")
            reg   = item.get("regcdi_value", 0)
            ts    = item.get("created_at", "")[:16]
            conf  = item.get("confidence_score", 0)
            css   = severity_css(cat)
            color = category_color(cat)
            st.markdown(f"""
            <div class="pred-card">
                <span style="font-family:Space Mono;font-size:0.8rem;color:#6b7280;">{ts}</span>
                &nbsp;&nbsp;
                <span class="severity-{css}" style="font-weight:700;">{cat}</span>
                &nbsp;·&nbsp;
                <span style="color:#d1d5db;">REGCDI: <b>{reg:.3f}</b></span>
                &nbsp;·&nbsp;
                <span style="color:#9ca3af;">📍 {loc}</span>
                &nbsp;·&nbsp;
                <span style="color:#6b7280;font-size:0.8rem;">conf: {conf:.0%}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No predictions yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — PREDICT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Predict":
    st.markdown('<div class="dash-header">🔮 Manual Prediction</div>', unsafe_allow_html=True)
    st.caption("Enter 12 months of climate data to generate a REGCDI forecast")
    st.markdown("---")

    with st.expander("ℹ️ Feature reference — Vidarbha GEE data"):
        st.markdown("""
        | Feature | Range | Description |
        |---|---|---|
        | EVI | 1100–5200 | Enhanced Vegetation Index (GEE pixel sum) |
        | LST | 26–50 °C | Land Surface Temperature day |
        | LST Night | 12–29 °C | Land Surface Temperature night |
        | Rainfall | 0–18 mm | Monthly rainfall |
        | Soil Moisture | 0.20–0.46 | Soil moisture fraction |
        | SPI | −3 to 3 | Standardized Precipitation Index |
        | PET | 70–262 mm | Potential Evapotranspiration |
        | SPEI | −7.5 to 1.2 | Standardized Precip Evapotranspiration Index |
        | NDVI_min/max | 1900–7348 | NDVI pixel sum reference range |
        | VCI/TCI/SMCI/VHI | 0–100 % | Condition indices |
        | SIWSI | 0.16–0.74 | Shortwave Infrared Water Stress Index |
        """)

    location = st.text_input("📍 Location", placeholder="e.g., Vidarbha, Amravati, Nagpur")

    # Vidarbha realistic defaults from dataset means
    defaults = dict(
        EVI=2757.0, LST=35.3, LST_Night=21.3, Rainfall=3.4,
        Soil_Moisture=0.30, SPI=-0.01, PET=176.8, SPEI=-0.16,
        NDVI_min=2234.0, NDVI_max=7041.0, VCI=48.3,
        LST_min=27.6, LST_max=48.6, TCI=63.0,
        SM_min=0.20, SM_max=0.45, SMCI=37.6, VHI=55.7, SIWSI=0.45
    )

    data_entries = []
    tabs = st.tabs([f"Month {i+1}" for i in range(12)])

    for i, tab in enumerate(tabs):
        with tab:
            c1, c2, c3 = st.columns(3)
            with c1:
                evi      = st.number_input("EVI",           value=defaults["EVI"],          key=f"evi{i}")
                lst      = st.number_input("LST °C",         value=defaults["LST"],          key=f"lst{i}")
                lst_n    = st.number_input("LST Night °C",   value=defaults["LST_Night"],    key=f"lstn{i}")
                rain     = st.number_input("Rainfall mm",    value=defaults["Rainfall"],     key=f"rain{i}")
                soil     = st.number_input("Soil Moisture",  value=defaults["Soil_Moisture"],key=f"soil{i}", format="%.4f")
                spi      = st.number_input("SPI",            value=defaults["SPI"],          key=f"spi{i}",  format="%.4f")
                pet      = st.number_input("PET mm",         value=defaults["PET"],          key=f"pet{i}")
            with c2:
                spei     = st.number_input("SPEI",           value=defaults["SPEI"],         key=f"spei{i}", format="%.4f")
                ndvi_min = st.number_input("NDVI_min",       value=defaults["NDVI_min"],     key=f"nmin{i}")
                ndvi_max = st.number_input("NDVI_max",       value=defaults["NDVI_max"],     key=f"nmax{i}")
                vci      = st.number_input("VCI %",          value=defaults["VCI"],          key=f"vci{i}")
                lst_min  = st.number_input("LST_min °C",     value=defaults["LST_min"],      key=f"lmin{i}")
                lst_max  = st.number_input("LST_max °C",     value=defaults["LST_max"],      key=f"lmax{i}")
            with c3:
                tci      = st.number_input("TCI %",          value=defaults["TCI"],          key=f"tci{i}")
                sm_min   = st.number_input("SM_min",         value=defaults["SM_min"],       key=f"smn{i}",  format="%.4f")
                sm_max   = st.number_input("SM_max",         value=defaults["SM_max"],       key=f"smx{i}",  format="%.4f")
                smci     = st.number_input("SMCI %",         value=defaults["SMCI"],         key=f"smci{i}")
                vhi      = st.number_input("VHI %",          value=defaults["VHI"],          key=f"vhi{i}")
                siwsi    = st.number_input("SIWSI",          value=defaults["SIWSI"],        key=f"siwsi{i}", format="%.4f")

            data_entries.append({
                "EVI": evi, "LST": lst, "LST_Night": lst_n,
                "Rainfall": rain, "Soil_Moisture": soil,
                "SPI": spi, "PET": pet, "SPEI": spei,
                "NDVI_min": ndvi_min, "NDVI_max": ndvi_max, "VCI": vci,
                "LST_min": lst_min, "LST_max": lst_max, "TCI": tci,
                "SM_min": sm_min, "SM_max": sm_max, "SMCI": smci,
                "VHI": vhi, "SIWSI": siwsi
            })

    if st.button("🔮 Run Prediction", type="primary"):
        with st.spinner("Running stat-LSTM inference..."):
            try:
                payload = {"data": data_entries, "location": location or None}
                resp = requests.post(f"{API_URL}/predict/manual", json=payload, timeout=30)

                if resp.status_code == 200:
                    result = resp.json()
                    st.success("✅ Prediction complete — saved to DynamoDB")

                    col1, col2 = st.columns([1, 1])

                    with col1:
                        cat   = result["drought_category"]
                        color = category_color(cat)
                        reg   = result["regcdi_value"]
                        conf  = result["confidence_score"]

                        st.markdown(f"""
                        <div style="background:{color};padding:1.5rem;border-radius:12px;text-align:center;margin-bottom:1rem;">
                            <div style="font-family:Space Mono;font-size:1.5rem;font-weight:700;color:white;">{cat}</div>
                            <div style="color:rgba(255,255,255,0.8);font-size:0.9rem;">REGCDI: {reg:.3f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.metric("REGCDI Value",      f"{reg:.4f}")
                        st.metric("Confidence Score",  f"{conf:.2%}")
                        st.metric("Severity Level",    result.get("severity_level", "—").upper())
                        st.metric("Model Version",     result.get("model_version", "1.0.0"))

                    with col2:
                        st.plotly_chart(gauge_chart(reg), use_container_width=True)

                    # Input radar
                    avg_inputs = {k: sum(d[k] for d in data_entries) / 12 for k in data_entries[0]}
                    radar_fig = go.Figure(go.Scatterpolar(
                        r=[
                            avg_inputs["Rainfall"] / 18,
                            avg_inputs["VCI"] / 100,
                            (avg_inputs["SPEI"] + 7.5) / 8.7,
                            avg_inputs["VHI"] / 100,
                            avg_inputs["Soil_Moisture"] / 0.46,
                        ],
                        theta=["Rainfall", "VCI", "SPEI", "VHI", "Soil Moisture"],
                        fill="toself",
                        line_color="#0066ff",
                        fillcolor="rgba(0,102,255,0.2)"
                    ))
                    radar_fig.update_layout(
                        polar=dict(
                            bgcolor="#111827",
                            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#374151", tickfont=dict(color="#6b7280")),
                            angularaxis=dict(tickfont=dict(color="#d1d5db", size=11)),
                        ),
                        paper_bgcolor="#0a0f1e",
                        height=280,
                        title=dict(text="Avg Input Profile", font=dict(color="#9ca3af", size=12)),
                        margin=dict(t=40, b=20)
                    )
                    st.plotly_chart(radar_fig, use_container_width=True)

                else:
                    st.error(f"API Error: {resp.json().get('detail', 'Unknown')}")

            except Exception as e:
                st.error(f"Connection error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — UPLOAD CSV
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📁 Upload CSV":
    st.markdown('<div class="dash-header">📁 Batch Upload</div>', unsafe_allow_html=True)
    st.caption("Upload CSV → batch REGCDI predictions → saved to DynamoDB")
    st.markdown("---")

    sample_df = pd.DataFrame({
        "rainfall_mm":   [85.5, 92.3, 78.1, 65.2, 45.8, 32.1, 28.5, 35.2, 42.8, 55.3, 68.7, 82.4],
        "tmax_c":        [32.4, 33.1, 34.2, 35.8, 36.5, 37.2, 36.8, 35.9, 34.5, 33.2, 32.1, 31.8],
        "tmin_c":        [18.2, 19.5, 20.8, 22.1, 23.5, 24.2, 23.8, 22.9, 21.5, 20.2, 19.1, 18.5],
        "spei":          [-0.5,-0.3,-0.2,-0.1, 0.1, 0.3, 0.2, 0.0,-0.2,-0.4,-0.5,-0.6],
        "spi":           [-0.3,-0.2, 0.0, 0.1, 0.2, 0.3, 0.2, 0.1,-0.1,-0.3,-0.4,-0.5],
        "ndvi":          [0.65,0.68,0.72,0.75,0.73,0.70,0.68,0.66,0.64,0.62,0.63,0.65],
        "soil_moisture": [45.0,48.2,52.1,55.3,53.8,50.2,47.5,45.8,43.2,42.5,43.8,45.2],
    })
    st.download_button("📥 Download sample CSV", sample_df.to_csv(index=False), "sample.csv", "text/csv")

    uploaded = st.file_uploader("Choose CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head(15), use_container_width=True)
        st.caption(f"{len(df)} rows · {max(0, len(df)-11)} possible prediction windows")

        if st.button("🚀 Upload & Predict", type="primary"):
            with st.spinner("Processing..."):
                try:
                    files = {"file": (uploaded.name, uploaded.getvalue(), "text/csv")}
                    resp  = requests.post(f"{API_URL}/data", files=files, timeout=120)

                    if resp.status_code == 200:
                        result = resp.json()
                        preds  = result["predictions"]
                        st.success(f"✅ {result['total_predictions']} predictions — saved to DynamoDB")

                        pred_df = pd.DataFrame(preds)
                        st.dataframe(pred_df, use_container_width=True)

                        if "regcdi_value" in pred_df.columns:
                            fig = px.line(
                                pred_df, y="regcdi_value",
                                title="REGCDI Over Batch Windows",
                                color_discrete_sequence=["#0066ff"]
                            )
                            fig.add_hline(y=0, line_dash="dot", line_color="#4b5563")
                            fig.update_layout(
                                paper_bgcolor="#0a0f1e", plot_bgcolor="#111827",
                                font=dict(color="#9ca3af"), height=320,
                                xaxis=dict(gridcolor="#1f2937"),
                                yaxis=dict(gridcolor="#1f2937"),
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        st.download_button("📥 Download results", pred_df.to_csv(index=False), "predictions.csv", "text/csv")
                    else:
                        st.error(f"Error: {resp.json().get('detail','Failed')}")
                except Exception as e:
                    st.error(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — DYNAMODB TABLE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 DynamoDB Table":
    st.markdown('<div class="dash-header">📋 DynamoDB Records</div>', unsafe_allow_html=True)
    st.caption(f"Live data from `{DYNAMO_TABLE}` · region: `{AWS_REGION}`")
    st.markdown("---")

    col_refresh, col_filter, _ = st.columns([1, 2, 3])
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
    with col_filter:
        category_filter = st.selectbox(
            "Filter by category",
            ["All", "No Drought", "Mild Drought", "Moderate Drought", "Severe Drought", "Extreme Drought"]
        )

    items = fetch_dynamo_history(200)

    if items:
        df_dyn = pd.DataFrame(items)

        # Keep only relevant columns
        cols = ["created_at", "location", "drought_category", "regcdi_value", "confidence_score", "prediction_type", "model_version"]
        cols = [c for c in cols if c in df_dyn.columns]
        df_dyn = df_dyn[cols].copy()

        if category_filter != "All":
            df_dyn = df_dyn[df_dyn["drought_category"] == category_filter]

        df_dyn["created_at"]      = df_dyn["created_at"].str[:16]
        df_dyn["regcdi_value"]    = df_dyn["regcdi_value"].apply(lambda x: f"{x:.4f}")
        df_dyn["confidence_score"] = df_dyn["confidence_score"].apply(lambda x: f"{float(x):.1%}")

        df_dyn.columns = ["Timestamp", "Location", "Category", "REGCDI", "Confidence", "Type", "Model"][:len(df_dyn.columns)]

        st.dataframe(
            df_dyn,
            use_container_width=True,
            height=420,
        )

        st.caption(f"Showing {len(df_dyn)} records")

        # Stats bar
        raw = fetch_dynamo_history(200)
        if raw:
            vals = [i["regcdi_value"] for i in raw]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total records", len(raw))
            c2.metric("Min REGCDI",   f"{min(vals):.3f}")
            c3.metric("Max REGCDI",   f"{max(vals):.3f}")
            c4.metric("Avg REGCDI",   f"{sum(vals)/len(vals):.3f}")

    else:
        st.info("No records found in DynamoDB yet. Run a prediction first!")
        st.markdown("""
        **Setup checklist:**
        - ✅ Set `AWS_ACCESS_KEY_ID` env variable
        - ✅ Set `AWS_SECRET_ACCESS_KEY` env variable
        - ✅ Set `AWS_REGION=ap-south-1`
        - ✅ IAM user has DynamoDB read/write permissions
        """)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — SEVERITY MAP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Severity Map":
    st.markdown('<div class="dash-header">🗺️ Drought Severity Map</div>', unsafe_allow_html=True)
    st.caption("Geographic distribution of drought predictions by location")
    st.markdown("---")

    items = fetch_dynamo_history(500)

    # Indian cities lat/lon lookup
    CITY_COORDS = {
        "chennai":      (13.0827, 80.2707),
        "mumbai":       (19.0760, 72.8777),
        "delhi":        (28.6139, 77.2090),
        "bangalore":    (12.9716, 77.5946),
        "bengaluru":    (12.9716, 77.5946),
        "hyderabad":    (17.3850, 78.4867),
        "kolkata":      (22.5726, 88.3639),
        "pune":         (18.5204, 73.8567),
        "ahmedabad":    (23.0225, 72.5714),
        "jaipur":       (26.9124, 75.7873),
        "maharashtra":  (19.7515, 75.7139),
        "rajasthan":    (27.0238, 74.2179),
        "gujarat":      (22.2587, 71.1924),
        "karnataka":    (15.3173, 75.7139),
        "kerala":       (10.8505, 76.2711),
        "tamilnadu":    (11.1271, 78.6569),
        "tamil nadu":   (11.1271, 78.6569),
        "andhra pradesh":(15.9129, 79.7400),
        "telangana":    (18.1124, 79.0193),
        "odisha":       (20.9517, 85.0985),
    }

    map_data = []
    for item in items:
        loc = item.get("location", "").lower().strip()
        coords = CITY_COORDS.get(loc)
        if coords:
            map_data.append({
                "location": item.get("location"),
                "lat": coords[0],
                "lon": coords[1],
                "regcdi_value": item.get("regcdi_value", 0),
                "drought_category": item.get("drought_category", "Unknown"),
                "created_at": item.get("created_at", "")[:16],
            })

    if map_data:
        df_map = pd.DataFrame(map_data)

        fig = px.scatter_mapbox(
            df_map,
            lat="lat", lon="lon",
            color="drought_category",
            size=[max(0.1, abs(v) + 0.3) for v in df_map["regcdi_value"]],
            hover_name="location",
            hover_data={"regcdi_value": ":.3f", "created_at": True, "lat": False, "lon": False},
            color_discrete_map=DROUGHT_COLORS,
            zoom=4.5,
            center={"lat": 20.5937, "lon": 78.9629},
            mapbox_style="carto-darkmatter",
            title="Drought Predictions by Location",
            height=520,
        )
        fig.update_layout(
            paper_bgcolor="#0a0f1e",
            font=dict(color="#d1d5db"),
            legend=dict(title="Category", font=dict(size=11)),
            margin=dict(t=40, b=0, l=0, r=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Location Summary")
        loc_summary = df_map.groupby("location").agg(
            predictions=("regcdi_value", "count"),
            avg_regcdi=("regcdi_value", "mean"),
            latest=("created_at", "max"),
        ).reset_index()
        loc_summary["avg_regcdi"] = loc_summary["avg_regcdi"].round(3)
        st.dataframe(loc_summary, use_container_width=True)

    else:
        st.info("No location data on map yet.")
        st.markdown("""
        To see predictions on the map, **enter a recognized location** when running a manual prediction.

        **Supported locations** (case-insensitive): Chennai, Mumbai, Delhi, Bangalore, Hyderabad,
        Kolkata, Pune, Ahmedabad, Jaipur, Maharashtra, Rajasthan, Gujarat, Karnataka, Kerala,
        Tamil Nadu, Andhra Pradesh, Telangana, Odisha.
        """)
        # Still show a blank India map
        fig = go.Figure(go.Scattermapbox())
        fig.update_layout(
            mapbox=dict(style="carto-darkmatter", center=dict(lat=20.5, lon=79), zoom=4.2),
            paper_bgcolor="#0a0f1e", height=400,
            margin=dict(t=0, b=0, l=0, r=0),
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — ABOUT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "ℹ️ About":
    st.markdown('<div class="dash-header">ℹ️ About</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("""
    ## Drought Insights & Analytics Platform

    ### Stack
    - **ML Model**: stat-LSTM · outputs REGCDI
    - **Backend**: FastAPI (Python)
    - **Frontend**: Streamlit
    - **Storage**: AWS DynamoDB (`ap-south-1`)
    - **Model files**: S3 (antigravity bucket)

    ### REGCDI Scale
    | Range | Category |
    |---|---|
    | ≥ 0.5 | ✅ No Drought |
    | 0.0–0.5 | 🟡 Mild Drought |
    | −0.5–0.0 | 🟠 Moderate Drought |
    | −1.0– −0.5 | 🔴 Severe Drought |
    | < −1.0 | ⚫ Extreme Drought |

    ### API Endpoints
    | Endpoint | Method | Purpose |
    |---|---|---|
    | `/health` | GET | Status check |
    | `/predict/manual` | POST | Single prediction |
    | `/data` | POST | Batch CSV |
    | `/forecast` | GET | Recent forecasts |
    | `/summary` | GET | Stats |
    | `/history` | GET | Paginated history |

    ### AWS Setup
    ```bash
    export AWS_ACCESS_KEY_ID=your_key
    export AWS_SECRET_ACCESS_KEY=your_secret
    export AWS_REGION=ap-south-1
    ```
    DynamoDB table `drought_predictions` is **auto-created** on first run.
    """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("Drought Analytics v2.0 · AWS DynamoDB · ap-south-1")