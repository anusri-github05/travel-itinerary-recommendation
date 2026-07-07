"""
Custom tools for the Trip Planner crew.

Each tool here is a plain Python class -- the "skill" an agent can choose to
use. Splitting tools into their own files/package (instead of jamming them
into crew.py) is a habit worth building early: it keeps deterministic logic
(like the expense calculator) clearly separate from LLM reasoning, and makes
each tool independently testable.
"""
