"""
llm_config.py
=============
Centralizes "which LLM does every agent use". Change providers in ONE
place (your .env file) instead of hunting through every agent definition.

Why this matters for a workshop: half the room might have a Gemini key,
the other half a Groq key, and someone's region might block one of them.
This file means nobody has to touch crew or graph code to switch --
they just change LLM_PROVIDER in .env.
"""

import os
from crewai import LLM


def get_llm() -> LLM:
    """Builds the LLM object every agent in the crew will share."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "groq":
        return LLM(
            model=os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.4,
        )

    if provider == "openrouter":
        # LiteLLM (which CrewAI uses under the hood) routes any model id in
        # the form "openrouter/<org>/<model>" straight to OpenRouter.
        # Pick any id ending in ":free" from https://openrouter.ai/models
        return LLM(
            model=os.getenv(
                "OPENROUTER_MODEL", "openrouter/meta-llama/llama-3.3-70b-instruct:free"
            ),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            temperature=0.4,
        )

    # Default: Google AI Studio / Gemini
    return LLM(
        model=os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash"),
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.4,
    )
