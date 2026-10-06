"""Streamlit UI.   streamlit run ui/app.py"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

import config  # noqa: E402,F401  (loads .env)
from agents.base import LLMError, usage_for_run  # noqa: E402
from orchestrator import graph  # noqa: E402
from orchestrator.state import Architecture, Requirements  # noqa: E402

st.set_page_config(page_title="App Factory", page_icon="🏭", layout="wide")

# Custom Premium CSS Injection & UI/UX Animations
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Keyframe Animations */
@keyframes fadeInScale {
    from { opacity: 0; transform: translateY(14px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 12px rgba(99, 102, 241, 0.3); }
    50% { box-shadow: 0 0 28px rgba(139, 92, 246, 0.55); }
    100% { box-shadow: 0 0 12px rgba(99, 102, 241, 0.3); }
}

/* Background & Main App Container */
.stApp {
    background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0f172a 100%) !important;
    color: #f8fafc !important;
}

/* Header styling */
h1 {
    font-weight: 800 !important;
    background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px !important;
}

h2, h3 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
}

/* Primary action buttons */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 0.65rem 1.25rem !important;
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.45) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.65) !important;
}

/* Secondary & template buttons */
div.stButton > button {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #cbd5e1 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    border-color: #6366f1 !important;
    color: #ffffff !important;
    background: rgba(99, 102, 241, 0.2) !important;
    transform: translateY(-1px) !important;
}

/* Download Button styling */
div.stDownloadButton > button {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100% !important;
}

div.stDownloadButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 28px rgba(16, 185, 129, 0.65) !important;
}

/* Expander / File Accordion styling */
.stExpander {
    background: rgba(15, 23, 42, 0.65) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 12px !important;
    margin-bottom: 12px !important;
    transition: all 0.25s ease !important;
}

.stExpander:hover {
    border-color: rgba(99, 102, 241, 0.45) !important;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.35) !important;
    transform: translateY(-2px) !important;
}

.stExpander [data-testid="stExpanderToggleHeader"] {
    color: #e2e8f0 !important;
    font-weight: 700 !important;
}

/* Success & Error Alert styling */
[data-testid="stNotification"] {
    background: rgba(16, 185, 129, 0.15) !important;
    border: 1px solid rgba(16, 185, 129, 0.35) !important;
    border-radius: 12px !important;
    color: #6ee7b7 !important;
    font-weight: 700 !important;
    animation: fadeInScale 0.4s ease-out forwards;
}

/* Code Viewer container */
[data-testid="stCodeBlock"] {
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Text input & area styling */
.stTextArea textarea {
    background: rgba(15, 23, 42, 0.75) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
    color: #f8fafc !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
}

.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35) !important;
}

/* Pipeline Step Indicator Header */
.pipeline-steps {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin: 12px 0 24px 0;
    padding: 12px 20px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    backdrop-filter: blur(12px);
    animation: fadeInScale 0.4s ease-out forwards;
}

.step-item {
    font-size: 13px;
    font-weight: 700;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 6px;
}

.step-item.active {
    color: #a5b4fc;
}

.step-item.completed {
    color: #34d399;
}

.step-divider {
    color: #334155;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("🏭 Requirements-to-App Pipeline")
ss = st.session_state
ss.setdefault("state", None)
ss.setdefault("stage", "idea")
ss.setdefault("error", "")

key = os.getenv("GEMINI_API_KEY", "")
if not key or key.startswith("paste-your"):
    st.error("GEMINI_API_KEY is missing. Put your key in the .env file, then restart Streamlit.")
    st.stop()
st.caption(f"Model: `{config.MODEL}`" + (f"  |  fallbacks: `{', '.join(config.FALLBACK_MODELS)}`"
                                         if config.FALLBACK_MODELS else ""))

# Render Pipeline Step Tracker Header
stages_order = ["idea", "requirements", "architecture", "build", "done"]
stage_labels = {
    "idea": "1. App Idea",
    "requirements": "2. Requirements",
    "architecture": "3. Architecture",
    "build": "4. Automated Build",
    "done": "5. Delivered Project"
}
curr_idx = stages_order.index(ss.stage) if ss.stage in stages_order else 0

steps_html = []
for idx, stg in enumerate(stages_order):
    cls = "completed" if idx < curr_idx else ("active" if idx == curr_idx else "")
    icon = "✓ " if idx < curr_idx else ("➔ " if idx == curr_idx else "• ")
    steps_html.append(f'<div class="step-item {cls}">{icon}{stage_labels[stg]}</div>')

st.markdown(f'<div class="pipeline-steps">{" <span class=\'step-divider\'>—</span> ".join(steps_html)}</div>', unsafe_allow_html=True)


def reset():
    ss.state, ss.stage, ss.error = None, "idea", ""


def show_error(e: Exception):
    st.error(str(e) if isinstance(e, LLMError) else f"Unexpected error: {e}")


def ensure_app_running(run_id: str):
    import socket
    import subprocess
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    res = sock.connect_ex(('127.0.0.1', 8000))
    sock.close()
    if res != 0:
        app_dir = Path(__file__).resolve().parent.parent / "workspace" / run_id
        if app_dir.exists():
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
                cwd=str(app_dir)
            )




# ---- Stage 1: idea ----
if ss.stage == "idea":
    ss.setdefault("idea_input", "A to-do list with add, delete and done")
    
    st.markdown("### 💡 What app would you like to build?")
    idea = st.text_area(
        "Describe your app idea:",
        value=ss.idea_input,
        height=140,
        placeholder="e.g. A to-do list with add, delete, filter, and completion tracking"
    )
    
    st.caption("Need inspiration? Click a template to auto-fill:")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📝 Task Tracker", use_container_width=True):
        ss.idea_input = "A modern task tracker with priority levels, search, due dates, and completion status."
        st.rerun()
    if c2.button("💰 Expense Tracker", use_container_width=True):
        ss.idea_input = "An expense tracker app to log daily expenses, categorize transactions, and view totals."
        st.rerun()
    if c3.button("📌 Note App", use_container_width=True):
        ss.idea_input = "A Markdown note taking app with categories, title search, and quick edit features."
        st.rerun()
    if c4.button("🌦️ Weather Dashboard", use_container_width=True):
        ss.idea_input = "A weather dashboard displaying current temperature, forecast details, and location search."
        st.rerun()

    st.write("")
    if st.button("🚀 Generate requirements", type="primary", use_container_width=True, disabled=not idea.strip()):
        ss.idea_input = idea
        try:
            with st.spinner("Product agent is working..."):
                ss.state = graph.plan_requirements(graph.new_state(idea.strip()))
            ss.stage = "requirements"
            st.rerun()
        except Exception as e:  # noqa: BLE001
            show_error(e)

# ---- Stage 2: approve requirements ----
elif ss.stage == "requirements":
    st.subheader("1. Requirements (edit if needed)")
    text = st.text_area("JSON", json.dumps(ss.state["requirements"], indent=2), height=400)
    c1, c2 = st.columns(2)
    if c1.button("Approve & design architecture", type="primary"):
        try:
            ss.state["requirements"] = Requirements.model_validate_json(text).model_dump()
            with st.spinner("Architect agent is working (using RAG)..."):
                graph.plan_architecture(ss.state)
            ss.stage = "architecture"
            st.rerun()
        except Exception as e:  # noqa: BLE001
            show_error(e)
    if c2.button("Start over"):
        reset()
        st.rerun()

# ---- Stage 3: approve architecture ----
elif ss.stage == "architecture":
    st.subheader("2. Architecture (edit if needed)")
    text = st.text_area("JSON", json.dumps(ss.state["architecture"], indent=2), height=450)
    c1, c2 = st.columns(2)
    if c1.button("Approve & build", type="primary"):
        try:
            ss.state["architecture"] = Architecture.model_validate_json(text).model_dump()
            ss.stage = "build"
            st.rerun()
        except Exception as e:  # noqa: BLE001
            show_error(e)
    if c2.button("Start over"):
        reset()
        st.rerun()

# ---- Stage 4: build (resumable: progress is saved after every step) ----
elif ss.stage == "build":
    st.subheader("3. Building")
    labels = {"code": "💻 Coder wrote/fixed code", "test": "🧪 Tester ran tests",
              "review": "🔍 Reviewer audited", "deliver": "📦 Delivered", "fail": "⚠️ Stopped"}
    status = st.status("Pipeline running...", expanded=True)

    def on_update(node, upd):
        ss.state.update(upd)                      # save progress so Retry can resume
        extra = ""
        if node == "test":
            tr = upd["test_results"]
            extra = " — PASSED" if tr["passed"] else (
                " — blocked (see message)" if tr.get("infra") else f" — FAILED (retry {upd['retry_count']})")
        status.write(labels.get(node, node) + extra)

    try:
        ss.state = graph.build(ss.state, on_update)
        status.update(label=f"Finished: {ss.state['status']}",
                      state="complete" if ss.state["status"] == "done" else "error")
        ss.stage = "done"
        st.rerun()
    except Exception as e:  # noqa: BLE001
        status.update(label="Paused", state="error")
        ss.error = str(e) if isinstance(e, LLMError) else f"Unexpected error: {e}"
        ss.stage = "build_error"
        st.rerun()

# ---- Stage 4b: paused by an error ----
elif ss.stage == "build_error":
    st.warning("The build paused. Your progress is saved.")
    st.error(ss.error)
    c1, c2 = st.columns(2)
    if c1.button("🔁 Retry / resume", type="primary"):
        ss.stage = "build"
        st.rerun()
    if c2.button("Start over"):
        reset()
        st.rerun()

# ---- Stage 5: result ----
elif ss.stage == "done":
    s = ss.state
    tr = s.get("test_results", {})
    (st.success if s["status"] == "done" else st.error)(f"Status: {s['status']}")
    
    if s["status"] == "done":
        ensure_app_running(s["run_id"])
        st.subheader("🎉 Live App Preview")
        st.caption("Your generated application is live on localhost:8000")
        
        c_link, c_dl = st.columns([2, 1])
        c_link.markdown('[🌐 **Open Live App in New Tab (http://127.0.0.1:8000)**](http://127.0.0.1:8000)')
        if s.get("zip_path"):
            c_dl.download_button("⬇️ Download project (.zip)", Path(s["zip_path"]).read_bytes(),
                                file_name=Path(s["zip_path"]).name, mime="application/zip")
            
        import streamlit.components.v1 as components
        components.iframe("http://127.0.0.1:8000", height=680, scrolling=True)

    if tr.get("infra"):
        st.warning(tr["log"])
    if s["status"] == "failed":
        label = "🔁 Retry (after fixing Docker)" if tr.get("infra") else "🔁 Re-run the tests"
        if st.button(label, type="primary"):
            s.update(status="running", retry_count=0, feedback="")   # re-test first; fix only if still failing
            ss.stage = "build"
            st.rerun()
    st.json(usage_for_run(s["run_id"]), expanded=False)
    if s.get("review_issues"):
        st.subheader("Reviewer notes")
        for i in s["review_issues"]:
            st.write(f"**{i['severity']}** `{i['file']}` — {i['description']}")
    if tr and not tr.get("passed") and not tr.get("infra"):
        st.subheader("Last test log")
        st.code(tr.get("log", ""))
    st.subheader("Source Files")
    for path, code in s.get("files", {}).items():
        with st.expander(path):
            st.code(code, language=Path(path).suffix.lstrip(".") or "text")
    st.button("New project", on_click=reset)

