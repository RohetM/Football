"""Streamlit Dashboard for WorldCup OS.

Provides a visual operational interface: live gate heatmap, transit status,
multilingual fan chat copilot, ops incident dispatch form, active simulation controls,
and dedicated "Agent Thoughts" reasoning cards.
"""

import os

import requests
import streamlit as st

# Coordinates coordinates map definition for Ops Agent
ZONE_COORDINATES = {
    "Gate_A": (0, 10),
    "North_Plaza": (0, 8),
    "Gate_B": (0, -10),
    "South_Plaza": (0, -8),
    "Gate_C": (10, 0),
    "East_Concourse": (8, 0),
    "Gate_D": (-10, 0),
    "West_Concourse": (-8, 0),
}

# Setup page config
st.set_page_config(
    page_title="WorldCup OS — Stadium Co-pilot",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API base URL configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Premium UI CSS injection
st.markdown(
    """
    <style>
    /* Dark Mode styling */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Header card styling */
    .header-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Info cards */
    .status-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    /* Bottleneck alert card */
    .alert-card {
        background-color: #7f1d1d;
        border: 1px solid #b91c1c;
        color: #fca5a5;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 16px;
    }
    
    /* Agent thoughts trace panel */
    .thoughts-card {
        background-color: #172554;
        border: 1px solid #2563eb;
        color: #93c5fd;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: 'Courier New', Courier, monospace;
        margin-top: 10px;
        font-size: 0.9em;
    }
    
    /* High contrast overriding layout class */
    .high-contrast-card {
        background-color: #ffffff !important;
        border: 3px solid #000000 !important;
        color: #000000 !important;
    }
    
    /* Button custom hover styling */
    .stButton>button {
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_stadium_state():
    """Fetch simulated live state from FastAPI backend.

    Falls back to a safe empty structure if backend is unreachable.
    """
    try:
        r = requests.get(f"{API_BASE_URL}/api/stadium-state", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fetch_crowd_predictions():
    """Fetch crowd bottleneck analysis from FastAPI backend."""
    try:
        r = requests.get(f"{API_BASE_URL}/api/crowd-predict", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/color/96/world-cup.png", width=70)
    st.title("WorldCup OS")
    st.markdown("### Co-pilot Controller")
    st.info(
        "💡 Run the FastAPI server at `http://localhost:8000` to stream simulated telemetry and trigger LLM logic."
    )

    # High Contrast accessibility mode toggle
    high_contrast = st.toggle(
        "♿ High Contrast Mode",
        help="Improves readability for visually impaired stewards.",
    )

    st.markdown("---")
    st.markdown("### Operational Controls")

    if st.button("🔄 Refresh Telemetry", use_container_width=True):
        st.toast("Telemetry refreshed!")

    if st.button(
        "⚡ Simulate Event Tick",
        help="Trigger dynamic wait-time fluctuations",
        use_container_width=True,
    ):
        try:
            r = requests.post(f"{API_BASE_URL}/api/simulate-tick", timeout=3)
            if r.status_code == 200:
                st.success("State mutated!")
                st.rerun()
            else:
                st.error("Failed to run tick.")
        except Exception as e:
            st.error(f"Backend offline: {e}")

# Load current state
state = fetch_stadium_state()

# Application Title
st.markdown(
    """
    <div class="header-card">
        <h1 style="margin: 0; color: #38bdf8;">🏆 WorldCup OS</h1>
        <p style="margin: 5px 0 0 0; color: #94a3b8;">Domain-Driven GenAI Stadium Operations & Crowd Bottleneck Co-pilot</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not state:
    st.warning(
        "⚠️ FastAPI Backend is offline. Run `uvicorn backend.main:app` to activate full GenAI capabilities."
    )
    # Provide static mock state so UI is still visual
    state = {
        "last_updated": "Offline Mode",
        "gates": {
            "Gate_A": {
                "status": "OPEN",
                "wait_time_minutes": 45,
                "security_wait_time_minutes": 30,
                "capacity_utilization": 0.85,
            },
            "Gate_B": {
                "status": "OPEN",
                "wait_time_minutes": 25,
                "security_wait_time_minutes": 15,
                "capacity_utilization": 0.60,
            },
            "Gate_C": {
                "status": "OPEN",
                "wait_time_minutes": 10,
                "security_wait_time_minutes": 8,
                "capacity_utilization": 0.35,
            },
            "Gate_D": {
                "status": "CLOSED",
                "wait_time_minutes": 0,
                "security_wait_time_minutes": 0,
                "capacity_utilization": 0.0,
            },
        },
        "transit": {
            "Metro_Line_1": {
                "status": "DELAYED",
                "delay_minutes": 15,
                "description": "Signal failure at Main Station",
            },
            "Metro_Line_2": {
                "status": "NORMAL",
                "delay_minutes": 0,
                "description": "Running on time",
            },
            "Stadium_Shuttle": {
                "status": "NORMAL",
                "delay_minutes": 0,
                "description": "Buses departing every 5 mins",
            },
        },
        "plazas": {
            "North_Plaza": {
                "capacity_utilization": 0.88,
                "crowd_density_level": "CRITICAL",
            },
            "South_Plaza": {
                "capacity_utilization": 0.40,
                "crowd_density_level": "NORMAL",
            },
            "East_Concourse": {
                "capacity_utilization": 0.75,
                "crowd_density_level": "WARNING",
            },
            "West_Concourse": {
                "capacity_utilization": 0.30,
                "crowd_density_level": "NORMAL",
            },
        },
        "weather": {"condition": "Clear", "temperature_c": 24, "humidity_percent": 60},
        "volunteers": [
            {
                "id": "V1",
                "name": "Elena Rostova",
                "location": "Gate_C",
                "status": "IDLE",
            },
            {
                "id": "V2",
                "name": "Marcus Aurelius",
                "location": "South_Plaza",
                "status": "IDLE",
            },
            {
                "id": "V3",
                "name": "Carlos Gomez",
                "location": "North_Plaza",
                "status": "BUSY",
            },
        ],
        "incidents": [],
    }

# Divide screen into two primary dashboard sections
col1, col2 = st.columns([3, 2])

# Left column: Telemetry Heatmap and Incident Dispatcher
with col1:
    st.markdown("### 📊 Stadium Telemetry Board")

    # Render Gates Wait-Times Heatmap
    st.markdown("#### Gates Checkpoint wait times")
    g_cols = st.columns(4)
    for i, (g_name, g_info) in enumerate(state["gates"].items()):
        with g_cols[i]:
            card_class = "high-contrast-card" if high_contrast else "status-card"
            color = (
                "#ef4444"
                if g_info["wait_time_minutes"] > 30
                else ("#eab308" if g_info["wait_time_minutes"] > 15 else "#22c55e")
            )
            if g_info["status"] == "CLOSED":
                color = "#64748b"
                wait_text = "CLOSED"
            else:
                wait_text = f"{g_info['wait_time_minutes']} min wait"

            st.markdown(
                f"""
                <div class="{card_class}">
                    <strong style="font-size: 1.1em; color: {color};">{g_name.replace("_", " ")}</strong>
                    <div style="font-size: 1.5em; font-weight: bold; margin: 5px 0;">{wait_text}</div>
                    <div style="font-size: 0.85em; opacity: 0.8;">Security: {g_info["security_wait_time_minutes"]}m</div>
                    <div style="font-size: 0.85em; opacity: 0.8;">Capacity load: {int(g_info["capacity_utilization"] * 100)}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Render Plaza Loads and Transit
    t_col, p_col = st.columns(2)
    with t_col:
        st.markdown("#### 🚇 Transit Status")
        for line, info in state["transit"].items():
            card_class = "high-contrast-card" if high_contrast else "status-card"
            color = "#ef4444" if info["status"] == "DELAYED" else "#22c55e"
            st.markdown(
                f"""
                <div class="{card_class}">
                    <strong>{line.replace("_", " ")}</strong> - <span style="color: {color}; font-weight: bold;">{info["status"]}</span>
                    <div style="font-size: 0.9em; margin-top: 4px;">{info["description"]}</div>
                    {f'<div style="font-size: 0.85em; color: #fca5a5;">Delay: {info["delay_minutes"]}m</div>' if info["status"] == "DELAYED" else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with p_col:
        st.markdown("#### 🏟️ Plazas Load")
        for plaza, info in state["plazas"].items():
            card_class = "high-contrast-card" if high_contrast else "status-card"
            color = (
                "#ef4444"
                if info["crowd_density_level"] == "CRITICAL"
                else (
                    "#eab308" if info["crowd_density_level"] == "WARNING" else "#22c55e"
                )
            )
            st.markdown(
                f"""
                <div class="{card_class}">
                    <strong>{plaza.replace("_", " ")}</strong>
                    <div style="font-size: 1.1em; font-weight: bold; color: {color};">{info["crowd_density_level"]}</div>
                    <div style="font-size: 0.85em; opacity: 0.8;">Capacity: {int(info["capacity_utilization"] * 100)}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Volunteer Operations dispatcher
    st.markdown("---")
    st.markdown("### 🚒 Operations Coordinator (Ops Agent)")

    op_col1, op_col2 = st.columns([1, 1])
    with op_col1:
        st.markdown("#### Report Incident")
        inc_desc = st.text_input(
            "Incident description",
            placeholder="e.g. Accessibility escort request from taxi drop-off",
        )
        inc_type = st.selectbox(
            "Incident category", ["accessibility", "medical", "security"]
        )
        inc_loc = st.selectbox(
            "Incident location",
            list(ZONE_COORDINATES.keys())
            if "ZONE_COORDINATES" in globals() or True
            else [
                "Gate_A",
                "Gate_B",
                "Gate_C",
                "Gate_D",
                "North_Plaza",
                "South_Plaza",
                "East_Concourse",
                "West_Concourse",
            ],
        )

        if st.button("🚨 Dispatch Nearest Steward", use_container_width=True):
            if inc_desc.strip():
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/api/ops-action",
                        json={
                            "description": inc_desc,
                            "type": inc_type,
                            "location": inc_loc,
                        },
                        timeout=5,
                    )
                    if r.status_code == 200:
                        res = r.json()
                        st.session_state["last_dispatch"] = res
                        st.toast("Ops Agent dispatched steward!")
                    else:
                        st.error(f"Dispatch request failed: {r.text}")
                except Exception as e:
                    # Fallback in case API is offline
                    st.error(f"FastAPI backend offline: {e}")
            else:
                st.warning("Please fill out the incident description.")

    with op_col2:
        st.markdown("#### Live Volunteers Feed")
        v_list = state.get("volunteers", [])
        v_df = [
            {
                "ID": v["id"],
                "Name": v["name"],
                "Location": v["location"],
                "Status": v["status"],
            }
            for v in v_list
        ]
        st.dataframe(v_df, use_container_width=True, hide_index=True)

    # Display Dispatch Result and Agent Thoughts
    if "last_dispatch" in st.session_state:
        ld = st.session_state["last_dispatch"]
        st.markdown("#### 📟 Dispatch Command Issued")
        st.success(ld.get("recommendation", "No assignment made."))

        # Transparent reasoning trace
        st.markdown(
            f"""
            <div class="thoughts-card">
                <strong>🤖 Ops Agent Thoughts (Reasoning Trace):</strong><br/>
                {ld.get("reasoning", "No reasoning logged.")}
            </div>
            """,
            unsafe_allow_html=True,
        )

# Right column: Fan Chat Copilot & Crowd Intel Agent Alerts
with col2:
    st.markdown("### 🚨 Predictive Bottleneck Analytics")

    # Fetch crowd bottleneck warning
    crowd_res = fetch_crowd_predictions()
    if crowd_res:
        color = "#fca5a5" if crowd_res.get("confidence") == "HIGH" else "#fef08a"
        st.markdown(
            f"""
            <div class="alert-card">
                <h4 style="margin: 0 0 5px 0; color: {color};">⚠️ Bottleneck Identified ({crowd_res.get("confidence")} Confidence)</h4>
                <strong>Issue:</strong> {crowd_res.get("issue")}<br/>
                <strong>Est. Escalation ETA:</strong> {crowd_res.get("eta_minutes")} minutes<br/>
                <strong>Recommended Mitigation:</strong> {crowd_res.get("recommended_action")}
            </div>
            <div class="thoughts-card" style="margin-bottom: 20px;">
                <strong>🤖 Crowd Agent Thoughts:</strong><br/>
                {crowd_res.get("reasoning")}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No active predictive bottleneck alerts. Stadium flow is stable.")

    st.markdown("---")
    st.markdown("### 💬 Fan Copilot (Fan Agent)")

    # Accessibility preference flags
    st.markdown("#### Copilot Preferences")
    f_lang = st.selectbox(
        "Preferred language",
        ["English", "Spanish", "French", "German", "Japanese", "Arabic"],
        index=0,
    )

    access_options = [
        "None",
        "Wheelchair access pathway",
        "Sensory friendly/Quiet accommodations",
        "Hearing assistance",
    ]
    f_access = st.selectbox("Accessibility Needs", access_options, index=0)

    # Chat log storage in streamlit session state
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Query Input
    query_input = st.text_input(
        "Ask a question (e.g. Can I bring a backpack? Which gate is wheelchair accessible?)"
    )

    if st.button("✈️ Send Query", use_container_width=True):
        if query_input.strip():
            # Trigger API
            acc_param = None if f_access == "None" else f_access
            try:
                r = requests.post(
                    f"{API_BASE_URL}/api/fan-query",
                    json={
                        "query": query_input,
                        "language": f_lang,
                        "accessibility_needs": acc_param,
                    },
                    timeout=5,
                )
                if r.status_code == 200:
                    ans = r.json()
                    st.session_state["chat_history"].append(
                        {
                            "query": query_input,
                            "response": ans.get("response"),
                            "reasoning": ans.get("reasoning"),
                            "sources": ans.get("sources", []),
                        }
                    )
                else:
                    st.error(f"Error ({r.status_code}): {r.text}")
            except Exception as e:
                st.error(f"FastAPI backend offline: {e}")
        else:
            st.warning("Please type a question first.")

    # Render Chat History
    if st.session_state["chat_history"]:
        st.markdown("#### Chat Feed")
        for chat in reversed(st.session_state["chat_history"]):
            st.markdown(f"**👤 Fan:** {chat['query']}")
            st.markdown(f"**🤖 Agent:** {chat['response']}")

            # Show sources
            if chat.get("sources"):
                st.markdown(f"*Sources grounded:* `{', '.join(chat['sources'])}`")

            # Transparent reasoning trace
            st.markdown(
                f"""
                <div class="thoughts-card">
                    <strong>🤖 Fan Agent Thoughts (Reasoning Trace):</strong><br/>
                    {chat.get("reasoning")}
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("---")
