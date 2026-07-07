"""
main.py -- command-line entry point.

Run with:
    python main.py

Use this to test your graph quickly from the terminal before wiring up
the Streamlit UI (app.py). Same graph, same agents -- just no browser.

Try changing the inputs below and re-running:
  - a country instead of a state ("Japan", "Vietnam")
  - an absurdly low budget (2000) to watch the Budget Advisor step in
  - a tight-but-possible budget to watch the revise loop fire
"""

import sys

from dotenv import load_dotenv

load_dotenv()  # reads your .env file before anything else touches os.environ

# Windows consoles sometimes choke on non-ASCII output from the LLM.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from graph_workflow import build_graph, make_initial_state


def run():
    graph = build_graph()

    initial_state = make_initial_state(
        destination="Himachal Pradesh",       # a city, a state, or a country
        expectations="mountains, trekking, cafes, snow views, local food",
        trip_length_days=5,
        budget_inr=40000.0,                   # TOTAL trip budget in INR
    )

    print("Kicking off the crew... this calls the LLM several times, so it can take a minute.\n")
    final_state = graph.invoke(initial_state)

    print("\n\n================= FINAL TRIP PLAN =================\n")
    print(final_state["final_plan"])
    print("\n=====================================================")
    print(f"Budget verdict: {final_state['budget_verdict']}")
    if final_state["budget_verdict"] != "UNREALISTIC":
        print(f"Route: {final_state['selected_bases']}")
        print(f"Revisions needed: {final_state['revision_count']}")


if __name__ == "__main__":
    run()
