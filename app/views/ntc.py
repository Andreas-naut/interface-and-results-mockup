"""NTC tab — interconnection capacity to neighbouring countries, by year."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app.model import (
    COUNTRY,
    DIRECTIONS,
    K_NTC,
    YEAR_COLS,
    YEARS,
    default_ntc,
    ntc_long,
    ntc_totals,
)
from app.theme import SERIES

_MAX_SLOTS = len(SERIES)
_TOTAL_SERIES = ["Import", "Export"]


def render() -> None:
    st.subheader("Net transfer capacity")
    st.caption(
        f"One row per border and direction, with a value for each year of the horizon, so a "
        f"reinforcement is entered as a step in the year it comes online. *Import* is capacity "
        f"into {COUNTRY}, *Export* is capacity out of it."
    )

    if st.button("Reset borders", key="reset_ntc"):
        st.session_state[K_NTC] = default_ntc()
        st.rerun()

    year_config = {
        year: st.column_config.NumberColumn(year, min_value=0.0, step=50.0, format="%.0f")
        for year in YEAR_COLS
    }
    edited = st.data_editor(
        st.session_state[K_NTC],
        key="ntc_editor",
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        height=340,
        column_config={
            "Neighbour": st.column_config.TextColumn("Neighbour", required=True, width="medium"),
            "Direction": st.column_config.SelectboxColumn("Direction", options=DIRECTIONS, required=True),
            **year_config,
        },
    )
    st.session_state[K_NTC] = edited
    st.caption("Values in MW. Add a row to open a new border, or a second row to give it the other direction.")

    long = ntc_long()
    long = long[long["Neighbour"].str.strip() != ""]
    if long.empty:
        st.warning("No borders defined. Add a row above to see the buildout.", icon="⚠️")
        return

    _tiles(long)
    st.divider()

    direction = st.radio("Direction", DIRECTIONS, horizontal=True, key="ntc_direction")
    subset = long[long["Direction"] == direction]
    if subset.empty:
        st.info(f"No {direction.lower()} rows yet.", icon="ℹ️")
    else:
        folded, domain = _fold_to_slots(subset)
        st.markdown(f"**{direction} capacity buildout by border**")
        st.altair_chart(
            charts.stacked_bars(folded, "Year", "NTC MW", "Neighbour", domain, y_title="MW", height=340)
        )
        if len(domain) < subset["Neighbour"].nunique():
            st.caption(f"Smaller borders are grouped as *Other* — {_MAX_SLOTS} colours is the readable limit.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Total transfer capacity**")
        st.altair_chart(
            charts.multi_line(_totals_frame(), "Year", "MW", "Series", _TOTAL_SERIES, y_title="MW", fmt=",.0f", height=300)
        )
    with right:
        st.markdown(f"**{direction} capacity per border in {YEARS[-1]}**")
        final = (
            subset[subset["Year"] == YEARS[-1]]
            .groupby("Neighbour", as_index=False)["NTC MW"]
            .sum()
        )
        if final.empty:
            st.caption("Nothing to show for the final year.")
        else:
            st.altair_chart(charts.hbars(final, "Neighbour", "NTC MW", x_title="MW", height=300))

    with st.expander("Buildout table"):
        wide = long.pivot_table(
            index=["Neighbour", "Direction"], columns="Year", values="NTC MW", aggfunc="sum"
        ).fillna(0.0)
        wide.columns = [str(c) for c in wide.columns]
        st.dataframe(wide.reset_index(), hide_index=True, width="stretch")


def _tiles(long: pd.DataFrame) -> None:
    totals = ntc_totals()
    first, last = totals.iloc[0], totals.iloc[-1]
    tiles = st.columns(4, gap="medium")
    tiles[0].metric("Borders", f"{long['Neighbour'].nunique()}")
    tiles[1].metric(
        f"Import capacity {YEARS[-1]}",
        f"{last['Import']:,.0f} MW",
        delta=f"{last['Import'] - first['Import']:,.0f} MW",
    )
    tiles[2].metric(
        f"Export capacity {YEARS[-1]}",
        f"{last['Export']:,.0f} MW",
        delta=f"{last['Export'] - first['Export']:,.0f} MW",
    )
    growth = (last["Import"] / first["Import"] - 1) * 100 if first["Import"] > 0 else 0.0
    tiles[3].metric("Import buildout", f"{growth:+,.0f}%", help=f"{YEARS[0]} to {YEARS[-1]}.")


def _fold_to_slots(subset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Keep the largest borders in their own colour slot; group the tail as Other."""
    ranked = subset.groupby("Neighbour")["NTC MW"].sum().sort_values(ascending=False)
    names = list(ranked.index)
    if len(names) <= _MAX_SLOTS:
        return subset.copy(), names

    kept = names[: _MAX_SLOTS - 1]
    folded = subset.copy()
    folded["Neighbour"] = folded["Neighbour"].where(folded["Neighbour"].isin(kept), "Other")
    folded = folded.groupby(["Year", "Neighbour"], as_index=False)["NTC MW"].sum()
    return folded, [*kept, "Other"]


def _totals_frame() -> pd.DataFrame:
    totals = ntc_totals()
    return pd.concat(
        [
            pd.DataFrame({"Year": totals["Year"], "MW": totals[direction], "Series": direction})
            for direction in _TOTAL_SERIES
        ],
        ignore_index=True,
    )
