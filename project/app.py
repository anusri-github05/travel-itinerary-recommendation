"""
app.py -- Streamlit front-end for the Multi-Agent Trip Planner.

Run with:
    streamlit run app.py

This file ONLY handles UI (inputs, layout, displaying results). All the
agent/graph logic lives in graph_workflow.py. That separation matters: you
could swap this Streamlit UI for a Slack bot or a FastAPI endpoint later,
and graph_workflow.py would not need to change at all.
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from graph_workflow import build_graph, make_initial_state

st.set_page_config(page_title="Multi-Agent Trip Planner", page_icon="🧭", layout="centered")

st.title("🧭 Multi-Agent Trip Planner")
st.caption(
    "CrewAI agents (Budget Advisor → Destination Expert → Local Guide → Concierge) "
    "orchestrated by a LangGraph state machine."
)

with st.sidebar:
    st.header("Trip details")
    destination = st.text_input(
        "Destination (a city, a state, or a country)", "Himachal Pradesh"
    )
    expectations = st.text_area(
        "What do you expect from this trip?",
        "mountains, trekking, cafes, snow views, local food",
        help="Anything: beaches, street food, nightlife, temples, adventure sports...",
    )
    trip_length_days = st.slider("Number of days", 2, 14, 5)
    budget_inr = st.number_input(
        "Total budget (₹ INR, for the whole trip)",
        min_value=1000,
        value=40000,
        step=5000,
        help="The Budget Advisor will tell you honestly if this is too low "
             "for your expectations.",
    )
    run_button = st.button("✈️ Plan my trip", type="primary", use_container_width=True)

if run_button:
    if not destination.strip():
        st.error("Please enter a destination.")
        st.stop()

    graph = build_graph()
    initial_state = make_initial_state(
        destination=destination.strip(),
        expectations=expectations.strip(),
        trip_length_days=trip_length_days,
        budget_inr=float(budget_inr),
    )

    with st.status("Assembling your crew...", expanded=True) as status:
        st.write("This calls an LLM several times and can take 30-90 seconds.")
        final_state = graph.invoke(initial_state)
        status.update(label="Done!", state="complete", expanded=False)

    if final_state["budget_verdict"] == "UNREALISTIC":
        st.warning(
            f"Your budget of ₹{budget_inr:,.0f} doesn't match these expectations. "
            f"A logical budget for this trip is about "
            f"**₹{final_state['suggested_budget_inr']:,.0f}**."
        )
        st.markdown(final_state["final_plan"])
    else:
        if final_state["budget_verdict"] == "TIGHT":
            st.info(
                "Heads up: the Budget Advisor rated this budget **TIGHT** — "
                "doable, but expect trade-offs."
            )

        st.subheader(f"Route: {final_state['selected_bases']}")
        with st.expander("Why this route?"):
            st.write(final_state["route_rationale"])

        with st.expander("Budget reality check"):
            st.write(final_state["feasibility_report"])

        st.subheader("Your itinerary & budget")
        st.markdown(final_state["final_plan"])

        if final_state["revision_count"] > 0:
            st.info(
                f"The Concierge revised the plan {final_state['revision_count']} "
                "time(s) to fit your budget."
            )

    with st.expander("Behind the scenes (agent trace)"):
        for entry in final_state["status_log"]:
            st.write(f"- {entry}")
else:
    st.info("Fill in your trip details on the left, then click **Plan my trip**.")
