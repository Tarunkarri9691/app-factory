"""LangGraph workflow: code -> test -> (fix loop) -> review -> (fix loop) -> deliver."""
import time
import uuid

from langgraph.graph import END, StateGraph

import config
from agents import architect_agent, coder_agent, product_agent, reviewer_agent, tester_agent
from agents.base import set_run
from orchestrator.state import PipelineState
from orchestrator.support import support_files
from orchestrator.workspace import make_zip, project_dir, write_files
from sandbox import runner


# ---------- planning (human-approval stages live outside the loop) ----------
def new_state(idea: str) -> PipelineState:
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    set_run(run_id)
    return PipelineState(
        run_id=run_id, idea=idea, files={}, tests_written=False, feedback="",
        retry_count=0, review_rounds=0, review_issues=[], status="planning",
    )


def plan_requirements(state: PipelineState) -> PipelineState:
    set_run(state["run_id"])
    state["requirements"] = product_agent.run(state["idea"])
    return state


def plan_architecture(state: PipelineState) -> PipelineState:
    set_run(state["run_id"])
    state["architecture"] = architect_agent.run(state["requirements"])
    return state


# ---------- build loop nodes ----------
def code_node(s: PipelineState) -> dict:
    set_run(s["run_id"])
    if not s["files"]:
        files = coder_agent.build_all(s)
    elif s.get("feedback"):
        files = {**s["files"], **coder_agent.fix(s)}
    else:                       # resuming after an interruption: nothing to change, go test
        return {"status": "running"}
    write_files(s["run_id"], files)
    return {"files": files, "status": "running", "feedback": ""}


def test_node(s: PipelineState) -> dict:
    set_run(s["run_id"])
    ok, msg = runner.check_available()
    if not ok:                  # Docker problem: stop cleanly, spend no quota
        return {"test_results": {"passed": False, "infra": True, "log": msg}, "feedback": ""}
    files = dict(s["files"])
    if not s["tests_written"]:
        files.update(tester_agent.write_tests(s))
    files.update(support_files())          # our own conftest.py / __init__.py always win
    write_files(s["run_id"], files)
    result = runner.run_tests(project_dir(s["run_id"]))
    update = {"files": files, "tests_written": True, "test_results": result}
    if result["passed"]:
        return {**update, "feedback": ""}
    return {
        **update,
        "retry_count": s["retry_count"] + 1,
        "feedback": "TEST FAILURES:\n" + result["log"],
    }


def review_node(s: PipelineState) -> dict:
    set_run(s["run_id"])
    review = reviewer_agent.run(s)
    blocking = [i for i in review["issues"] if i["severity"] in ("high", "medium")]
    if blocking and s["review_rounds"] < config.MAX_REVIEW_ROUNDS:
        text = "\n".join(f"- [{i['severity']}] {i['file']}: {i['description']}" for i in blocking)
        return {
            "review_issues": review["issues"],
            "review_rounds": s["review_rounds"] + 1,
            "feedback": "REVIEW ISSUES:\n" + text,
        }
    return {"review_issues": review["issues"], "feedback": ""}


def deliver_node(s: PipelineState) -> dict:
    return {"status": "done", "zip_path": str(make_zip(s["run_id"]))}


def fail_node(s: PipelineState) -> dict:
    # Keep the partial project so a human can take over.
    return {"status": "failed", "zip_path": str(make_zip(s["run_id"]))}


# ---------- routing ----------
def route_after_test(s: PipelineState) -> str:
    tr = s["test_results"]
    if tr.get("infra"):
        return "fail"
    if tr["passed"]:
        done_review = s["review_rounds"] > 0 and s["review_rounds"] >= config.MAX_REVIEW_ROUNDS
        return "deliver" if done_review else "review"     # no pointless second review call
    return "fail" if s["retry_count"] > config.MAX_TEST_RETRIES else "code"


def route_after_review(s: PipelineState) -> str:
    return "code" if s.get("feedback") else "deliver"


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("code", code_node)
    g.add_node("test", test_node)
    g.add_node("review", review_node)
    g.add_node("deliver", deliver_node)
    g.add_node("fail", fail_node)
    g.set_entry_point("code")
    g.add_edge("code", "test")
    g.add_conditional_edges("test", route_after_test, {"review": "review", "code": "code", "fail": "fail", "deliver": "deliver"})
    g.add_conditional_edges("review", route_after_review, {"code": "code", "deliver": "deliver"})
    g.add_edge("deliver", END)
    g.add_edge("fail", END)
    return g.compile()


def build(state: PipelineState, on_update=None) -> PipelineState:
    """Run the build loop. on_update(node_name, update_dict) is called after every node."""
    set_run(state["run_id"])
    final = dict(state)
    for chunk in build_graph().stream(state, stream_mode="updates", config={"recursion_limit": 60}):
        for node, update in chunk.items():
            final.update(update)
            if on_update:
                on_update(node, update)
    return final


def run_pipeline(idea: str, approve=None, on_update=None) -> PipelineState:
    """Full pipeline. approve(stage, data) -> data (possibly edited) or None to abort."""
    approve = approve or (lambda stage, data: data)
    state = new_state(idea)
    plan_requirements(state)
    edited = approve("requirements", state["requirements"])
    if edited is None:
        state["status"] = "aborted"
        return state
    state["requirements"] = edited
    plan_architecture(state)
    edited = approve("architecture", state["architecture"])
    if edited is None:
        state["status"] = "aborted"
        return state
    state["architecture"] = edited
    return build(state, on_update)
