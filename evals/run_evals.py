"""Run every benchmark idea (auto-approved) and record pass rate, cost and time.
   python -m evals.run_evals [N]   # N = only the first N ideas"""
import json
import sys
import time

import config
from agents.base import usage_for_run
from orchestrator import graph

IDEAS = json.loads((config.BASE_DIR / "evals" / "benchmark_ideas.json").read_text())


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(IDEAS)
    rows = []
    for idea in IDEAS[:limit]:
        start = time.time()
        try:
            s = graph.run_pipeline(idea)
            row = {"idea": idea, "status": s["status"], "retries": s.get("retry_count", 0),
                   "review_rounds": s.get("review_rounds", 0), **usage_for_run(s["run_id"])}
        except Exception as e:  # noqa: BLE001
            row = {"idea": idea, "status": f"error: {e}"}
        row["seconds"] = round(time.time() - start, 1)
        rows.append(row)
        print(row)
    passed = sum(r["status"] == "done" for r in rows)
    print(f"\nPass rate: {passed}/{len(rows)}")
    out = config.LOGS_DIR / f"eval-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
