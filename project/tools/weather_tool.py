"""
weather_tool.py
===============
BONUS TOOL (optional stretch goal -- not required to finish the core
project). This is here to show that adding "more tools" is easy once the
pattern clicks, and to introduce a genuinely free, keyless API.

Uses Open-Meteo (https://open-meteo.com) for geocoding + current weather.
No API key. No signup. No rate-limit surprises during a workshop.

To wire it in: import WeatherLookupTool in graph_workflow.py and add it to
an agent's tools list, e.g. the Local Guide:

    from tools.weather_tool import WeatherLookupTool
    ...
    tools=[search_tool, WeatherLookupTool()]
"""

import requests
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    city: str = Field(..., description="City name, e.g. 'Lisbon' or 'Bangkok'")


class WeatherLookupTool(BaseTool):
    name: str = "Weather Lookup"
    description: str = (
        "Looks up the CURRENT weather for a city. Useful for suggesting what "
        "to pack, or whether to plan indoor vs outdoor activities."
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, city: str) -> str:
        try:
            geo_response = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1},
                timeout=10,
            ).json()

            results = geo_response.get("results")
            if not results:
                return f"Could not find coordinates for '{city}'."

            place = results[0]
            lat, lon = place["latitude"], place["longitude"]

            weather_response = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,precipitation,wind_speed_10m",
                },
                timeout=10,
            ).json()

            current = weather_response.get("current", {})
            return (
                f"Current weather in {place.get('name', city)}, "
                f"{place.get('country', '')}: "
                f"{current.get('temperature_2m')}°C, "
                f"precipitation {current.get('precipitation')} mm, "
                f"wind {current.get('wind_speed_10m')} km/h."
            )
        except Exception as exc:  # noqa: BLE001
            return f"Weather lookup failed: {exc}"
