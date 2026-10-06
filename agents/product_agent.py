"""Product agent: raw idea -> structured requirements."""
from agents.base import call_json, load_prompt
from orchestrator.state import Requirements


def run(idea: str) -> dict:
    return call_json(load_prompt("product"), f"App idea:\n{idea}", "product", Requirements)
