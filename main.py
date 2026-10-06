"""CLI entry point.   python main.py "a to-do app"   [--auto]"""
import argparse
import json

from agents.base import LLMError, usage_for_run
from orchestrator.graph import run_pipeline


def cli_approve(stage, data):
    print(f"\n===== {stage.upper()} =====")
    print(json.dumps(data, indent=2))
    ans = input(f"Approve {stage}? [y/n] ").strip().lower()
    return data if ans == "y" else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea")
    ap.add_argument("--auto", action="store_true", help="skip human approval steps")
    args = ap.parse_args()
    try:
        state = run_pipeline(
            args.idea,
            approve=None if args.auto else cli_approve,
            on_update=lambda node, upd: print(f"[{node}] done"),
        )
    except LLMError as e:
        raise SystemExit(f"\nStopped: {e}")
    print(f"\nStatus: {state['status']}")
    if state.get("zip_path"):
        print(f"Project: {state['zip_path']}")
    if state["status"] == "failed":
        print("Last test log:\n", state.get("test_results", {}).get("log", ""))
    print("Usage:", usage_for_run(state["run_id"]))


if __name__ == "__main__":
    main()
