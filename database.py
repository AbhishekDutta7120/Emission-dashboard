import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = Path("emissions_data.db")

@st.cache_resource
def init_database() -> None:
    """Initialize SQLite database with emissions data"""
    with sqlite3.connect(DB_PATH) as conn:
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

@st.cache_data
def get_sector_data(year: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT sector, value, change, subsectors FROM sector_emissions WHERE year = ?"
        df = pd.read_sql_query(query, conn, params=(year,))
    return df

@st.cache_data
def get_all_sector_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM sector_emissions ORDER BY year, sector", conn)
    return df

@st.cache_data
def get_yearly_totals() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM yearly_totals ORDER BY year", conn)
    return df

@st.cache_data
def get_regional_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM regional_data", conn)
    return df

def update_sector_emission(id: int, year: str, sector: str, value: int, change: float, subsectors: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sector_emissions SET year=?, sector=?, value=?, change=?, subsectors=? WHERE id=?",
                       (year, sector, value, change, subsectors, id))
        conn.commit()
    st.cache_data.clear()

def add_sector_emission(year: str, sector: str, value: int, change: float, subsectors: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sector_emissions (year, sector, value, change, subsectors) VALUES (?, ?, ?, ?, ?)",
                       (year, sector, value, change, subsectors))
        conn.commit()
    st.cache_data.clear()

def delete_sector_emission(id: int) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sector_emissions WHERE id=?", (id,))
        conn.commit()
    st.cache_data.clear()

def update_regional_data(id: int, region: str, value: int, color: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE regional_data SET region=?, value=?, color=? WHERE id=?", (region, value, color, id))
        conn.commit()
    st.cache_data.clear()
