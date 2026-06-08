"""
AI Assistant for Emissions Monitor Dashboard.

Key fixes vs original:
- Proper multi-turn agentic loop so web search actually works
- Updated model to claude-sonnet-4-6
- Specific error types with helpful messages
- Cleaner system prompt with precise data context
"""

import os
import json
from typing import Any

import streamlit as st
import anthropic


# ─── Helpers ───────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    """Return API key from env or Streamlit secrets, or '' if absent."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key and hasattr(st, "secrets"):
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
    return key.strip()


def _build_system_prompt(current_year: str, current_data: Any, total_emissions: float) -> str:
    sector_rows = current_data.to_dict("records")
    return f"""You are an expert climate data analyst for an Emissions Monitor Dashboard.

=== CURRENT DASHBOARD CONTEXT ===
Year selected : {current_year}
Total emissions: {total_emissions:,.0f} Mt CO2e  ({total_emissions / 1000:.2f} Gt)
Sector breakdown:
{json.dumps(sector_rows, indent=2)}

=== YOUR ROLE ===
1. Answer questions about the data above with precision — always cite specific numbers.
2. Analyse trends, compare sectors, and explain year-over-year changes.
3. Use the web_search tool for current climate news, recent policies, or anything
   that may have changed after your training cut-off.
4. Be professional, objective, and science-based.
5. Keep responses concise (3–5 sentences unless a detailed breakdown is requested).

All values are in Million tonnes CO2e (Mt CO2e).  1 000 Mt = 1 Gt."""


def _content_to_dicts(content_blocks) -> list:
    """Convert SDK content-block objects to plain dicts for re-use in messages."""
    result = []
    for block in content_blocks:
        btype = getattr(block, "type", "")
        if btype == "text":
            result.append({"type": "text", "text": block.text})
        elif btype == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        # ignore other block types (tool_result, etc.)
    return result


# ─── Fallback (no API key) ─────────────────────────────────────────────────

def _fallback(query: str, selected_year: str, current_data: Any, total: float) -> str:
    """Rule-based fallback when no API key is configured."""
    q = query.lower()

    def _row(sector: str):
        return current_data[current_data["sector"] == sector].iloc[0]

    def _direction(change: float) -> str:
        return "down" if change < 0 else "up"

    if "energy" in q or "power" in q or "electricity" in q or "coal" in q:
        row = _row("Energy Production")
        return (
            f"Energy Production is the largest emission source in {selected_year} at "
            f"**{row['value']:,.0f} Mt CO₂e** ({row['value'] / total * 100:.1f}% of total). "
            f"It went {_direction(row['change'])} by {abs(row['change']):.1f}% year-over-year, "
            f"driven by coal, natural gas, and oil consumption."
        )
    if "transport" in q or "vehicle" in q or "road" in q or "aviation" in q or "ship" in q:
        row = _row("Transportation")
        return (
            f"Transportation emitted **{row['value']:,.0f} Mt CO₂e** in {selected_year} "
            f"({row['value'] / total * 100:.1f}% of total), "
            f"{_direction(row['change'])} {abs(row['change']):.1f}% from the prior year. "
            f"Road transport, aviation, and shipping are the main contributors."
        )
    if "build" in q or "residential" in q or "commercial" in q or "house" in q:
        row = _row("Buildings")
        trend = "improved" if row['change'] < 0 else "worsened"
        return (
            f"Buildings emitted **{row['value']:,.0f} Mt CO₂e** in {selected_year} "
            f"({row['value'] / total * 100:.1f}% of total). "
            f"This {trend} by {abs(row['change']):.1f}% vs the previous year, "
            f"covering residential and commercial energy use for heating, cooling, and lighting."
        )
    if "industry" in q or "industrial" in q or "steel" in q or "cement" in q or "manufactur" in q:
        row = _row("Industrial Process")
        return (
            f"Industrial Processes contributed **{row['value']:,.0f} Mt CO₂e** in {selected_year} "
            f"({row['value'] / total * 100:.1f}% of total), "
            f"{_direction(row['change'])} {abs(row['change']):.1f}% year-over-year. "
            f"Steel, cement, and chemical production are the primary sources."
        )
    if "agriculture" in q or "farming" in q or "livestock" in q or "crop" in q or "food" in q:
        row = _row("Agriculture")
        return (
            f"Agriculture emitted **{row['value']:,.0f} Mt CO₂e** in {selected_year} "
            f"({row['value'] / total * 100:.1f}% of total), "
            f"{_direction(row['change'])} {abs(row['change']):.1f}% from last year. "
            f"Livestock (methane) and crop production are the key drivers."
        )
    if "waste" in q or "landfill" in q or "recycl" in q:
        row = _row("Waste")
        return (
            f"Waste management emitted **{row['value']:,.0f} Mt CO₂e** in {selected_year} "
            f"({row['value'] / total * 100:.1f}% of total), "
            f"{_direction(row['change'])} {abs(row['change']):.1f}% year-over-year. "
            f"Landfills and wastewater treatment are the main contributors."
        )
    if "trend" in q or "year" in q or "history" in q or "over time" in q:
        return (
            "Global emissions have risen steadily: **36.4 Gt** (2021) → **37.5 Gt** (2022) → "
            "**38.1 Gt** (2023) → **38.9 Gt** (2024) → **39.4 Gt** (2025). "
            "That's an 8.2% increase over five years, moving further from the Paris Agreement target."
        )
    if "region" in q or "country" in q or "asia" in q or "europe" in q or "america" in q or "africa" in q:
        return (
            "Regional breakdown: **Asia-Pacific** leads at 18,500 Mt (48.6%), "
            "followed by **North America** 6,800 Mt (17.9%), **Europe** 4,200 Mt (11.0%), "
            "**Middle East** 3,900 Mt (10.2%), **Latin America** 2,400 Mt (6.3%), "
            "and **Africa** 1,500 Mt (3.9%)."
        )
    if "total" in q or "overall" in q or "summary" in q or "status" in q or "overview" in q:
        largest = current_data.loc[current_data["value"].idxmax()]
        return (
            f"In {selected_year}, total global emissions reached **{total / 1000:.2f} Gt CO₂e** "
            f"({total:,.0f} Mt). "
            f"The largest source is **{largest['sector']}** at {largest['value']:,.0f} Mt "
            f"({largest['value'] / total * 100:.1f}% of total)."
        )

    # Generic fallback — still pulls live data
    largest = current_data.loc[current_data["value"].idxmax()]
    return (
        f"In {selected_year}, global emissions totalled **{total / 1000:.2f} Gt CO₂e**. "
        f"The biggest contributor is {largest['sector']} at {largest['value']:,.0f} Mt "
        f"({largest['value'] / total * 100:.1f}%). "
        f"Try asking about a specific sector — Energy, Transport, Buildings, Industry, Agriculture, or Waste."
    )


# ─── Main entry point ──────────────────────────────────────────────────────

def process_chat_query(
    messages: list,
    current_year: str,
    current_data: Any,
    total_emissions: float,
) -> str:
    """
    Send the conversation to Claude and return the assistant's reply.

    Implements a proper multi-turn agentic loop so web_search tool calls
    are followed up correctly instead of being silently dropped.
    """
    api_key = _get_api_key()
    if not api_key:
        latest = messages[-1]["content"] if messages else ""
        return _fallback(latest, current_year, current_data, total_emissions)

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = _build_system_prompt(current_year, current_data, total_emissions)

    # Keep the last 6 turns for context (avoid hitting token limits)
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages[-6:]
    ]

    tools = [{"type": "web_search_20250305", "name": "web_search"}]

    try:
        MAX_TURNS = 4  # Guard against infinite loops
        for _turn in range(MAX_TURNS):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=system_prompt,
                messages=api_messages,
                tools=tools,
            )

            text_blocks = [
                b for b in response.content if getattr(b, "type", "") == "text"
            ]
            tool_blocks = [
                b for b in response.content if getattr(b, "type", "") == "tool_use"
            ]

            # ── Done: model finished speaking ──
            if response.stop_reason == "end_turn" or not tool_blocks:
                answer = "\n".join(b.text for b in text_blocks).strip()
                return answer or "I couldn't generate a response — please try rephrasing."

            # ── Tool use: extend the conversation and iterate ──
            if tool_blocks and response.stop_reason == "tool_use":
                # 1. Append the assistant turn (with tool_use blocks)
                api_messages.append({
                    "role": "assistant",
                    "content": _content_to_dicts(response.content),
                })

                # 2. Append a user turn acknowledging each tool_use
                #    For the built-in web_search tool, Anthropic executes the
                #    search server-side; we just need to return a tool_result
                #    so the conversation can continue.
                tool_results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Search results retrieved.",
                    }
                    for block in tool_blocks
                ]
                api_messages.append({"role": "user", "content": tool_results})
                continue  # Let the model process search results and respond

        return (
            "The assistant is taking too long. "
            "Please try a more specific question."
        )

    except anthropic.AuthenticationError:
        return "⚠️ Invalid API key. Check your `ANTHROPIC_API_KEY` in Streamlit secrets."
    except anthropic.RateLimitError:
        return "⚠️ Rate limit reached. Please wait a moment and try again."
    except anthropic.APIConnectionError:
        return "⚠️ Connection error. Check your internet connection and try again."
    except anthropic.APIStatusError as e:
        return f"⚠️ API error {e.status_code}: {e.message}"
    except Exception as e:  # noqa: BLE001
        return f"⚠️ Unexpected error: {e}"
