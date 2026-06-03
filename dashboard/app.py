import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

API_BASE = "http://127.0.0.1:8000/api/v1"

st.set_page_config(
    page_title="Purplle Store Intelligence",
    page_icon="🛍️",
    layout="wide"
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🛍️ Store Intelligence")
st.sidebar.markdown("**Purplle Tech Challenge 2026**")

store_options = {"All Stores": None, "Store 1 (ST1008)": "ST1008", "Store 2 (ST1076)": "ST1076"}
selected_label = st.sidebar.selectbox("Select Store", list(store_options.keys()))
store_id = store_options[selected_label]

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Pipeline Status**")
try:
    r = requests.get("http://127.0.0.1:8000/health", timeout=2)
    if r.status_code == 200:
        st.sidebar.success("API: Online")
except:
    st.sidebar.error("API: Offline")

# ── Helper ────────────────────────────────────────────────────────────────────
def fetch(endpoint, params={}):
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=5)
        return r.json()
    except:
        return None

params = {"store_id": store_id} if store_id else {}

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("🛍️ Purplle Store Intelligence Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── Fetch all data ────────────────────────────────────────────────────────────
summary_data = fetch("store-summary", params)
footfall_data = fetch("footfall", params)
zone_data = fetch("zone-heatmap", params)
queue_data = fetch("queue-status", params)
anomaly_data = fetch("anomalies", params)
live_data = fetch("live-footfall", params)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
st.subheader("📊 Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

total_footfall = footfall_data.get("total_footfall", 0) if footfall_data else 0
total_zones = len(zone_data.get("zones", [])) if zone_data else 0
avg_wait = queue_data.get("avg_wait_seconds", 0) if queue_data else 0
abandon_rate = queue_data.get("abandonment_rate", 0) if queue_data else 0
anomaly_count = anomaly_data.get("total_anomalies", 0) if anomaly_data else 0
queue_health = queue_data.get("queue_health", "N/A") if queue_data else "N/A"

col1.metric("👥 Total Footfall", total_footfall)
col2.metric("🗺️ Active Zones", total_zones)
col3.metric("⏱️ Avg Queue Wait", f"{int(avg_wait)}s")
col4.metric("🚶 Abandon Rate", f"{abandon_rate}%")
col5.metric("⚠️ Anomalies", anomaly_count)

st.markdown("---")

# ── Row 1: Footfall + Queue ───────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("👥 Footfall Analysis")
    if footfall_data:
        tab1, tab2 = st.tabs(["Gender Split", "Age Distribution"])

        with tab1:
            gender = footfall_data.get("gender_split", {})
            if gender:
                fig = px.pie(
                    values=list(gender.values()),
                    names=list(gender.keys()),
                    color_discrete_sequence=["#e91e8c", "#1e90ff"],
                    hole=0.4
                )
                fig.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

        with tab2:
            age = footfall_data.get("age_distribution", {})
            if age:
                df_age = pd.DataFrame(
                    list(age.items()),
                    columns=["Age Bucket", "Count"]
                ).sort_values("Age Bucket")
                fig = px.bar(
                    df_age, x="Age Bucket", y="Count",
                    color="Count",
                    color_continuous_scale="Purples"
                )
                fig.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No footfall data yet")

with col_right:
    st.subheader("⏱️ Queue Intelligence")
    if queue_data:
        health_color = {"GOOD": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}
        health = queue_data.get("queue_health", "N/A")
        st.markdown(f"**Queue Health:** {health_color.get(health, '⚪')} {health}")

        q_col1, q_col2, q_col3 = st.columns(3)
        q_col1.metric("Completed", queue_data.get("completed", 0))
        q_col2.metric("Abandoned", queue_data.get("abandoned", 0))
        q_col3.metric("Long Waits", queue_data.get("long_wait_count", 0))

        completed = queue_data.get("completed", 0)
        abandoned = queue_data.get("abandoned", 0)
        if completed + abandoned > 0:
            fig = px.pie(
                values=[completed, abandoned],
                names=["Completed", "Abandoned"],
                color_discrete_sequence=["#4caf50", "#f44336"],
                hole=0.4
            )
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No queue data yet")

st.markdown("---")

# ── Row 2: Zone Heatmap + Live Footfall ───────────────────────────────────────
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("🗺️ Zone Visit Heatmap")
    if zone_data and zone_data.get("zones"):
        zones = zone_data["zones"]
        df_zones = pd.DataFrame(zones)
        fig = px.bar(
            df_zones,
            x="zone_name",
            y="total_visits",
            color="zone_type",
            color_discrete_sequence=px.colors.qualitative.Vivid,
            labels={"zone_name": "Zone", "total_visits": "Visits"}
        )
        fig.update_layout(margin=dict(t=20, b=20), xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**Most Visited Zone:** 🏆 {zone_data.get('most_visited', 'N/A')}")
    else:
        st.info("No zone data yet")

with col_right2:
    st.subheader("📈 Hourly Footfall Trend")
    if live_data and live_data.get("hourly_footfall"):
        df_live = pd.DataFrame(live_data["hourly_footfall"])
        fig = px.line(
            df_live,
            x="hour",
            y="count",
            markers=True,
            color_discrete_sequence=["#e91e8c"]
        )
        fig.update_layout(
            margin=dict(t=20, b=20),
            xaxis_title="Hour",
            yaxis_title="People Count"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hourly data yet")

st.markdown("---")

# ── Anomalies Table ───────────────────────────────────────────────────────────
st.subheader("⚠️ Anomaly Detection Log")
if anomaly_data and anomaly_data.get("anomalies"):
    anomalies = anomaly_data["anomalies"]
    df_anomaly = pd.DataFrame(anomalies)

    def color_severity(val):
        colors = {"HIGH": "background-color: #ffcccc",
                  "MEDIUM": "background-color: #fff3cc",
                  "LOW": "background-color: #ccffcc"}
        return colors.get(val, "")

    st.dataframe(
        df_anomaly.style.applymap(color_severity, subset=["severity"]),
        use_container_width=True
    )
else:
    st.info("No anomalies detected yet — pipeline may still be processing")

# ── Store Comparison ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏪 Store Comparison")
summary_all = fetch("store-summary", {})
if summary_all and summary_all.get("summary"):
    df_summary = pd.DataFrame(summary_all["summary"])
    fig = go.Figure(data=[
        go.Bar(name="Footfall", x=df_summary["store_id"], y=df_summary["total_footfall"],
               marker_color="#e91e8c"),
        go.Bar(name="Zone Visits", x=df_summary["store_id"], y=df_summary["zone_visits"],
               marker_color="#9c27b0"),
        go.Bar(name="Anomalies", x=df_summary["store_id"], y=df_summary["anomalies_detected"],
               marker_color="#ff5722"),
    ])
    fig.update_layout(barmode="group", margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)