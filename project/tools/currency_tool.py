"""
currency_tool.py
================
Converts money between currencies, with INR as the "home" currency of our
traveler. Same resilience pattern as search_tool.py:

  1. Tries a LIVE, keyless exchange-rate API first (open.er-api.com --
     free, no signup, 160+ currencies, refreshed daily).
  2. If the network call fails for ANY reason (no wifi, rate limit,
     API down), it silently falls back to a built-in table of
     APPROXIMATE rates so the workshop never grinds to a halt.

Why the agent needs this: hotel prices in Bangkok are quoted in THB,
flights to Paris in EUR, but our traveler's budget is in INR. An LLM
guessing exchange rates in its head is as unreliable as it doing
arithmetic in its head -- so we make it a deterministic tool.
"""

import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Offline fallback: APPROXIMATE rates, expressed as "1 unit of X = ? INR".
# These will drift out of date -- that's fine, they're a safety net, and the
# tool clearly labels its output as approximate when it uses them.
# ---------------------------------------------------------------------------
STATIC_RATES_TO_INR = {
    "INR": 1.0,
    "USD": 88.0,
    "EUR": 96.0,
    "GBP": 112.0,
    "JPY": 0.58,
    "CNY": 12.2,
    "AUD": 57.0,
    "CAD": 63.0,
    "SGD": 65.0,
    "AED": 24.0,
    "CHF": 98.0,
    "THB": 2.6,
    "MYR": 20.0,
    "IDR": 0.0054,
    "VND": 0.0034,
    "LKR": 0.29,
    "NPR": 0.55,
    "KRW": 0.061,
    "TRY": 2.1,
    "EGP": 1.8,
    "ZAR": 4.8,
}


class CurrencyInput(BaseModel):
    amount: float = Field(..., description="The amount of money to convert, e.g. 120.0")
    from_currency: str = Field(
        ..., description="3-letter ISO code of the currency you HAVE, e.g. 'USD', 'THB', 'EUR'"
    )
    to_currency: str = Field(
        "INR", description="3-letter ISO code to convert INTO (default 'INR')"
    )


class CurrencyConverterTool(BaseTool):
    name: str = "Currency Converter"
    description: str = (
        "Converts an amount of money from one currency to another using a "
        "real exchange rate. Use this whenever you find a price quoted in a "
        "foreign currency (USD, EUR, THB, ...) and need it in INR -- never "
        "guess exchange rates in your head. Example input: amount=120, "
        "from_currency='USD', to_currency='INR'."
    )
    args_schema: Type[BaseModel] = CurrencyInput

    def _run(self, amount: float, from_currency: str, to_currency: str = "INR") -> str:
        from_cur = from_currency.strip().upper()
        to_cur = to_currency.strip().upper()

        if from_cur == to_cur:
            return f"{amount:,.2f} {from_cur} is already in {to_cur} -- no conversion needed."

        # Allow tests / offline classrooms to skip the network entirely.
        if os.getenv("CURRENCY_TOOL_OFFLINE", "").strip() != "1":
            try:
                return self._convert_live(amount, from_cur, to_cur)
            except Exception as exc:  # noqa: BLE001 - ANY failure falls back
                print(f"[CurrencyConverterTool] Live rate lookup failed ({exc}); "
                      "using approximate offline rates.")

        return self._convert_static(amount, from_cur, to_cur)

    # -- Option A: live rates, keyless & free ---------------------------------
    def _convert_live(self, amount: float, from_cur: str, to_cur: str) -> str:
        response = requests.get(
            f"https://open.er-api.com/v6/latest/{from_cur}", timeout=10
        ).json()

        if response.get("result") != "success":
            raise ValueError(f"API returned: {response.get('error-type', 'unknown error')}")

        rates = response.get("rates", {})
        if to_cur not in rates:
            raise ValueError(f"No live rate for {to_cur}")

        rate = float(rates[to_cur])
        converted = amount * rate
        return (
            f"{amount:,.2f} {from_cur} = {converted:,.2f} {to_cur} "
            f"(live rate: 1 {from_cur} = {rate:,.4f} {to_cur}, source: open.er-api.com)"
        )

    # -- Option B: offline approximate rates ----------------------------------
    def _convert_static(self, amount: float, from_cur: str, to_cur: str) -> str:
        if from_cur not in STATIC_RATES_TO_INR or to_cur not in STATIC_RATES_TO_INR:
            known = ", ".join(sorted(STATIC_RATES_TO_INR))
            return (
                f"Cannot convert {from_cur} -> {to_cur} offline. "
                f"Offline table only knows: {known}. "
                "Try again with one of those, or quote the price in USD first."
            )

        # Cross-rate via INR: X -> INR -> Y
        rate = STATIC_RATES_TO_INR[from_cur] / STATIC_RATES_TO_INR[to_cur]
        converted = amount * rate
        return (
            f"{amount:,.2f} {from_cur} = {converted:,.2f} {to_cur} "
            f"(APPROXIMATE offline rate: 1 {from_cur} = {rate:,.4f} {to_cur} -- "
            "live lookup was unavailable)"
        )
