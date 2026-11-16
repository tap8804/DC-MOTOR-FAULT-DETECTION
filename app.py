from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="DC Motor Digital Twin",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULTS = {
    "temp_warning": 45.0,
    "temp_fault": 50.0,
    "vib_warning": 140.0,
    "vib_fault": 160.0,
    "current_warning": 0.40,
    "current_fault": 0.45,
    "voltage_warning": 13.5,
    "voltage_fault": 14.0,
    "refresh_seconds": 20,
    "history_count": 60,
    "dashboard_title": "12V DC Motor Digital Twin",
    "subtitle": "Live condition monitoring",
    "accent": "#2F80ED",
    "show_temperature": True,
    "show_vibration": True,
    "show_current": True,
    "show_voltage": True,
    "show_rpm": True,
    "show_charts": True,
    "show_last_update": True,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------------------------------------
# Credentials: use Streamlit secrets on cloud, or sidebar input
# ------------------------------------------------------------
secret_channel = ""
secret_read_key = ""
try:
    secret_channel = str(st.secrets.get("THINGSPEAK_CHANNEL_ID", ""))
    secret_read_key = str(st.secrets.get("THINGSPEAK_READ_API_KEY", ""))
except Exception:
    pass

# ------------------------------------------------------------
# Sidebar settings
# ------------------------------------------------------------
st.sidebar.title("⚙️ Digital Twin Settings")
st.sidebar.caption("Changes apply to this browser session.")

with st.sidebar.expander("ThingSpeak connection", expanded=not bool(secret_read_key)):
    channel_id = st.text_input(
        "Channel ID",
        value=secret_channel or "3581766",
        help="Your ThingSpeak channel ID.",
    )
    read_api_key = st.text_input(
        "Read API Key",
        value=secret_read_key,
        type="password",
        help="Use the channel Read API Key. Keep it private.",
    )
    feed_results = st.selectbox("Data points to fetch", [30, 60, 100, 200], index=2)

with st.sidebar.expander("Operating conditions", expanded=True):
    st.markdown("**Temperature (°C)**")
    st.number_input("Warning at", min_value=-50.0, max_value=250.0, step=1.0,
                    key="temp_warning")
    st.number_input("Fault above", min_value=-50.0, max_value=250.0, step=1.0,
                    key="temp_fault")

    st.markdown("**Vibration (events/s)**")
    st.number_input("Vibration warning at", min_value=0.0, max_value=10000.0, step=1.0,
                    key="vib_warning")
    st.number_input("Vibration fault above", min_value=0.0, max_value=10000.0, step=1.0,
                    key="vib_fault")

    st.markdown("**Current (A)**")
    st.number_input("Current warning at", min_value=0.0, max_value=100.0, step=0.01,
                    format="%.2f", key="current_warning")
    st.number_input("Current fault above", min_value=0.0, max_value=100.0, step=0.01,
                    format="%.2f", key="current_fault")

    st.markdown("**Voltage (V)**")
    st.number_input("Voltage warning at", min_value=0.0, max_value=100.0, step=0.1,
                    key="voltage_warning")
    st.number_input("Voltage fault above", min_value=0.0, max_value=100.0, step=0.1,
                    key="voltage_fault")

with st.sidebar.expander("Interface and display", expanded=False):
    st.text_input("Dashboard title", key="dashboard_title")
    st.text_input("Subtitle", key="subtitle")
    st.color_picker("Accent colour", key="accent")
    st.slider("Auto-refresh interval (seconds)", 15, 120, step=5, key="refresh_seconds")
    st.slider("Chart history (readings)", 10, 200, step=10, key="history_count")
    st.checkbox("Show temperature", key="show_temperature")
    st.checkbox("Show vibration", key="show_vibration")
    st.checkbox("Show current", key="show_current")
    st.checkbox("Show voltage", key="show_voltage")
    st.checkbox("Show RPM", key="show_rpm")
    st.checkbox("Show trend charts", key="show_charts")
    st.checkbox("Show last update time", key="show_last_update")

if st.sidebar.button("Reset settings to defaults", use_container_width=True):
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.rerun()

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
accent = st.session_state.accent
st.markdown(
    f"""
    <style>
      .stApp {{ background: linear-gradient(135deg, #0b1220 0%, #101b2d 100%); }}
      [data-testid="stSidebar"] {{ background-color: #0b1424; }}
      h1, h2, h3, p, label {{ color: #edf3fb; }}
      div[data-testid="stMetric"] {{
        background: #17263a; border: 1px solid #2b3d55;
        padding: 16px; border-radius: 14px;
      }}
      div[data-testid="stMetricLabel"] p {{ color: #b7c7da !important; }}
      div[data-testid="stMetricValue"] {{ color: #ffffff !important; }}
      .status-panel {{
        padding: 18px 22px; border-radius: 14px; font-size: 1.25rem;
        font-weight: 700; border: 1px solid #40536b; margin: 8px 0 18px 0;
      }}
      .stButton button {{ border-color: {accent}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# ThingSpeak data retrieval
# ------------------------------------------------------------
@st.cache_data(ttl=10, show_spinner=False)
def fetch_thingspeak(channel, key, results):
    url = f"https://api.thingspeak.com/channels/{channel}/feeds.json"
    params = {"results": results}
    if key.strip():
        params["api_key"] = key.strip()
    response = requests.get(url, params=params, timeout=12)
    response.raise_for_status()
    payload = response.json()
    feeds = payload.get("feeds", [])
    if not feeds:
        return pd.DataFrame()
    rows = []
    for item in feeds:
        rows.append({
            "created_at": item.get("created_at"),
            "Temperature": pd.to_numeric(item.get("field1"), errors="coerce"),
            "Vibration": pd.to_numeric(item.get("field2"), errors="coerce"),
            "Current": pd.to_numeric(item.get("field3"), errors="coerce"),
            "RPM": pd.to_numeric(item.get("field4"), errors="coerce"),
            "Voltage": pd.to_numeric(item.get("field5"), errors="coerce"),
            "ESP32_Status": pd.to_numeric(item.get("field6"), errors="coerce"),
        })
    df = pd.DataFrame(rows)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df = df.dropna(subset=["created_at"]).sort_values("created_at")
    return df

# ------------------------------------------------------------
# Condition evaluation from editable dashboard settings
# ------------------------------------------------------------
def evaluate_limit(value, warning, fault):
    if pd.isna(value):
        return "NO DATA"
    if fault <= warning:
        return "SETTINGS ERROR"
    if value > fault:
        return "FAULT"
    if value >= warning:
        return "WARNING"
    return "NORMAL"

def overall_condition(states):
    if "SETTINGS ERROR" in states:
        return "SETTINGS ERROR"
    if "FAULT" in states:
        return "FAULT"
    if "NO DATA" in states:
        return "WAITING FOR DATA"
    if "WARNING" in states:
        return "WARNING"
    return "NORMAL"

def state_color(state):
    return {
        "NORMAL": "#167d55",
        "WARNING": "#a66a08",
        "FAULT": "#a83232",
        "NO DATA": "#526174",
        "WAITING FOR DATA": "#526174",
        "SETTINGS ERROR": "#7a3db8",
    }.get(state, "#526174")

# Validate thresholds
threshold_pairs = [
    ("Temperature", st.session_state.temp_warning, st.session_state.temp_fault),
    ("Vibration", st.session_state.vib_warning, st.session_state.vib_fault),
    ("Current", st.session_state.current_warning, st.session_state.current_fault),
    ("Voltage", st.session_state.voltage_warning, st.session_state.voltage_fault),
]
invalid_pairs = [name for name, warning, fault in threshold_pairs if fault <= warning]

# ------------------------------------------------------------
# Header and automatic refresh
# ------------------------------------------------------------
st_autorefresh(interval=int(st.session_state.refresh_seconds) * 1000, key="motor_twin_refresh")
st.title(st.session_state.dashboard_title)
st.caption(st.session_state.subtitle)
st.markdown(
    f"<div style='height:4px;background:{accent};border-radius:5px;margin-bottom:18px'></div>",
    unsafe_allow_html=True,
)

if invalid_pairs:
    st.error("Fault limits must be higher than warning limits for: " + ", ".join(invalid_pairs))
    st.stop()

if not channel_id.strip():
    st.warning("Enter your ThingSpeak Channel ID in the settings panel.")
    st.stop()

if not read_api_key.strip():
    st.info("Enter your ThingSpeak Read API Key in the ThingSpeak connection settings.")
    st.stop()

try:
    with st.spinner("Receiving motor data from ThingSpeak..."):
        data = fetch_thingspeak(channel_id.strip(), read_api_key.strip(), feed_results)
except requests.exceptions.RequestException as exc:
    st.error(f"Could not connect to ThingSpeak: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Could not read the ThingSpeak response: {exc}")
    st.stop()

if data.empty:
    st.warning("No readings are available yet. Check that your ESP32 is uploading data to this channel.")
    st.stop()

latest = data.iloc[-1]
sensor_states = {
    "Temperature": evaluate_limit(latest["Temperature"], st.session_state.temp_warning, st.session_state.temp_fault),
    "Vibration": evaluate_limit(latest["Vibration"], st.session_state.vib_warning, st.session_state.vib_fault),
    "Current": evaluate_limit(latest["Current"], st.session_state.current_warning, st.session_state.current_fault),
    "Voltage": evaluate_limit(latest["Voltage"], st.session_state.voltage_warning, st.session_state.voltage_fault),
}
motor_state = overall_condition(list(sensor_states.values()))

if st.session_state.show_last_update:
    local_time = latest["created_at"].tz_convert("Asia/Kolkata").strftime("%d %b %Y, %I:%M:%S %p IST")
    st.caption(f"Last ThingSpeak update: {local_time}")

# Overall status
st.markdown(
    f"<div class='status-panel' style='background:{state_color(motor_state)}22;"
    f"border-color:{state_color(motor_state)};color:#ffffff'>"
    f"MOTOR CONDITION: {motor_state}</div>",
    unsafe_allow_html=True,
)

# Metric cards, responsive columns
metric_specs = [
    ("Temperature", "°C", st.session_state.show_temperature, 1),
    ("Vibration", "events/s", st.session_state.show_vibration, 0),
    ("Current", "A", st.session_state.show_current, 2),
    ("Voltage", "V", st.session_state.show_voltage, 2),
    ("RPM", "RPM", st.session_state.show_rpm, 0),
]
visible_specs = [item for item in metric_specs if item[2]]
if visible_specs:
    cols = st.columns(len(visible_specs))
    for col, (name, unit, _, decimals) in zip(cols, visible_specs):
        value = latest[name]
        if pd.isna(value):
            display_value = "No data"
        else:
            display_value = f"{value:.{decimals}f} {unit}"
        state = sensor_states.get(name, "NORMAL")
        with col:
            st.metric(name, display_value)
            if name in sensor_states:
                st.caption(f"Condition: {state}")

# Sensor condition table
with st.expander("Sensor condition details", expanded=True):
    condition_rows = []
    for name, state in sensor_states.items():
        val = latest[name]
        condition_rows.append({
            "Parameter": name,
            "Live reading": "No data" if pd.isna(val) else val,
            "Condition": state,
        })
    st.dataframe(pd.DataFrame(condition_rows), use_container_width=True, hide_index=True)

# Trend charts
if st.session_state.show_charts:
    st.subheader("Live trends")
    chart_data = data.tail(st.session_state.history_count).copy()
    chart_data["Time"] = chart_data["created_at"].dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M:%S")
    chart_parameters = [
        ("Temperature", "Temperature (°C)", st.session_state.show_temperature),
        ("Vibration", "Vibration (events/s)", st.session_state.show_vibration),
        ("Current", "Current (A)", st.session_state.show_current),
        ("Voltage", "Voltage (V)", st.session_state.show_voltage),
        ("RPM", "Speed (RPM)", st.session_state.show_rpm),
    ]
    chosen = [(column, label) for column, label, enabled in chart_parameters if enabled]
    if chosen:
        chart_cols = st.columns(2)
        for index, (column, axis_label) in enumerate(chosen):
            fig = px.line(chart_data, x="created_at", y=column, markers=True,
                          title=axis_label)
            fig.update_traces(line=dict(color=accent, width=2), marker=dict(size=4))
            fig.update_layout(
                height=300, margin=dict(l=10, r=10, t=45, b=10),
                paper_bgcolor="#17263a", plot_bgcolor="#17263a",
                font_color="#edf3fb",
                xaxis_title="Time", yaxis_title=axis_label,
            )
            fig.update_xaxes(showgrid=True, gridcolor="#2b3d55")
            fig.update_yaxes(showgrid=True, gridcolor="#2b3d55")
            with chart_cols[index % 2]:
                st.plotly_chart(fig, use_container_width=True)

# Data table
with st.expander("Recent readings from ThingSpeak"):
    table = data.tail(20).copy()
    table["created_at"] = table["created_at"].dt.tz_convert("Asia/Kolkata").dt.strftime("%d-%m-%Y %H:%M:%S")
    table = table[["created_at", "Temperature", "Vibration", "Current", "Voltage", "RPM"]]
    table = table.rename(columns={"created_at": "Time"})
    st.dataframe(table.iloc[::-1], use_container_width=True, hide_index=True)

st.caption(
    "Condition limits are evaluated in this dashboard. This is a monitoring digital twin, "
    "not a safety-rated motor protection system."
)

