"""Ardania power system model — interface and results mockup.

Run with:  uv run streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from app import views
from app.auth import USERNAME, login_gate, logout
from app.model import COUNTRY, START_YEAR, YEARS, init_state, reset_scenario
from app.widgets import bump_editor_nonce

st.set_page_config(
    page_title=f"{COUNTRY} — Power System Model",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

login_gate()
init_state()

TABS = [
    ("Overview", views.overview),
    ("Load", views.load),
    ("Generation", views.generation),
    ("Hydro", views.hydro),
    ("NTC", views.ntc),
]


def sidebar() -> None:
    with st.sidebar:
        st.markdown(f"### ⚡ {COUNTRY}")
        st.caption(f"Signed in as `{USERNAME}`")
        st.divider()
        st.markdown("**Scenario**")
        st.caption(f"Horizon {START_YEAR}–{YEARS[-1]} ({len(YEARS)} years)")
        st.caption("Every tab edits one shared scenario held in the session — nothing is persisted.")
        if st.button("Reset all assumptions", width="stretch"):
            reset_scenario()
            bump_editor_nonce()
            st.rerun()
        st.divider()
        if st.button("Sign out", width="stretch"):
            logout()
        st.caption("Mockup — figures are illustrative, not a validated study.")


sidebar()

st.title(f"{COUNTRY} — Power System Model")
for tab, (label, module) in zip(st.tabs([label for label, _ in TABS]), TABS, strict=True):
    with tab:
        module.render()
