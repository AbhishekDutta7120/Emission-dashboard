import os
import streamlit as st
import anthropic
import json
from typing import Dict, Any, List

def analyze_query_fallback(query: str, selected_year: str, current_data: Any, total_emissions: float) -> str:
    """Fallback rule-based system when API key is missing."""
    q = query.lower()
    if 'energy' in q or 'power' in q:
        energy_data = current_data[current_data['sector'] == 'Energy Production'].iloc[0]
        return f'[Fallback Mode] Energy production remains the largest emissions source at {energy_data["value"]:,.0f} Mt CO2e ({(energy_data["value"] / total_emissions * 100):.1f}% of total), showing a {energy_data["change"]:+.1f}% change from the previous year.'
    if 'transport' in q:
        transport_data = current_data[current_data['sector'] == 'Transportation'].iloc[0]
        return f'[Fallback Mode] Transportation emissions reached {transport_data["value"]:,.0f} Mt CO2e, {"up" if transport_data["change"] > 0 else "down"} {abs(transport_data["change"]):.1f}% from the previous year.'
    if 'trend' in q:
        return '[Fallback Mode] Global emissions increased from 36.4 Gt in 2021 to 39.4 Gt in 2025, an 8.2% growth.'
    if 'region' in q:
        return '[Fallback Mode] Asia-Pacific leads with 18,500 Mt CO2e (48.6%), driven by China and India.'
    return f'[Fallback Mode] Viewing {selected_year} data with {total_emissions / 1000:.1f} Gt total. Please add an Anthropic API Key to enable the advanced AI Agent.'

def process_chat_query(messages: List[Dict[str, str]], current_year: str, current_data: Any, total_emissions: float) -> str:
    """Uses Claude API for intelligent conversation with context of the dashboard data."""
    api_key = os.getenv('ANTHROPIC_API_KEY') or (st.secrets.get('ANTHROPIC_API_KEY', '') if hasattr(st, "secrets") else "")

    # If no API key, fall back to simple rule-based approach using the latest user prompt
    if not api_key:
        latest_query = messages[-1]["content"] if messages else ""
        return analyze_query_fallback(latest_query, current_year, current_data, total_emissions)

    # Prepare data context for the AI
    data_summary = current_data.to_dict('records')
    system_prompt = f"""You are an expert climate data analyst and AI assistant for an Emissions Monitor Dashboard.

Current Dashboard Context:
- Selected Year: {current_year}
- Total Global Emissions for year: {total_emissions:,.0f} Mt CO2e
- Sector Data: {json.dumps(data_summary)}

Your task is to answer user questions about this data, analyze trends, and provide insights.
If the user asks about recent climate news or policies that are not in the data context, you should use the web_search tool.
Always be professional, objective, and reference the specific numbers when discussing sectors."""

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Anthropic API expects messages in specific format
        # We only pass the last few messages to avoid context limit issues and focus on current intent
        api_messages = [{"role": m["role"], "content": m["content"]} for m in messages[-5:]]

        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            system=system_prompt,
            messages=api_messages,
            tools=[{"type": "web_search_20250305", "name": "web_search"}]
        )

        # Handle tool use or text response
        final_text = ""
        for block in response.content:
            if block.type == "text":
                final_text += block.text
            elif block.type == "tool_use":
                # The LLM decided to use web search. We inform the user.
                # Since we don't have a complex multi-turn tool execution loop setup here,
                # we just inform the user what the LLM searched for.
                # A fully robust agent would execute the search and feed it back, but let's
                # keep it simple and just acknowledge it or show the search query it attempted.
                final_text += f"\n*(I attempted to search the web for: '{block.input.get('query', 'something')}', but my web browsing capabilities are currently limited in this interface.)*"

        return final_text or "I'm sorry, I couldn't generate a response."

    except anthropic.APIError as e:
        return f"Anthropic API Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
