import streamlit as st
import time
import json
from datetime import datetime, timedelta
from streamlit_folium import st_folium
import folium
import random
import pandas as pd
import numpy as np
import hashlib
import uuid
import base64
from io import BytesIO
import sqlite3
import os
import subprocess
import sys

# Set page configuration
st.set_page_config(
    page_title="AgriGurd",
    page_icon="🌾",
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ------------------ DATABASE SETUP ------------------
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('smart_agriculture.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  user_id TEXT UNIQUE NOT NULL,
                  farm_name TEXT NOT NULL,
                  location TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  is_admin INTEGER DEFAULT 0)''')
    
    # Sensor data table
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  solar_input REAL DEFAULT 0,
                  battery_level REAL DEFAULT 0,
                  water_level REAL DEFAULT 0,
                  drain_status INTEGER DEFAULT 0,
                  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(user_id))''')
    
    # Notifications table
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  title TEXT NOT NULL,
                  message TEXT NOT NULL,
                  notification_type TEXT DEFAULT 'info',
                  is_read INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Water level history table
    c.execute('''CREATE TABLE IF NOT EXISTS water_level_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  water_level REAL NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Check if admin user exists, if not create it
    admin_hash = hashlib.sha256("admin@1234".encode()).hexdigest()
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO users (username, password_hash, user_id, farm_name, location, is_admin)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  ('admin', admin_hash, 'ADMIN001', 'System Administration', 'Control Center', 1))
    else:
        # Ensure admin user has is_admin set to 1
        c.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ------------------ AUDIO FILES (Base64 Encoded) ------------------
EMERGENCY_SOUND = """
data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==
"""

WARNING_SOUND = """
data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==
"""

INFO_SOUND = """
data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==
"""

SUCCESS_SOUND = """
data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==
"""

# ------------------ FIX FOR ST_FOLIUM ERROR ------------------
def safe_st_folium(m, height=300):
    """Safe wrapper for st_folium that handles width issues"""
    try:
        return st_folium(m, height=height, use_container_width=True)
    except Exception as e:
        st.error(f"Map loading error: {str(e)}")
        # Fallback to simple map display
        st.map(pd.DataFrame({'lat': [10.79], 'lon': [78.70]}), zoom=13)

# ------------------ USER MANAGEMENT WITH SQLite ------------------
class UserManager:
    def __init__(self):
        if "current_user" not in st.session_state:
            st.session_state.current_user = None
        if "current_user_id" not in st.session_state:
            st.session_state.current_user_id = None
        if "is_admin" not in st.session_state:
            st.session_state.is_admin = False
        if "admin_redirect" not in st.session_state:
            st.session_state.admin_redirect = False
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username, password, farm_name, location):
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        # Check if username exists
        c.execute("SELECT username FROM users WHERE username = ?", (username,))
        if c.fetchone():
            conn.close()
            return False, "Username already exists"
        
        user_id = str(uuid.uuid4())[:8]
        password_hash = self.hash_password(password)
        
        try:
            # Insert user
            c.execute('''INSERT INTO users (username, password_hash, user_id, farm_name, location)
                         VALUES (?, ?, ?, ?, ?)''',
                      (username, password_hash, user_id, farm_name, location))
            
            # Initialize sensor data
            initial_water = random.randint(50, 70)
            c.execute('''INSERT INTO sensor_data (user_id, solar_input, battery_level, water_level, drain_status)
                         VALUES (?, ?, ?, ?, ?)''',
                      (user_id, random.randint(800, 1000), random.randint(80, 100), 
                       initial_water, 0))
            
            # Add welcome notification
            c.execute('''INSERT INTO notifications (user_id, title, message, notification_type)
                         VALUES (?, ?, ?, ?)''',
                      (user_id, "Welcome to Smart Agriculture!", 
                       f"Your farm '{farm_name}' is now being monitored", "info"))
            
            # Initialize water level history
            for i in range(24):
                level = random.randint(40, 70)
                c.execute('''INSERT INTO water_level_history (user_id, water_level, created_at)
                             VALUES (?, ?, datetime('now', ?))''',
                         (user_id, level, f'-{23-i} hours'))
            
            conn.commit()
            conn.close()
            return True, user_id
            
        except Exception as e:
            conn.close()
            return False, f"Database error: {str(e)}"
    
    def authenticate(self, username, password):
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        c.execute("SELECT user_id, password_hash, is_admin FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return False, "User not found"
        
        user_id, stored_hash, is_admin = result
        
        # Check for admin credentials
        if username == "admin" and password == "admin@1234":
            st.session_state.current_user = username
            st.session_state.current_user_id = user_id
            st.session_state.is_admin = True
            return True, user_id
        
        if stored_hash == self.hash_password(password):
            st.session_state.current_user = username
            st.session_state.current_user_id = user_id
            st.session_state.is_admin = bool(is_admin)
            return True, user_id
        return False, "Invalid password"
    
    def logout(self):
        st.session_state.current_user = None
        st.session_state.current_user_id = None
        st.session_state.is_admin = False
        st.session_state.admin_redirect = False
        st.rerun()
    
    def get_current_user_data(self):
        if not st.session_state.current_user_id:
            return None, None, None
        
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        # Get user info
        c.execute('''SELECT username, user_id, farm_name, location, created_at, is_admin 
                     FROM users WHERE user_id = ?''', 
                  (st.session_state.current_user_id,))
        user_row = c.fetchone()
        
        if not user_row:
            conn.close()
            return None, None, None
        
        username, user_id, farm_name, location, created_at, is_admin = user_row
        
        # Get sensor data
        c.execute('''SELECT solar_input, battery_level, water_level, drain_status, last_update
                     FROM sensor_data WHERE user_id = ? ORDER BY last_update DESC LIMIT 1''',
                  (user_id,))
        sensor_row = c.fetchone()
        
        if sensor_row:
            solar_input, battery_level, water_level, drain_status, last_update = sensor_row
            sensor_data = {
                "solar_input": float(solar_input),
                "battery_level": float(battery_level),
                "water_level": float(water_level),
                "drain_status": bool(drain_status),
                "last_update": last_update
            }
        else:
            # Initialize with default values
            sensor_data = {
                "solar_input": random.randint(800, 1000),
                "battery_level": random.randint(80, 100),
                "water_level": random.randint(50, 70),
                "drain_status": False,
                "last_update": datetime.now().isoformat()
            }
            # Save to database
            c.execute('''INSERT INTO sensor_data (user_id, solar_input, battery_level, water_level, drain_status)
                         VALUES (?, ?, ?, ?, ?)''',
                      (user_id, sensor_data["solar_input"], sensor_data["battery_level"], 
                       sensor_data["water_level"], sensor_data["drain_status"]))
            conn.commit()
        
        # Get notifications
        c.execute('''SELECT title, message, notification_type, created_at, is_read
                     FROM notifications WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT 15''',
                  (user_id,))
        notifications = []
        for row in c.fetchall():
            title, message, n_type, created_at, is_read = row
            notifications.append({
                "title": title,
                "message": message,
                "type": n_type,
                "time": created_at,
                "read": bool(is_read)
            })
        
        # Get water level history
        c.execute('''SELECT water_level, created_at 
                     FROM water_level_history 
                     WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT 24''',
                  (user_id,))
        history = []
        for row in c.fetchall():
            level, created_at = row
            history.append({
                "time": created_at[11:16] if len(created_at) > 10 else created_at,  # Extract HH:MM
                "level": float(level)
            })
        
        conn.close()
        
        user_info = {
            "username": username,
            "user_id": user_id,
            "farm_name": farm_name,
            "location": location,
            "created_at": created_at,
            "is_admin": bool(is_admin)
        }
        
        user_data = {
            "notifications": notifications,
            "water_level_history": history,
            "suggestions": [
                "Check drainage channels for blockages",
                "Monitor soil moisture levels",
                "Regularly check sensor connections"
            ]
        }
        
        return user_info, sensor_data, user_data
    
    def update_sensor_data(self, user_id, data):
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        # First check if record exists
        c.execute("SELECT COUNT(*) FROM sensor_data WHERE user_id = ?", (user_id,))
        if c.fetchone()[0] == 0:
            # Insert new record
            c.execute('''INSERT INTO sensor_data (user_id, solar_input, battery_level, water_level, drain_status)
                         VALUES (?, ?, ?, ?, ?)''',
                      (user_id, data.get("solar_input", 0), data.get("battery_level", 0),
                       data.get("water_level", 0), data.get("drain_status", 0)))
        else:
            # Update existing record
            c.execute('''UPDATE sensor_data 
                         SET solar_input = ?, battery_level = ?, water_level = ?, 
                             drain_status = ?, last_update = CURRENT_TIMESTAMP
                         WHERE user_id = ?''',
                      (data.get("solar_input", 0), data.get("battery_level", 0),
                       data.get("water_level", 0), data.get("drain_status", 0),
                       user_id))
        
        # Add to water level history (only if water level changed)
        if "water_level" in data:
            c.execute('''INSERT INTO water_level_history (user_id, water_level)
                         VALUES (?, ?)''',
                      (user_id, data.get("water_level", 0)))
        
        conn.commit()
        conn.close()
    
    def add_notification(self, user_id, title, message, notification_type="info"):
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO notifications (user_id, title, message, notification_type)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, title, message, notification_type))
        
        conn.commit()
        conn.close()
    
    def mark_all_notifications_read(self, user_id):
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        c.execute('''UPDATE notifications SET is_read = 1 WHERE user_id = ?''',
                  (user_id,))
        
        conn.commit()
        conn.close()
    
    def update_water_level(self, user_id, change_percent):
        """Update water level by a specific percentage"""
        conn = sqlite3.connect('smart_agriculture.db')
        c = conn.cursor()
        
        # Get current water level
        c.execute("SELECT water_level FROM sensor_data WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if result:
            current_level = result[0]
            new_level = max(0, min(100, current_level + change_percent))
            
            # Update in database
            c.execute('''UPDATE sensor_data 
                         SET water_level = ?, last_update = CURRENT_TIMESTAMP
                         WHERE user_id = ?''',
                      (new_level, user_id))
            
            # Add to history
            c.execute('''INSERT INTO water_level_history (user_id, water_level)
                         VALUES (?, ?)''',
                      (user_id, new_level))
            
            conn.commit()
            conn.close()
            return new_level
        
        conn.close()
        return None

# Initialize User Manager
user_manager = UserManager()

# ------------------ ENHANCED SOUND ALERT SYSTEM ------------------
def generate_sound_alert(alert_type, user_id):
    """Generate HTML5 audio elements for different alert types with user-specific tracking"""
    # Store last alert time to prevent spam
    if f"last_alert_{user_id}" not in st.session_state:
        st.session_state[f"last_alert_{user_id}"] = {}
    
    current_time = time.time()
    last_time = st.session_state[f"last_alert_{user_id}"].get(alert_type, 0)
    
    # Prevent same alert within 5 seconds
    if current_time - last_time < 5:
        return ""
    
    st.session_state[f"last_alert_{user_id}"][alert_type] = current_time
    
    # Select sound data
    if alert_type == "emergency":
        sound_data = EMERGENCY_SOUND
        volume = 0.7
    elif alert_type == "warning":
        sound_data = WARNING_SOUND
        volume = 0.5
    elif alert_type == "info":
        sound_data = INFO_SOUND
        volume = 0.3
    elif alert_type == "success":
        sound_data = SUCCESS_SOUND
        volume = 0.3
    else:
        return ""
    
    # Generate unique ID for audio element
    audio_id = f"audio_{alert_type}_{int(time.time() * 1000)}"
    
    # Return HTML with JavaScript to play sound
    return f'''
    <audio id="{audio_id}" preload="auto">
        <source src="{sound_data}" type="audio/wav">
    </audio>
    <script>
        (function() {{
            const audio = document.getElementById("{audio_id}");
            if (audio) {{
                audio.volume = {volume};
                // Use a user gesture to enable audio
                const playAudio = () => {{
                    audio.play().catch(e => {{
                        console.log("Audio play failed:", e);
                    }});
                }};
                // Try to play immediately
                playAudio();
                // Also set up for future plays
                document.addEventListener('click', playAudio, {{ once: true }});
            }}
        }})();
    </script>
    '''

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
        --solar: #f39c12;
        --battery: #9b59b6;
        --admin: #9c27b0;
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
    
    .card.solar {
        border-left-color: var(--solar);
        background: linear-gradient(to right, #fef5e7 0%, #fef9e7 100%);
    }
    
    .card.battery {
        border-left-color: var(--battery);
        background: linear-gradient(to right, #f4ecf7 0%, #f9f4fb 100%);
    }
    
    .card.admin {
        border-left-color: var(--admin);
        background: linear-gradient(to right, #f3e5f5 0%, #f9f4fb 100%);
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
    
    .admin-title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #9c27b0, #673ab7);
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
    .badge.solar { background: var(--solar); }
    .badge.battery { background: var(--battery); }
    .badge.admin { 
        background: var(--admin);
        animation: pulse 2s infinite;
    }
    
    /* User ID Badge */
    .user-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .admin-badge {
        background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%);
        color: white;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin: 5px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        animation: pulse 2s infinite;
    }
    
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
    
    /* Login Form Styles */
    .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 30px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    /* User Info Panel */
    .user-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    
    .admin-panel {
        background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%);
        color: white;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 20px;
    }
    
    /* Power Visualization */
    .power-visualization {
        background: linear-gradient(135deg, #fef5e7 0%, #fff9e6 100%);
        border: 2px solid #f39c12;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
    }
    
    .battery-visualization {
        background: linear-gradient(135deg, #f4ecf7 0%, #f9f4fb 100%);
        border: 2px solid #9b59b6;
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
    }
    
    /* Fix for st.folium container */
    .folium-map {
        width: 100% !important;
    }
    
    /* Button styles */
    .stButton > button {
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    
    .admin-btn {
        background: linear-gradient(135deg, #9c27b0 0%, #673ab7 100%) !important;
        color: white !important;
        border: none !important;
    }
    
    .admin-btn:hover {
        background: linear-gradient(135deg, #8e24aa 0%, #5e35b1 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(156, 39, 176, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ UTILITY FUNCTIONS ------------------
def enforce_water_level_control(user_id, sensor_data):
    """Enforce water level control logic for specific user"""
    water_level = sensor_data["water_level"]
    drain_open = sensor_data["drain_status"]
    
    # CRITICAL: If water reaches 95%, automatically CLOSE drain
    if water_level >= 95:
        if drain_open:
            sensor_data["drain_status"] = False
            user_manager.add_notification(user_id, "🚨 EMERGENCY SHUTDOWN", 
                                f"Water level CRITICAL at {water_level:.1f}%. Drainage CLOSED automatically!", 
                                "emergency")
            # Play emergency sound
            st.markdown(generate_sound_alert("emergency", user_id), unsafe_allow_html=True)
        
        # Prevent any further increase in water level
        sensor_data["water_level"] = min(95, water_level)
    
    # If water is between 90-95%, open drain to reduce level
    elif water_level >= 90 and not drain_open:
        sensor_data["drain_status"] = True
        user_manager.add_notification(user_id, "⚠️ High Water Level", 
                            f"Water level reached {water_level:.1f}%. Drainage automatically OPENED.", 
                            "warning")
        # Play warning sound
        st.markdown(generate_sound_alert("warning", user_id), unsafe_allow_html=True)
    
    # If water drops below 30%, close drain to conserve water
    elif water_level <= 30 and drain_open:
        sensor_data["drain_status"] = False
        user_manager.add_notification(user_id, "💧 Low Water Level", 
                            f"Water level dropped to {water_level:.1f}%. Drainage CLOSED to conserve water.", 
                            "info")
        # Play info sound
        st.markdown(generate_sound_alert("info", user_id), unsafe_allow_html=True)
    
    return sensor_data

def simulate_sensor_data(user_id):
    """Simulate sensor data changes for a user"""
    conn = sqlite3.connect('smart_agriculture.db')
    c = conn.cursor()
    
    # Get current sensor data
    c.execute('''SELECT solar_input, battery_level, water_level, drain_status 
                 FROM sensor_data WHERE user_id = ? ORDER BY last_update DESC LIMIT 1''',
              (user_id,))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return
    
    solar_input, battery_level, water_level, drain_status = result
    
    # Simulate solar input (based on time of day)
    current_hour = datetime.now().hour
    if 6 <= current_hour <= 18:  # Daytime
        solar_change = random.uniform(-50, 100)
    else:  # Nighttime
        solar_change = random.uniform(-100, 20)
    
    solar_input = max(0, min(1200, solar_input + solar_change))
    
    # Simulate battery level (charges from solar, discharges for operations)
    battery_discharge = 0.1  # Base discharge rate
    if solar_input > 500:
        battery_charge = (solar_input - 500) / 100
        battery_discharge = -battery_charge
    
    battery_level = max(0, min(100, battery_level - battery_discharge + random.uniform(-1, 1)))
    
    # Simulate water level changes based on drainage status
    if drain_status:
        change = -random.uniform(0.5, 2.0)
    else:
        if water_level >= 95:
            change = 0  # Prevent increase at critical level
        elif water_level >= 90:
            change = random.uniform(0.1, 0.5)
        else:
            change = random.uniform(0.5, 2.0)
    
    water_level = max(0, min(100, water_level + change))
    
    # Create updated sensor data
    updated_data = {
        "solar_input": solar_input,
        "battery_level": battery_level,
        "water_level": water_level,
        "drain_status": drain_status
    }
    
    # Enforce control logic
    updated_data = enforce_water_level_control(user_id, updated_data)
    
    # Update database
    user_manager.update_sensor_data(user_id, updated_data)
    
    # Add occasional notifications for simulation
    if random.random() < 0.1:  # 10% chance each update
        if water_level > 90:
            user_manager.add_notification(user_id, "High Water Level Warning", 
                               f"Water level at {water_level:.1f}%.", 
                               "warning")
        elif battery_level < 30:
            user_manager.add_notification(user_id, "Low Battery Warning", 
                               f"Battery at {battery_level:.0f}%.", 
                               "warning")
        elif solar_input < 200:
            user_manager.add_notification(user_id, "Low Solar Output", 
                               f"Solar input at {solar_input:.0f}W.", 
                               "info")
        elif solar_input > 900:
            user_manager.add_notification(user_id, "High Solar Output", 
                               f"Excellent solar generation: {solar_input:.0f}W!", 
                               "success")
    
    conn.close()

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

# ------------------ ADMIN REDIRECT ------------------
# Update the load_admin_module function in the code:

# ------------------ ADMIN REDIRECT ------------------
def load_admin_module():
    """Dynamically load admin module"""
    try:
        # Import the admin module from the same directory
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Check if log.py exists
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.py")
        if os.path.exists(log_path):
            # Clear the current display
            st.empty()
            
            # Read the log.py content with proper encoding handling
            try:
                # Try UTF-8 first
                with open(log_path, 'r', encoding='utf-8') as f:
                    admin_code = f.read()
            except UnicodeDecodeError:
                try:
                    # Try Latin-1 if UTF-8 fails
                    with open(log_path, 'r', encoding='latin-1') as f:
                        admin_code = f.read()
                except UnicodeDecodeError:
                    # Try UTF-8 with error handling as last resort
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        admin_code = f.read()
            
            # Create a namespace for execution with all required imports
            admin_namespace = {
                'st': st,
                'pd': pd,
                'np': np,
                'datetime': datetime,
                'timedelta': timedelta,
                'sqlite3': sqlite3,
                'os': os,
                'json': json,
                'time': time,
                'hashlib': hashlib,
                'uuid': uuid,
                'random': random,
                'base64': base64,
                'BytesIO': BytesIO,
                'folium': folium,
                'st_folium': st_folium
            }
            
            # Execute the admin code
            exec(admin_code, admin_namespace)
            return True
        else:
            st.error("Admin module (log.py) not found in the current directory.")
            # Create a simple admin viewer as fallback
            st.info("Creating fallback admin viewer...")
            create_fallback_admin_viewer()
            return True
    except Exception as e:
        st.error(f"Error loading admin module: {str(e)}")
        # Provide detailed error information
        st.error("""
        **Troubleshooting steps:**
        1. Check if `log.py` exists in the same directory
        2. Ensure `log.py` has valid Python syntax
        3. Check file encoding (should be UTF-8)
        4. Look for special characters in the file
        """)
        
        # Create a fallback admin interface
        st.info("Loading fallback admin interface...")
        create_fallback_admin_viewer()
        return True

def create_fallback_admin_viewer():
    """Create a fallback admin interface when log.py fails to load"""
    st.markdown("## 🔧 Fallback Admin Interface")
    
    conn = sqlite3.connect('smart_agriculture.db')
    
    # Users table
    st.subheader("👥 Users")
    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    st.dataframe(users_df, use_container_width=True)
    
    # Sensor data
    st.subheader("📊 Sensor Data")
    sensor_df = pd.read_sql_query("SELECT * FROM sensor_data", conn)
    st.dataframe(sensor_df, use_container_width=True)
    
    # Notifications
    st.subheader("🔔 Notifications")
    notifications_df = pd.read_sql_query("SELECT * FROM notifications", conn)
    st.dataframe(notifications_df, use_container_width=True)
    
    # Water level history
    st.subheader("💧 Water Level History")
    water_df = pd.read_sql_query("SELECT * FROM water_level_history", conn)
    st.dataframe(water_df, use_container_width=True)
    
    conn.close()
    
    # Admin actions
    st.subheader("⚙️ Admin Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Simulate All Sensor Data"):
            with st.spinner("Simulating sensor data for all users..."):
                conn = sqlite3.connect('smart_agriculture.db')
                users = conn.execute("SELECT user_id FROM users").fetchall()
                for user in users:
                    simulate_sensor_data(user[0])
                conn.close()
                st.success("Sensor data simulated for all users!")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear Old Notifications"):
            with st.spinner("Clearing notifications older than 30 days..."):
                conn = sqlite3.connect('smart_agriculture.db')
                cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                deleted = conn.execute(
                    "DELETE FROM notifications WHERE DATE(created_at) < ?", 
                    (cutoff_date,)
                ).rowcount
                conn.commit()
                conn.close()
                st.success(f"Deleted {deleted} old notifications!")
                st.rerun()

# Replace the entire "CHECK FOR ADMIN REDIRECT" section and "load_admin_module" function with this:

# ------------------ ADMIN VIEW (Integrated) ------------------
def show_admin_dashboard():
    """Show integrated admin dashboard"""
    st.markdown('<div class="admin-title">👑 Admin Dashboard</div>', unsafe_allow_html=True)
    
    # Check if user is actually admin
    if not st.session_state.get('is_admin'):
        st.error("Access denied. Admin privileges required.")
        if st.button("Return to Dashboard"):
            st.session_state.admin_redirect = False
            st.rerun()
        return
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "👥 Users", "📈 Analytics", "⚙️ Settings"])
    
    with tab1:
        st.markdown("## 📊 System Overview")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            st.metric("Total Users", total_users)
        
        with col2:
            total_alerts = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            st.metric("Total Alerts", total_alerts)
        
        with col3:
            active_users = conn.execute("""
                SELECT COUNT(DISTINCT user_id) 
                FROM sensor_data 
                WHERE datetime(last_update) > datetime('now', '-24 hours')
            """).fetchone()[0]
            st.metric("Active Users (24h)", active_users)
        
        with col4:
            emergencies = conn.execute("""
                SELECT COUNT(*) 
                FROM notifications 
                WHERE notification_type = 'emergency'
                AND datetime(created_at) > datetime('now', '-7 days')
            """).fetchone()[0]
            st.metric("Emergencies (7d)", emergencies)
        
        # Recent activity
        st.markdown("### 🔄 Recent Activity")
        
        # Recent notifications
        recent_notifs = pd.read_sql_query("""
            SELECT n.*, u.username, u.farm_name
            FROM notifications n
            JOIN users u ON n.user_id = u.user_id
            ORDER BY n.created_at DESC
            LIMIT 10
        """, conn)
        
        if not recent_notifs.empty:
            st.dataframe(recent_notifs[['username', 'farm_name', 'title', 'notification_type', 'created_at']], 
                        use_container_width=True, hide_index=True)
        else:
            st.info("No recent notifications")
        
        conn.close()
    
    with tab2:
        st.markdown("## 👥 User Management")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # Users table with actions
        users_df = pd.read_sql_query("""
            SELECT username, user_id, farm_name, location, created_at, is_admin
            FROM users
            ORDER BY created_at DESC
        """, conn)
        
        st.dataframe(users_df, use_container_width=True)
        
        # User actions
        st.markdown("### 👤 User Actions")
        
        col_user1, col_user2, col_user3 = st.columns(3)
        
        with col_user1:
            st.markdown("#### Add New User")
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_farm = st.text_input("Farm Name")
                new_location = st.text_input("Location")
                is_admin_user = st.checkbox("Admin User")
                
                if st.form_submit_button("Create User"):
                    if new_username and new_password and new_farm:
                        success, message = user_manager.create_user(new_username, new_password, new_farm, new_location)
                        if success:
                            if is_admin_user:
                                conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (new_username,))
                                conn.commit()
                            st.success(f"User '{new_username}' created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {message}")
                    else:
                        st.error("Please fill required fields")
        
        with col_user2:
            st.markdown("#### Send Notification")
            with st.form("send_notification_form"):
                target_user = st.selectbox("Select User", users_df['username'].tolist())
                notif_title = st.text_input("Title")
                notif_message = st.text_area("Message")
                notif_type = st.selectbox("Type", ["info", "warning", "success", "emergency"])
                
                if st.form_submit_button("Send Notification"):
                    if target_user and notif_title:
                        user_id = users_df[users_df['username'] == target_user]['user_id'].iloc[0]
                        user_manager.add_notification(user_id, notif_title, notif_message, notif_type)
                        st.success(f"Notification sent to {target_user}!")
                        st.rerun()
                    else:
                        st.error("Please fill required fields")
        
        with col_user3:
            st.markdown("#### System Actions")
            
            if st.button("🔄 Simulate All Users Data", use_container_width=True):
                with st.spinner("Simulating..."):
                    users = conn.execute("SELECT user_id FROM users").fetchall()
                    for user in users:
                        simulate_sensor_data(user[0])
                    st.success(f"Simulated data for {len(users)} users!")
                    st.rerun()
            
            if st.button("🗑️ Clean Old Data", use_container_width=True):
                with st.spinner("Cleaning..."):
                    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    water_count = conn.execute(
                        "DELETE FROM water_level_history WHERE DATE(created_at) < ?", 
                        (cutoff_date,)
                    ).rowcount
                    notif_count = conn.execute(
                        "DELETE FROM notifications WHERE DATE(created_at) < ?", 
                        (cutoff_date,)
                    ).rowcount
                    conn.commit()
                    st.success(f"Cleaned {water_count} water records and {notif_count} notifications!")
                    st.rerun()
        
        conn.close()
    
    with tab3:
        st.markdown("## 📈 System Analytics")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # Chart 1: Users by location
        st.markdown("### 📍 Users by Location")
        location_data = pd.read_sql_query("""
            SELECT location, COUNT(*) as count
            FROM users
            GROUP BY location
            ORDER BY count DESC
        """, conn)
        
        if not location_data.empty:
            st.bar_chart(location_data.set_index('location')['count'])
        
        # Chart 2: Notifications by type
        st.markdown("### 🔔 Notifications by Type")
        notif_data = pd.read_sql_query("""
            SELECT notification_type, COUNT(*) as count
            FROM notifications
            WHERE datetime(created_at) > datetime('now', '-30 days')
            GROUP BY notification_type
        """, conn)
        
        if not notif_data.empty:
            st.bar_chart(notif_data.set_index('notification_type')['count'])
        
        # Chart 3: Active times
        st.markdown("### ⏰ Activity by Hour")
        activity_data = pd.read_sql_query("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as count
            FROM notifications
            WHERE datetime(created_at) > datetime('now', '-7 days')
            GROUP BY strftime('%H', created_at)
            ORDER BY hour
        """, conn)
        
        if not activity_data.empty:
            st.line_chart(activity_data.set_index('hour')['count'])
        
        # Data export
        st.markdown("### 📤 Data Export")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            if st.button("Export Users Data"):
                users_df = pd.read_sql_query("SELECT * FROM users", conn)
                csv = users_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Users CSV",
                    data=csv,
                    file_name="users_export.csv",
                    mime="text/csv"
                )
        
        with col_exp2:
            if st.button("Export Sensor Data"):
                sensor_df = pd.read_sql_query("SELECT * FROM sensor_data", conn)
                csv = sensor_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Sensor CSV",
                    data=csv,
                    file_name="sensor_export.csv",
                    mime="text/csv"
                )
        
        conn.close()
    
    with tab4:
        st.markdown("## ⚙️ System Settings")
        
        # Database info
        conn = sqlite3.connect('smart_agriculture.db')
        
        db_size = os.path.getsize('smart_agriculture.db') / (1024 * 1024)  # MB
        
        st.metric("Database Size", f"{db_size:.2f} MB")
        
        # Table sizes
        tables = ['users', 'sensor_data', 'notifications', 'water_level_history']
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            st.metric(f"{table.replace('_', ' ').title()}", f"{count:,}")
        
        # System info
        st.markdown("### ℹ️ System Information")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.info(f"**Python Version:** {sys.version.split()[0]}")
            st.info(f"**Streamlit Version:** {st.__version__}")
            st.info(f"**Pandas Version:** {pd.__version__}")
        
        with info_col2:
            st.info(f"**Database Path:** {os.path.abspath('smart_agriculture.db')}")
            st.info(f"**Current Directory:** {os.getcwd()}")
            st.info(f"**System Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        conn.close()
        
        # Danger zone
        st.markdown("### ⚠️ Danger Zone")
        
        with st.expander("Reset Database (⚠️ Irreversible)"):
            st.warning("This will delete ALL data and reset the database to initial state.")
            if st.button("🗑️ Reset Database", type="secondary"):
                os.remove('smart_agriculture.db')
                init_db()
                st.success("Database reset complete!")
                st.rerun()
    
    # Return button
    st.markdown("---")
    if st.button("← Return to Main Dashboard", use_container_width=True):
        st.session_state.admin_redirect = False
        st.rerun()

# ------------------ CHECK FOR ADMIN REDIRECT ------------------
if st.session_state.get('admin_redirect'):
    st.session_state.admin_redirect = False
    show_admin_dashboard()
    st.stop()
# ------------------ CHECK FOR ADMIN REDIRECT ------------------
if st.session_state.get('admin_redirect'):
    st.session_state.admin_redirect = False
    st.markdown('<div class="admin-title">🔐 Admin Data Viewer</div>', unsafe_allow_html=True)
    st.info("Loading admin data viewer...")
    
    if not load_admin_module():
        if st.button("Return to Dashboard"):
            st.session_state.admin_redirect = False
            st.rerun()
    st.stop()

# ------------------ AUTHENTICATION SCREEN ------------------
if not st.session_state.current_user:
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #2e5cb8;">🌾 Smart Agriculture IoT</h1>
        <p style="color: #666;">Login to access your farm monitoring dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        with st.form("login_form"):
            st.subheader("User Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login", type="primary"):
                if username and password:
                    success, message = user_manager.authenticate(username, password)
                    if success:
                        if username == "admin" and password == "admin@1234":
                            st.success("Admin login successful! Redirecting to admin dashboard...")
                            time.sleep(1)
                            st.session_state.admin_redirect = True
                            st.rerun()
                        else:
                            st.success(f"Welcome back, {username}!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error(f"Login failed: {message}")
                else:
                    st.error("Please enter both username and password")
    
    with tab2:
        with st.form("register_form"):
            st.subheader("Create New Account")
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            farm_name = st.text_input("Farm Name")
            location = st.text_input("Location")
            
            if st.form_submit_button("Register", type="primary"):
                if new_username and new_password and farm_name:
                    if new_password != confirm_password:
                        st.error("Passwords do not match!")
                    else:
                        success, message = user_manager.create_user(new_username, new_password, farm_name, location)
                        if success:
                            st.success(f"Account created successfully! Your User ID: {message}")
                            st.info("Please login with your new credentials")
                        else:
                            st.error(f"Registration failed: {message}")
                else:
                    st.error("Please fill all required fields")
    
    st.stop()

# ------------------ MAIN DASHBOARD (After Login) ------------------
# Get current user data
user_info, sensor_data, user_data = user_manager.get_current_user_data()

# Check if user_info is None (user might have been deleted)
if user_info is None:
    st.error("User data not found. Please login again.")
    user_manager.logout()
    st.stop()

user_id = user_info["user_id"]
farm_name = user_info["farm_name"]
location = user_info["location"]
is_admin = user_info.get("is_admin", False)

# Initialize user-specific session state
if f"auto_mode_{user_id}" not in st.session_state:
    st.session_state[f"auto_mode_{user_id}"] = True

# ------------------ SIDEBAR (User Info & Controls) ------------------
with st.sidebar:
    # User Info Panel
    if is_admin:
        st.markdown(f"""
        <div class="admin-panel">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="font-size: 24px; margin-right: 10px;">👑</div>
                <div>
                    <div style="font-size: 18px; font-weight: bold;">{farm_name}</div>
                    <div style="font-size: 12px; opacity: 0.9;">{location}</div>
                </div>
            </div>
            <div class="admin-badge">👑 ADMIN User ID: {user_id}</div>
            <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">
                <i class="fas fa-calendar"></i> Joined: {user_info['created_at'][:10]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="user-panel">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="font-size: 24px; margin-right: 10px;">👨‍🌾</div>
                <div>
                    <div style="font-size: 18px; font-weight: bold;">{farm_name}</div>
                    <div style="font-size: 12px; opacity: 0.9;">{location}</div>
                </div>
            </div>
            <div class="user-badge">User ID: {user_id}</div>
            <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">
                <i class="fas fa-calendar"></i> Joined: {user_info['created_at'][:10]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Admin Dashboard Button
    if is_admin:
        if st.button("👑 Admin Dashboard", use_container_width=True, type="primary", 
                    help="Access system-wide data and analytics"):
            st.session_state.admin_redirect = True
            st.rerun()
    
    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        user_manager.logout()
    
    st.markdown("---")
    
    # Control Panel
    st.markdown("### ⚙️ Control Panel")
    
    # Auto Mode Toggle
    auto_mode = st.toggle(
        "**Automatic Mode**",
        value=st.session_state[f"auto_mode_{user_id}"],
        help="When enabled, system will automatically control drainage based on water level rules"
    )
    
    if auto_mode != st.session_state[f"auto_mode_{user_id}"]:
        st.session_state[f"auto_mode_{user_id}"] = auto_mode
        status = "ENABLED" if auto_mode else "DISABLED"
        user_manager.add_notification(user_id, f"Auto Mode {status}", 
                            f"Automatic control system {status.lower()}.", 
                            "info")
        st.rerun()
    
    # Manual Drainage Control
    st.markdown("### 👨‍🔧 Manual Control")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open Drain", type="primary", use_container_width=True,
                    disabled=sensor_data["water_level"] >= 95):
            user_manager.update_sensor_data(user_id, {"drain_status": 1})
            user_manager.add_notification(user_id, "Drainage Manually Opened", 
                                "Drainage valve opened manually", "info")
            st.rerun()
    with col2:
        if st.button("Close Drain", type="secondary", use_container_width=True):
            user_manager.update_sensor_data(user_id, {"drain_status": 0})
            user_manager.add_notification(user_id, "Drainage Manually Closed", 
                                "Drainage valve closed manually", "warning")
            st.rerun()
    
    # Water Level Simulation Controls
    st.markdown("### 💧 Water Level Simulation")
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        if st.button("+10%", use_container_width=True,
                    disabled=sensor_data["water_level"] >= 95):
            # Update water level by +10%
            new_level = min(95, sensor_data["water_level"] + 10)
            user_manager.update_sensor_data(user_id, {"water_level": new_level})
            user_manager.add_notification(user_id, "Water Level Increased", 
                                f"Water level manually increased to {new_level:.1f}%", "info")
            st.rerun()
    with sim_col2:
        if st.button("-10%", use_container_width=True):
            # Update water level by -10%
            new_level = max(0, sensor_data["water_level"] - 10)
            user_manager.update_sensor_data(user_id, {"water_level": new_level})
            user_manager.add_notification(user_id, "Water Level Decreased", 
                                f"Water level manually decreased to {new_level:.1f}%", "info")
            st.rerun()
    
    # Fine-grained water level control
    st.markdown("#### Precise Water Level Control")
    water_slider = st.slider("Set Water Level (%)", 0, 100, int(sensor_data["water_level"]), 5,
                           disabled=sensor_data["water_level"] >= 95)
    
    if water_slider != sensor_data["water_level"]:
        user_manager.update_sensor_data(user_id, {"water_level": water_slider})
        user_manager.add_notification(user_id, "Water Level Adjusted", 
                            f"Water level set to {water_slider}%", "info")
        st.rerun()
    
    # Notifications Section
    st.markdown("---")
    st.markdown("### 🔔 Notifications")
    
    # Count unread notifications
    notifications = user_data.get("notifications", [])
    unread_count = sum(1 for n in notifications if not n["read"])
    
    if unread_count > 0:
        st.markdown(f"<div class='badge danger'>{unread_count} unread</div>", unsafe_allow_html=True)
    
    if st.button("Mark All as Read", use_container_width=True):
        user_manager.mark_all_notifications_read(user_id)
        st.rerun()
    
    # Display notifications
    for notification in notifications[:5]:
        icon_map = {"emergency": "🚨", "warning": "⚠️", "success": "✅", "info": "ℹ️"}
        icon = icon_map.get(notification["type"], "🔔")
        read_class = "read" if notification["read"] else "unread"
        st.markdown(f"""
        <div class='card {notification["type"] if not notification["read"] else ""}' 
             style='padding: 12px; margin: 8px 0; opacity: {0.7 if notification["read"] else 1};'>
            <b>{icon} {notification["title"]}</b><br>
            <small>{notification["message"]}</small><br>
            <small style='color: #666;'>{notification["time"]}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Sound Alert Test Buttons
    st.markdown("---")
    st.markdown("### 🔊 Test Sound Alerts")
    
    col_sound1, col_sound2 = st.columns(2)
    with col_sound1:
        if st.button("Emergency", use_container_width=True):
            st.markdown(generate_sound_alert("emergency", user_id), unsafe_allow_html=True)
    with col_sound2:
        if st.button("Warning", use_container_width=True):
            st.markdown(generate_sound_alert("warning", user_id), unsafe_allow_html=True)

# ------------------ HEADER ------------------
col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    if is_admin:
        st.markdown(f'<div class="admin-title">👑 {farm_name} - Admin Dashboard</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="title">🌾 {farm_name} - Smart Agriculture System</div>', unsafe_allow_html=True)
    
    st.markdown(f"<div class='subtitle'>Location: {location} | User ID: {user_id}</div>", unsafe_allow_html=True)

with col_header2:
    # Display water level with status
    status_class, status_text = get_water_level_status(sensor_data["water_level"])
    if is_admin:
        st.markdown(f'<div class="badge admin" style="margin-top: 10px; font-size: 14px;">👑 ADMIN MODE</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="badge {status_class}" style="margin-top: 10px; font-size: 14px;">{sensor_data["water_level"]:.1f}% - {status_text}</div>', unsafe_allow_html=True)

# ------------------ ADMIN INFO CARD ------------------
if is_admin:
    st.markdown(f"""
    <div class="card admin">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 36px; margin-right: 15px;">👑</div>
            <div>
                <b style="font-size: 20px; color: #9c27b0;">ADMINISTRATOR DASHBOARD</b><br>
                <span style="color: #673ab7;">
                    • Full system access privileges<br>
                    • View all user data and analytics<br>
                    • System-wide monitoring and control<br>
                    • Database management capabilities
                </span><br>
                <small><i class="fas fa-shield-alt"></i> Administrator privileges active</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------ EMERGENCY WARNING (if applicable) ------------------
if sensor_data["water_level"] >= 95:
    st.markdown(generate_sound_alert("emergency", user_id), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card emergency">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 36px; margin-right: 15px;">🚨</div>
            <div>
                <b style="font-size: 20px; color: #ff0000;">EMERGENCY SHUTDOWN ACTIVE</b><br>
                Water level reached CRITICAL {sensor_data["water_level"]:.1f}%<br>
                <span style="color: #d35400;">
                    • Drainage system LOCKED CLOSED<br>
                    • Water level increase PREVENTED<br>
                    • Manual override DISABLED<br>
                    • Safety protocols ENGAGED
                </span><br>
                <small><i class="fas fa-clock"></i> Emergency activated</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif sensor_data["water_level"] >= 90:
    st.markdown(generate_sound_alert("warning", user_id), unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card danger">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 32px; margin-right: 15px;">⚠️</div>
            <div>
                <b>HIGH WATER LEVEL WARNING</b><br>
                <span style="color: #d35400;">Water level at {sensor_data["water_level"]:.1f}% - Approaching critical level</span><br>
                <b>System will automatically:</b><br>
                • CLOSE drain at 95% (Emergency Lock)<br>
                • PREVENT water level increase<br>
                • Disable manual controls<br>
                <small><i class="fas fa-clock"></i> Current prediction: Critical in {max(0, (95 - sensor_data["water_level"])/2):.0f} minutes</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ------------------ MAIN DASHBOARD TABS ------------------
if is_admin:
    # Admin has simplified tabs since they can access full data viewer
    tab1, tab2, tab3 = st.tabs(["📊 Quick Stats", "⚙️ Admin Tools", "📈 System Health"])
else:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💧 Water Management", "🔋 Power System", "📈 Analytics"])

if is_admin:
    with tab1:
        st.markdown("## 📊 System Quick Statistics")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # Get system stats
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_sensor_records = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
        total_notifications = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        total_water_readings = conn.execute("SELECT COUNT(*) FROM water_level_history").fetchone()[0]
        
        # Get active users (users with sensor data in last 24 hours)
        active_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM sensor_data 
            WHERE datetime(last_update) > datetime('now', '-1 day')
        """).fetchone()[0]
        
        # Get emergency count
        emergency_count = conn.execute("""
            SELECT COUNT(*) 
            FROM notifications 
            WHERE notification_type = 'emergency' 
            AND datetime(created_at) > datetime('now', '-7 days')
        """).fetchone()[0]
        
        conn.close()
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", total_users)
            st.metric("Active Users (24h)", active_users)
        with col2:
            st.metric("Sensor Records", total_sensor_records)
            st.metric("Water Readings", total_water_readings)
        with col3:
            st.metric("Notifications", total_notifications)
            st.metric("Emergencies (7d)", emergency_count)
        
        # Quick data preview
        st.markdown("### 🔍 Recent Activity")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # Recent users
        recent_users = pd.read_sql_query("""
            SELECT username, farm_name, location, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 5
        """, conn)
        
        # Recent notifications
        recent_notifications = pd.read_sql_query("""
            SELECT n.title, n.message, n.notification_type, u.username, n.created_at
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.user_id
            ORDER BY n.created_at DESC 
            LIMIT 5
        """, conn)
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Recent Users**")
            st.dataframe(recent_users, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("**Recent Notifications**")
            st.dataframe(recent_notifications, use_container_width=True, hide_index=True)
    
    with tab2:
        st.markdown("## ⚙️ Admin Tools")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Database Operations")
            
            if st.button("🔄 Refresh All Data", use_container_width=True):
                with st.spinner("Refreshing all sensor data..."):
                    conn = sqlite3.connect('smart_agriculture.db')
                    users = conn.execute("SELECT user_id FROM users").fetchall()
                    for user in users:
                        simulate_sensor_data(user[0])
                    conn.close()
                    st.success("All sensor data refreshed!")
                    st.rerun()
            
            if st.button("🗑️ Clean Old Data", use_container_width=True, type="secondary"):
                with st.spinner("Cleaning up old data..."):
                    conn = sqlite3.connect('smart_agriculture.db')
                    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    # Count records to be deleted
                    water_count = conn.execute(
                        "SELECT COUNT(*) FROM water_level_history WHERE DATE(created_at) < ?", 
                        (cutoff_date,)
                    ).fetchone()[0]
                    
                    notification_count = conn.execute(
                        "SELECT COUNT(*) FROM notifications WHERE DATE(created_at) < ?", 
                        (cutoff_date,)
                    ).fetchone()[0]
                    
                    # Delete old data
                    conn.execute("DELETE FROM water_level_history WHERE DATE(created_at) < ?", (cutoff_date,))
                    conn.execute("DELETE FROM notifications WHERE DATE(created_at) < ?", (cutoff_date,))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"Cleaned up {water_count} water history records and {notification_count} notifications older than 30 days.")
                    st.rerun()
            
            if st.button("📊 Export All Data", use_container_width=True):
                with st.spinner("Preparing data export..."):
                    conn = sqlite3.connect('smart_agriculture.db')
                    
                    # Export all tables
                    tables = ['users', 'sensor_data', 'notifications', 'water_level_history']
                    export_data = {}
                    
                    for table in tables:
                        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                        export_data[table] = df.to_dict('records')
                    
                    conn.close()
                    
                    # Create JSON export
                    import json
                    export_json = json.dumps(export_data, indent=2, default=str)
                    
                    st.download_button(
                        label="📥 Download Full Export",
                        data=export_json,
                        file_name=f"agriculture_full_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
        
        with col2:
            st.markdown("### User Management")
            
            # View all users
            conn = sqlite3.connect('smart_agriculture.db')
            all_users = pd.read_sql_query("""
                SELECT username, user_id, farm_name, location, created_at, is_admin
                FROM users
                ORDER BY created_at DESC
            """, conn)
            conn.close()
            
            st.dataframe(all_users, use_container_width=True, height=200)
            
            # Add new user manually
            with st.expander("➕ Add New User"):
                with st.form("admin_add_user"):
                    new_username = st.text_input("Username")
                    new_password = st.text_input("Password", type="password")
                    new_farm = st.text_input("Farm Name")
                    new_location = st.text_input("Location")
                    make_admin = st.checkbox("Make Administrator")
                    
                    if st.form_submit_button("Create User"):
                        if new_username and new_password and new_farm:
                            success, message = user_manager.create_user(new_username, new_password, new_farm, new_location)
                            if success:
                                if make_admin:
                                    conn = sqlite3.connect('smart_agriculture.db')
                                    conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (new_username,))
                                    conn.commit()
                                    conn.close()
                                st.success(f"User '{new_username}' created successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to create user: {message}")
                        else:
                            st.error("Please fill all required fields")
    
    with tab3:
        st.markdown("## 📈 System Health Monitor")
        
        conn = sqlite3.connect('smart_agriculture.db')
        
        # System health metrics
        # Database size
        db_size = os.path.getsize('smart_agriculture.db') / (1024 * 1024)  # MB
        
        # Table sizes
        table_sizes = {}
        tables = ['users', 'sensor_data', 'notifications', 'water_level_history']
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            table_sizes[table] = count
        
        # Recent activity
        recent_activity = pd.read_sql_query("""
            SELECT 
                'sensor_data' as table_name,
                COUNT(*) as record_count,
                MAX(last_update) as last_update
            FROM sensor_data
            WHERE datetime(last_update) > datetime('now', '-1 day')
            UNION ALL
            SELECT 
                'notifications' as table_name,
                COUNT(*) as record_count,
                MAX(created_at) as last_update
            FROM notifications
            WHERE datetime(created_at) > datetime('now', '-1 day')
            UNION ALL
            SELECT 
                'water_level_history' as table_name,
                COUNT(*) as record_count,
                MAX(created_at) as last_update
            FROM water_level_history
            WHERE datetime(created_at) > datetime('now', '-1 day')
        """, conn)
        
        conn.close()
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Database Size", f"{db_size:.2f} MB")
            st.metric("Users Table", f"{table_sizes['users']:,}")
        with col2:
            st.metric("Sensor Records", f"{table_sizes['sensor_data']:,}")
            st.metric("Notifications", f"{table_sizes['notifications']:,}")
        with col3:
            st.metric("Water Readings", f"{table_sizes['water_level_history']:,}")
            st.metric("System Uptime", "99.8%")
        
        # Recent activity chart
        if not recent_activity.empty:
            st.markdown("### 📊 Last 24 Hours Activity")
            st.bar_chart(recent_activity.set_index('table_name')['record_count'])
        
        # System status
        st.markdown("### 🟢 System Status")
        
        status_col1, status_col2, status_col3, status_col4 = st.columns(4)
        with status_col1:
            st.success("Database ✓")
        with status_col2:
            st.success("Authentication ✓")
        with status_col3:
            st.success("Sensor Simulation ✓")
        with status_col4:
            st.success("Notifications ✓")

else:
    # Regular user tabs
    with tab1:
        # WEATHER & SENSOR CARDS
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="card info">
                <div style="font-size: 24px; color: #4a90ff;">🌧️</div>
                <b>Rain Forecast</b><br>
                <h3>{'Heavy Rain' if random.random() > 0.5 else 'Light Rain'}</h3>
                <small>Next 12 hours</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="card solar">
                <div style="font-size: 24px; color: #f39c12;">☀️</div>
                <b>Solar Input</b><br>
                <h3>{sensor_data['solar_input']:.0f}W</h3>
                <small>{'High Output' if sensor_data['solar_input'] > 700 else 'Normal'}</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="card battery">
                <div style="font-size: 24px; color: #9b59b6;">🔋</div>
                <b>Battery Level</b><br>
                <h3>{sensor_data['battery_level']:.0f}%</h3>
                <small>{'Fully Charged' if sensor_data['battery_level'] > 90 else 'Charging' if sensor_data['solar_input'] > 500 else 'Discharging'}</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="card">
                <div style="font-size: 24px; color: #17a2b8;">💧</div>
                <b>Humidity</b><br>
                <h3>{random.randint(60, 95)}%</h3>
                <small>Field Sensor</small>
            </div>
            """, unsafe_allow_html=True)

        # WATER LEVEL VISUALIZATION
        st.markdown("## 💧 Water Level Monitoring")
        
        water_height = sensor_data["water_level"]
        
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
        <br>
            <div style="margin-top: 10px; font-size: 14px; color: #666; text-align: center;">
                <div>Drain Status: <b style="color: {'#28a745' if sensor_data['drain_status'] else '#dc3545'}">
                    {'OPEN' if sensor_data['drain_status'] else 'CLOSED'}</b></div>
                <div>Auto Mode: <b style="color: {'#28a745' if st.session_state[f'auto_mode_{user_id}'] else '#6c757d'}">
                    {'ON' if st.session_state[f'auto_mode_{user_id}'] else 'OFF'}</b></div>
                <div>Last Update: <b>{sensor_data['last_update'][11:19] if 'last_update' in sensor_data and len(sensor_data['last_update']) > 10 else 'N/A'}</b></div>
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

    with tab2:
        st.markdown("## 🌊 Water Management System")
        
        # Water Pipeline Map
        if sensor_data["water_level"] >= 95:
            badge_class = "danger"
            badge_text = "🚨 EMERGENCY MODE"
        else:
            badge_class = "success"
            badge_text = "Live Status: Normal Flow"
        
        st.markdown(f"""
        <div class="card">
            <b>Water Pipeline Network</b>
            <span class="badge {badge_class}">{badge_text}</span>
            <p style="color: #666; margin-top: 5px;">Real-time monitoring of irrigation and drainage systems</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Interactive Map
        m = folium.Map(location=[10.79, 78.70], zoom_start=13, tiles='CartoDB positron')
        
        # Add pipeline with color based on status
        line_color = "#ff0000" if sensor_data["water_level"] >= 95 else "#4a90ff"
        
        folium.PolyLine(
            [[10.79,78.69],[10.80,78.71],[10.81,78.72],[10.82,78.70]], 
            color=line_color, 
            weight=4,
            opacity=0.7,
            popup="Main Irrigation Pipeline"
        ).add_to(m)
        
        # Add markers
        folium.Marker(
            [10.79,78.69], 
            tooltip="Water Source",
            icon=folium.Icon(color="blue", icon="tint", prefix="fa")
        ).add_to(m)
        
        drain_color = "red" if sensor_data["water_level"] >= 95 else ("green" if sensor_data["drain_status"] else "orange")
        folium.Marker(
            [10.80,78.71], 
            tooltip=f"Drainage Point - {'OPEN' if sensor_data['drain_status'] else 'CLOSED'}",
            icon=folium.Icon(color=drain_color, icon="cog", prefix="fa")
        ).add_to(m)
        
        safe_st_folium(m, height=300)
        
        # Water Level History Chart
        st.markdown("### 📈 Water Level History (Last 24 hours)")
        
        history = user_data.get("water_level_history", [])
        if history:
            history_df = pd.DataFrame(history)
            st.line_chart(history_df.set_index('time')['level'], height=250)
            
            st.markdown("""
            <div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin-top: 10px;">
                <small><b>Thresholds:</b></small><br>
                <small><span style="color: #4a90ff;">▬ Normal (0-74%)</span> | 
                <span style="color: #ff9800;">▬ Warning (75-89%)</span> | 
                <span style="color: #dc3545;">▬ Critical (90-94%)</span> | 
                <span style="color: #ff0000;">▬ Emergency (95%+)</span></small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No water level history available yet. Data will appear after system updates.")

    with tab3:
        st.markdown("## 🔋 Power & Energy Management")
        
        col_power1, col_power2 = st.columns(2)
        
        with col_power1:
            # Solar Panel Monitoring
            solar_efficiency = min(100, (sensor_data["solar_input"] / 1000) * 100)
            solar_status = "Optimal" if sensor_data["solar_input"] > 500 else "Low"
            solar_status_class = "success" if sensor_data["solar_input"] > 500 else "warning"
            
            st.markdown(f"""
            <div class="card solar">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="font-size: 32px; margin-right: 15px;">☀️</div>
                    <div>
                        <b>Solar Panel Status</b><br>
                        <span style="font-size: 24px; font-weight: bold;">{sensor_data['solar_input']:.0f} W</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Efficiency:</span>
                        <span><b>{solar_efficiency:.1f}%</b></span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {solar_efficiency}%; background-color: #f39c12;">
                            {solar_efficiency:.1f}%
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Daily Production:</span>
                        <span><b>{(sensor_data['solar_input'] * 12 / 1000):.1f} kWh</b></span>
                    </div>
                </div>
                
                <div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Status:</span>
                        <span class="badge {solar_status_class}">{solar_status}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_power2:
            # Battery System Monitoring
            if sensor_data["battery_level"] > 70:
                battery_health = "Good"
                health_class = "success"
                health_color = "#27ae60"
            elif sensor_data["battery_level"] > 30:
                battery_health = "Fair"
                health_class = "warning"
                health_color = "#f39c12"
            else:
                battery_health = "Poor"
                health_class = "danger"
                health_color = "#e74c3c"
            
            charging = "Yes" if sensor_data["solar_input"] > 100 else "No"
            
            st.markdown(f"""
            <div class="card battery">
                <div style="display: flex; align-items: center; margin-bottom: 15px;">
                    <div style="font-size: 32px; margin-right: 15px;">🔋</div>
                    <div>
                        <b>Battery System</b><br>
                        <span style="font-size: 24px; font-weight: bold;">{sensor_data['battery_level']:.0f}%</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Charge Level:</span>
                        <span><b>{sensor_data['battery_level']:.0f}%</b></span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: {sensor_data['battery_level']}%; 
                              background-color: {health_color};">
                            {sensor_data['battery_level']:.0f}%
                        </div>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Estimated Runtime:</span>
                        <span><b>{(sensor_data['battery_level'] * 2):.0f} hours</b></span>
                    </div>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>Charging:</span>
                        <span><b>{charging}</b></span>
                    </div>
                </div>
                
                <div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>Health:</span>
                        <span class="badge {health_class}">{battery_health}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Power Visualization Charts
        st.markdown("### 📊 Power Visualization")
        
        # Create solar power data visualization
        solar_data = pd.DataFrame({
            'Hour': list(range(24)),
            'Power': [max(0, sensor_data["solar_input"] * (0.2 + 0.8 * (1 - abs(h - 12)/12))) + random.uniform(-50, 50) for h in range(24)]
        })
        
        st.subheader("☀️ Solar Power Generation (24-hour simulation)")
        st.line_chart(solar_data.set_index('Hour')['Power'], height=200)
        
        # Create battery level trend
        battery_trend = pd.DataFrame({
            'Time': [f"{h}:00" for h in range(24)],
            'Level': [max(0, min(100, sensor_data["battery_level"] + random.uniform(-5, 5))) for _ in range(24)]
        })
        
        st.subheader("🔋 Battery Level Trend")
        st.line_chart(battery_trend.set_index('Time')['Level'], height=200)
        
        # Power Consumption Analysis
        st.markdown("### ⚡ Power Consumption Analysis")
        
        col_cons1, col_cons2, col_cons3 = st.columns(3)
        
        with col_cons1:
            pump_power = 150 + random.randint(-20, 20)
            pump_change = f"{random.choice(['-', '+'])}{random.randint(1, 5)}%"
            st.metric("Pump Power", f"{pump_power} W", pump_change)
        
        with col_cons2:
            sensor_power = 25 + random.randint(-5, 5)
            sensor_change = f"{random.choice(['-', '+'])}{random.randint(1, 3)}%"
            st.metric("Sensor Network", f"{sensor_power} W", sensor_change)
        
        with col_cons3:
            control_power = 15 + random.randint(-3, 3)
            st.metric("Control System", f"{control_power} W", "0%")
        
        # Power Efficiency Metrics
        st.markdown("### 📈 Power Efficiency Metrics")
        
        col_eff1, col_eff2, col_eff3 = st.columns(3)
        
        with col_eff1:
            system_efficiency = random.randint(85, 95)
            st.metric("System Efficiency", f"{system_efficiency}%", f"+{random.randint(1, 3)}%")
        
        with col_eff2:
            energy_saved = random.randint(20, 40)
            st.metric("Energy Saved", f"{energy_saved} kWh", "Today")
        
        with col_eff3:
            co2_reduced = random.randint(15, 30)
            st.metric("CO₂ Reduced", f"{co2_reduced} kg", "This month")
        
        # Power Recommendations
        st.markdown("### 💡 Power Management Suggestions")
        
        suggestions = [
            "Clean Solar Panels - Dust accumulation reduces efficiency by up to 25%",
            "Schedule Pump Operation - Run pumps during peak solar hours (10AM-2PM)",
            "Battery Maintenance - Check connections monthly, replace every 3-5 years",
            "Energy Audit - Conduct monthly review of power consumption patterns"
        ]
        
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"""
            <div class="suggestion-card">
                <div style="display: flex; align-items: flex-start;">
                    <div style="background: #e8f4f8; padding: 5px 10px; border-radius: 5px; margin-right: 10px;">{i}</div>
                    <div>{suggestion}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab4:
        st.markdown("## 📊 System Analytics & Reports")
        
        col_analytics1, col_analytics2 = st.columns(2)
        
        with col_analytics1:
            # System Status Summary
            if sensor_data["water_level"] >= 95:
                safety_status = "🚨 EMERGENCY LOCK"
                safety_color = "emergency"
                safety_icon = "🔒"
            elif sensor_data["water_level"] >= 90:
                safety_status = "⚠️ HIGH ALERT"
                safety_color = "danger"
                safety_icon = "⚠️"
            elif sensor_data["water_level"] >= 75:
                safety_status = "🟡 WARNING"
                safety_color = "warning"
                safety_icon = "⚠️"
            else:
                safety_status = "✅ NORMAL"
                safety_color = "success"
                safety_icon = "✅"
            
            auto_status = "ACTIVE" if st.session_state[f"auto_mode_{user_id}"] else "INACTIVE"
            
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
                        <span><b>{auto_status}</b></span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin: 15px 0 8px 0;">
                        <span>Safety Margin:</span>
                        <span><b>{100 - sensor_data['water_level']:.1f}%</b></span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin: 15px 0 8px 0;">
                        <span>System Uptime:</span>
                        <span><b>99.8%</b></span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin: 15px 0 8px 0;">
                        <span>Last Maintenance:</span>
                        <span><b>15 days ago</b></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_analytics2:
            # Sensor Status
            water_sensor_status = "CRITICAL" if sensor_data["water_level"] >= 95 else "Active"
            water_sensor_class = "danger" if sensor_data["water_level"] >= 95 else "success"
            
            solar_sensor_status = "Low" if sensor_data["solar_input"] < 300 else "Active"
            solar_sensor_class = "warning" if sensor_data["solar_input"] < 300 else "success"
            
            battery_sensor_status = "Low" if sensor_data["battery_level"] < 30 else "Active"
            battery_sensor_class = "warning" if sensor_data["battery_level"] < 30 else "success"
            
            drain_status_text = "OPEN" if sensor_data["drain_status"] else "CLOSED"
            drain_status_class = "success" if sensor_data["drain_status"] else "warning"
            
            st.markdown(f"""
            <div class="card">
                <b>📡 Sensor Status Report</b><br>
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span><i class="fas fa-tint"></i> Water Level Sensor</span>
                        <span class="badge {water_sensor_class}">{water_sensor_status}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span><i class="fas fa-sun"></i> Solar Sensor</span>
                        <span class="badge {solar_sensor_class}">{solar_sensor_status}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span><i class="fas fa-battery-full"></i> Battery Monitor</span>
                        <span class="badge {battery_sensor_class}">{battery_sensor_status}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span><i class="fas fa-cog"></i> Drainage Valve</span>
                        <span class="badge {drain_status_class}">{drain_status_text}</span>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between;">
                        <span><i class="fas fa-satellite-dish"></i> Communication</span>
                        <span class="badge success">Online</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # User Statistics
        st.markdown("### 📈 User Statistics")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            days_active = (datetime.now() - datetime.fromisoformat(user_info['created_at'][:10])).days
            st.metric("Days Active", str(max(1, days_active)), "days")
        
        with col_stat2:
            total_notifications = len(user_data.get("notifications", []))
            st.metric("Total Alerts", str(total_notifications))
        
        with col_stat3:
            emergency_count = sum(1 for n in user_data.get("notifications", []) 
                                if n.get("type") == "emergency")
            st.metric("Emergency Alerts", str(emergency_count))
        
        # Performance Charts
        st.markdown("### 📊 Performance Trends")
        
        # Create performance data
        performance_data = pd.DataFrame({
            'Metric': ['Response Time', 'Accuracy', 'Uptime', 'Efficiency'],
            'Score': [95, 88, 99.8, 92],
            'Target': [90, 90, 99.5, 85]
        })
        
        # Create chart using Streamlit's native chart
        st.subheader("System Performance Metrics")
        chart_data = pd.DataFrame({
            'Score': [95, 88, 99.8, 92],
            'Target': [90, 90, 99.5, 85]
        }, index=['Response Time', 'Accuracy', 'Uptime', 'Efficiency'])
        
        st.bar_chart(chart_data)
        
        # Additional Analytics
        st.markdown("### 📋 Additional Analytics")
        
        # Create sample data for analytics
        analytics_data = pd.DataFrame({
            'Time Period': ['Last Hour', 'Last 6 Hours', 'Last 24 Hours', 'Last 7 Days'],
            'Water Usage (L)': [random.randint(1000, 5000) for _ in range(4)],
            'Energy Generated (kWh)': [random.randint(10, 50) for _ in range(4)],
            'Efficiency (%)': [random.randint(80, 98) for _ in range(4)]
        })
        
        st.dataframe(analytics_data, use_container_width=True)

# ------------------ FOOTER ------------------
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    user_type = "👑 ADMIN" if is_admin else "👨‍🌾 USER"
    st.markdown(f"<small>{user_type}: <b>{st.session_state.current_user} | ID: {user_id}</b></small>", unsafe_allow_html=True)
with footer_col2:
    last_update = sensor_data.get('last_update', '')[11:19] if 'last_update' in sensor_data and len(sensor_data['last_update']) > 10 else 'N/A'
    status_icon = "🔴" if sensor_data['water_level'] >= 95 else "🟢"
    st.markdown(f"<small>📶 <b>Last Update:</b> {last_update} {status_icon}</small>", unsafe_allow_html=True)
with footer_col3:
    st.markdown(f"<small>📍 <b>Farm:</b> {farm_name}, {location}</small>", unsafe_allow_html=True)

# ------------------ AUTO SIMULATION ------------------
# Simulate sensor data changes automatically
if f"last_update_{user_id}" not in st.session_state:
    st.session_state[f"last_update_{user_id}"] = time.time()

current_time = time.time()
if current_time - st.session_state[f"last_update_{user_id}"] > 5:  # Update every 5 seconds
    simulate_sensor_data(user_id)
    st.session_state[f"last_update_{user_id}"] = current_time
    st.rerun()

# Add manual refresh button
if st.sidebar.button("🔄 Refresh Sensor Data", use_container_width=True):
    simulate_sensor_data(user_id)
    st.rerun()

# Display system status in sidebar
st.sidebar.markdown("---")
if sensor_data["water_level"] >= 95:
    status_bg = "#ffe6e6"
    status_border = "#ff0000"
else:
    status_bg = "#e8f5e9"
    status_border = "#28a745"

st.sidebar.markdown(f"""
<div style="background: {status_bg}; 
                padding: 10px; 
                border-radius: 10px; 
                border-left: 4px solid {status_border};">
    <small><b>System Status</b></small><br>
    <small>Water: <b>{sensor_data['water_level']:.1f}%</b></small><br>
    <small>Solar: <b>{sensor_data['solar_input']:.0f}W</b></small><br>
    <small>Battery: <b>{sensor_data['battery_level']:.0f}%</b></small><br>
    <small>Drain: <b>{'🔓 OPEN' if sensor_data['drain_status'] else '🔒 CLOSED'}</b></small>
</div>
""", unsafe_allow_html=True)

# Database info in sidebar
conn = sqlite3.connect('smart_agriculture.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM users")
user_count = c.fetchone()[0]
conn.close()

st.sidebar.markdown(f"""
<div style="background: #f8f9fa; padding: 10px; border-radius: 10px; margin-top: 10px;">
    <small><b>Database Info</b></small><br>
    <small>Total Users: <b>{user_count}</b></small><br>
    <small>Storage: <b>SQLite</b></small>
</div>
""", unsafe_allow_html=True)

