import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Set page configuration
st.set_page_config(
    page_title="Agriculture IoT Data Viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2e5cb8;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4a90ff;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .data-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    .export-btn {
        background: #28a745;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
    }
    .export-btn:hover {
        background: #218838;
    }
</style>
""", unsafe_allow_html=True)

# Database connection
def get_db_connection():
    conn = sqlite3.connect('smart_agriculture.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database connection
@st.cache_resource
def init_connection():
    return get_db_connection()

# Main title
st.markdown('<div class="main-header">🌾 Smart Agriculture IoT - Data Viewer</div>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar for filters and controls
with st.sidebar:
    st.markdown("### 🔍 Data Filters")
    
    # Date range filter
    st.markdown("**Date Range**")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now().date())
    
    # User selection
    conn = get_db_connection()
    users = conn.execute("SELECT user_id, username, farm_name FROM users ORDER BY username").fetchall()
    conn.close()
    
    user_options = ["All Users"] + [f"{user['username']} ({user['user_id']}) - {user['farm_name']}" for user in users]
    selected_user = st.selectbox("Select User", user_options)
    
    # Data type selection
    data_types = ["All Data", "Users", "Sensor Data", "Notifications", "Water Level History"]
    selected_data_type = st.selectbox("Data Type", data_types)
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    conn = get_db_connection()
    
    # Calculate quick statistics
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    if selected_user != "All Users":
        user_id = selected_user.split("(")[1].split(")")[0]
        total_sensor_records = conn.execute("SELECT COUNT(*) FROM sensor_data WHERE user_id = ?", (user_id,)).fetchone()[0]
        total_notifications = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ?", (user_id,)).fetchone()[0]
        total_water_history = conn.execute("SELECT COUNT(*) FROM water_level_history WHERE user_id = ?", (user_id,)).fetchone()[0]
    else:
        total_sensor_records = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
        total_notifications = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
        total_water_history = conn.execute("SELECT COUNT(*) FROM water_level_history").fetchone()[0]
    
    conn.close()
    
    st.metric("Total Users", total_users)
    st.metric("Sensor Records", total_sensor_records)
    st.metric("Notifications", total_notifications)
    st.metric("Water History", total_water_history)

# Main content area
st.markdown('<div class="sub-header">📋 Database Contents</div>', unsafe_allow_html=True)

# Create tabs for different data views
tab1, tab2, tab3, tab4 = st.tabs(["👥 Users", "📡 Sensor Data", "🔔 Notifications", "💧 Water History"])

with tab1:
    st.markdown("### Users Table")
    
    conn = get_db_connection()
    
    # Get users data
    if selected_user == "All Users":
        users_df = pd.read_sql_query("""
            SELECT 
                id,
                username,
                user_id,
                farm_name,
                location,
                created_at,
                (SELECT COUNT(*) FROM sensor_data WHERE sensor_data.user_id = users.user_id) as sensor_records,
                (SELECT COUNT(*) FROM notifications WHERE notifications.user_id = users.user_id) as notification_count
            FROM users 
            ORDER BY created_at DESC
        """, conn)
    else:
        user_id = selected_user.split("(")[1].split(")")[0]
        users_df = pd.read_sql_query(f"""
            SELECT 
                id,
                username,
                user_id,
                farm_name,
                location,
                created_at,
                (SELECT COUNT(*) FROM sensor_data WHERE sensor_data.user_id = users.user_id) as sensor_records,
                (SELECT COUNT(*) FROM notifications WHERE notifications.user_id = users.user_id) as notification_count
            FROM users 
            WHERE user_id = '{user_id}'
            ORDER BY created_at DESC
        """, conn)
    
    conn.close()
    
    if not users_df.empty:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(users_df))
        with col2:
            avg_records = users_df['sensor_records'].mean()
            st.metric("Avg Sensor Records", f"{avg_records:.1f}")
        with col3:
            avg_notifications = users_df['notification_count'].mean()
            st.metric("Avg Notifications", f"{avg_notifications:.1f}")
        with col4:
            oldest_user = users_df['created_at'].min()
            st.metric("Oldest User", oldest_user[:10])
        
        # Display dataframe
        st.dataframe(
            users_df,
            use_container_width=True,
            column_config={
                "id": "ID",
                "username": "Username",
                "user_id": "User ID",
                "farm_name": "Farm Name",
                "location": "Location",
                "created_at": "Created At",
                "sensor_records": "Sensor Records",
                "notification_count": "Notifications"
            }
        )
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = users_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="users_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_data = users_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name="users_data.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Visualization
        st.markdown("### 📈 User Activity Visualization")
        
        col1, col2 = st.columns(2)
        with col1:
            # Users by location
            if not users_df['location'].isnull().all():
                location_counts = users_df['location'].value_counts().reset_index()
                location_counts.columns = ['Location', 'Count']
                fig1 = px.bar(
                    location_counts.head(10),
                    x='Location',
                    y='Count',
                    title='Users by Location',
                    color='Count',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Users over time
            users_df['created_date'] = pd.to_datetime(users_df['created_at']).dt.date
            daily_users = users_df.groupby('created_date').size().reset_index()
            daily_users.columns = ['Date', 'New Users']
            
            fig2 = px.line(
                daily_users,
                x='Date',
                y='New Users',
                title='New Users Over Time',
                markers=True
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No user data found.")

with tab2:
    st.markdown("### Sensor Data Table")
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = """
        SELECT 
            sd.id,
            sd.user_id,
            u.username,
            u.farm_name,
            sd.solar_input,
            sd.battery_level,
            sd.water_level,
            CASE 
                WHEN sd.drain_status = 1 THEN 'OPEN' 
                ELSE 'CLOSED' 
            END as drain_status,
            sd.last_update
        FROM sensor_data sd
        LEFT JOIN users u ON sd.user_id = u.user_id
        WHERE DATE(sd.last_update) BETWEEN ? AND ?
    """
    
    params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    if selected_user != "All Users":
        user_id = selected_user.split("(")[1].split(")")[0]
        query += " AND sd.user_id = ?"
        params.append(user_id)
    
    query += " ORDER BY sd.last_update DESC"
    
    sensor_df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not sensor_df.empty:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_solar = sensor_df['solar_input'].mean()
            st.metric("Avg Solar Input", f"{avg_solar:.1f}W")
        with col2:
            avg_battery = sensor_df['battery_level'].mean()
            st.metric("Avg Battery", f"{avg_battery:.1f}%")
        with col3:
            avg_water = sensor_df['water_level'].mean()
            st.metric("Avg Water Level", f"{avg_water:.1f}%")
        with col4:
            open_drains = len(sensor_df[sensor_df['drain_status'] == 'OPEN'])
            st.metric("Open Drains", open_drains)
        
        # Display dataframe
        st.dataframe(
            sensor_df,
            use_container_width=True,
            column_config={
                "id": "ID",
                "user_id": "User ID",
                "username": "Username",
                "farm_name": "Farm Name",
                "solar_input": "Solar (W)",
                "battery_level": "Battery (%)",
                "water_level": "Water (%)",
                "drain_status": "Drain Status",
                "last_update": "Last Update"
            }
        )
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = sensor_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="sensor_data.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_data = sensor_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name="sensor_data.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Visualization
        st.markdown("### 📈 Sensor Data Visualization")
        
        if len(sensor_df) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Time series of sensor readings
                sensor_df['last_update_dt'] = pd.to_datetime(sensor_df['last_update'])
                fig1 = go.Figure()
                
                fig1.add_trace(go.Scatter(
                    x=sensor_df['last_update_dt'],
                    y=sensor_df['solar_input'],
                    mode='lines+markers',
                    name='Solar Input',
                    line=dict(color='orange', width=2)
                ))
                
                fig1.add_trace(go.Scatter(
                    x=sensor_df['last_update_dt'],
                    y=sensor_df['battery_level'],
                    mode='lines+markers',
                    name='Battery Level',
                    yaxis='y2',
                    line=dict(color='purple', width=2)
                ))
                
                fig1.update_layout(
                    title='Solar & Battery Over Time',
                    xaxis_title='Time',
                    yaxis=dict(title='Solar Input (W)', color='orange'),
                    yaxis2=dict(
                        title='Battery Level (%)',
                        color='purple',
                        overlaying='y',
                        side='right'
                    ),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Water level distribution
                fig2 = px.histogram(
                    sensor_df,
                    x='water_level',
                    nbins=20,
                    title='Water Level Distribution',
                    color_discrete_sequence=['blue'],
                    opacity=0.7
                )
                fig2.update_layout(
                    xaxis_title='Water Level (%)',
                    yaxis_title='Count'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Recent sensor data chart
            recent_data = sensor_df.head(50)  # Show last 50 records
            fig3 = px.scatter(
                recent_data,
                x='last_update',
                y='water_level',
                color='username',
                size='solar_input',
                hover_data=['battery_level', 'drain_status'],
                title='Recent Sensor Readings',
                labels={
                    'water_level': 'Water Level (%)',
                    'last_update': 'Time',
                    'solar_input': 'Solar Input (W)',
                    'username': 'User'
                }
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No sensor data found for the selected filters.")

with tab3:
    st.markdown("### Notifications Table")
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = """
        SELECT 
            n.id,
            n.user_id,
            u.username,
            u.farm_name,
            n.title,
            n.message,
            n.notification_type,
            CASE 
                WHEN n.is_read = 1 THEN 'READ' 
                ELSE 'UNREAD' 
            END as status,
            n.created_at
        FROM notifications n
        LEFT JOIN users u ON n.user_id = u.user_id
        WHERE DATE(n.created_at) BETWEEN ? AND ?
    """
    
    params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    if selected_user != "All Users":
        user_id = selected_user.split("(")[1].split(")")[0]
        query += " AND n.user_id = ?"
        params.append(user_id)
    
    query += " ORDER BY n.created_at DESC"
    
    notifications_df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not notifications_df.empty:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_notifications = len(notifications_df)
            st.metric("Total Notifications", total_notifications)
        with col2:
            unread_count = len(notifications_df[notifications_df['status'] == 'UNREAD'])
            st.metric("Unread", unread_count)
        with col3:
            emergency_count = len(notifications_df[notifications_df['notification_type'] == 'emergency'])
            st.metric("Emergencies", emergency_count)
        with col4:
            warning_count = len(notifications_df[notifications_df['notification_type'] == 'warning'])
            st.metric("Warnings", warning_count)
        
        # Display dataframe
        st.dataframe(
            notifications_df,
            use_container_width=True,
            column_config={
                "id": "ID",
                "user_id": "User ID",
                "username": "Username",
                "farm_name": "Farm Name",
                "title": "Title",
                "message": "Message",
                "notification_type": "Type",
                "status": "Status",
                "created_at": "Created At"
            },
            height=400
        )
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = notifications_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="notifications.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_data = notifications_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name="notifications.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Visualization
        st.markdown("### 📈 Notification Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Notification types pie chart
            type_counts = notifications_df['notification_type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            
            fig1 = px.pie(
                type_counts,
                values='Count',
                names='Type',
                title='Notification Types Distribution',
                color='Type',
                color_discrete_map={
                    'emergency': 'red',
                    'warning': 'orange',
                    'info': 'blue',
                    'success': 'green'
                }
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Notifications over time
            notifications_df['created_date'] = pd.to_datetime(notifications_df['created_at']).dt.date
            daily_notifications = notifications_df.groupby('created_date').size().reset_index()
            daily_notifications.columns = ['Date', 'Count']
            
            fig2 = px.line(
                daily_notifications,
                x='Date',
                y='Count',
                title='Notifications Over Time',
                markers=True,
                line_shape='spline'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # User notification stats
        if selected_user == "All Users":
            user_notification_counts = notifications_df.groupby('username').size().reset_index()
            user_notification_counts.columns = ['User', 'Notification Count']
            
            fig3 = px.bar(
                user_notification_counts.sort_values('Notification Count', ascending=False).head(10),
                x='User',
                y='Notification Count',
                title='Top 10 Users by Notification Count',
                color='Notification Count',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No notifications found for the selected filters.")

with tab4:
    st.markdown("### Water Level History Table")
    
    conn = get_db_connection()
    
    # Build query based on filters
    query = """
        SELECT 
            wlh.id,
            wlh.user_id,
            u.username,
            u.farm_name,
            wlh.water_level,
            wlh.created_at
        FROM water_level_history wlh
        LEFT JOIN users u ON wlh.user_id = u.user_id
        WHERE DATE(wlh.created_at) BETWEEN ? AND ?
    """
    
    params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    
    if selected_user != "All Users":
        user_id = selected_user.split("(")[1].split(")")[0]
        query += " AND wlh.user_id = ?"
        params.append(user_id)
    
    query += " ORDER BY wlh.created_at DESC"
    
    water_df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not water_df.empty:
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_water = water_df['water_level'].mean()
            st.metric("Avg Water Level", f"{avg_water:.1f}%")
        with col2:
            max_water = water_df['water_level'].max()
            st.metric("Max Water Level", f"{max_water:.1f}%")
        with col3:
            min_water = water_df['water_level'].min()
            st.metric("Min Water Level", f"{min_water:.1f}%")
        with col4:
            total_readings = len(water_df)
            st.metric("Total Readings", total_readings)
        
        # Display dataframe
        st.dataframe(
            water_df,
            use_container_width=True,
            column_config={
                "id": "ID",
                "user_id": "User ID",
                "username": "Username",
                "farm_name": "Farm Name",
                "water_level": "Water Level (%)",
                "created_at": "Timestamp"
            },
            height=400
        )
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = water_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="water_history.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            json_data = water_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_data,
                file_name="water_history.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Visualization
        st.markdown("### 📈 Water Level Analysis")
        
        if len(water_df) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Water level over time
                water_df['created_dt'] = pd.to_datetime(water_df['created_at'])
                
                fig1 = px.line(
                    water_df,
                    x='created_dt',
                    y='water_level',
                    color='username' if selected_user == "All Users" else None,
                    title='Water Level Over Time',
                    labels={
                        'created_dt': 'Time',
                        'water_level': 'Water Level (%)',
                        'username': 'User'
                    },
                    markers=True
                )
                
                # Add threshold lines
                fig1.add_hline(y=95, line_dash="dash", line_color="red", annotation_text="Emergency (95%)")
                fig1.add_hline(y=90, line_dash="dash", line_color="orange", annotation_text="Critical (90%)")
                fig1.add_hline(y=75, line_dash="dash", line_color="yellow", annotation_text="Warning (75%)")
                
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Water level distribution
                fig2 = px.histogram(
                    water_df,
                    x='water_level',
                    nbins=20,
                    title='Water Level Distribution',
                    color_discrete_sequence=['blue'],
                    opacity=0.7
                )
                
                # Add vertical lines for thresholds
                fig2.add_vline(x=95, line_dash="dash", line_color="red", annotation_text="Emergency")
                fig2.add_vline(x=90, line_dash="dash", line_color="orange", annotation_text="Critical")
                fig2.add_vline(x=75, line_dash="dash", line_color="yellow", annotation_text="Warning")
                
                fig2.update_layout(
                    xaxis_title='Water Level (%)',
                    yaxis_title='Frequency'
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # Hourly water level analysis
            if len(water_df) > 100:
                water_df['hour'] = pd.to_datetime(water_df['created_at']).dt.hour
                hourly_avg = water_df.groupby('hour')['water_level'].mean().reset_index()
                
                fig3 = px.bar(
                    hourly_avg,
                    x='hour',
                    y='water_level',
                    title='Average Water Level by Hour of Day',
                    labels={'hour': 'Hour of Day', 'water_level': 'Avg Water Level (%)'},
                    color='water_level',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No water level history found for the selected filters.")

# Database schema viewer
st.markdown("---")
st.markdown('<div class="sub-header">🗄️ Database Schema</div>', unsafe_allow_html=True)

with st.expander("View Database Schema"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get table information
    tables = cursor.execute("""
        SELECT name, sql 
        FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()
    
    for table in tables:
        table_name = table['name']
        table_sql = table['sql']
        
        st.markdown(f"### **Table: {table_name}**")
        
        # Get column information
        columns = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
        
        col_info_df = pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
        
        # Display column information
        st.dataframe(
            col_info_df[['name', 'type', 'notnull', 'pk']],
            column_config={
                'name': 'Column Name',
                'type': 'Data Type',
                'notnull': 'Not Null',
                'pk': 'Primary Key'
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Get row count
        row_count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        st.caption(f"Total rows: {row_count}")
        
        st.markdown("---")
    
    conn.close()

# Data Management Section
st.markdown("---")
st.markdown('<div class="sub-header">⚙️ Data Management</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🗑️ Clear Old Data", use_container_width=True, type="secondary"):
        with st.spinner("Cleaning up old data..."):
            conn = get_db_connection()
            # Delete data older than 30 days
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

with col2:
    if st.button("📊 Generate Report", use_container_width=True, type="primary"):
        with st.spinner("Generating report..."):
            # Create a comprehensive report
            conn = get_db_connection()
            
            report_data = {
                "report_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "filters_applied": {
                    "date_range": f"{start_date} to {end_date}",
                    "user": selected_user
                },
                "summary": {
                    "total_users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                    "total_sensor_records": conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0],
                    "total_notifications": conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0],
                    "total_water_readings": conn.execute("SELECT COUNT(*) FROM water_level_history").fetchone()[0]
                }
            }
            
            conn.close()
            
            # Display report
            st.json(report_data)
            
            # Offer download
            import json
            report_json = json.dumps(report_data, indent=2)
            st.download_button(
                label="📥 Download Report",
                data=report_json,
                file_name=f"agriculture_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

with col3:
    if st.button("🔄 Reset Filters", use_container_width=True):
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🌾 <b>Smart Agriculture IoT Data Viewer</b> | Database: smart_agriculture.db</p>
        <p>Last Updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    unsafe_allow_html=True
)