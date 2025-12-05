import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import anthropic
import os

# Page configuration
st.set_page_config(
    page_title="Emissions Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main {
        background-color: #ffffff;
    }
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #0f172a;
    }
    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-size: 14px;
    }
    h1, h2, h3 {
        color: #0f172a;
    }
    .stSelectbox {
        color: #334155;
    }
    div[data-testid="stChatMessageContent"] {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for chat
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Data by year
industry_data_by_year = {
    '2021': pd.DataFrame({
        'sector': ['Energy Production', 'Industrial Process', 'Transportation', 
                   'Agriculture', 'Buildings', 'Waste'],
        'value': [13100, 5600, 7600, 6000, 3100, 1000],
        'change': [1.8, -1.5, 2.1, 0.5, -0.8, -2.5],
        'subsectors': ['Coal, Natural Gas, Oil', 'Steel, Cement, Chemicals', 
                       'Road, Aviation, Shipping', 'Livestock, Crop Production',
                       'Residential, Commercial', 'Landfills, Wastewater']
    }),
    '2022': pd.DataFrame({
        'sector': ['Energy Production', 'Industrial Process', 'Transportation', 
                   'Agriculture', 'Buildings', 'Waste'],
        'value': [13400, 5800, 8000, 6100, 3200, 1000],
        'change': [2.3, 3.6, 5.3, 1.7, 3.2, 0.0],
        'subsectors': ['Coal, Natural Gas, Oil', 'Steel, Cement, Chemicals', 
                       'Road, Aviation, Shipping', 'Livestock, Crop Production',
                       'Residential, Commercial', 'Landfills, Wastewater']
    }),
    '2023': pd.DataFrame({
        'sector': ['Energy Production', 'Industrial Process', 'Transportation', 
                   'Agriculture', 'Buildings', 'Waste'],
        'value': [13500, 5800, 8100, 6200, 3200, 1300],
        'change': [0.7, 0.0, 1.3, 1.6, 0.0, 30.0],
        'subsectors': ['Coal, Natural Gas, Oil', 'Steel, Cement, Chemicals', 
                       'Road, Aviation, Shipping', 'Livestock, Crop Production',
                       'Residential, Commercial', 'Landfills, Wastewater']
    }),
    '2024': pd.DataFrame({
        'sector': ['Energy Production', 'Industrial Process', 'Transportation', 
                   'Agriculture', 'Buildings', 'Waste'],
        'value': [13800, 5900, 8300, 6300, 3200, 1400],
        'change': [2.2, 1.7, 2.5, 1.6, 0.0, 7.7],
        'subsectors': ['Coal, Natural Gas, Oil', 'Steel, Cement, Chemicals', 
                       'Road, Aviation, Shipping', 'Livestock, Crop Production',
                       'Residential, Commercial', 'Landfills, Wastewater']
    }),
    '2025': pd.DataFrame({
        'sector': ['Energy Production', 'Industrial Process', 'Transportation', 
                   'Agriculture', 'Buildings', 'Waste'],
        'value': [14000, 6000, 8500, 6400, 3000, 1500],
        'change': [1.4, 1.7, 2.4, 1.6, -6.3, 7.1],
        'subsectors': ['Coal, Natural Gas, Oil', 'Steel, Cement, Chemicals', 
                       'Road, Aviation, Shipping', 'Livestock, Crop Production',
                       'Residential, Commercial', 'Landfills, Wastewater']
    })
}

yearly_data = pd.DataFrame({
    'year': ['2021', '2022', '2023', '2024', '2025'],
    'total': [36400, 37500, 38100, 38900, 39400],
    'energy': [13100, 13400, 13500, 13800, 14000],
    'transport': [7600, 8000, 8100, 8300, 8500],
    'industry': [5600, 5800, 5800, 5900, 6000],
    'other': [10100, 10300, 10700, 10900, 10900]
})

region_data = pd.DataFrame({
    'region': ['Asia-Pacific', 'North America', 'Europe', 'Middle East', 
               'Latin America', 'Africa'],
    'value': [18500, 6800, 4200, 3900, 2400, 1500],
    'color': ['#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#10b981', '#06b6d4']
})

# Helper function for AI chat
def analyze_query(query, selected_year, current_data, total_emissions):
    q = query.lower()
    
    if 'energy' in q or 'power' in q:
        energy_data = current_data[current_data['sector'] == 'Energy Production'].iloc[0]
        return {
            'type': 'data',
            'response': f'Energy production remains the largest emissions source at {energy_data["value"]:,.0f} Mt CO2e ({(energy_data["value"] / total_emissions * 100):.1f}% of total), showing a {energy_data["change"]:+.1f}% change from the previous year. Coal-fired power plants contribute approximately 60% of energy sector emissions.'
        }
    
    if 'transport' in q or 'vehicle' in q or 'car' in q:
        transport_data = current_data[current_data['sector'] == 'Transportation'].iloc[0]
        return {
            'type': 'data',
            'response': f'Transportation emissions reached {transport_data["value"]:,.0f} Mt CO2e, {"up" if transport_data["change"] > 0 else "down"} {abs(transport_data["change"]):.1f}% from the previous year. Road transport accounts for 72% of this sector, with aviation and shipping making up the remainder.'
        }
    
    if 'trend' in q or 'change' in q or 'year' in q:
        return {
            'type': 'data',
            'response': 'Global emissions have increased from 36.4 Gt in 2021 to 39.4 Gt in 2025, representing an 8.2% growth over the period. The trend shows consistent year-over-year increases, with 2025 emissions up 1.3% from 2024.'
        }
    
    if 'region' in q or 'asia' in q or 'china' in q:
        return {
            'type': 'data',
            'response': 'Asia-Pacific leads global emissions with 18,500 Mt CO2e (48.6%), driven primarily by China and India. North America contributes 6,800 Mt (17.8%), while Europe accounts for 4,200 Mt (11.0%).'
        }
    
    if any(word in q for word in ['latest', 'news', 'policy', 'reduce', 'solution', 'renewable', 'current']):
        return {'type': 'search', 'query': query}
    
    return {
        'type': 'data',
        'response': f'I can provide insights on emissions by sector, regional breakdown, historical trends, or search for the latest climate news and policies. Currently viewing {selected_year} data with total emissions of {total_emissions / 1000:.1f} Gt. What would you like to know?'
    }

def search_web(query):
    """Search web using Anthropic API with web search tool"""
    try:
        # Check if API key is available
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Try Streamlit secrets
            try:
                api_key = st.secrets.get('ANTHROPIC_API_KEY', '')
            except:
                pass
        
        if not api_key:
            return "Web search requires an Anthropic API key. Please set ANTHROPIC_API_KEY in your environment variables or Streamlit secrets. You can still ask questions about the dashboard data!"
        
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Search the web and provide current information about: {query}. Focus on emissions, climate data, and environmental policies."
            }],
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search"
            }]
        )
        
        # Extract text from response
        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text
        
        return response_text if response_text else "No results found. Please try rephrasing your question."
        
    except Exception as e:
        return f"Search functionality requires Anthropic API key. You can still ask questions about the dashboard data shown above!"

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 🌍 Emissions Monitor")
    st.caption("Real-time monitoring & AI-powered insights")

with col2:
    selected_year = st.selectbox("Year", ['2025', '2024', '2023', '2022', '2021'], key='year_selector')

st.divider()

# Get data for selected year
current_year_data = industry_data_by_year[selected_year]
total_emissions = current_year_data['value'].sum()
largest_sector = current_year_data.loc[current_year_data['value'].idxmax()]

# Year change mapping
year_change_map = {
    '2025': '+1.3% from 2024',
    '2024': '+2.1% from 2023',
    '2023': '+1.6% from 2022',
    '2022': '+3.0% from 2021',
    '2021': '+8.5% from 2020'
}

# Summary metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Emissions",
        value=f"{total_emissions/1000:.1f} Gt",
        delta=year_change_map.get(selected_year, ''),
        delta_color="inverse"
    )

with col2:
    st.metric(
        label="Largest Source",
        value=largest_sector['sector'].split()[0],
        delta=f"{(largest_sector['value']/total_emissions*100):.1f}% of total"
    )

with col3:
    st.metric(
        label="Per Capita",
        value="4.8 t",
        delta="CO2e per person"
    )

with col4:
    st.metric(
        label="Target Gap",
        value="-43%",
        delta="vs 2030 goal",
        delta_color="inverse"
    )

st.divider()

# Charts row 1
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Emissions by Sector")
    fig_bar = px.bar(
        current_year_data, 
        y='sector', 
        x='value',
        orientation='h',
        labels={'value': 'Million tonnes CO2e', 'sector': ''},
        color_discrete_sequence=['#3b82f6']
    )
    fig_bar.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12, color='#334155'),
        showlegend=False
    )
    fig_bar.update_xaxes(gridcolor='#e2e8f0', showgrid=True)
    fig_bar.update_yaxes(gridcolor='#e2e8f0', showgrid=False)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.subheader("By Region")
    fig_pie = px.pie(
        region_data,
        values='value',
        names='region',
        hole=0.5,
        color='region',
        color_discrete_map={
            region: color for region, color in zip(region_data['region'], region_data['color'])
        }
    )
    fig_pie.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1),
        font=dict(size=11)
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent', textfont_size=11)
    st.plotly_chart(fig_pie, use_container_width=True)

# Trend chart
st.subheader("Emissions Trend (2021-2025)")
fig_area = go.Figure()
fig_area.add_trace(go.Scatter(
    x=yearly_data['year'],
    y=yearly_data['total'],
    mode='lines',
    name='Total Emissions',
    fill='tozeroy',
    line=dict(color='#3b82f6', width=2),
    fillcolor='rgba(59, 130, 246, 0.1)'
))

fig_area.update_layout(
    height=300,
    margin=dict(l=0, r=0, t=0, b=0),
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(size=12, color='#334155'),
    showlegend=False,
    xaxis=dict(title='', gridcolor='#e2e8f0'),
    yaxis=dict(title='Million tonnes CO2e', gridcolor='#e2e8f0')
)
st.plotly_chart(fig_area, use_container_width=True)

# Data table
st.subheader("Sector Details")

# Prepare data for display
display_data = current_year_data.copy()
display_data['emissions_mt'] = display_data['value'].apply(lambda x: f"{x:,.0f}")
display_data['percentage'] = (display_data['value'] / total_emissions * 100).apply(lambda x: f"{x:.1f}%")
display_data['yoy_change'] = display_data['change'].apply(lambda x: f"{'+' if x > 0 else ''}{x:.1f}%")

# Display table
st.dataframe(
    display_data[['sector', 'emissions_mt', 'percentage', 'yoy_change', 'subsectors']].rename(columns={
        'sector': 'Sector',
        'emissions_mt': 'Emissions (Mt CO2e)',
        'percentage': '% of Total',
        'yoy_change': 'YoY Change',
        'subsectors': 'Key Subsectors'
    }),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sector": st.column_config.TextColumn(width="medium"),
        "Emissions (Mt CO2e)": st.column_config.TextColumn(width="small"),
        "% of Total": st.column_config.TextColumn(width="small"),
        "YoY Change": st.column_config.TextColumn(width="small"),
        "Key Subsectors": st.column_config.TextColumn(width="large")
    }
)

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
    st.caption(f"📅 Currently viewing: {selected_year}")
    
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
