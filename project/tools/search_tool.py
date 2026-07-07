"""
search_tool.py
==============
A web search tool with a FREE fallback chain:

  1. Tries Tavily first, IF a TAVILY_API_KEY is set (free tier: 1,000
     searches/month, no credit card).
  2. If no key is set, or the Tavily call fails for any reason (rate
     limit, network blip, expired key), it silently falls back to
     DuckDuckGo search via the `ddgs` package -- which needs NO api key
     at all and never expires.

This "try the nice paid-tier-adjacent option, fall back to the always-free
option" pattern is worth teaching on its own: it's exactly how you'd build
a resilient tool in a real production agent.
"""

import os
from typing import Type, List, Dict

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(
        ...,
        description="A plain-language search query, e.g. 'best time to visit Lisbon in October'",
    )


class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = (
        "Searches the live web for current information -- prices, weather, "
        "events, opening hours, neighborhoods, restaurants, etc. "
        "Input should be a single plain-text search query."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        tavily_key = os.getenv("TAVILY_API_KEY")

        if tavily_key:
            try:
                return self._search_tavily(query, tavily_key)
            except Exception as exc:  # noqa: BLE001 - we want ANY failure to fall back
                print(f"[WebSearchTool] Tavily failed ({exc}); falling back to DuckDuckGo.")

        return self._search_duckduckgo(query)

    # -- Option A: Tavily (free tier, no card, but needs a key) --------------
    def _search_tavily(self, query: str, api_key: str) -> str:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=5)
        results = [
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
        return self._format_results(results, source="Tavily")

    # -- Option B: DuckDuckGo (always free, zero setup) -----------------------
    def _search_duckduckgo(self, query: str) -> str:
        from ddgs import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=5))

        results = [
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw_results
        ]
        return self._format_results(results, source="DuckDuckGo")

    @staticmethod
    def _format_results(results: List[Dict[str, str]], source: str) -> str:
        if not results:
            return f"No {source} results found for that query."

        lines = [f"({source} results)"]
        for i, r in enumerate(results, start=1):
            lines.append(f"{i}. {r['title']}\n   {r['snippet']}\n   Source: {r['url']}")
        return "\n".join(lines)
