"""Mockup login gate.

Deliberately not secure: the single credential pair is hard-coded in the clear
and compared in plain Python. It exists to shape the UI, not to protect
anything. Replace with a real identity provider before this holds real data.
"""

from __future__ import annotations

import streamlit as st

from app.model import COUNTRY, K_AUTH

USERNAME = "country"
PASSWORD = "country"


def login_gate() -> None:
    """Render the login form and halt the script until the user signs in."""
    if st.session_state.get(K_AUTH):
        return

    st.title(f"{COUNTRY} — Power System Model")
    st.caption("Sign in to open the scenario workspace.")

    _, middle, _ = st.columns([1, 1.4, 1])
    with middle:
        with st.form("login", border=True):
            user = st.text_input("User", placeholder="country")
            password = st.text_input("Password", type="password", placeholder="country")
            if st.form_submit_button("Sign in", width="stretch", type="primary"):
                if user.strip() == USERNAME and password == PASSWORD:
                    st.session_state[K_AUTH] = True
                    st.rerun()
                else:
                    st.error("Wrong user or password.")
        st.caption("Mockup credentials: `country` / `country` — no real authentication.")

    st.stop()


def logout() -> None:
    st.session_state[K_AUTH] = False
    st.rerun()
