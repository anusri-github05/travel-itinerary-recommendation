# 🧭 Multi-Agent Trip Planner

A capstone project combining **CrewAI** (autonomous role-playing agents) and
**LangGraph** (explicit state-machine orchestration), built for a 2-day AI
agents workshop. Runs entirely on free-tier LLMs and free, keyless APIs.

## What it does

You give it four things:

1. **Destination** — a city, a state, or a whole country ("Manali",
   "Himachal Pradesh", "Japan")
2. **Expectations** — mountains, beaches, cafes, street food, trekking,
   nightlife... anything
3. **Days** — trip length
4. **Budget** — TOTAL trip budget, in INR

Four agents then collaborate:

1. **Budget Advisor** — reality-checks the budget FIRST, using a real
   currency-conversion tool. If ₹5,000 for the Swiss Alps is absurd, it
   says so and shows the *logical* budget for those expectations —
   no planning agents run at all.
2. **Destination & Route Expert** — resolves "Himachal Pradesh" or "Japan"
   into a realistic ROUTE: one base for a short trip, 2–3 bases with
   nights-per-base and approximate travel times for a longer one.
3. **Local Guide** — writes a day-by-day itinerary that follows the route,
   with several specific spots per day and an approximate travel time for
   every move (between cities AND between spots).
4. **Travel Concierge** — prices the trip in INR (Currency Converter for
   foreign prices + a deterministic Expense Calculator for the total,
   including intercity hops), and if it's over budget, loops back to
   revise the plan (up to 2 times).

## Project structure

```
project/
├── .env.example          # Copy to .env and fill in your free API key(s)
├── .gitignore             # Keeps .env and caches out of git
├── requirements.txt        # All dependencies (see setup guide for install steps)
├── llm_config.py           # ONE place to switch between Gemini / Groq / OpenRouter
├── graph_workflow.py        # The LangGraph state machine + the CrewAI agents/tasks it runs
├── main.py                 # Command-line entry point (no browser needed)
├── app.py                  # Streamlit UI — the same graph, with a form and results page
├── config/
│   ├── agents.yaml          # Agent role / goal / backstory (edit personalities here)
│   └── tasks.yaml           # Task descriptions + expected output formats
└── tools/
    ├── __init__.py
    ├── search_tool.py        # WebSearchTool: Tavily -> DuckDuckGo fallback, always free
    ├── currency_tool.py       # CurrencyConverterTool: live keyless rates -> offline fallback
    ├── expense_tool.py        # ExpenseCalculatorTool: pure Python INR math, no LLM involved
    └── weather_tool.py         # WeatherLookupTool (bonus/optional): free, keyless Open-Meteo
```

## The graph

```
START ──> reality_check ──(unrealistic)──> budget_advice ──> END
               │                             (no LLM! plain Python node)
             (ok)
               v
      resolve_destination ──> local_guide ──> concierge ──(within budget)──> END
                                                 │  ^
                                    (over budget)│  │(re-check)
                                                 v  │
                                               revise
```

## Why the code is organized this way

- **`config/*.yaml` vs `graph_workflow.py`** — an agent's *personality*
  (role/goal/backstory) and a task's *instructions* are data, not code. Keeping
  them in YAML means you can rewrite an agent's whole personality without
  touching a single line of Python, and it mirrors how CrewAI's own official
  project generator (`crewai create crew`) structures real projects.
- **`tools/` as its own package** — every tool is a small, independently
  testable class. `ExpenseCalculatorTool` never calls an LLM (arithmetic
  should always be exact); `CurrencyConverterTool` never lets the LLM guess
  an exchange rate; `WebSearchTool` isolates the messy "which search
  provider is up right now" logic in one place.
- **`llm_config.py` as a single seam** — every agent asks this one function
  for an LLM. Change `.env`, not code, to switch every agent from Gemini to
  Groq at once.
- **`graph_workflow.py` as the orchestration layer** — this is the only file
  that knows about *both* CrewAI and LangGraph. Each LangGraph node builds a
  tiny one-agent CrewAI crew, runs it, and writes the result into a shared
  `TripState` dictionary (a `TypedDict`) that flows through the graph. Note
  that `budget_advice_node` calls no LLM at all — a node is just a function.
- **Two routers, one worked example** — `route_after_reality_check` is
  written for you (study it); `route_after_budget_check` is yours to write.
- **`app.py` vs `main.py`** — two different front doors into the exact same
  `graph_workflow.py`. This separation is what lets you swap the UI later
  (a Slack bot, a FastAPI endpoint) without touching any agent logic.

## Setup (see the full Setup Guide for details)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then edit .env with your free API key
```

## Run it

```bash
# Command line:
python main.py

# Or the Streamlit app:
streamlit run app.py
```

## Your TODOs (see inline comments for hints)

| File | What to fill in |
|---|---|
| `config/agents.yaml` | `goal` + `backstory` for `local_guide` and `concierge` |
| `config/tasks.yaml` | `description` + `expected_output` for `itinerary_task` and `budget_task` |
| `graph_workflow.py` | The condition inside `route_after_budget_check()` |

Check your progress at any time (offline, costs nothing):

```bash
# from the repo root:
python check.py capstone
```

It verifies your YAML is complete (with the required `{placeholders}`),
feeds your router fake states to prove the loop logic, checks the tools'
math, and confirms the graph compiles.

## Pushing this to GitHub

```bash
git init
git add .
git commit -m "Multi-agent trip planner: CrewAI + LangGraph"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.env` is already excluded by `.gitignore` — double check it never shows up
in `git status` before your first commit.
