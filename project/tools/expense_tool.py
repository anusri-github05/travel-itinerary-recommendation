"""
expense_tool.py
===============
This tool does NOT call an LLM. It's plain, deterministic Python arithmetic.

That's the point: an LLM is bad at reliable multi-step math and will
happily "hallucinate" a plausible-looking but wrong total. Whenever a task
needs a number to be RIGHT every single time, write a tool instead of
trusting the model to compute it in its head. The agent's job becomes:
figure out reasonable INPUTS (travel fare, nights, etc.), then call this
tool to get a trustworthy total.

All amounts here are in INR (Indian Rupees). If the agent found a price in
a foreign currency, it should convert it with the Currency Converter tool
FIRST, then feed the INR number in here -- one tool per job.
"""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ExpenseInput(BaseModel):
    num_days: int = Field(..., description="Trip length in days")
    num_travelers: int = Field(1, description="Number of travelers (default 1)")
    travel_fare_per_person: float = Field(
        ...,
        description=(
            "Round-trip travel fare per traveler in INR -- flight, train, or "
            "bus, whatever the plan uses to reach the route's first base and "
            "get home from its last"
        ),
    )
    intercity_transport_total: float = Field(
        0.0,
        description=(
            "Total cost of all hops BETWEEN base cities during the trip "
            "(mid-trip buses/trains/flights), in INR, for the whole group. "
            "0 for a single-base trip."
        ),
    )
    stay_cost_per_night: float = Field(
        ..., description="Hotel/hostel/homestay cost per night for the whole room/group, in INR"
    )
    food_cost_per_day_per_person: float = Field(
        ..., description="Estimated food cost per traveler per day, in INR"
    )
    activities_total: float = Field(
        0.0,
        description=(
            "Total cost of all planned paid activities/tickets/permits for "
            "the whole trip, in INR (treks, entry fees, rentals, ...)"
        ),
    )
    local_transport_per_day: float = Field(
        500.0, description="Local transport (metro/auto/taxi/scooter) per day for the group, in INR"
    )
    contingency_percent: float = Field(
        10.0, description="Safety buffer as a percent of the subtotal, e.g. 10 for 10%"
    )


class ExpenseCalculatorTool(BaseTool):
    name: str = "Expense Calculator"
    description: str = (
        "Calculates a trustworthy total trip cost in INR. Give it the trip "
        "length, number of travelers, and estimated INR costs for travel "
        "fare/stay/food/activities/local transport, and it returns an "
        "itemized breakdown plus a grand total (including a contingency "
        "buffer). Convert any foreign-currency prices to INR with the "
        "Currency Converter tool BEFORE calling this."
    )
    args_schema: Type[BaseModel] = ExpenseInput

    def _run(
        self,
        num_days: int,
        num_travelers: int = 1,
        travel_fare_per_person: float = 0.0,
        intercity_transport_total: float = 0.0,
        stay_cost_per_night: float = 0.0,
        food_cost_per_day_per_person: float = 0.0,
        activities_total: float = 0.0,
        local_transport_per_day: float = 500.0,
        contingency_percent: float = 10.0,
    ) -> str:
        travel = travel_fare_per_person * num_travelers
        stay = stay_cost_per_night * num_days
        food = food_cost_per_day_per_person * num_travelers * num_days
        transport = local_transport_per_day * num_days

        subtotal = (travel + intercity_transport_total + stay + food
                    + transport + activities_total)
        contingency = subtotal * (contingency_percent / 100.0)
        total = subtotal + contingency

        return (
            f"Travel fare to/from route ({num_travelers} traveler(s)): INR {travel:,.0f}\n"
            f"Intercity hops between bases: INR {intercity_transport_total:,.0f}\n"
            f"Stay ({num_days} nights): INR {stay:,.0f}\n"
            f"Food ({num_travelers} traveler(s) x {num_days} days): INR {food:,.0f}\n"
            f"Local transport ({num_days} days): INR {transport:,.0f}\n"
            f"Activities: INR {activities_total:,.0f}\n"
            f"Subtotal: INR {subtotal:,.0f}\n"
            f"Contingency ({contingency_percent:.0f}%): INR {contingency:,.0f}\n"
            f"GRAND TOTAL: INR {total:,.0f}"
        )
