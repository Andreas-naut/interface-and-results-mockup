"""Overview tab — the scenario at a glance."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app.model import (
    COUNTRY,
    START_YEAR,
    TECHNOLOGIES,
    YEARS,
    adequacy,
    capacity_by_year,
    generation_clean,
    ntc_totals,
)
from app.theme import STATUS_CRITICAL, STATUS_GOOD, STATUS_WARNING

_ENERGY_SERIES = ["Demand", "Generation capability"]
_POWER_SERIES = ["Peak demand", "Firm capacity + imports"]


def render() -> None:
    st.subheader("Scenario overview")
    st.caption(
        f"{COUNTRY}, {START_YEAR}–{YEARS[-1]}. Every figure here is derived from the other tabs — "
        "edit an assumption there and it lands on this page."
    )

    adq = adequacy()
    first, last = adq.iloc[0], adq.iloc[-1]
    gen = generation_clean()

    _stat_tiles(first, last, gen)
    st.divider()

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Annual energy — demand against fleet capability**")
        st.altair_chart(charts.multi_line(_energy_frame(adq), "Year", "TWh", "Series", _ENERGY_SERIES, y_title="TWh", fmt=",.1f"))
        st.caption("Capability is nameplate × capacity factor × 8760 for every unit online that year.")
    with right:
        st.markdown("**Peak hour — demand against firm capacity**")
        st.altair_chart(charts.multi_line(_power_frame(adq), "Year", "MW", "Series", _POWER_SERIES, y_title="MW", fmt=",.0f"))
        st.caption("Firm capacity applies a technology derating; imports use the yearly NTC total.")

    st.markdown("**Installed capacity by technology**")
    st.altair_chart(
        charts.stacked_bars(
            capacity_by_year(), "Year", "Capacity MW", "Technology", TECHNOLOGIES, y_title="MW", height=340
        )
    )

    st.markdown("**Adequacy summary**")
    st.dataframe(
        adq[["Year", "Demand TWh", "Peak MW", "Load factor %", "Firm MW", "Import MW", "Available MW", "Margin %"]],
        hide_index=True,
        width="stretch",
        column_config={
            "Year": st.column_config.NumberColumn(format="%d"),
            "Demand TWh": st.column_config.NumberColumn(format="%.1f"),
            "Peak MW": st.column_config.NumberColumn(format="%.0f"),
            "Load factor %": st.column_config.NumberColumn(format="%.1f"),
            "Firm MW": st.column_config.NumberColumn(format="%.0f"),
            "Import MW": st.column_config.NumberColumn(format="%.0f"),
            "Available MW": st.column_config.NumberColumn(format="%.0f"),
            "Margin %": st.column_config.NumberColumn(format="%.1f", help="Available capacity over peak demand, minus one."),
        },
    )

    tight = adq[adq["Margin %"] < 10.0]
    if not tight.empty:
        years = ", ".join(str(int(y)) for y in tight["Year"])
        st.warning(f"Capacity margin below 10% in {years}. Add capacity or interconnection to close the gap.", icon="⚠️")
    else:
        st.success("Capacity margin stays above 10% across the horizon.", icon="✅")


def _stat_tiles(first: pd.Series, last: pd.Series, gen: pd.DataFrame) -> None:
    imports = ntc_totals()
    cols = st.columns(5, gap="medium")
    cols[0].metric(
        "Installed capacity",
        f"{last['Installed MW']:,.0f} MW",
        delta=f"{last['Installed MW'] - first['Installed MW']:,.0f} MW",
        help=f"Online in {int(last['Year'])}, against {int(first['Year'])}.",
    )
    cols[1].metric(
        "Annual demand",
        f"{last['Demand TWh']:,.1f} TWh",
        delta=f"{(last['Demand TWh'] / first['Demand TWh'] - 1) * 100:+.1f}%",
    )
    cols[2].metric(
        "Peak demand",
        f"{last['Peak MW']:,.0f} MW",
        delta=f"{last['Peak MW'] - first['Peak MW']:,.0f} MW",
    )
    cols[3].metric(
        "Import capacity",
        f"{imports['Import'].iloc[-1]:,.0f} MW",
        delta=f"{imports['Import'].iloc[-1] - imports['Import'].iloc[0]:,.0f} MW",
    )
    margin = float(last["Margin %"])
    icon, colour = _margin_cue(margin)
    cols[4].metric(f"{icon} Capacity margin", f"{margin:,.1f}%", delta=f"{margin - float(first['Margin %']):+.1f} pp")
    cols[4].markdown(
        f"<span style='color:{colour};font-size:0.78rem'>{_margin_word(margin)} in {int(last['Year'])}</span>",
        unsafe_allow_html=True,
    )
    st.caption(f"{len(gen)} generating units in the fleet across {gen['type'].nunique()} technologies.")


def _margin_cue(margin: float) -> tuple[str, str]:
    if margin < 5.0:
        return "🔴", STATUS_CRITICAL
    if margin < 15.0:
        return "🟠", STATUS_WARNING
    return "🟢", STATUS_GOOD


def _margin_word(margin: float) -> str:
    if margin < 5.0:
        return "Critical"
    return "Tight" if margin < 15.0 else "Adequate"


def _energy_frame(adq: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(
        [
            pd.DataFrame({"Year": adq["Year"], "TWh": adq["Demand TWh"], "Series": _ENERGY_SERIES[0]}),
            pd.DataFrame({"Year": adq["Year"], "TWh": adq["Generation TWh"], "Series": _ENERGY_SERIES[1]}),
        ],
        ignore_index=True,
    )


def _power_frame(adq: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(
        [
            pd.DataFrame({"Year": adq["Year"], "MW": adq["Peak MW"], "Series": _POWER_SERIES[0]}),
            pd.DataFrame({"Year": adq["Year"], "MW": adq["Available MW"], "Series": _POWER_SERIES[1]}),
        ],
        ignore_index=True,
    )
