import os
import streamlit as st
import anthropic
from typing import Dict, Any, Union

def analyze_query(query: str, selected_year: str, current_data: Any, total_emissions: float) -> Dict[str, str]:
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

def search_web(query: str) -> str:
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY') or (st.secrets.get('ANTHROPIC_API_KEY', '') if hasattr(st, "secrets") else "")
        if not api_key:
            return "Web search requires an Anthropic API key. Please check your `.streamlit/secrets.toml` or environment variables!"

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Search: {query}. Focus on emissions and climate."}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}]
        )
        return "".join([block.text for block in message.content if block.type == "text"]) or "No results found."

    except anthropic.APIError as e:
        return f"Anthropic API Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred during the web search: {e}"
