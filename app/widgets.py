"""Small widget helpers.

``st.data_editor`` keeps its pending edits under its own widget key, so writing
new data into ``st.session_state`` behind a live editor lets the stale edits
reapply on the next rerun. Every editor and slider therefore takes its key from
``editor_key``, and any code that replaces scenario data programmatically calls
``bump_editor_nonce`` to hand the widgets a fresh identity.
"""

from __future__ import annotations

import streamlit as st

K_NONCE = "editor_nonce"


def editor_key(base: str) -> str:
    return f"{base}__{st.session_state.get(K_NONCE, 0)}"


def bump_editor_nonce() -> None:
    st.session_state[K_NONCE] = st.session_state.get(K_NONCE, 0) + 1
