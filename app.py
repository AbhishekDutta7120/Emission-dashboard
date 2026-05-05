import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import hashlib
from database import (
    init_database, get_sector_data, get_all_sector_data, get_yearly_totals,
    get_regional_data, update_sector_emission, add_sector_emission,
    delete_sector_emission, update_regional_data, DB_PATH
)
from ai_assistant import analyze_query, search_web

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

# Admin password handling (Security improvement)
# Tries to load from st.secrets, falls back to old hash to avoid breaking existing setups, but removes plaintext from code.
try:
    ADMIN_PASSWORD_HASH = st.secrets["ADMIN_PASSWORD_HASH"]
except FileNotFoundError:
    ADMIN_PASSWORD_HASH = "4eaca7fe0eac47808711a187660712b6c10bf5fdeb182f5cfebd626fe3604fbc"
except KeyError:
    ADMIN_PASSWORD_HASH = "4eaca7fe0eac47808711a187660712b6c10bf5fdeb182f5cfebd626fe3604fbc"

# Initialize Database
init_database()

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


# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Interface - Only on Dashboard
if page == "📊 Dashboard":
    st.subheader("💬 AI Emissions Assistant")
    st.caption("Ask questions about the data or search for latest climate information")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about emissions data or search the web..."):
        # Get current data
        current_year = st.session_state.selected_year
        current_data = get_sector_data(current_year)
        total = current_data['value'].sum()
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                analysis = analyze_query(prompt, current_year, current_data, total)
                
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
    
    # Only show if on dashboard page
    if page == "📊 Dashboard":
        col1, col2 = st.columns(2)
        
        # Get current data safely
        current_year = st.session_state.selected_year
        current_data = get_sector_data(current_year)
        total = current_data['value'].sum()
        
        with col1:
            if st.button("🔍 Highest emitter?", use_container_width=True):
                prompt = "Which sector emits the most?"
                st.session_state.messages.append({"role": "user", "content": prompt})
                analysis = analyze_query(prompt, current_year, current_data, total)
                st.session_state.messages.append({"role": "assistant", "content": analysis['response']})
                st.rerun()
        
        with col2:
            if st.button("📈 Show trend", use_container_width=True):
                prompt = "Show me the emissions trend"
                st.session_state.messages.append({"role": "user", "content": prompt})
                analysis = analyze_query(prompt, current_year, current_data, total)
                st.session_state.messages.append({"role": "assistant", "content": analysis['response']})
                st.rerun()
        
        if st.button("🌍 Regional breakdown", use_container_width=True):
            prompt = "Tell me about regional emissions"
            st.session_state.messages.append({"role": "user", "content": prompt})
            analysis = analyze_query(prompt, current_year, current_data, total)
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
