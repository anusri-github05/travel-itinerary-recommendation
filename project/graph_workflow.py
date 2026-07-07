"""
graph_workflow.py
==================
THE ORCHESTRATION LAYER of the Multi-Agent Trip Planner.

Mental model:
  - CrewAI answers: "HOW does one stage get done?"
    (which agent, which tools, which instructions)
  - LangGraph answers: "WHAT stage happens next?"
    (the flowchart -- including loops and branches)

Each LangGraph *node* function below builds a tiny, single-purpose CrewAI
crew (one agent + one task), runs it, and writes the result into a shared
`TripState` dictionary that flows through the whole graph. That's the
"CrewAI agents inside a LangGraph state machine" pattern this project
teaches.

The flowchart:

    START
      |
    reality_check          <- is this budget even sane for these expectations?
      |          \
      | (ok)      \ (unrealistic)
      v            v
    resolve_destination   budget_advice  -> END   <- no LLM! plain Python node
      |
    local_guide
      |
    concierge
      |  \
      |   \ (over budget, retries left)
      v    v
     END  revise ---(loops back through the same check)---> END
"""

import os
from typing import TypedDict, List, Dict, Any, Literal

import yaml
from crewai import Agent, Task, Crew, Process
from langgraph.graph import StateGraph, START, END

from llm_config import get_llm
from tools.search_tool import WebSearchTool
from tools.expense_tool import ExpenseCalculatorTool
from tools.currency_tool import CurrencyConverterTool

# ---------------------------------------------------------------------------
# Load agent + task blueprints from YAML (see config/agents.yaml & tasks.yaml)
# Keeping these in YAML (instead of hardcoding strings in Python) means you
# can tune an agent's personality or a task's instructions without touching
# any orchestration code.
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_yaml(filename: str) -> dict:
    path = os.path.join(_BASE_DIR, "config", filename)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


AGENTS_CFG = _load_yaml("agents.yaml")
TASKS_CFG = _load_yaml("tasks.yaml")

# Shared tool instances -- reused across every agent that needs them.
search_tool = WebSearchTool()
expense_tool = ExpenseCalculatorTool()
currency_tool = CurrencyConverterTool()

# Safety valve: the "make it cheaper" loop can retry at most this many times,
# so a stubborn over-budget plan can never spin forever.
MAX_REVISIONS = 2


def _cfg_field(cfg: dict, key: str) -> str:
    """Reads a field out of a loaded YAML block and trims stray whitespace
    (YAML's `>` block-scalar style adds a trailing newline by default)."""
    return str(cfg[key]).strip()


def _inr(amount: float) -> str:
    """Formats a number as an INR amount for console logs."""
    return f"INR {amount:,.0f}"


# ---------------------------------------------------------------------------
# Shared state -- every node reads from this dict and returns UPDATES to it.
# LangGraph merges whatever a node returns back into the overall state, so
# nodes only need to return the keys they actually changed.
# ---------------------------------------------------------------------------
class TripState(TypedDict):
    # ---- inputs supplied by the user (Streamlit form or main.py) ----
    destination: str        # a city, a state, or a country -- e.g. "Himachal Pradesh"
    expectations: str       # "mountains, trekking, cafes, street food, ..."
    trip_length_days: int
    budget_inr: float       # TOTAL trip budget, in Indian Rupees

    # ---- filled in as the graph runs ----
    budget_verdict: str            # REALISTIC / TIGHT / UNREALISTIC
    suggested_budget_inr: float    # what the Budget Advisor says it really takes
    feasibility_report: str
    selected_bases: str            # the route, e.g. "Manali" or "Manali, Kasol"
    route_rationale: str
    itinerary: str
    cost_breakdown: str
    estimated_total_cost_inr: float
    revision_count: int
    final_plan: str
    status_log: List[str]  # human-readable trace of what happened, for the UI


def _extract_labeled_line(text: str, label: str, default: str = "") -> str:
    """Small helper: pulls a value out of a line formatted like 'LABEL: value'.
    This is how we get a clean, structured value (like a city name) out of
    an LLM's free-text response -- by being strict about the output format
    in expected_output, then parsing for it here."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("*#- ")  # tolerate markdown decoration
        if stripped.upper().startswith(label.upper() + ":"):
            return stripped.split(":", 1)[1].strip().strip("*")
    return default


def _extract_number(text: str, label: str, default: float = 0.0) -> float:
    """Pulls 'LABEL: 45000' out of the text and returns it as a float."""
    raw = _extract_labeled_line(text, label, default="")
    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    try:
        return float(cleaned) if cleaned else default
    except ValueError:
        return default


def _extract_total_cost(text: str) -> float:
    total = _extract_number(text, "TOTAL_COST_INR", default=-1.0)
    if total < 0:  # be forgiving if the agent wrote TOTAL_COST instead
        total = _extract_number(text, "TOTAL_COST", default=0.0)
    return total


# ---------------------------------------------------------------------------
# NODE 1 -- Budget Reality Check
# Before planning ANYTHING, an honest advisor checks: can this budget
# actually deliver these expectations? (Rs. 5,000 for the Swiss Alps -> no.)
# ---------------------------------------------------------------------------
def budget_reality_check_node(state: TripState) -> Dict[str, Any]:
    cfg = AGENTS_CFG["budget_advisor"]
    agent = Agent(
        role=_cfg_field(cfg, "role"),
        goal=_cfg_field(cfg, "goal"),
        backstory=_cfg_field(cfg, "backstory"),
        tools=[currency_tool, search_tool],
        llm=get_llm(),
        verbose=True,
    )

    task_cfg = TASKS_CFG["feasibility_task"]
    task = Task(
        description=_cfg_field(task_cfg, "description").format(
            destination=state["destination"],
            expectations=state["expectations"],
            trip_length_days=state["trip_length_days"],
            budget_inr=f"{state['budget_inr']:,.0f}",
        ),
        expected_output=_cfg_field(task_cfg, "expected_output"),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    verdict = _extract_labeled_line(result, "VERDICT", default="REALISTIC").upper()
    # Normalize: the LLM sometimes writes "VERDICT: TIGHT (but doable)" etc.
    for known in ("UNREALISTIC", "REALISTIC", "TIGHT"):
        if known in verdict:
            verdict = known
            break
    else:
        verdict = "REALISTIC"

    suggested = _extract_number(result, "SUGGESTED_BUDGET_INR", default=state["budget_inr"])

    log_entry = (
        f"Budget Advisor verdict: {verdict} "
        f"(stated: {_inr(state['budget_inr'])}, suggested: {_inr(suggested)})"
    )
    print(f"\n[NODE] {log_entry}")

    return {
        "budget_verdict": verdict,
        "suggested_budget_inr": suggested,
        "feasibility_report": result,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# NODE 1b -- Budget Advice (only runs when the verdict is UNREALISTIC)
#
# NOTE: this node calls NO LLM at all -- it's plain Python string formatting.
# A LangGraph node is just a function that reads state and returns updates;
# whether it uses an agent inside is entirely up to you.
# ---------------------------------------------------------------------------
def budget_advice_node(state: TripState) -> Dict[str, Any]:
    final = (
        "## Let's talk about the budget first\n\n"
        f"Your expectations -- *{state['expectations']}* in "
        f"**{state['destination']}** for {state['trip_length_days']} days -- "
        f"don't fit a total budget of {_inr(state['budget_inr'])}.\n\n"
        f"**A logical budget for this trip is about "
        f"{_inr(state['suggested_budget_inr'])}.**\n\n"
        "Here is the Budget Advisor's full reality check, including what you "
        "COULD do at your current budget:\n\n"
        f"{state['feasibility_report']}\n\n"
        "---\n"
        "Adjust the budget (or the expectations) and run the planner again."
    )

    log_entry = "Budget unrealistic -- returned advice instead of an itinerary."
    print(f"\n[NODE] {log_entry}")

    return {
        "final_plan": final,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# NODE 2 -- Destination & Route Expert
# The user may have typed a city ("Jaipur"), a state ("Himachal Pradesh"),
# or a country ("Japan"). This node resolves that into a realistic ROUTE:
# one base for a short trip, two or three bases (with travel times) for a
# longer one.
# ---------------------------------------------------------------------------
def resolve_destination_node(state: TripState) -> Dict[str, Any]:
    cfg = AGENTS_CFG["destination_expert"]
    agent = Agent(
        role=_cfg_field(cfg, "role"),
        goal=_cfg_field(cfg, "goal"),
        backstory=_cfg_field(cfg, "backstory"),
        tools=[search_tool],
        llm=get_llm(),
        verbose=True,
    )

    task_cfg = TASKS_CFG["destination_task"]
    task = Task(
        description=_cfg_field(task_cfg, "description").format(
            destination=state["destination"],
            expectations=state["expectations"],
            trip_length_days=state["trip_length_days"],
        ),
        expected_output=_cfg_field(task_cfg, "expected_output"),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    selected_bases = _extract_labeled_line(result, "BASES", default=state["destination"])
    log_entry = f"Destination Expert planned route: {selected_bases}"
    print(f"\n[NODE] {log_entry}")

    return {
        "selected_bases": selected_bases,
        "route_rationale": result,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# NODE 3 -- Local Guide
# ---------------------------------------------------------------------------
def plan_itinerary_node(state: TripState) -> Dict[str, Any]:
    cfg = AGENTS_CFG["local_guide"]
    agent = Agent(
        role=_cfg_field(cfg, "role"),
        goal=_cfg_field(cfg, "goal"),
        backstory=_cfg_field(cfg, "backstory"),
        tools=[search_tool],
        llm=get_llm(),
        verbose=True,
    )

    task_cfg = TASKS_CFG["itinerary_task"]
    task = Task(
        description=_cfg_field(task_cfg, "description").format(
            selected_bases=state["selected_bases"],
            trip_length_days=state["trip_length_days"],
            expectations=state["expectations"],
        ),
        expected_output=_cfg_field(task_cfg, "expected_output"),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    log_entry = (
        f"Local Guide drafted a {state['trip_length_days']}-day itinerary "
        f"along: {state['selected_bases']}"
    )
    print(f"\n[NODE] {log_entry}")

    return {
        "itinerary": result,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# NODE 4 -- Travel Concierge (builds the budget + the final plan)
# ---------------------------------------------------------------------------
def compile_budget_node(state: TripState) -> Dict[str, Any]:
    cfg = AGENTS_CFG["concierge"]
    agent = Agent(
        role=_cfg_field(cfg, "role"),
        goal=_cfg_field(cfg, "goal"),
        backstory=_cfg_field(cfg, "backstory"),
        tools=[expense_tool, currency_tool, search_tool],
        llm=get_llm(),
        verbose=True,
    )

    task_cfg = TASKS_CFG["budget_task"]
    task = Task(
        description=_cfg_field(task_cfg, "description").format(
            itinerary=state["itinerary"],
            trip_length_days=state["trip_length_days"],
            budget_inr=f"{state['budget_inr']:,.0f}",
            selected_bases=state["selected_bases"],
        ),
        expected_output=_cfg_field(task_cfg, "expected_output"),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    total_cost = _extract_total_cost(result)
    log_entry = (
        f"Concierge estimated total cost: {_inr(total_cost)} "
        f"(budget: {_inr(state['budget_inr'])})"
    )
    print(f"\n[NODE] {log_entry}")

    return {
        "cost_breakdown": result,
        "estimated_total_cost_inr": total_cost,
        "final_plan": result,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# NODE 5 -- Revise (only runs if the router below sends us here)
# ---------------------------------------------------------------------------
def revise_plan_node(state: TripState) -> Dict[str, Any]:
    cfg = AGENTS_CFG["concierge"]
    agent = Agent(
        role=_cfg_field(cfg, "role"),
        goal=_cfg_field(cfg, "goal"),
        backstory=_cfg_field(cfg, "backstory"),
        tools=[expense_tool, currency_tool, search_tool],
        llm=get_llm(),
        verbose=True,
    )

    revision_task = Task(
        description=(
            f"Your previous plan cost INR {state['estimated_total_cost_inr']:,.0f}, which "
            f"is OVER the traveler's budget of INR {state['budget_inr']:,.0f}.\n\n"
            f"Previous plan:\n{state['final_plan']}\n\n"
            "Revise it to fit the budget: suggest a cheaper stay (hostel/"
            "homestay instead of hotel), sleeper/train instead of flight, trim "
            "or combine paid activities, or reduce food budget assumptions. "
            "Call the Expense Calculator tool again with your new INR numbers."
        ),
        expected_output=(
            "Same format as before: a revised, traveler-ready plan, ending "
            "with a line 'TOTAL_COST_INR: <number>' (no currency symbol, no commas)."
        ),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[revision_task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    total_cost = _extract_total_cost(result)
    log_entry = f"Revision #{state['revision_count'] + 1}: new total {_inr(total_cost)}"
    print(f"\n[NODE] {log_entry}")

    return {
        "cost_breakdown": result,
        "estimated_total_cost_inr": total_cost,
        "final_plan": result,
        "revision_count": state["revision_count"] + 1,
        "status_log": state.get("status_log", []) + [log_entry],
    }


# ---------------------------------------------------------------------------
# ROUTERS -- pure Python, NO LLM calls. They read state, return a node name.
# This is the "conditional routing" LangGraph is built for: a plain
# function that looks at the current state and decides where to go next.
# ---------------------------------------------------------------------------
def route_after_reality_check(state: TripState) -> Literal["advise", "plan"]:
    """WORKED EXAMPLE -- study this one before writing yours below.

    After the Budget Advisor gives its verdict, this fork decides:
      - UNREALISTIC budget -> go give honest advice instead of a fake plan
      - otherwise          -> proceed to actual planning
    Note there is NO LLM here: just an if-statement over the state dict.
    """
    if state["budget_verdict"] == "UNREALISTIC":
        return "advise"
    return "plan"


def route_after_budget_check(state: TripState) -> Literal["revise", "end"]:
    # TODO: Student Code Here
  
    if (
        state["estimated_total_cost_inr"] > state["budget_inr"]
        and state["revision_count"] < MAX_REVISIONS
    ):
        return "revise"
    return "end"


# ---------------------------------------------------------------------------
# BUILD THE GRAPH
# ---------------------------------------------------------------------------
def build_graph():
    workflow = StateGraph(TripState)

    workflow.add_node("reality_check", budget_reality_check_node)
    workflow.add_node("budget_advice", budget_advice_node)
    workflow.add_node("resolve_destination", resolve_destination_node)
    workflow.add_node("local_guide", plan_itinerary_node)
    workflow.add_node("concierge", compile_budget_node)
    workflow.add_node("revise", revise_plan_node)

    # Everything starts with the reality check.
    workflow.add_edge(START, "reality_check")

    # Conditional fork #1: absurd budget -> honest advice, then stop.
    workflow.add_conditional_edges(
        "reality_check",
        route_after_reality_check,
        {"advise": "budget_advice", "plan": "resolve_destination"},
    )
    workflow.add_edge("budget_advice", END)

    # Fixed edges: these stages always run in this order.
    workflow.add_edge("resolve_destination", "local_guide")
    workflow.add_edge("local_guide", "concierge")

    # Conditional fork #2: after the concierge (or a revision) produces a
    # cost, the router decides whether we're done or need another pass.
    # This is what turns a straight-line pipeline into a LOOP.
    workflow.add_conditional_edges(
        "concierge",
        route_after_budget_check,
        {"revise": "revise", "end": END},
    )
    workflow.add_conditional_edges(
        "revise",
        route_after_budget_check,
        {"revise": "revise", "end": END},
    )

    return workflow.compile()


def make_initial_state(
    destination: str,
    expectations: str,
    trip_length_days: int,
    budget_inr: float,
) -> TripState:
    """Convenience factory so main.py / app.py don't repeat this boilerplate."""
    return {
        "destination": destination,
        "expectations": expectations,
        "trip_length_days": trip_length_days,
        "budget_inr": budget_inr,
        "budget_verdict": "",
        "suggested_budget_inr": 0.0,
        "feasibility_report": "",
        "selected_bases": "",
        "route_rationale": "",
        "itinerary": "",
        "cost_breakdown": "",
        "estimated_total_cost_inr": 0.0,
        "revision_count": 0,
        "final_plan": "",
        "status_log": [],
    }
