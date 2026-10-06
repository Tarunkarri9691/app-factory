"""Reviewer agent: audits code for bugs, security, validation and requirement coverage."""
import json

from agents.base import call_json, load_prompt
from orchestrator.state import Review


def run(state: dict) -> dict:
    code = "\n\n".join(
        f"=== FILE: {p} ===\n{c}\n=== END FILE ===" for p, c in state["files"].items()
    )
    user = (
        f"REQUIREMENTS:\n{json.dumps(state['requirements'], indent=2)}\n\n"
        f"CODE:\n{code}\n\nTEST RESULT: {'passed' if state['test_results']['passed'] else 'failed'}"
    )
    return call_json(load_prompt("reviewer"), user, "reviewer", Review)
