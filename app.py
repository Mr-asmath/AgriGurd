import streamlit as st
import time
import json
from datetime import datetime, timedelta
from streamlit_folium import st_folium
import folium
import random
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Smart Agriculture IoT", layout="centered", initial_sidebar_state="expanded")

# ------------------ SESSION STATE ------------------
if "water_level" not in st.session_state:
    st.session_state.water_level = 85
if "drain_open" not in st.session_state:
    st.session_state.drain_open = True
if "auto_mode" not in st.session_state:
    st.session_state.auto_mode = True
if "last_auto_action" not in st.session_state:
    st.session_state.last_auto_action = None
if "notifications" not in st.session_state:
    st.session_state.notifications = [
        {"id": 1, "title": "Heavy Rain Alert", "message": "120mm rainfall predicted in next 12 hours", "time": "2 hours ago", "type": "warning", "read": False},
        {"id": 2, "title": "System Check", "message": "All sensors functioning normally", "time": "4 hours ago", "type": "info", "read": True},
        {"id": 3, "title": "Drainage Activated", "message": "Automatic drainage started at 14:30", "time": "Yesterday", "type": "success", "read": True},
    ]
if "suggestions" not in st.session_state:
    st.session_state.suggestions = [
        "Check drainage channels for blockages",
        "Delay fertilizer application until after rain",
        "Install additional support for tall crops",
        "Monitor soil moisture levels hourly"
    ]
if "water_level_history" not in st.session_state:
    # Generate some historical data
    st.session_state.water_level_history = []
    for i in range(24):
        time_point = datetime.now() - timedelta(hours=23-i)
        level = random.randint(60, 95) if i < 12 else random.randint(70, 90)
        st.session_state.water_level_history.append({
            "time": time_point.strftime("%H:%M"),
            "level": level
        })
if "drain_override" not in st.session_state:
    st.session_state.drain_override = False
if "emergency_shutdown" not in st.session_state:
    st.session_state.emergency_shutdown = False

# ------------------ CSS (Enhanced with Animations) ------------------
st.markdown("""
<style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
    
    :root {
        --primary: #4a90ff;
        --success: #28a745;
        --warning: #ff9800;
        --danger: #dc3545;
        --emergency: #ff0000;
        --info: #17a2b8;
        --light: #f8f9fa;
        --dark: #343a40;
    }
    
    body { 
        background: linear-gradient(135deg, #f4f7f6 0%, #e8f4f8 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Card Styles */
    .card {
        background: #ffffff;
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0 6px 15px rgba(0,0,0,0.08);
        margin-bottom: 18px;
        transition: all 0.3s ease;
        border-left: 4px solid var(--primary);
    }
    
    .card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.12);
    }
    
    .card.warning {
        border-left-color: var(--warning);
        background: linear-gradient(to right, #fff3cd 0%, #fff8e1 100%);
        animation: pulse 2s infinite;
    }
    
    .card.success {
        border-left-color: var(--success);
        background: linear-gradient(to right, #e8f5e9 0%, #f1f8e9 100%);
    }
    
    .card.danger {
        border-left-color: var(--danger);
        background: linear-gradient(to right, #f8d7da 0%, #fde8e8 100%);
        animation: dangerPulse 1.5s infinite;
    }
    
    .card.emergency {
        border-left-color: var(--emergency);
        background: linear-gradient(to right, #ffcccc 0%, #ffe6e6 100%);
        animation: emergencyPulse 1s infinite;
    }
    
    .card.info {
        border-left-color: var(--info);
        background: linear-gradient(to right, #d1ecf1 0%, #e8f4f8 100%);
    }
    
    /* Animations */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 152, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 152, 0, 0); }
    }
    
    @keyframes dangerPulse {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    
    @keyframes emergencyPulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.6); }
        50% { box-shadow: 0 0 0 15px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    
    @keyframes slideIn {
        from { transform: translateX(-20px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes waterRipple {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    /* Titles and Text */
    .title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #4a90ff, #2e5cb8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    .subtitle {
        color: #666;
        font-size: 16px;
        margin-bottom: 20px;
    }
    
    /* Badge */
    .badge {
        background: var(--primary);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 0;
    }
    
    .badge.success { background: var(--success); }
    .badge.warning { background: var(--warning); }
    .badge.danger { background: var(--danger); }
    .badge.emergency { 
        background: var(--emergency);
        animation: emergencyPulse 1s infinite;
    }
    .badge.info { background: var(--info); }
    
    /* Tank Animation */
    .tank-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin: 25px 0;
    }
    
    .tank {
        width: 140px;
        height: 240px;
        border-radius: 18px;
        border: 4px solid #333;
        margin: auto;
        position: relative;
        overflow: hidden;
        background: #f8f9fa;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.1);
    }
    
    .water {
        position: absolute;
        bottom: 0;
        width: 100%;
        background: linear-gradient(180deg, #4a90ff 0%, #2e5cb8 100%);
        background-size: 200% 200%;
        text-align: center;
        color: white;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: height 1.5s ease;
        animation: waterRipple 3s ease infinite;
    }
    
    .water-level-text {
        position: absolute;
        top: 10px;
        left: 0;
        width: 100%;
        text-align: center;
        font-weight: bold;
        font-size: 18px;
        color: var(--dark);
        z-index: 10;
    }
    
    /* Toggle Switch Customization */
    .stToggle {
        margin: 15px 0;
    }
    
    .stToggle > label {
        font-weight: 600;
    }
    
    /* Button Styles */
    .stButton > button {
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.3s;
        border: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    /* Progress Bar */
    .progress-container {
        width: 100%;
        background-color: #e9ecef;
        border-radius: 10px;
        margin: 10px 0;
        height: 20px;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
        line-height: 20px;
        font-size: 12px;
        transition: width 0.5s ease;
    }
    
    /* Suggestion Cards */
    .suggestion-card {
        background: #f8f9fa;
        padding: 12px 15px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid var(--success);
        animation: slideIn 0.5s ease;
    }
    
    .emergency-card {
        background: #ffe6e6;
        padding: 12px 15px;
        border-radius: 10px;
        margin: 8px 0;
        border-left: 4px solid var(--emergency);
        animation: shake 0.5s ease;
        border: 2px solid #ff0000;
    }
    
    /* Disabled Controls */
    .disabled-control {
        opacity: 0.6;
        cursor: not-allowed;
        position: relative;
    }
    
    .disabled-control::after {
        content: "🔒 AUTO-CONTROLLED";
        position: absolute;
        top: -25px;
        right: 0;
        background: var(--danger);
        color: white;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 10px;
        font-weight: bold;
    }
    
    /* Tab Styles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ UTILITY FUNCTIONS ------------------
def add_notification(title, message, notification_type="info"):
    """Add a new notification to the list"""
    new_id = max([n["id"] for n in st.session_state.notifications], default=0) + 1
    st.session_state.notifications.insert(0, {
        "id": new_id,
        "title": title,
        "message": message,
        "time": "Just now",
        "type": notification_type,
        "read": False
    })
    
    # Limit notifications to 10
    if len(st.session_state.notifications) > 10:
        st.session_state.notifications = st.session_state.notifications[:10]

def mark_all_notifications_read():
    """Mark all notifications as read"""
    for notification in st.session_state.notifications:
        notification["read"] = True

def enforce_water_level_control():
    """Enforce water level control logic"""
    water_level = st.session_state.water_level
    
    # CRITICAL: If water reaches 95%, automatically CLOSE drain and don't allow increase
    if water_level >= 95 and st.session_state.auto_mode:
        # Force close the drain
        if st.session_state.drain_open:
            st.session_state.drain_open = False
            st.session_state.last_auto_action = "emergency_close_95"
            add_notification("🚨 EMERGENCY SHUTDOWN", 
                           f"Water level CRITICAL at {water_level:.1f}%. Drainage CLOSED automatically to prevent overflow!", 
                           "emergency")
            st.session_state.emergency_shutdown = True
        
        # Prevent any further increase in water level
        if st.session_state.water_level > 95:
            st.session_state.water_level = 95  # Cap at 95%
    
    # If water is between 90-95%, open drain to reduce level
    elif water_level >= 90 and st.session_state.auto_mode and not st.session_state.drain_open:
        if st.session_state.last_auto_action != "open_90":
            st.session_state.drain_open = True
            st.session_state.last_auto_action = "open_90"
            add_notification("⚠️ High Water Level", 
                           f"Water level reached {water_level:.1f}%. Drainage automatically OPENED.", 
                           "warning")
    
    # If water drops below 30%, close drain to conserve water
    elif water_level <= 30 and st.session_state.auto_mode and st.session_state.drain_open:
        if st.session_state.last_auto_action != "close_30":
            st.session_state.drain_open = False
            st.session_state.last_auto_action = "close_30"
            add_notification("💧 Low Water Level", 
                           f"Water level dropped to {water_level:.1f}%. Drainage CLOSED to conserve water.", 
                           "info")
            st.session_state.emergency_shutdown = False

def simulate_water_level_change():
    """Simulate water level changes based on drainage status"""
    # First enforce control logic
    enforce_water_level_control()
    
    # Calculate water level change based on drainage status
    if st.session_state.drain_open:
        # When drain is open, water level decreases
        if st.session_state.emergency_shutdown:
            # During emergency shutdown, drain is closed, so water shouldn't decrease
            change = 0
        else:
            change = -random.uniform(1.0, 3.0)
    else:
        # When drain is closed, water level increases (simulating rain)
        if st.session_state.water_level >= 95:
            # Critical level - prevent any increase
            change = 0
        elif st.session_state.water_level >= 90:
            # High level - minimal increase
            change = random.uniform(0.1, 0.5)
        else:
            # Normal increase
            change = random.uniform(0.5, 2.0)
    
    # Apply the change
    new_level = st.session_state.water_level + change
    
    # Ensure water level stays within 0-100%
    new_level = max(0, min(100, new_level))
    
    # During emergency shutdown (95%+), cap at 95% and prevent increase
    if st.session_state.emergency_shutdown and new_level > 95:
        new_level = 95
    
    st.session_state.water_level = new_level
    
    # Add to history
    current_time = datetime.now().strftime("%H:%M")
    st.session_state.water_level_history.append({
        "time": current_time,
        "level": new_level
    })
    
    # Keep only last 24 entries
    if len(st.session_state.water_level_history) > 24:
        st.session_state.water_level_history = st.session_state.water_level_history[-24:]

def get_water_level_status(level):
    """Get status based on water level"""
    if level >= 95:
        return "emergency", "🚨 EMERGENCY - SYSTEM LOCKED"
    elif level >= 90:
        return "danger", "CRITICAL - Flood Risk"
    elif level >= 75:
        return "warning", "HIGH - Drainage Recommended"
    elif level >= 40:
        return "info", "NORMAL - Optimal"
    else:
        return "success", "LOW - Irrigation Needed"

# ------------------ SIDEBAR (Notifications & Settings) ------------------
with st.sidebar:
    st.markdown("<div class='title'><i class='fas fa-cogs'></i> Control Panel</div>", unsafe_allow_html=True)
    
    # Auto Mode Toggle
    st.markdown("### 🤖 Auto Control Settings")
    auto_mode = st.toggle(
        "**Automatic Mode**",
        value=st.session_state.auto_mode,
        help="When enabled, system will automatically control drainage based on water level rules"
    )
    
    if auto_mode != st.session_state.auto_mode:
        st.session_state.auto_mode = auto_mode
        status = "ENABLED" if auto_mode else "DISABLED"
        add_notification(f"Auto Mode {status}", 
                       f"Automatic control system {status.lower()}.", 
                       "info" if auto_mode else "warning")
        st.rerun()
    
    # Emergency Override
    if st.session_state.emergency_shutdown:
        st.markdown("### 🚨 Emergency Control")
        if st.button("RESET EMERGENCY LOCK", type="primary", use_container_width=True):
            st.session_state.emergency_shutdown = False
            st.session_state.water_level = 85  # Reset to safe level
            add_notification("Emergency Reset", "Emergency lock reset. System returning to normal operation.", "success")
            st.rerun()
    
    # Manual Drainage Control (with restrictions)
    st.markdown("### 👨‍🔧 Manual Control")
    
    # Show warning if manual control is restricted
    if st.session_state.emergency_shutdown:
        st.warning("🚨 Manual control LOCKED during emergency shutdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        open_disabled = st.session_state.emergency_shutdown or (st.session_state.auto_mode and st.session_state.water_level >= 95)
        if st.button("Open Drain", 
                    type="primary", 
                    use_container_width=True,
                    disabled=open_disabled):
            st.session_state.drain_open = True
            st.session_state.drain_override = True
            add_notification("Drainage Manually Opened", "Drainage valve opened manually", "info")
    
    with col2:
        close_disabled = st.session_state.emergency_shutdown or (st.session_state.auto_mode and st.session_state.water_level <= 30)
        if st.button("Close Drain", 
                    type="secondary", 
                    use_container_width=True,
                    disabled=close_disabled):
            st.session_state.drain_open = False
            st.session_state.drain_override = True
            add_notification("Drainage Manually Closed", "Drainage valve closed manually", "warning")
    
    # Water Level Simulation Controls
    st.markdown("### 💧 Water Level Simulation")
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        # Prevent increase if at 95% or in emergency
        increase_disabled = st.session_state.water_level >= 95 or st.session_state.emergency_shutdown
        if st.button("+10%", 
                    use_container_width=True,
                    disabled=increase_disabled):
            if not increase_disabled:
                st.session_state.water_level = min(100, st.session_state.water_level + 10)
                # Check if this triggers emergency
                if st.session_state.water_level >= 95:
                    enforce_water_level_control()
    with sim_col2:
        if st.button("-10%", use_container_width=True):
            st.session_state.water_level = max(0, st.session_state.water_level - 10)
    
    # Notifications Section
    st.markdown("---")
    st.markdown("<div class='title'><i class='fas fa-bell'></i> Notifications</div>", unsafe_allow_html=True)
    
    # Count unread notifications
    unread_count = sum(1 for n in st.session_state.notifications if not n["read"])
    
    if unread_count > 0:
        st.markdown(f"<div class='badge danger'>{unread_count} unread</div>", unsafe_allow_html=True)
    
    if st.button("Mark All as Read", use_container_width=True):
        mark_all_notifications_read()
        st.rerun()
    
    # Display notifications
    for notification in st.session_state.notifications[:5]:  # Show only 5 most recent
        icon_map = {
            "emergency": "🚨",
            "warning": "⚠️",
            "success": "✅",
            "info": "ℹ️"
        }
        icon = icon_map.get(notification["type"], "🔔")
        st.markdown(f"""
        <div class='card {notification["type"]}' style='padding: 12px; margin: 8px 0;'>
            <b>{icon} {notification["title"]}</b><br>
            <small>{notification["message"]}</small><br>
            <small style='color: #666;'>{notification["time"]}</small>
        </div>
        """, unsafe_allow_html=True)

# ------------------ HEADER ------------------
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.markdown("<div class='title'>🌧️ Smart Rain Protection System</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>மழை சேதத்தை முன்கூட்டியே தடுக்கும் புத்திசாலி அமைப்பு</div>", unsafe_allow_html=True)

with col_header2:
    # Display water level with status
    status_class, status_text = get_water_level_status(st.session_state.water_level)
    if st.session_state.emergency_shutdown:
        status_text = "🚨 EMERGENCY LOCK ACTIVE"
    st.markdown(f"<div class='badge {status_class}' style='margin-top: 10px; font-size: 14px;'>{st.session_state.water_level:.1f}% - {status_text}</div>", unsafe_allow_html=True)

# ------------------ EMERGENCY WARNING (if applicable) ------------------
if st.session_state.emergency_shutdown:
    st.markdown(f"""
    <div class="card emergency">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 36px; margin-right: 15px;">🚨</div>
            <div>
                <b style="font-size: 20px; color: #ff0000;">EMERGENCY SHUTDOWN ACTIVE</b><br>
                Water level reached CRITICAL {st.session_state.water_level:.1f}%<br>
                <span style="color: #d35400;">
                    • Drainage system LOCKED CLOSED<br>
                    • Water level increase PREVENTED<br>
                    • Manual override DISABLED<br>
                    • Safety protocols ENGAGED
                </span><br>
                <small><i class="fas fa-clock"></i> Emergency activated at: {datetime.now().strftime("%H:%M:%S")}</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif st.session_state.water_level >= 90:
    st.markdown(f"""
    <div class="card danger">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 32px; margin-right: 15px;">⚠️</div>
            <div>
                <b>HIGH WATER LEVEL WARNING</b><br>
                <span style="color: #d35400;">Water level at {st.session_state.water_level:.1f}% - Approaching critical level</span><br>
                <b>System will automatically:</b><br>
                • CLOSE drain at 95% (Emergency Lock)<br>
                • PREVENT water level increase<br>
                • Disable manual controls<br>
                <small><i class="fas fa-clock"></i> Current prediction: Critical in {max(0, (95 - st.session_state.water_level)/2):.0f} minutes</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------ MAIN DASHBOARD TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💧 Water Management", "🌱 Crop Advisory", "📈 Analytics"])

with tab1:
    # WEATHER CARDS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="card info">
            <div style="font-size: 24px; color: #4a90ff;">🌧️</div>
            <b>Rain Forecast</b><br>
            <h3>Heavy Rain</h3>
            <small>Next 12 hours</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <div style="font-size: 24px; color: #17a2b8;">💧</div>
            <b>Humidity</b><br>
            <h3>92%</h3>
            <small>Very High</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <div style="font-size: 24px; color: #ff9800;">🌬️</div>
            <b>Wind Speed</b><br>
            <h3>45 km/h</h3>
            <small>Strong Winds</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="card success">
            <div style="font-size: 24px; color: #28a745;">🌡️</div>
            <b>Temperature</b><br>
            <h3>26°C</h3>
            <small>Cool & Rainy</small>
        </div>
        """, unsafe_allow_html=True)

    # WATER LEVEL VISUALIZATION
    st.markdown("## 💧 Water Level Monitoring")
    
    # Tank visualization
    water_height = st.session_state.water_level
    
    # Determine water color based on level
    if water_height >= 95:
        water_color = "linear-gradient(180deg, #ff0000 0%, #cc0000 100%)"
        border_effect = "box-shadow: 0 0 20px rgba(255, 0, 0, 0.7);"
    elif water_height >= 90:
        water_color = "linear-gradient(180deg, #dc3545 0%, #c82333 100%)"
        border_effect = "box-shadow: 0 0 15px rgba(220, 53, 69, 0.5);"
    elif water_height >= 75:
        water_color = "linear-gradient(180deg, #ff9800 0%, #e68900 100%)"
        border_effect = ""
    else:
        water_color = "linear-gradient(180deg, #4a90ff 0%, #2e5cb8 100%)"
        border_effect = ""
    
    st.markdown(f"""
    <div class="tank-container">
        <div class="water-level-text">Water Level: {water_height:.1f}%</div>
        <div class="tank" style="{border_effect}">
            <div class="water" style="height:{water_height}%; background: {water_color};">
                {water_height:.1f}%
            </div>
        </div>
        <div style="margin-top: 10px; font-size: 14px; color: #666; text-align: center;">
            <div>Drain Status: <b style="color: {'#28a745' if st.session_state.drain_open else '#dc3545'}">{'OPEN' if st.session_state.drain_open else 'CLOSED'}</b></div>
            <div>Auto Mode: <b style="color: {'#28a745' if st.session_state.auto_mode else '#6c757d'}">{'ON' if st.session_state.auto_mode else 'OFF'}</b></div>
            <div>Emergency Lock: <b style="color: {'#dc3545' if st.session_state.emergency_shutdown else '#6c757d'}">{'ACTIVE' if st.session_state.emergency_shutdown else 'Inactive'}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Progress bar for water level
    if water_height >= 95:
        progress_color = "#ff0000"
    elif water_height >= 90:
        progress_color = "#dc3545"
    elif water_height >= 75:
        progress_color = "#ff9800"
    else:
        progress_color = "#4a90ff"
    
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {water_height}%; background-color: {progress_color};">
            {water_height:.1f}%
        </div>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666; margin-top: 5px;">
        <span>0%</span>
        <span>Safe Zone</span>
        <span style="color: #ff9800;">75% Warning</span>
        <span style="color: #dc3545;">90% Critical</span>
        <span style="color: #ff0000;">95% EMERGENCY</span>
        <span>100%</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Drainage Control
    st.markdown("### 🎛️ Drainage Control")
    
    # Show if controls are disabled
    if st.session_state.emergency_shutdown:
        st.markdown("""
        <div class="emergency-card">
            <div style="display: flex; align-items: center;">
                <div style="font-size: 24px; margin-right: 10px;">🔒</div>
                <div>
                    <b>CONTROLS LOCKED - EMERGENCY MODE</b><br>
                    Drainage system locked CLOSED to prevent overflow.<br>
                    Reset emergency in sidebar to regain control.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    col_drain1, col_drain2 = st.columns([3, 1])
    with col_drain1:
        # Determine if toggle should be disabled
        toggle_disabled = st.session_state.emergency_shutdown or (
            st.session_state.auto_mode and (
                (st.session_state.water_level >= 95) or 
                (st.session_state.water_level <= 30 and not st.session_state.drain_open)
            )
        )
        
        # Toggle for drainage with enhanced styling
        toggle_label = "**Drainage Valve Control**"
        if toggle_disabled and st.session_state.auto_mode:
            toggle_label += " 🔒 (Auto-controlled)"
        
        new_drain_state = st.toggle(
            toggle_label,
            value=st.session_state.drain_open,
            key="drain_toggle",
            disabled=toggle_disabled,
            help="Toggle to OPEN/CLOSE the drainage valve. When Auto Mode is ON, system will override based on safety rules."
        )
        
        if not toggle_disabled and new_drain_state != st.session_state.drain_open:
            st.session_state.drain_open = new_drain_state
            st.session_state.drain_override = True
            status = "OPENED" if new_drain_state else "CLOSED"
            add_notification(f"Drainage Valve {status}", 
                           f"Drainage valve manually {status.lower()}.", 
                           "info" if new_drain_state else "warning")
            st.rerun()
    
    with col_drain2:
        status_color = "success" if st.session_state.drain_open else "warning"
        if st.session_state.emergency_shutdown:
            status_color = "emergency"
        
        st.markdown(f"""
        <div class="card {status_color}" style="text-align: center; padding: 10px;">
            <h3>{'OPEN' if st.session_state.drain_open else 'CLOSED'}</h3>
            <small>Valve Status</small>
            <br>
            <small>
                { '🔒 Auto-Locked' if st.session_state.emergency_shutdown else 
                  '🤖 Auto-controlled' if st.session_state.auto_mode and not st.session_state.drain_override else 
                  '👨‍🔧 Manual' }
            </small>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("## 🌊 Smart Water Management")
    
    # Water Pipeline Map
    st.markdown("""
    <div class="card">
        <b>Water Pipeline Network – M.K. Kottai</b>
        <span class="badge {'danger' if st.session_state.emergency_shutdown else 'success'}">
            {'🚨 EMERGENCY MODE' if st.session_state.emergency_shutdown else 'Live Status: Normal Flow'}
        </span>
        <p style="color: #666; margin-top: 5px;">Real-time monitoring of irrigation channels and drainage systems</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Interactive Map
    m = folium.Map(location=[10.79, 78.70], zoom_start=13, tiles='CartoDB positron')
    
    # Add pipeline with color based on status
    line_color = "#ff0000" if st.session_state.emergency_shutdown else "#4a90ff"
    
    folium.PolyLine(
        [[10.79,78.69],[10.80,78.71],[10.81,78.72],[10.82,78.70]], 
        color=line_color, 
        weight=4,
        opacity=0.7,
        popup="Main Irrigation Pipeline"
    ).add_to(m)
    
    # Add markers with different colors
    folium.Marker(
        [10.79,78.69], 
        tooltip="Distribution Point",
        icon=folium.Icon(color="blue", icon="tint", prefix="fa")
    ).add_to(m)
    
    # Drainage control point with status-based color
    drain_color = "red" if st.session_state.emergency_shutdown else ("green" if st.session_state.drain_open else "orange")
    
    folium.Marker(
        [10.80,78.71], 
        tooltip=f"Drainage Control Point - {'OPEN' if st.session_state.drain_open else 'CLOSED'}",
        icon=folium.Icon(color=drain_color, icon="cog", prefix="fa")
    ).add_to(m)
    
    folium.Marker(
        [10.82,78.70], 
        tooltip="Water Reservoir",
        icon=folium.Icon(color="lightblue", icon="water", prefix="fa")
    ).add_to(m)
    
    # Add emergency zone if in emergency mode
    if st.session_state.emergency_shutdown:
        folium.Circle(
            location=[10.80, 78.71],
            radius=300,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.2,
            popup='Emergency Zone - Drainage Locked'
        ).add_to(m)
    
    st_folium(m, height=300, width=700)
    
    # Water Level History Chart
    st.markdown("### 📈 Water Level History (Last 24 hours)")
    
    # Create a simple line chart using streamlit
    if st.session_state.water_level_history:
        history_df = pd.DataFrame(st.session_state.water_level_history)
        
        # Add threshold lines
        chart_data = history_df.set_index('time')['level']
        
        # Create a line chart with thresholds
        st.line_chart(chart_data, height=250)
        
        # Display threshold information
        st.markdown("""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin-top: 10px;">
            <small><b>Thresholds:</b></small><br>
            <small><span style="color: #4a90ff;">▬ Normal Operation (0-74%)</span> | 
            <span style="color: #ff9800;">▬ Warning Zone (75-89%)</span> | 
            <span style="color: #dc3545;">▬ Critical Zone (90-94%)</span> | 
            <span style="color: #ff0000;">▬ Emergency Lock (95%+)</span></small>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    st.markdown("## 🌱 Crop Advisory & Suggestions")
    
    # Emergency suggestions if applicable
    if st.session_state.emergency_shutdown:
        st.markdown("""
        <div class="emergency-card">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="font-size: 32px; margin-right: 10px;">🚨</div>
                <div><b>EMERGENCY ACTIONS REQUIRED</b></div>
            </div>
            <div style="margin-left: 15px;">
                1. <b>ACTIVATE BACKUP DRAINAGE</b> - Use manual pumps if available<br>
                2. <b>EVACUATE LOW-LYING CROPS</b> - Move portable crops to higher ground<br>
                3. <b>CONTACT EMERGENCY SERVICES</b> - Local flood control: 108<br>
                4. <b>MONITOR EMBANKMENTS</b> - Check for signs of breach<br>
                5. <b>SECURE EQUIPMENT</b> - Move machinery to safe locations
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Regular suggestions
    st.markdown("""
    <div class="card success">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="font-size: 24px; margin-right: 10px;">💡</div>
            <div><b>Smart Suggestions for Current Conditions</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Dynamic suggestions based on conditions
    suggestions_to_show = st.session_state.suggestions.copy()
    
    # Add conditional suggestions based on water level
    if st.session_state.water_level >= 95:
        suggestions_to_show = [
            "IMMEDIATE: Activate backup drainage systems",
            "URGENT: Check field embankments for integrity",
            "PRIORITY: Move equipment to higher ground",
            "ALERT: Monitor water level every 15 minutes"
        ]
    elif st.session_state.water_level >= 90:
        suggestions_to_show.insert(0, "URGENT: Prepare for emergency drainage procedures")
        suggestions_to_show.insert(1, "WARNING: System will auto-lock at 95% - Take preventive action")
    elif st.session_state.water_level >= 75:
        suggestions_to_show.insert(0, "Monitor water level closely - approaching critical zone")
    
    # Add suggestion about auto-control
    if st.session_state.auto_mode:
        suggestions_to_show.insert(0, f"Auto-control ACTIVE - System will {'LOCK at 95%' if st.session_state.water_level >= 90 else 'manage drainage automatically'}")

    for i, suggestion in enumerate(suggestions_to_show[:6]):  # Show top 6 suggestions
        if "IMMEDIATE" in suggestion or "URGENT" in suggestion:
            icon = "🚨"
            card_class = "emergency-card"
        elif "WARNING" in suggestion or "ALERT" in suggestion:
            icon = "⚠️"
            card_class = "emergency-card"
        else:
            icon = "✅"
            card_class = "suggestion-card"
        
        st.markdown(f"""
        <div class="{card_class}">
            <div style="display: flex; align-items: flex-start;">
                <div style="font-size: 18px; margin-right: 10px;">{icon}</div>
                <div>{suggestion}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Crop Protection Tips
    st.markdown("""
    <div class="card info" style="margin-top: 20px;">
        <b>🌾 Crop Protection Guidelines for Heavy Rain</b>
        
        <div style="margin-top: 15px;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 10px;">
                <div style="background: #e8f5e9; padding: 5px 10px; border-radius: 5px; margin-right: 10px;">1</div>
                <div><b>Drainage Maintenance</b><br>மழைக்கு முன் வடிகால் பாதைகளை சுத்தம் செய்யவும்.</div>
            </div>
            
            <div style="display: flex; align-items: flex-start; margin-bottom: 10px;">
                <div style="background: #e8f5e9; padding: 5px 10px; border-radius: 5px; margin-right: 10px;">2</div>
                <div><b>Fertilizer Delay</b><br>உரம் இடுவதை தற்காலிகமாக தவிர்க்கவும்.</div>
            </div>
            
            <div style="display: flex; align-items: flex-start; margin-bottom: 10px;">
                <div style="background: #e8f5e9; padding: 5px 10px; border-radius: 5px; margin-right: 10px;">3</div>
                <div><b>Support Crops</b><br>பயிர்களுக்கு முட்டுக் கொடுக்கவும்.</div>
            </div>
            
            <div style="display: flex; align-items: flex-start;">
                <div style="background: #e8f5e9; padding: 5px 10px; border-radius: 5px; margin-right: 10px;">4</div>
                <div><b>Pest Monitoring</b><br>Increased humidity may lead to pest outbreaks.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab4:
    st.markdown("## 📊 System Analytics & Safety Status")
    
    col_analytics1, col_analytics2 = st.columns(2)
    
    with col_analytics1:
        # Safety Status Card
        if st.session_state.emergency_shutdown:
            safety_status = "🚨 EMERGENCY LOCK"
            safety_color = "emergency"
            safety_icon = "🔒"
        elif st.session_state.water_level >= 90:
            safety_status = "⚠️ HIGH ALERT"
            safety_color = "danger"
            safety_icon = "⚠️"
        elif st.session_state.water_level >= 75:
            safety_status = "🟡 WARNING"
            safety_color = "warning"
            safety_icon = "⚠️"
        else:
            safety_status = "✅ NORMAL"
            safety_color = "success"
            safety_icon = "✅"
        
        st.markdown(f"""
        <div class="card {safety_color}">
            <b>{safety_icon} System Safety Status</b><br>
            <div style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                    <span>Overall Status:</span>
                    <span class="badge {safety_color}">{safety_status}</span>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>Auto-Control:</span>
                    <span><b>{'ACTIVE' if st.session_state.auto_mode else 'INACTIVE'}</b></span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {'100' if st.session_state.auto_mode else '0'}%; background-color: {'#28a745' if st.session_state.auto_mode else '#6c757d'};">
                        {'100%' if st.session_state.auto_mode else '0%'}
                    </div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin: 15px 0 8px 0;">
                    <span>Safety Margin:</span>
                    <span><b>{100 - st.session_state.water_level:.1f}%</b></span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {100 - st.session_state.water_level}%; background-color: {'#dc3545' if (100 - st.session_state.water_level) < 10 else '#ff9800' if (100 - st.session_state.water_level) < 25 else '#28a745'};">
                        {100 - st.session_state.water_level:.1f}%
                    </div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin: 15px 0 8px 0;">
                    <span>Time to Critical:</span>
                    <span><b>{max(0, (95 - st.session_state.water_level)/2):.1f} min</b></span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {(st.session_state.water_level/95)*100}%; background-color: {'#dc3545' if st.session_state.water_level >= 90 else '#ff9800' if st.session_state.water_level >= 75 else '#4a90ff'};">
                        {(st.session_state.water_level/95)*100:.1f}%
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_analytics2:
        st.markdown("""
        <div class="card">
            <b>📡 Sensor & Control Status</b><br>
            <div style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><i class="fas fa-tint"></i> Water Level Sensor</span>
                    <span class="badge {'danger' if st.session_state.water_level >= 95 else 'success'}">
                        {'CRITICAL' if st.session_state.water_level >= 95 else 'Active'}
                    </span>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><i class="fas fa-cog"></i> Drainage Valve</span>
                    <span class="badge {'success' if st.session_state.drain_open else 'warning'}">
                        {'OPEN' if st.session_state.drain_open else 'CLOSED'}
                    </span>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><i class="fas fa-robot"></i> Auto-Control</span>
                    <span class="badge {'success' if st.session_state.auto_mode else 'info'}">
                        {'ACTIVE' if st.session_state.auto_mode else 'Manual'}
                    </span>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span><i class="fas fa-shield-alt"></i> Emergency System</span>
                    <span class="badge {'emergency' if st.session_state.emergency_shutdown else 'success'}">
                        {'ACTIVE' if st.session_state.emergency_shutdown else 'Standby'}
                    </span>
                </div>
                
                <div style="display: flex; justify-content: space-between;">
                    <span><i class="fas fa-satellite-dish"></i> Communication</span>
                    <span class="badge success">Online</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # System Rules Panel
    st.markdown("""
    <div class="card info">
        <b>⚙️ Automatic Control Rules</b>
        <div style="margin-top: 15px; background: #f8f9fa; padding: 15px; border-radius: 10px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background: #ff0000; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;">!</div>
                        <div><b>95%+ EMERGENCY</b></div>
                    </div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li>Drainage automatically CLOSED</li>
                        <li>Water increase PREVENTED</li>
                        <li>Manual controls LOCKED</li>
                        <li>Emergency notifications sent</li>
                    </ul>
                </div>
                
                <div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background: #dc3545; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;">!</div>
                        <div><b>90-94% CRITICAL</b></div>
                    </div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li>Drainage automatically OPENED</li>
                        <li>Warning notifications sent</li>
                        <li>Manual override allowed</li>
                        <li>System monitors closely</li>
                    </ul>
                </div>
                
                <div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background: #ff9800; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;">!</div>
                        <div><b>75-89% WARNING</b></div>
                    </div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li>Drainage may be opened</li>
                        <li>Advisory notifications sent</li>
                        <li>Full manual control</li>
                        <li>Monitor water level</li>
                    </ul>
                </div>
                
                <div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="background: #28a745; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-weight: bold;">✓</div>
                        <div><b>30-74% NORMAL</b></div>
                    </div>
                    <ul style="margin: 0; padding-left: 20px; font-size: 14px;">
                        <li>Optimal water levels</li>
                        <li>Drainage as needed</li>
                        <li>Full system control</li>
                        <li>Normal operation</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------ FOOTER ------------------
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.markdown("<small>🛠️ <b>System Version:</b> 3.0.1 (Emergency Control)</small>", unsafe_allow_html=True)
with footer_col2:
    current_time = datetime.now().strftime("%H:%M:%S")
    status_icon = "🔴" if st.session_state.emergency_shutdown else "🟢"
    st.markdown(f"<small>📶 <b>Last Updated:</b> {current_time} {status_icon}</small>", unsafe_allow_html=True)
with footer_col3:
    st.markdown("<small>📍 <b>Location:</b> M.K. Kottai, Tamil Nadu</small>", unsafe_allow_html=True)

# ------------------ AUTO SIMULATION ------------------
# Simulate water level changes automatically
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

current_time = time.time()
if current_time - st.session_state.last_update > 3:  # Update every 3 seconds
    simulate_water_level_change()
    st.session_state.last_update = current_time
    
    # Add occasional notifications for simulation
    if random.random() < 0.1:  # 10% chance each update
        if st.session_state.water_level >= 95:
            # Already handled by emergency system
            pass
        elif st.session_state.water_level > 90:
            add_notification("High Water Level Warning", 
                           f"Water level at {st.session_state.water_level:.1f}%. Approaching emergency lock at 95%.", 
                           "warning")
        elif st.session_state.water_level > 85:
            add_notification("Water Level Rising", 
                           f"Water level at {st.session_state.water_level:.1f}%. Monitor closely.", 
                           "info")
    
    # Force a rerun to update the UI
    st.rerun()

# Add a refresh button in sidebar to manually update
if st.sidebar.button("🔄 Simulate Water Change", use_container_width=True):
    simulate_water_level_change()
    st.rerun()

# Display auto-control status in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="background: {'#ffe6e6' if st.session_state.emergency_shutdown else '#e8f5e9'}; 
                    padding: 10px; 
                    border-radius: 10px; 
                    border-left: 4px solid {'#ff0000' if st.session_state.emergency_shutdown else '#28a745'};">
    <small><b>Auto-Control Status</b></small><br>
    <small>System: <b>{'🔒 LOCKED' if st.session_state.emergency_shutdown else '🤖 ACTIVE' if st.session_state.auto_mode else '👨‍🔧 MANUAL'}</b></small><br>
    <small>Water: <b>{st.session_state.water_level:.1f}%</b></small><br>
    <small>Drain: <b>{'🔓 OPEN' if st.session_state.drain_open else '🔒 CLOSED'}</b></small>
</div>
""", unsafe_allow_html=True)