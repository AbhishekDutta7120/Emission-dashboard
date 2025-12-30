import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import anthropic
import os
import sqlite3
from pathlib import Path
import hashlib

st.set_page_config(page_title="Emissions Monitor", page_icon="🌍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .main {background-color: #ffffff;}
    .stMetric {background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px;}
    [data-testid="stMetricValue"] {font-size: 28px; color: #0f172a;}
    [data-testid="stMetricLabel"] {color: #64748b; font-size: 14px;}
    h1, h2, h3 {color: #0f172a;}
    .admin-section {
        background-color: #fef3c7;
        border: 2px solid #f59e0b;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session states
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'show_admin' not in st.session_state:
    st.session_state.show_admin = False

# Admin password
ADMIN_PASSWORD_HASH = hashlib.sha256("B0B6@11e25".encode()).hexdigest()

# Database setup
DB_PATH = Path("emissions_data.db")

def init_database():
    """Initialize SQLite database with emissions data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sector_emissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL,
            sector TEXT NOT NULL,
            value INTEGER NOT NULL,
            change REAL NOT NULL,
            subsectors TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS yearly_totals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year TEXT NOT NULL UNIQUE,
            total INTEGER NOT NULL,
            energy INTEGER NOT NULL,
            transport INTEGER NOT NULL,
            industry INTEGER NOT NULL,
            other INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regional_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT NOT NULL UNIQUE,
            value INTEGER NOT NULL,
            color TEXT NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM sector_emissions")
    if cursor.fetchone()[0] == 0:
        sector_data = [
            ('2021', 'Energy Production', 13100, 1.8, 'Coal, Natural Gas, Oil'),
            ('2021', 'Industrial Process', 5600, -1.5, 'Steel, Cement, Chemicals'),
            ('2021', 'Transportation', 7600, 2.1, 'Road, Aviation, Shipping'),
            ('2021', 'Agriculture', 6000, 0.5, 'Livestock, Crop Production'),
            ('2021', 'Buildings', 3100, -0.8, 'Residential, Commercial'),
            ('2021', 'Waste', 1000, -2.5, 'Landfills, Wastewater'),
            ('2022', 'Energy Production', 13400, 2.3, 'Coal, Natural Gas, Oil'),
            ('2022', 'Industrial Process', 5800, 3.6, 'Steel, Cement, Chemicals'),
            ('2022', 'Transportation', 8000, 5.3, 'Road, Aviation, Shipping'),
            ('2022', 'Agriculture', 6100, 1.7, 'Livestock, Crop Production'),
            ('2022', 'Buildings', 3200, 3.2, 'Residential, Commercial'),
            ('2022', 'Waste', 1000, 0.0, 'Landfills, Wastewater'),
            ('2023', 'Energy Production', 13500, 0.7, 'Coal, Natural Gas, Oil'),
            ('2023', 'Industrial Process', 5800, 0.0, 'Steel, Cement, Chemicals'),
            ('2023', 'Transportation', 8100, 1.3, 'Road, Aviation, Shipping'),
            ('2023', 'Agriculture', 6200, 1.6, 'Livestock, Crop Production'),
            ('2023', 'Buildings', 3200, 0.0, 'Residential, Commercial'),
            ('2023', 'Waste', 1300, 30.0, 'Landfills, Wastewater'),
            ('2024', 'Energy Production', 13800, 2.2, 'Coal, Natural Gas, Oil'),
            ('2024', 'Industrial Process', 5900, 1.7, 'Steel, Cement, Chemicals'),
            ('2024', 'Transportation', 8300, 2.5, 'Road, Aviation, Shipping'),
            ('2024', 'Agriculture', 6300, 1.6, 'Livestock, Crop Production'),
            ('2024', 'Buildings', 3200, 0.0, 'Residential, Commercial'),
            ('2024', 'Waste', 1400, 7.7, 'Landfills, Wastewater'),
            ('2025', 'Energy Production', 14000, 1.4, 'Coal, Natural Gas, Oil'),
            ('2025', 'Industrial Process', 6000, 1.7, 'Steel, Cement, Chemicals'),
            ('2025', 'Transportation', 8500, 2.4, 'Road, Aviation, Shipping'),
            ('2025', 'Agriculture', 6400, 1.6, 'Livestock, Crop Production'),
            ('2025', 'Buildings', 3000, -6.3, 'Residential, Commercial'),
            ('2025', 'Waste', 1500, 7.1, 'Landfills, Wastewater'),
        ]
        cursor.executemany("INSERT INTO sector_emissions (year, sector, value, change, subsectors) VALUES (?, ?, ?, ?, ?)", sector_data)
        
        yearly_data = [
            ('2021', 36400, 13100, 7600, 5600, 10100),
            ('2022', 37500, 13400, 8000, 5800, 10300),
            ('2023', 38100, 13500, 8100, 5800, 10700),
            ('2024', 38900, 13800, 8300, 5900, 10900),
            ('2025', 39400, 14000, 8500, 6000, 10900),
        ]
        cursor.executemany("INSERT INTO yearly_totals (year, total, energy, transport, industry, other) VALUES (?, ?, ?, ?, ?, ?)", yearly_data)
        
        regional_data = [
            ('Asia-Pacific', 18500, '#f59e0b'),
            ('North America', 6800, '#3b82f6'),
            ('Europe', 4200, '#8b5cf6'),
            ('Middle East', 3900, '#ec4899'),
            ('Latin America', 2400, '#10b981'),
            ('Africa', 1500, '#06b6d4'),
        ]
        cursor.executemany("INSERT INTO regional_data (region, value, color) VALUES (?, ?, ?)", regional_data)
    
    conn.commit()
    conn.close()

init_database()

def get_sector_data(year):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT sector, value, change, subsectors FROM sector_emissions WHERE year = ?"
    df = pd.read_sql_query(query, conn, params=(year,))
    conn.close()
    return df

def get_all_sector_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM sector_emissions ORDER BY year, sector", conn)
    conn.close()
    return df

def get_yearly_totals():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM yearly_totals ORDER BY year", conn)
    conn.close()
    return df

def get_regional_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM regional_data", conn)
    conn.close()
    return df

def update_sector_emission(id, year, sector, value, change, subsectors):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE sector_emissions SET year=?, sector=?, value=?, change=?, subsectors=? WHERE id=?",
                   (year, sector, value, change, subsectors, id))
    conn.commit()
    conn.close()

def add_sector_emission(year, sector, value, change, subsectors):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sector_emissions (year, sector, value, change, subsectors) VALUES (?, ?, ?, ?, ?)",
                   (year, sector, value, change, subsectors))
    conn.commit()
    conn.close()

def delete_sector_emission(id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sector_emissions WHERE id=?", (id,))
    conn.commit()
    conn.close()

def update_regional_data(id, region, value, color):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE regional_data SET region=?, value=?, color=? WHERE id=?", (region, value, color, id))
    conn.commit()
    conn.close()

def analyze_query(query, selected_year, current_data, total_emissions):
    q = query.lower()
    if 'energy' in q or 'power' in q:
        energy_data = current_data[current_data['sector'] == 'Energy Production'].iloc[0]
        return {'type': 'data', 'response': f'Energy production remains the largest emissions source at {energy_data["value"]:,.0f} Mt CO2e ({(energy_data["value"] / total_emissions * 100):.1f}% of total), showing a {energy_data["change"]:+.1f}% change from the previous year.'}
    if 'transport' in q:
        transport_data = current_data[current_data['sector'] == 'Transportation'].iloc[0]
        return {'type': 'data', 'response': f'Transportation emissions reached {transport_data["value"]:,.0f} Mt CO2e, {"up" if transport_data["change"] > 0 else "down"} {abs(transport_data["change"]):.1f}% from the previous year.'}
    if 'trend' in q:
        return {'type': 'data', 'response': 'Global emissions increased from 36.4 Gt in 2021 to 39.4 Gt in 2025, an 8.2% growth.'}
    if 'region' in q:
        return {'type': 'data', 'response': 'Asia-Pacific leads with 18,500 Mt CO2e (48.6%), driven by China and India.'}
    if any(word in q for word in ['latest', 'news', 'policy']):
        return {'type': 'search', 'query': query}
    return {'type': 'data', 'response': f'Viewing {selected_year} data with {total_emissions / 1000:.1f} Gt total. What would you like to know?'}

def search_web(query):
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            return "Web search requires API key. Ask about dashboard data!"
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1000, messages=[{"role": "user", "content": f"Search: {query}. Focus on emissions and climate."}], tools=[{"type": "web_search_20250305", "name": "web_search"}])
        return "".join([block.text for block in message.content if block.type == "text"]) or "No results."
    except:
        return "Search needs API key. Ask about dashboard data!"

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio("Go to", ["📊 Dashboard", "🔧 Admin Panel"], label_visibility="collapsed")
    
    if page == "🔧 Admin Panel":
        st.divider()
        if not st.session_state.admin_authenticated:
            st.warning("⚠️ Admin access required")

# ADMIN PANEL
if page == "🔧 Admin Panel":
    st.title("🔧 Admin Panel")
    
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Admin Login")
        #st.info("")
        
        password = st.text_input("Enter admin password", type="password", key="admin_password")
        
        if st.button("Login", type="primary"):
            if hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
                st.session_state.admin_authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid password")
    
    else:
        st.success("✅ Logged in as Admin")
        
        if st.button("🚪 Logout"):
            st.session_state.admin_authenticated = False
            st.rerun()
        
        st.divider()
        
        tab1, tab2, tab3 = st.tabs(["📊 Sector Emissions", "🌍 Regional Data", "📥 Export/Import"])
        
        # TAB 1: Sector Emissions Management
        with tab1:
            st.subheader("Manage Sector Emissions")
            
            all_sectors = get_all_sector_data()
            
            st.markdown("#### Add New Sector Data")
            col1, col2, col3 = st.columns(3)
            with col1:
                new_year = st.selectbox("Year", ['2021', '2022', '2023', '2024', '2025', '2026', '2027'], key="new_year")
                new_sector = st.selectbox("Sector", ['Energy Production', 'Industrial Process', 'Transportation', 'Agriculture', 'Buildings', 'Waste'], key="new_sector")
            with col2:
                new_value = st.number_input("Emissions (Mt CO2e)", min_value=0, value=10000, key="new_value")
                new_change = st.number_input("YoY Change (%)", value=0.0, format="%.1f", key="new_change")
            with col3:
                new_subsectors = st.text_input("Subsectors (comma separated)", value="Subsector 1, Subsector 2", key="new_subsectors")
            
            if st.button("➕ Add New Record", type="primary"):
                add_sector_emission(new_year, new_sector, new_value, new_change, new_subsectors)
                st.success(f"✅ Added {new_sector} data for {new_year}")
                st.rerun()
            
            st.divider()
            st.markdown("#### Edit Existing Data")
            
            st.dataframe(all_sectors, width='stretch', height=400)
            
            st.markdown("#### Delete Record")
            record_to_delete = st.number_input("Enter ID to delete", min_value=1, value=1, key="delete_id")
            if st.button("🗑️ Delete Record", type="secondary"):
                delete_sector_emission(record_to_delete)
                st.success(f"✅ Deleted record ID: {record_to_delete}")
                st.rerun()
        
        # TAB 2: Regional Data Management
        with tab2:
            st.subheader("Manage Regional Data")
            
            regional = get_regional_data()
            st.dataframe(regional, width='stretch')
            
            st.markdown("#### Edit Regional Data")
            region_id = st.selectbox("Select Region to Edit", regional['id'].tolist())
            selected_region = regional[regional['id'] == region_id].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                edit_region = st.text_input("Region Name", value=selected_region['region'])
            with col2:
                edit_value = st.number_input("Emissions Value", value=int(selected_region['value']))
            with col3:
                edit_color = st.color_picker("Chart Color", value=selected_region['color'])
            
            if st.button("💾 Update Regional Data", type="primary"):
                update_regional_data(region_id, edit_region, edit_value, edit_color)
                st.success(f"✅ Updated {edit_region}")
                st.rerun()
        
        # TAB 3: Export/Import
        with tab3:
            st.subheader("Export & Import Data")
            
            st.markdown("#### 📥 Export Database")
            st.info("Download your database for backup or offline editing")
            
            col1, col2 = st.columns(2)
            with col1:
                # Export sector data as CSV
                sectors_csv = all_sectors.to_csv(index=False)
                st.download_button(
                    label="📊 Download Sector Data (CSV)",
                    data=sectors_csv,
                    file_name="sector_emissions.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Export regional data as CSV
                regional_csv = regional.to_csv(index=False)
                st.download_button(
                    label="🌍 Download Regional Data (CSV)",
                    data=regional_csv,
                    file_name="regional_data.csv",
                    mime="text/csv"
                )
            
            st.divider()
            st.markdown("#### 📤 Database Info")
            st.info(f"""
            **Database Location:** {DB_PATH}  
            **Total Sector Records:** {len(all_sectors)}  
            **Regional Records:** {len(regional)}  
            **Years Covered:** {', '.join(sorted(all_sectors['year'].unique()))}
            """)

# MAIN DASHBOARD
else:
    selected_year = st.selectbox("Year", ['2025', '2024', '2023', '2022', '2021'], key='year_selector')
    st.session_state.selected_year = selected_year
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🌍 Emissions Monitor")
        st.caption("Real-time monitoring & AI-powered insights • Database-powered")
    with col2:
        st.write("")

    st.divider()

    current_year_data = get_sector_data(selected_year)
    yearly_data = get_yearly_totals()
    region_data = get_regional_data()

    total_emissions = current_year_data['value'].sum()
    largest_sector = current_year_data.loc[current_year_data['value'].idxmax()]
    year_change_map = {'2025': '+1.3% from 2024', '2024': '+2.1% from 2023', '2023': '+1.6% from 2022', '2022': '+3.0% from 2021', '2021': '+8.5% from 2020'}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Emissions", f"{total_emissions/1000:.1f} Gt", year_change_map.get(selected_year, ''), delta_color="inverse")
    with col2:
        st.metric("Largest Source", largest_sector['sector'].split()[0], f"{(largest_sector['value']/total_emissions*100):.1f}% of total")
    with col3:
        st.metric("Per Capita", "4.8 t", "CO2e per person")
    with col4:
        st.metric("Target Gap", "-43%", "vs 2030 goal", delta_color="inverse")

    st.divider()

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Emissions by Sector")
        fig_bar = px.bar(current_year_data, y='sector', x='value', orientation='h', labels={'value': 'Million tonnes CO2e', 'sector': ''}, color_discrete_sequence=['#3b82f6'])
        fig_bar.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12), showlegend=False)
        fig_bar.update_xaxes(gridcolor='rgba(100,116,139,0.3)', showgrid=True)
        fig_bar.update_yaxes(gridcolor='rgba(100,116,139,0.3)', showgrid=False)
        st.plotly_chart(fig_bar, width='stretch')

    with col2:
        st.subheader("By Region")
        fig_pie = px.pie(region_data, values='value', names='region', hole=0.5, color='region', color_discrete_map={region: color for region, color in zip(region_data['region'], region_data['color'])})
        fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0), showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1), font=dict(size=11), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        fig_pie.update_traces(textposition='inside', textinfo='percent', textfont_size=11)
        st.plotly_chart(fig_pie, width='stretch')

    st.subheader("Emissions Trend (2021-2025)")
    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(x=yearly_data['year'], y=yearly_data['total'], mode='lines', fill='tozeroy', line=dict(color='#3b82f6', width=2), fillcolor='rgba(59, 130, 246, 0.1)'))
    fig_area.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12), showlegend=False, xaxis=dict(title='', gridcolor='rgba(100,116,139,0.3)'), yaxis=dict(title='Million tonnes CO2e', gridcolor='rgba(100,116,139,0.3)'))
    st.plotly_chart(fig_area, width='stretch')

    st.subheader("Sector Details")
    display_data = current_year_data.copy()
    display_data['emissions_mt'] = display_data['value'].apply(lambda x: f"{x:,.0f}")
    display_data['percentage'] = (display_data['value'] / total_emissions * 100).apply(lambda x: f"{x:.1f}%")
    display_data['yoy_change'] = display_data['change'].apply(lambda x: f"{'+' if x > 0 else ''}{x:.1f}%")
    st.dataframe(display_data[['sector', 'emissions_mt', 'percentage', 'yoy_change', 'subsectors']].rename(columns={'sector': 'Sector', 'emissions_mt': 'Emissions (Mt CO2e)', 'percentage': '% of Total', 'yoy_change': 'YoY Change', 'subsectors': 'Key Subsectors'}), width='stretch', hide_index=True)

    st.divider()

# Chat Interface
st.subheader("💬 AI Emissions Assistant")
st.caption("Ask questions about the data or search for latest climate information")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about emissions data or search the web..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            analysis = analyze_query(prompt, selected_year, current_year_data, total_emissions)
            
            if analysis['type'] == 'search':
                response = search_web(analysis['query'])
            else:
                response = analysis['response']
            
            st.markdown(response)
    
    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar with quick actions
with st.sidebar:
    st.header("Quick Questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Highest emitter?", use_container_width=True):
            prompt = "Which sector emits the most?"
            st.session_state.messages.append({"role": "user", "content": prompt})
            analysis = analyze_query(prompt, selected_year, current_year_data, total_emissions)
            st.session_state.messages.append({"role": "assistant", "content": analysis['response']})
            st.rerun()
    
    with col2:
        if st.button("📈 Show trend", use_container_width=True):
            prompt = "Show me the emissions trend"
            st.session_state.messages.append({"role": "user", "content": prompt})
            analysis = analyze_query(prompt, selected_year, current_year_data, total_emissions)
            st.session_state.messages.append({"role": "assistant", "content": analysis['response']})
            st.rerun()
    
    if st.button("🌍 Regional breakdown", use_container_width=True):
        prompt = "Tell me about regional emissions"
        st.session_state.messages.append({"role": "user", "content": prompt})
        analysis = analyze_query(prompt, selected_year, current_year_data, total_emissions)
        st.session_state.messages.append({"role": "assistant", "content": analysis['response']})
        st.rerun()
    
    if st.button("📰 Latest climate news", use_container_width=True):
        prompt = "What's the latest climate news?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": "Searching the web for latest climate news..."})
        st.rerun()
    
    st.divider()
    
    st.caption("📊 Data updated: December 2025")
    st.caption("🔍 Web search powered by Claude")
    st.caption(f"📅 Currently viewing: {st.session_state.selected_year}")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    with st.expander("ℹ️ About"):
        st.write("""
        **Emissions Monitor Dashboard**
        
        This dashboard provides real-time insights into global emissions data across different sectors and regions.
        
        **Features:**
        - Interactive year selector (2021-2025)
        - Sector-wise emission breakdown
        - Regional distribution analysis
        - AI-powered chat assistant
        - Web search for latest climate news
        
        **Data Sources:**
        Global emissions data compiled from various international agencies and research institutions.
        """)
