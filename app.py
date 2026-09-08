"""
app.py — CodeSentinel Streamlit application.

Upload or paste a Python script; get:
  - AST-based static analysis (issue list, severity, issues/100 lines)
  - Claude-generated optimization suggestions
  - One-click Claude-generated docstrings, with a downloadable updated file

Run locally:
  export ANTHROPIC_API_KEY=sk-ant-...
  streamlit run app.py

On Replit: set ANTHROPIC_API_KEY in Secrets, set run command to
`streamlit run app.py --server.port 8080 --server.address 0.0.0.0`
"""

import time

import streamlit as st

from analyzer import analyze_source
from claude_assist import generate_docstrings, suggest_optimizations

st.set_page_config(page_title="CodeSentinel", page_icon="🛡️", layout="wide")

st.title("🛡️ CodeSentinel")
st.caption("AI Code Review & Performance Optimization Assistant")

SEVERITY_COLOR = {"error": "🔴", "warning": "🟠", "info": "🔵"}

with st.sidebar:
    st.header("Input")
    uploaded = st.file_uploader("Upload a .py file", type=["py"])
    pasted = st.text_area("...or paste code here", height=300)
    run_btn = st.button("Analyze", type="primary", use_container_width=True)

if "source" not in st.session_state:
    st.session_state.source = ""

if run_btn:
    if uploaded is not None:
        st.session_state.source = uploaded.read().decode("utf-8")
    elif pasted.strip():
        st.session_state.source = pasted
    else:
        st.warning("Upload a file or paste code first.")

source = st.session_state.source

if source:
    try:
        result = analyze_source(source)
    except SyntaxError as e:
        st.error(f"Could not parse source: {e}")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Lines", result.total_lines)
    col2.metric("Functions", result.total_functions)
    col3.metric("Issues Found", len(result.issues))
    col4.metric("Issues / 100 lines", result.issues_per_100_lines)

    st.subheader("Static Analysis Findings")
    if not result.issues:
        st.success("No issues detected by static analysis.")
    else:
        for issue in result.issues:
            icon = SEVERITY_COLOR.get(issue.severity, "⚪")
            st.write(f"{icon} **Line {issue.line}** — `{issue.kind}`: {issue.message}")

    with st.expander("View source"):
        st.code(source, language="python")

    st.divider()
    st.subheader("Claude Optimization Suggestions")
    if st.button("Get AI suggestions"):
        issues_summary = "\n".join(
            f"- Line {i.line} [{i.severity}] {i.kind}: {i.message}" for i in result.issues
        ) or "No static-analysis issues found."
        with st.spinner("Asking Claude to review the code..."):
            start = time.time()
            try:
                suggestions = suggest_optimizations(source, issues_summary)
                elapsed = time.time() - start
                st.info(f"Generated in {elapsed:.2f}s")
                st.markdown(suggestions)
            except RuntimeError as e:
                st.error(str(e))

    st.divider()
    st.subheader("Auto-Generate Docstrings")
    if result.functions_missing_docstrings:
        st.write(
            f"{len(result.functions_missing_docstrings)} function(s) missing docstrings: "
            f"{', '.join(result.functions_missing_docstrings)}"
        )
        if st.button("Generate docstrings with Claude"):
            with st.spinner("Generating docstrings..."):
                try:
                    updated = generate_docstrings(
                        source, result.functions_missing_docstrings
                    )
                    st.code(updated, language="python")
                    st.download_button(
                        "Download updated file",
                        data=updated,
                        file_name="documented_script.py",
                        mime="text/x-python",
                    )
                except RuntimeError as e:
                    st.error(str(e))
    else:
        st.success("All functions already have docstrings.")
else:
    st.info("Upload a Python file or paste code in the sidebar, then click Analyze.")
