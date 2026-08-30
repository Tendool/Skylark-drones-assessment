"""Conversational UI for the Skylark Drones BI agent.

Run locally:   streamlit run app/streamlit_app.py
Deploy:        point Streamlit Community Cloud (or similar) at this file and
                set the env vars documented in README.md as app secrets.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Streamlit Cloud secrets don't land in os.environ automatically -- mirror them
# in so the rest of the codebase can keep using plain os.environ.get(...).
try:
    for key, value in st.secrets.items():
        os.environ.setdefault(key, str(value))
except Exception:
    pass  # no secrets.toml locally -- fine, we fall back to real env vars / mock mode

from src.agent.llm_adapter import get_llm_adapter
from src.agent.orchestrator import run_conversation
from src.config import get_llm_provider, get_monday_client
from src.data.repo import DataRepo

st.set_page_config(page_title="Skylark Drones BI Agent", page_icon="📊", layout="wide")


@st.cache_resource
def get_repo() -> DataRepo:
    return DataRepo(get_monday_client())


def get_llm():
    provider = get_llm_provider()
    try:
        return get_llm_adapter(provider), None
    except Exception as exc:  # missing/invalid API key, unimplemented provider, etc.
        return None, str(exc)


def render_sidebar(repo: DataRepo) -> None:
    st.sidebar.header("Data source")
    mode = os.environ.get("MONDAY_MODE", "mock").lower()
    if mode == "live":
        st.sidebar.success("Connected to live monday.com boards")
    else:
        st.sidebar.info("Running on local mock data (fixtures/) -- no monday.com credentials configured. See README.md to switch to MONDAY_MODE=live.")

    if st.sidebar.button("Refresh data from monday.com"):
        repo.refresh()
        st.sidebar.success("Refreshed.")

    with st.sidebar.expander("Data quality report", expanded=False):
        report = repo.quality_report
        for section in ("work_orders", "deals"):
            st.markdown(f"**{report[section]['board']}** -- {report[section]['row_count']} rows")
            for note in report[section]["notes"]:
                st.caption(f"- {note}")
        for note in report["cross_board_notes"]:
            st.caption(f"- {note}")


def main() -> None:
    st.title("📊 Skylark Drones — Business Intelligence Agent")
    st.caption("Ask about pipeline health, delivery status, revenue, or sector performance across the Work Orders and Deals boards.")

    repo = get_repo()
    render_sidebar(repo)

    llm, llm_error = get_llm()
    if llm_error:
        st.error(
            f"LLM not configured ({llm_error}). Set ANTHROPIC_API_KEY (default provider) as an "
            "environment variable or Streamlit secret to enable the chat agent."
        )
        st.stop()

    if "display_history" not in st.session_state:
        st.session_state.display_history = []
    if "llm_history" not in st.session_state:
        st.session_state.llm_history = []

    for turn in st.session_state.display_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    if prompt := st.chat_input("e.g. How's our pipeline looking for the energy sector this quarter?"):
        st.session_state.display_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Checking the boards..."):
                answer, updated_history = run_conversation(repo, llm, st.session_state.llm_history, prompt)
            st.markdown(answer)

        st.session_state.llm_history = updated_history
        st.session_state.display_history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
