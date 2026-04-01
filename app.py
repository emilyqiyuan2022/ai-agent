"""
app.py — Streamlit UI for the Research Assistant AI Agent
Highlights: real-time tool call visualization, reasoning chain display
Run: streamlit run app.py
"""

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from agent import run_agent


# ── Environment & output directory ───────────────────────
def load_api_key():
    """Load API key from Streamlit Secrets (cloud) or .env (local)."""
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
        os.environ["ANTHROPIC_API_KEY"] = key
        return key
    except Exception:
        pass
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        st.error(
            "ANTHROPIC_API_KEY not found. "
            "Add it to your .env file (local) or Streamlit Secrets (cloud)."
        )
        st.stop()
    return key

load_api_key()

OUTPUT_DIR = "./outputs"
Path(OUTPUT_DIR).mkdir(exist_ok=True)


# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title = "Research Assistant AI Agent",
    page_icon  = "🤖",
    layout     = "wide",
)
st.title("🤖 Research Assistant AI Agent")
st.caption("Describe a task — the agent searches the web, runs calculations, and generates a report automatically.")


# ── Tool icons ────────────────────────────────────────────
TOOL_ICONS = {
    "web_search"  : "🔍",
    "calculate"   : "🔢",
    "read_file"   : "📂",
    "write_file"  : "💾",
    "get_datetime": "🕐",
}


# ── Example tasks ─────────────────────────────────────────
EXAMPLES = [
    "Compare Python vs JavaScript job market demand in 2025 and analyze which has better prospects",
    "Search for global EV sales data in 2024, calculate the year-over-year growth rate, and save a report",
    "Search for the key differences between GPT-4 and Claude, compile a comparison report and save it",
    "Get the current time, search for today's AI industry news, and write a briefing to a file",
]


# ── Layout ────────────────────────────────────────────────
col_main, col_side = st.columns([2, 1])

with col_main:
    st.markdown("**Quick examples**")
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        label = ex[:40] + "..." if len(ex) > 40 else ex
        if cols[i % 2].button(label, key=f"ex{i}", use_container_width=True):
            st.session_state["task_input"] = ex

    task = st.text_area(
        "Enter your task",
        value       = st.session_state.get("task_input", ""),
        height      = 100,
        placeholder = "e.g. Search for the latest AI model releases, compare the top 3, and save a report...",
    )

    run_btn = st.button("Run Agent", type="primary", use_container_width=True)

with col_side:
    st.markdown("**Generated files**")
    output_files = list(Path(OUTPUT_DIR).glob("*"))
    if output_files:
        for f in sorted(output_files, key=lambda x: x.stat().st_mtime, reverse=True):
            size_kb = f.stat().st_size // 1024 + 1
            if st.button(f"📄 {f.name} ({size_kb} KB)", key=f"file_{f.name}", use_container_width=True):
                st.session_state["view_file"] = f.name
    else:
        st.caption("No files yet — run a task to generate reports here.")

    # Preview selected file
    if "view_file" in st.session_state:
        fpath = Path(OUTPUT_DIR) / st.session_state["view_file"]
        if fpath.exists():
            st.divider()
            st.markdown(f"**{st.session_state['view_file']}**")
            content = fpath.read_text(encoding="utf-8")
            st.markdown(content)


# ── Run agent ─────────────────────────────────────────────
if run_btn and task.strip():
    st.divider()
    st.markdown("### Execution trace")

    process_container = st.container()
    tool_steps = []

    def on_tool_call(name: str, inputs: dict):
        """Callback fired when the agent calls a tool."""
        icon = TOOL_ICONS.get(name, "🔧")
        # Truncate long parameter values for display
        display_inputs = {
            k: (str(v)[:80] + "..." if len(str(v)) > 80 else str(v))
            for k, v in inputs.items()
        }
        tool_steps.append({
            "type"  : "call",
            "name"  : name,
            "inputs": display_inputs,
            "icon"  : icon,
        })
        with process_container:
            _render_steps(tool_steps)

    def on_tool_result(name: str, result: str):
        """Callback fired when a tool returns its result."""
        preview = str(result)[:200].replace("\n", " ")
        if tool_steps and tool_steps[-1]["type"] == "call":
            tool_steps[-1]["result"] = (
                preview + "..." if len(str(result)) > 200 else preview
            )
        with process_container:
            _render_steps(tool_steps)

    def _render_steps(steps: list):
        """Render the live tool call trace inside the container."""
        process_container.empty()
        with process_container:
            for i, step in enumerate(steps):
                icon       = step.get("icon", "🔧")
                name       = step["name"]
                inp        = step.get("inputs", {})
                main_param = next(iter(inp.values()), "") if inp else ""
                result     = step.get("result", "Running...")

                with st.expander(
                    f"{icon} {name}  —  {str(main_param)[:40]}",
                    expanded=(i == len(steps) - 1),
                ):
                    st.caption("Input parameters")
                    st.json(inp)
                    st.caption("Tool result")
                    st.text(result)

    with st.spinner("Agent is working on your task..."):
        final_answer = run_agent(
            task           = task,
            on_tool_call   = on_tool_call,
            on_tool_result = on_tool_result,
        )

    st.divider()
    st.markdown("### Final answer")
    st.markdown(final_answer)

    # Refresh file list after agent writes new files
    st.rerun()

elif run_btn:
    st.warning("Please enter a task before running the agent.")
