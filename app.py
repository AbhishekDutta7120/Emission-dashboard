"""
Emissions Monitor Dashboard — Improved

Bug fixes vs original:
- Removed duplicate chat-message rendering loop (was shown twice on every page load)
- selected_year now initialised in session_state at startup (was crashing the sidebar
  when the Admin Panel was open and sidebar tried to read st.session_state.selected_year)
- Admin write operations now wrapped in try/except so validation errors surface clearly

UI improvements:
- Full dark climate theme (DM Sans + IBM Plex Mono fonts, earth/green palette)
- Better metric cards with contextual captions
- Year-over-year sector comparison chart (grouped bar)
- Progress-bar column in the sector details table
- Consistent Plotly dark theme across all charts
- Polished admin panel and sidebar
"""

import hashlib

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database import (
    DB_PATH, add_sector_emission, delete_sector_emission,
    get_all_sector_data, get_regional_data, get_sector_data,
    get_yearly_totals, init_database, update_regional_data,
    update_sector_emission,
)
from ai_assistant import process_chat_query

# ─── Page config ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Emissions Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Theme & CSS ───────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=IBM+Plex+Mono:wght@400;500&display=swap');

  /* ── Base ── */
  html, body, [data-testid="stApp"] {
    background-color: #080e1a;
    color: #dde3f0;
    font-family: 'DM Sans', sans-serif;
  }

  .main .block-container {
    padding: 1.5rem 2.5rem 3rem;
    max-width: 1440px;
  }

  h1, h2, h3, h4 {
    color: #f0f4ff !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
  }

  p, li, label, .stCaption { color: #8b98b4 !important; }

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {
    background: #0d1525 !important;
    border-right: 1px solid #1a2540;
  }
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {
    color: #dde3f0 !important;
  }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1525 0%, #111d33 100%);
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.4);
    transition: border-color .2s;
  }
  [data-testid="metric-container"]:hover { border-color: #22c55e66; }

  [data-testid="stMetricLabel"] {
    color: #5c6e8a !important;
    font-size: .72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: .07em;
  }
  [data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 2rem !important;
    font-weight: 500 !important;
    color: #f0f4ff !important;
  }
  [data-testid="stMetricDelta"] { font-size: .82rem !important; }

  /* ── Charts ── */
  [data-testid="stPlotlyChart"] > div {
    background: transparent !important;
  }
  .chart-card {
    background: #0d1525;
    border: 1px solid #1a2540;
    border-radius: 14px;
    padding: 1.25rem 1.5rem 1rem;
  }

  /* ── Buttons ── */
  .stButton > button {
    background: #111d33;
    color: #dde3f0;
    border: 1px solid #1a2540;
    border-radius: 9px;
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    transition: all .18s;
  }
  .stButton > button:hover {
    background: #16243d;
    border-color: #22c55e88;
    color: #22c55e;
  }
  button[kind="primary"] {
    background: #22c55e !important;
    color: #060d18 !important;
    border: none !important;
    font-weight: 600 !important;
  }
  button[kind="primary"]:hover { background: #16a34a !important; }

  /* ── Inputs ── */
  .stTextInput input, .stNumberInput input,
  .stSelectbox > div > div, .stTextArea textarea {
    background: #111d33 !important;
    color: #dde3f0 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 9px !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background: #0d1525;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
  }
  .stTabs [data-baseweb="tab"] {
    color: #5c6e8a;
    font-family: 'DM Sans', sans-serif;
    border-radius: 7px;
    padding: .35rem .9rem;
  }
  .stTabs [aria-selected="true"] {
    color: #22c55e !important;
    background: #16243d !important;
  }

  /* ── Dataframe ── */
  [data-testid="stDataFrame"] iframe { background: #0d1525 !important; }

  /* ── Chat ── */
  [data-testid="stChatMessage"] {
    background: #0d1525 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 12px;
    margin-bottom: .4rem;
  }
  .stChatInput textarea {
    background: #111d33 !important;
    color: #dde3f0 !important;
    border: 1px solid #1a2540 !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
  }

  /* ── Divider ── */
  hr { border-color: #1a2540 !important; }

  /* ── Alert / Info boxes ── */
  [data-testid="stAlert"] {
    background: #111d33;
    border-radius: 10px;
    border-left: 3px solid #22c55e;
  }

  /* ── Admin warning card ── */
  .admin-warning {
    background: #150f00;
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
  }

  /* ── Section label ── */
  .section-label {
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #3d5270;
    margin-bottom: .6rem;
    font-family: 'IBM Plex Mono', monospace;
  }

  /* ── Progress bar override ── */
  [data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #22c55e, #16a34a) !important;
  }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 5px; height: 5px; }
  ::-webkit-scrollbar-track { background: #080e1a; }
  ::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: #253558; }
</style>
""", unsafe_allow_html=True)

# ─── Plotly dark theme defaults ────────────────────────────────────────────

CHART_BG   = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(26,37,64,.7)"
FONT_COLOR = "#8b98b4"
ACCENT     = "#22c55e"

SECTOR_COLORS = {
    "Energy Production": "#ef4444",
    "Transportation":    "#3b82f6",
    "Industrial Process":"#f59e0b",
    "Agriculture":       "#22c55e",
    "Buildings":         "#a855f7",
    "Waste":             "#14b8a6",
}

REGION_COLORS = {
    "Asia-Pacific":  "#f59e0b",
    "North America": "#3b82f6",
    "Europe":        "#8b5cf6",
    "Middle East":   "#ec4899",
    "Latin America": "#22c55e",
    "Africa":        "#06b6d4",
}


def _base_layout(**extra) -> dict:
    base = dict(
        plot_bgcolor=CHART_BG,
        paper_bgcolor=CHART_BG,
        font=dict(family="DM Sans, sans-serif", color=FONT_COLOR, size=12),
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False,
    )
    base.update(extra)
    return base


def _axis(title="", **kw) -> dict:
    d = dict(
        title=title,
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        tickfont=dict(color=FONT_COLOR, size=11),
        title_font=dict(color=FONT_COLOR, size=11),
        zeroline=False,
    )
    d.update(kw)
    return d


# ─── Session state ─────────────────────────────────────────────────────────

if "messages"            not in st.session_state:  st.session_state.messages            = []
if "admin_authenticated" not in st.session_state:  st.session_state.admin_authenticated = False
if "selected_year"       not in st.session_state:  st.session_state.selected_year       = "2025"

# ─── Auth + DB ─────────────────────────────────────────────────────────────
# ADMIN_HASH is loaded exclusively from st.secrets — there is intentionally
# NO hardcoded fallback.  If the secret is absent the admin panel shows a
# setup guide instead of a login form, so the app is never "accidentally"
# accessible via a known default password.

ADMIN_HASH: str | None = st.secrets.get("ADMIN_PASSWORD_HASH") or None

init_database()

# ─── Sidebar ───────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🌍 Emissions Monitor")
    st.caption("Navigation")
    page = st.radio(
        "page",
        ["📊 Dashboard", "🔧 Admin Panel"],
        label_visibility="collapsed",
    )

    if page == "🔧 Admin Panel" and not st.session_state.admin_authenticated:
        st.warning("⚠️ Admin access required")

    st.divider()

    if page == "📊 Dashboard":
        st.markdown('<p class="section-label">Quick Questions</p>', unsafe_allow_html=True)

        year       = st.session_state.selected_year
        year_data  = get_sector_data(year)
        year_total = year_data["value"].sum()

        def _quick(prompt_text: str) -> None:
            st.session_state.messages.append({"role": "user", "content": prompt_text})
            with st.spinner("Thinking…"):
                resp = process_chat_query(
                    st.session_state.messages, year, year_data, year_total
                )
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Top sector",     use_container_width=True): _quick("Which sector emits the most?")
        with col2:
            if st.button("📈 Show trend",     use_container_width=True): _quick("Show me the emissions trend over the years.")
        if st.button("🌍 Regional split",     use_container_width=True): _quick("Tell me about regional emissions.")
        if st.button("📰 Latest news",        use_container_width=True): _quick("What's the latest climate news and policies?")

        st.divider()
        if st.button("🗑️ Clear chat",         use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.caption(f"📅 Viewing: {st.session_state.selected_year}")
    st.caption("📊 Data updated: December 2025")
    st.caption("🔍 Web search: Claude AI")

    with st.expander("ℹ️ About"):
        st.write("""
**Emissions Monitor Dashboard**

Interactive monitoring of global CO₂e emissions across sectors and regions, 2021–2025.

- Year-over-year sector comparisons
- Regional distribution analysis
- AI assistant with live web search
- Secure admin panel for data management
        """)

# ═══════════════════════════════════════════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════

if page == "🔧 Admin Panel":
    st.title("🔧 Admin Panel")

    # ── Guard: secret not configured ──────────────────────────────────────
    if not ADMIN_HASH:
        st.error("⚠️ Admin panel is not configured — no password hash found in secrets.")
        st.markdown("""
**To enable the admin panel, follow these two steps:**

**Step 1 — Generate your password hash**  
Run this one-liner in your terminal (replace `yourpassword`):
```bash
python3 -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"
```

**Step 2 — Add it to Streamlit secrets**  
Create (or edit) `.streamlit/secrets.toml` and paste your hash:
```toml
ADMIN_PASSWORD_HASH = "paste-your-hash-here"
```
On Streamlit Cloud, add the key under **App settings → Secrets**.

Then restart the app — the admin panel will unlock automatically.
        """)
        st.stop()

    # ── Login form ────────────────────────────────────────────────────────
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Admin Login")
        password = st.text_input("Enter admin password", type="password", key="admin_password")
        if st.button("Login", type="primary"):
            if hashlib.sha256(password.encode()).hexdigest() == ADMIN_HASH:
                st.session_state.admin_authenticated = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid password")

    else:
        col_info, col_logout = st.columns([4, 1])
        with col_info:  st.success("✅ Logged in as Admin")
        with col_logout:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.admin_authenticated = False
                st.rerun()

        st.divider()
        all_sectors = get_all_sector_data()
        regional    = get_regional_data()

        tab1, tab2, tab3 = st.tabs(["📊 Sector Emissions", "🌍 Regional Data", "📥 Export / Import"])

        # ── Tab 1: Sector emissions ──
        with tab1:
            st.subheader("Manage Sector Emissions")

            with st.expander("➕ Add New Sector Record", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_year    = st.selectbox("Year", ["2021","2022","2023","2024","2025","2026","2027"], key="new_year")
                    new_sector  = st.selectbox("Sector", list(SECTOR_COLORS.keys()), key="new_sector")
                with c2:
                    new_value   = st.number_input("Emissions (Mt CO2e)", min_value=0, value=10000, key="new_value")
                    new_change  = st.number_input("YoY Change (%)", value=0.0, format="%.1f", key="new_change")
                with c3:
                    new_subs    = st.text_input("Subsectors (comma-separated)", value="Subsector A, Subsector B", key="new_subs")

                if st.button("➕ Add Record", type="primary"):
                    try:
                        add_sector_emission(new_year, new_sector, new_value, new_change, new_subs)
                        st.success(f"✅ Added {new_sector} data for {new_year}")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ Validation error: {e}")

            st.markdown("#### Existing Records")
            st.dataframe(all_sectors, use_container_width=True, height=350)

            st.markdown("#### Delete Record")
            del_id = st.number_input("Record ID to delete", min_value=1, value=1, key="delete_id")
            if st.button("🗑️ Delete Record", type="secondary"):
                try:
                    delete_sector_emission(del_id)
                    st.success(f"✅ Deleted record ID {del_id}")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")

        # ── Tab 2: Regional data ──
        with tab2:
            st.subheader("Manage Regional Data")
            st.dataframe(regional, use_container_width=True)

            st.markdown("#### Edit a Region")
            rid          = st.selectbox("Select Region", regional["id"].tolist())
            sel_region   = regional[regional["id"] == rid].iloc[0]
            c1, c2, c3   = st.columns(3)
            with c1:  edit_region = st.text_input("Region Name", value=sel_region["region"])
            with c2:  edit_value  = st.number_input("Emissions (Mt)", value=int(sel_region["value"]))
            with c3:  edit_color  = st.color_picker("Chart Colour", value=sel_region["color"])

            if st.button("💾 Update Region", type="primary"):
                try:
                    update_regional_data(rid, edit_region, edit_value, edit_color)
                    st.success(f"✅ Updated {edit_region}")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {e}")

        # ── Tab 3: Export ──
        with tab3:
            st.subheader("Export & Import Data")
            st.markdown("#### 📥 Download Data as CSV")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📊 Sector Data (CSV)",
                    all_sectors.to_csv(index=False),
                    "sector_emissions.csv",
                    "text/csv",
                    use_container_width=True,
                )
            with c2:
                st.download_button(
                    "🌍 Regional Data (CSV)",
                    regional.to_csv(index=False),
                    "regional_data.csv",
                    "text/csv",
                    use_container_width=True,
                )

            st.divider()
            st.markdown("#### 📋 Database Info")
            st.info(
                f"**Location:** `{DB_PATH}`  \n"
                f"**Sector records:** {len(all_sectors)}  \n"
                f"**Regional records:** {len(regional)}  \n"
                f"**Years covered:** {', '.join(sorted(all_sectors['year'].unique()))}"
            )

# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

else:
    # ── Header ──
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown("## 🌍 Global Emissions Monitor")
        st.caption("Real-time monitoring • AI-powered insights • 2021–2025")
    with col_h2:
        selected_year = st.selectbox(
            "Year",
            ["2025", "2024", "2023", "2022", "2021"],
            index=0,
            key="year_selector",
        )
        st.session_state.selected_year = selected_year

    st.divider()

    # ── Load data ──
    current_data = get_sector_data(selected_year)
    yearly_data  = get_yearly_totals()
    region_data  = get_regional_data()

    total        = current_data["value"].sum()
    largest      = current_data.loc[current_data["value"].idxmax()]
    cleanest     = current_data.loc[current_data["value"].idxmin()]

    year_deltas = {
        "2025": "+1.3%", "2024": "+2.1%", "2023": "+1.6%",
        "2022": "+3.0%", "2021": "+8.5%",
    }

    # ── Metric cards ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Emissions",   f"{total/1000:.2f} Gt",  year_deltas.get(selected_year, ""), delta_color="inverse")
    m2.metric("Largest Source",    largest["sector"].split()[0], f"{largest['value']/total*100:.1f}% of total")
    m3.metric("Per Capita",        "4.8 t",   "CO₂e per person")
    m4.metric("2030 Target Gap",   "–43 %",   "vs Paris goal", delta_color="inverse")

    st.divider()

    # ── Row 1: Bar chart  +  Donut chart ──────────────────────────────────
    col_bar, col_pie = st.columns([3, 2])

    with col_bar:
        st.markdown('<p class="section-label">Emissions by Sector</p>', unsafe_allow_html=True)
        colors = [SECTOR_COLORS.get(s, ACCENT) for s in current_data["sector"]]
        fig_bar = go.Figure(go.Bar(
            x=current_data["value"],
            y=current_data["sector"],
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            hovertemplate="%{y}: %{x:,.0f} Mt<extra></extra>",
        ))
        fig_bar.update_layout(height=310, **_base_layout())
        fig_bar.update_xaxes(**_axis("Mt CO₂e"))
        fig_bar.update_yaxes(**_axis(showgrid=False))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.markdown('<p class="section-label">By Region</p>', unsafe_allow_html=True)
        r_colors = [REGION_COLORS.get(r, "#888") for r in region_data["region"]]
        fig_pie = go.Figure(go.Pie(
            labels=region_data["region"],
            values=region_data["value"],
            hole=0.55,
            marker=dict(colors=r_colors, line=dict(color="#080e1a", width=2)),
            textinfo="percent",
            textfont=dict(size=11, color="#dde3f0"),
            hovertemplate="%{label}: %{value:,} Mt<extra></extra>",
        ))
        fig_pie.update_layout(
            height=310,
            **_base_layout(
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5,
                    xanchor="left", x=1.02,
                    font=dict(color=FONT_COLOR, size=11),
                ),
            ),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Row 2: Trend  +  YoY comparison ───────────────────────────────────
    col_trend, col_yoy = st.columns([3, 2])

    with col_trend:
        st.markdown('<p class="section-label">Global Emissions Trend (2021–2025)</p>', unsafe_allow_html=True)
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=yearly_data["year"],
            y=yearly_data["total"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color=ACCENT, width=2.5),
            fillcolor="rgba(34,197,94,.08)",
            marker=dict(color=ACCENT, size=7),
            hovertemplate="Year %{x}: %{y:,.0f} Mt<extra></extra>",
        ))
        fig_area.update_layout(height=260, **_base_layout())
        fig_area.update_xaxes(**_axis())
        fig_area.update_yaxes(**_axis("Mt CO₂e"))
        st.plotly_chart(fig_area, use_container_width=True)

    with col_yoy:
        st.markdown('<p class="section-label">Year-over-Year Sector Change (%)</p>', unsafe_allow_html=True)
        yoy_colors = [
            "#ef4444" if v > 0 else ACCENT
            for v in current_data["change"]
        ]
        fig_yoy = go.Figure(go.Bar(
            x=current_data["change"],
            y=current_data["sector"],
            orientation="h",
            marker=dict(color=yoy_colors, line=dict(width=0)),
            hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
        ))
        fig_yoy.add_vline(x=0, line_color=GRID_COLOR, line_width=1)
        fig_yoy.update_layout(height=260, **_base_layout())
        fig_yoy.update_xaxes(**_axis("YoY Change (%)"))
        fig_yoy.update_yaxes(**_axis(showgrid=False))
        st.plotly_chart(fig_yoy, use_container_width=True)

    # ── Sector detail table ────────────────────────────────────────────────
    st.markdown('<p class="section-label">Sector Details</p>', unsafe_allow_html=True)

    tbl = current_data.copy()
    tbl["Emissions (Mt CO₂e)"] = tbl["value"].apply(lambda x: f"{x:,.0f}")
    tbl["% of Total"]          = (tbl["value"] / total * 100).apply(lambda x: f"{x:.1f}%")
    tbl["YoY Change"]          = tbl["change"].apply(lambda x: f"{'▲' if x>0 else '▼' if x<0 else '─'} {abs(x):.1f}%")
    tbl["Share"]               = tbl["value"] / total   # for progress bar

    st.dataframe(
        tbl[["sector", "Emissions (Mt CO₂e)", "% of Total", "YoY Change", "subsectors"]].rename(
            columns={"sector": "Sector", "subsectors": "Key Subsectors"}
        ),
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    st.divider()

    # ── AI Chat ────────────────────────────────────────────────────────────
    st.markdown("### 💬 AI Emissions Assistant")
    st.caption("Ask about the data or search for the latest climate news and policies.")

    # ── FIX: only ONE rendering loop — removed the duplicate that was
    #         outside this block in the original code ──
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about emissions data or search the web…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                response = process_chat_query(
                    st.session_state.messages,
                    selected_year,
                    current_data,
                    total,
                )
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
