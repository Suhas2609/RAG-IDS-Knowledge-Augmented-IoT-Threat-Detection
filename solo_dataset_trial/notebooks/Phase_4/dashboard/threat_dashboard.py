"""
RAG-IDS Threat Dashboard - Streamlit UI
========================================

Real-time visualization interface for the RAG-IDS detection system.
Connects to threat_api.py to display alerts, trends, and system status.

Features:
    - Auto-refresh every 2 seconds
    - Severity breakdown (pie chart)
    - Attack type distribution (bar chart)
    - Live alert feed with drill-down
    - System health monitoring

Usage:
    streamlit run threat_dashboard.py --server.port 8501
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time


# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
REFRESH_INTERVAL = 2  # seconds
MAX_ALERTS_DISPLAY = 50


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="RAG-IDS Threat Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def fetch_health():
    """Check API health status"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def fetch_latest_alerts(limit=50):
    """Fetch recent alerts from API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/alerts/latest",
            params={"limit": limit},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def fetch_alert_details(alert_id):
    """Fetch full details for specific alert"""
    try:
        response = requests.get(f"{API_BASE_URL}/alerts/{alert_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def fetch_stats():
    """Fetch engine statistics"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def get_severity_color(severity):
    """Map severity to color"""
    colors = {
        'CRITICAL': '#DC143C',  # Crimson
        'HIGH': '#FF6347',      # Tomato
        'MEDIUM': '#FFA500',    # Orange
        'LOW': '#FFD700',       # Gold
        'BENIGN': '#32CD32'     # LimeGreen
    }
    return colors.get(severity, '#808080')


def format_timestamp(iso_timestamp):
    """Format ISO timestamp to readable format"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_timestamp


# ============================================================================
# DASHBOARD HEADER
# ============================================================================

st.title("🛡️ RAG-IDS Threat Intelligence Dashboard")
st.markdown("**Real-Time IoT Intrusion Detection System**")
st.markdown("---")


# ============================================================================
# SIDEBAR - SYSTEM STATUS
# ============================================================================

with st.sidebar:
    st.header("🔧 System Status")
    
    # Health check
    health = fetch_health()
    
    if health and health.get('status') == 'ONLINE':
        st.success("🟢 API: ONLINE")
        st.metric("Engine Status", health.get('engine_status', 'UNKNOWN'))
        st.metric("Vector Database", f"{health.get('vector_count', 0):,} patterns")
        
        uptime_hours = health.get('uptime_seconds', 0) / 3600
        st.metric("Uptime", f"{uptime_hours:.1f} hours")
    else:
        st.error("🔴 API: OFFLINE")
        st.warning("⚠️ Detection engine unavailable")
        st.info("Start the API server:\n```bash\ncd notebooks/Phase_4/api\nuvicorn threat_api:app --reload\n```")
    
    st.markdown("---")
    
    # Refresh controls
    st.header("⚙️ Controls")
    auto_refresh = st.checkbox("Auto-Refresh", value=True)
    refresh_button = st.button("🔄 Refresh Now")
    
    if auto_refresh:
        st.info(f"⏱️ Refreshing every {REFRESH_INTERVAL}s")
    
    st.markdown("---")
    st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")


# ============================================================================
# MAIN CONTENT
# ============================================================================

# Fetch data
alerts = fetch_latest_alerts(MAX_ALERTS_DISPLAY)
stats = fetch_stats()

# If no API connection, show error and stop
if health is None:
    st.error("❌ Cannot connect to RAG-IDS API")
    st.info("**Setup Instructions:**")
    st.code("""
# Terminal 1 - Start API Server
cd notebooks/Phase_4/api
uvicorn threat_api:app --reload --port 8000

# Terminal 2 - Start Dashboard
cd notebooks/Phase_4/dashboard
streamlit run threat_dashboard.py --server.port 8501
""")
    st.stop()


# ============================================================================
# METRICS ROW
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

total_alerts = len(alerts)
critical_alerts = sum(1 for a in alerts if a.get('severity') == 'CRITICAL')
high_alerts = sum(1 for a in alerts if a.get('severity') == 'HIGH')

with col1:
    st.metric("Total Alerts", total_alerts, delta=None)

with col2:
    st.metric("Critical", critical_alerts, delta=None, delta_color="inverse")

with col3:
    st.metric("High Severity", high_alerts, delta=None, delta_color="inverse")

with col4:
    if total_alerts > 0:
        critical_pct = (critical_alerts / total_alerts) * 100
        st.metric("Critical %", f"{critical_pct:.1f}%", delta=None)
    else:
        st.metric("Critical %", "0.0%")


# ============================================================================
# CHARTS ROW
# ============================================================================

if total_alerts > 0:
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("📊 Severity Distribution")
        
        # Count alerts by severity
        severity_counts = {}
        for alert in alerts:
            sev = alert.get('severity', 'UNKNOWN')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Create pie chart
        fig_severity = px.pie(
            values=list(severity_counts.values()),
            names=list(severity_counts.keys()),
            color=list(severity_counts.keys()),
            color_discrete_map={
                'CRITICAL': '#DC143C',
                'HIGH': '#FF6347',
                'MEDIUM': '#FFA500',
                'LOW': '#FFD700',
                'BENIGN': '#32CD32'
            },
            hole=0.4
        )
        fig_severity.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_severity, use_container_width=True)
    
    with chart_col2:
        st.subheader("🎯 Attack Types")
        
        # Count alerts by attack type
        attack_counts = {}
        for alert in alerts:
            atype = alert.get('attack_type', 'Unknown')
            attack_counts[atype] = attack_counts.get(atype, 0) + 1
        
        # Create bar chart
        attack_df = pd.DataFrame({
            'Attack Type': list(attack_counts.keys()),
            'Count': list(attack_counts.values())
        }).sort_values('Count', ascending=False)
        
        fig_attacks = px.bar(
            attack_df,
            x='Attack Type',
            y='Count',
            color='Count',
            color_continuous_scale='Reds'
        )
        fig_attacks.update_layout(showlegend=False)
        st.plotly_chart(fig_attacks, use_container_width=True)

else:
    st.info("🟢 No alerts detected. System is monitoring traffic.")


# ============================================================================
# ALERT FEED
# ============================================================================

st.markdown("---")
st.subheader("🚨 Live Alert Feed")

if total_alerts == 0:
    st.success("✅ All systems normal. No threats detected.")
else:
    # Display alerts in expandable cards
    for alert in alerts[:20]:  # Show top 20 most recent
        severity = alert.get('severity', 'UNKNOWN')
        attack_type = alert.get('attack_type', 'Unknown')
        timestamp = alert.get('timestamp', 'N/A')
        confidence = alert.get('confidence', 0.0)
        src_ip = alert.get('src_ip', '0.0.0.0')
        dst_ip = alert.get('dst_ip', '0.0.0.0')
        alert_id = alert.get('alert_id', '')
        
        # Color-coded severity indicator
        color = get_severity_color(severity)
        
        # Create expander with severity badge
        with st.expander(
            f"🔴 **{severity}** | {attack_type} | {format_timestamp(timestamp)} | {confidence:.1%} confidence",
            expanded=False
        ):
            # Alert details
            detail_col1, detail_col2, detail_col3 = st.columns(3)
            
            with detail_col1:
                st.markdown(f"**Source:** `{src_ip}`")
                st.markdown(f"**Destination:** `{dst_ip}`")
            
            with detail_col2:
                st.markdown(f"**Attack Type:** {attack_type}")
                st.markdown(f"**Severity:** {severity}")
            
            with detail_col3:
                st.markdown(f"**Confidence:** {confidence:.1%}")
                st.markdown(f"**Alert ID:** `{alert_id}`")
            
            # Fetch full details button
            if st.button(f"🔍 View Full Analysis", key=alert_id):
                details = fetch_alert_details(alert_id)
                if details:
                    st.json(details)


# ============================================================================
# STATISTICS PANEL
# ============================================================================

if stats:
    st.markdown("---")
    st.subheader("📈 Engine Statistics")
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    
    engine_stats = stats.get('engine', {})
    alert_stats = stats.get('alerts', {})
    
    with stat_col1:
        st.metric("Vector Database Size", f"{engine_stats.get('vector_count', 0):,}")
        st.metric("Current Window Size", engine_stats.get('current_window_size', 0))
    
    with stat_col2:
        st.metric("Window Duration", f"{engine_stats.get('adaptive_window_seconds', 0):.1f}s")
        st.metric("Total Alerts", alert_stats.get('total', 0))
    
    with stat_col3:
        uptime = stats.get('uptime_seconds', 0) / 3600
        st.metric("System Uptime", f"{uptime:.2f} hours")
    
    # Severity breakdown table
    if alert_stats.get('by_severity'):
        st.markdown("**Alert Distribution by Severity:**")
        severity_df = pd.DataFrame({
            'Severity': list(alert_stats['by_severity'].keys()),
            'Count': list(alert_stats['by_severity'].values())
        })
        st.dataframe(severity_df, use_container_width=True, hide_index=True)


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("RAG-IDS: Retrieval-Augmented Generation for IoT Intrusion Detection | Phase 4 Dashboard")


# ============================================================================
# AUTO-REFRESH LOOP
# ============================================================================

if auto_refresh:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
