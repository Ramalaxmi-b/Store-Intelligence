import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path

st.set_page_config(
    page_title="Purplle Store Intelligence",
    page_icon="🛍️",
    layout="wide"
)

@st.cache_data
def load_events():
    events_file = Path("events_output.jsonl")
    person_events, zone_events, queue_events = [], [], []
    
    with open(events_file) as f:
        for line in f:
            e = json.loads(line)
            if e["event_type"] in ["entry", "exit"]:
                person_events.append(e)
            elif e["event_type"] in ["zone_entered", "zone_exited"]:
                zone_events.append(e)
            elif e["event_type"] in ["queue_completed", "queue_abandoned"]:
                queue_events.append(e)
    
    return (
        pd.DataFrame(person_events) if person_events else pd.DataFrame(),
        pd.DataFrame(zone_events) if zone_events else pd.DataFrame(),
        pd.DataFrame(queue_events) if queue_events else pd.DataFrame()
    )

df_person, df_zone, df_queue = load_events()

# Sidebar
st.sidebar.title("🛍️ Store Intelligence")
st.sidebar.markdown("**Purplle Tech Challenge 2026**")

store_options = {"All Stores": None, "Store 1 (ST1008)": "ST1008", "Store 2 (ST1076)": "ST1076"}
selected = st.sidebar.selectbox("Select Store", list(store_options.keys()))
store_id = store_options[selected]

# Filter by store
def filter_store(df, col):
    if df.empty or store_id is None:
        return df
    return df[df[col] == store_id]

p = filter_store(df_person, "store_code")
z = filter_store(df_zone, "store_id")
q = filter_store(df_queue, "store_id")

entries = p[p["event_type"] == "entry"] if not p.empty else pd.DataFrame()
zone_entries = z[z["event_type"] == "zone_entered"] if not z.empty else pd.DataFrame()

# Title
st.title("🛍️ Purplle Store Intelligence Dashboard")
st.caption("AI-powered CCTV Analytics | Purplle Tech Challenge 2026")

# KPIs
st.subheader("📊 Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

total_footfall = len(entries)
active_zones = zone_entries["zone_name"].nunique() if not zone_entries.empty else 0
avg_wait = q["wait_seconds"].mean() if not q.empty else 0
abandon_rate = (q["abandoned"].sum() / len(q) * 100) if not q.empty else 0
completed = (~q["abandoned"]).sum() if not q.empty else 0
abandoned = q["abandoned"].sum() if not q.empty else 0

col1.metric("👥 Total Footfall", total_footfall)
col2.metric("🗺️ Active Zones", active_zones)
col3.metric("⏱️ Avg Queue Wait", f"{int(avg_wait)}s")
col4.metric("🚶 Abandon Rate", f"{abandon_rate:.1f}%")
col5.metric("✅ Queue Completed", int(completed))

st.markdown("---")

# Row 1
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("👥 Footfall Analysis")
    if not entries.empty:
        tab1, tab2 = st.tabs(["Gender Split", "Age Distribution"])
        with tab1:
            gender = entries["gender_pred"].value_counts().reset_index()
            gender.columns = ["Gender", "Count"]
            fig = px.pie(gender, values="Count", names="Gender",
                        color_discrete_sequence=["#e91e8c", "#1e90ff"], hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            age = entries["age_bucket"].value_counts().reset_index()
            age.columns = ["Age Bucket", "Count"]
            fig = px.bar(age, x="Age Bucket", y="Count",
                        color="Count", color_continuous_scale="Purples")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No footfall data")

with col_r:
    st.subheader("⏱️ Queue Intelligence")
    if not q.empty:
        avg_w = q["wait_seconds"].mean()
        health = "🔴 CRITICAL" if avg_w > 300 else "🟡 WARNING" if avg_w > 180 else "🟢 GOOD"
        st.markdown(f"**Queue Health:** {health}")
        
        q_c1, q_c2, q_c3 = st.columns(3)
        q_c1.metric("Completed", int(completed))
        q_c2.metric("Abandoned", int(abandoned))
        q_c3.metric("Avg Wait", f"{int(avg_w)}s")

        fig = px.pie(
            values=[int(completed), int(abandoned)],
            names=["Completed", "Abandoned"],
            color_discrete_sequence=["#4caf50", "#f44336"], hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No queue data")

st.markdown("---")

# Row 2
col_l2, col_r2 = st.columns(2)

with col_l2:
    st.subheader("🗺️ Zone Visit Heatmap")
    if not zone_entries.empty:
        zone_counts = zone_entries.groupby(["zone_name", "zone_type"]).size().reset_index(name="visits")
        zone_counts = zone_counts.sort_values("visits", ascending=False)
        fig = px.bar(zone_counts, x="zone_name", y="visits", color="zone_type",
                    color_discrete_sequence=px.colors.qualitative.Vivid)
        fig.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"**Most Visited:** 🏆 {zone_counts.iloc[0]['zone_name']}")
    else:
        st.info("No zone data")

with col_r2:
    st.subheader("📈 Hourly Footfall Trend")
    if not entries.empty and "event_timestamp" in entries.columns:
        entries2 = entries.copy()
        entries2["hour"] = entries2["event_timestamp"].str[:13]
        hourly = entries2.groupby("hour").size().reset_index(name="count")
        fig = px.line(hourly, x="hour", y="count", markers=True,
                     color_discrete_sequence=["#e91e8c"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hourly data")

st.markdown("---")

# Store comparison
st.subheader("🏪 Store Comparison")
if not df_person.empty:
    store_footfall = df_person[df_person["event_type"]=="entry"].groupby("store_code").size().reset_index(name="footfall")
    store_zones = df_zone[df_zone["event_type"]=="zone_entered"].groupby("store_id").size().reset_index(name="zone_visits") if not df_zone.empty else pd.DataFrame()
    
    fig = go.Figure()
    if not store_footfall.empty:
        fig.add_trace(go.Bar(name="Footfall", x=store_footfall["store_code"],
                            y=store_footfall["footfall"], marker_color="#e91e8c"))
    if not store_zones.empty:
        fig.add_trace(go.Bar(name="Zone Visits", x=store_zones["store_id"],
                            y=store_zones["zone_visits"], marker_color="#9c27b0"))
    fig.update_layout(barmode="group")
    st.plotly_chart(fig, use_container_width=True)
