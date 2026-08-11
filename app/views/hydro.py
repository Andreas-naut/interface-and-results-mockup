"""Hydro tab — monthly capacity factors per hydro unit."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app import charts
from app.model import (
    DAYS_IN_MONTH,
    K_HYDRO,
    MONTHS,
    default_hydro_monthly,
    generation_clean,
    hydro_annual_cf,
    hydro_units,
    sync_hydro_units,
)
from app.theme import SERIES
from app.widgets import bump_editor_nonce, editor_key

_MAX_LINES = len(SERIES)


def render() -> None:
    st.subheader("Hydro monthly capacity factors")
    st.caption(
        "The seasonal shape of each hydro unit. The energy-weighted annual mean of each row is "
        "what the **Generation** tab shows as that unit's capacity factor — this table is the only "
        "place it can be set."
    )

    sync_hydro_units()
    units = hydro_units()
    if not units:
        st.info("No units of type *Hydro* in the fleet. Add one on the Generation tab.", icon="💧")
        return

    if st.button("Reset profiles", key="reset_hydro"):
        st.session_state[K_HYDRO] = default_hydro_monthly(units)
        bump_editor_nonce()
        st.rerun()

    month_config = {
        month: st.column_config.NumberColumn(month, min_value=0.0, max_value=1.0, step=0.01, format="%.2f")
        for month in MONTHS
    }
    edited = st.data_editor(
        st.session_state[K_HYDRO],
        key=editor_key("hydro_editor"),
        hide_index=True,
        width="stretch",
        column_config={
            "Unit": st.column_config.TextColumn(
                "Unit", disabled=True, width="medium", help="Managed on the Generation tab."
            ),
            **month_config,
        },
    )
    st.session_state[K_HYDRO] = edited

    annual = hydro_annual_cf()
    long = _long_form(edited)

    tiles = st.columns(min(4, len(units)), gap="medium")
    for i, unit in enumerate(units[: len(tiles)]):
        tiles[i].metric(unit, f"{annual.get(unit, 0.0):.3f}", help="Energy-weighted annual capacity factor.")

    st.divider()

    st.markdown("**Monthly shape by unit**")
    if len(units) <= _MAX_LINES:
        shown = st.multiselect("Units", units, default=units, key="hydro_units_shown")
        subset = long[long["Unit"].isin(shown)] if shown else long
        st.altair_chart(
            charts.multi_line(
                subset, "Month", "Capacity factor", "Unit", units,
                y_title="Capacity factor", x_title="Month", fmt=",.2f", height=320,
            )
        )
    else:
        st.caption(f"{len(units)} hydro units — shown as a grid rather than {len(units)} overlapping lines.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Capacity factor grid**")
        st.altair_chart(
            charts.heatmap(
                long, "Month", "Unit", "Capacity factor",
                x_order=MONTHS, y_order=units, height=max(180, 46 * len(units)),
            )
        )
    with right:
        st.markdown("**Hydro fleet energy by month**")
        st.altair_chart(charts.bars(_fleet_energy(edited), "Month", "Energy GWh", y_title="GWh", sort=MONTHS, fmt=",.0f", height=max(180, 46 * len(units))))

    _fleet_summary(edited, annual)


def _long_form(monthly: pd.DataFrame) -> pd.DataFrame:
    long = monthly.melt(id_vars=["Unit"], value_vars=MONTHS, var_name="Month", value_name="Capacity factor")
    long["Unit"] = long["Unit"].astype(str)
    long["Capacity factor"] = pd.to_numeric(long["Capacity factor"], errors="coerce").fillna(0.0)
    return long


def _unit_power() -> dict[str, float]:
    gen = generation_clean()
    hydro = gen[gen["type"] == "Hydro"]
    return dict(zip(hydro["name"].astype(str), hydro["power_mw"].astype(float), strict=True))


def _fleet_energy(monthly: pd.DataFrame) -> pd.DataFrame:
    """Monthly hydro energy across the fleet, in GWh."""
    power = _unit_power()
    hours = np.array(DAYS_IN_MONTH, dtype=float) * 24.0
    totals = np.zeros(12)
    for _, row in monthly.iterrows():
        factors = pd.to_numeric(row[MONTHS], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        totals += factors * power.get(str(row["Unit"]), 0.0) * hours / 1000.0
    return pd.DataFrame({"Month": MONTHS, "Energy GWh": totals})


def _fleet_summary(monthly: pd.DataFrame, annual: dict[str, float]) -> None:
    power = _unit_power()
    energy = _fleet_energy(monthly)
    rows = []
    hours_total = float(np.array(DAYS_IN_MONTH, dtype=float).sum() * 24.0)
    for _, row in monthly.iterrows():
        unit = str(row["Unit"])
        factors = pd.to_numeric(row[MONTHS], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        capacity = power.get(unit, 0.0)
        rows.append(
            {
                "Unit": unit,
                "Power MW": capacity,
                "Annual CF": annual.get(unit, 0.0),
                "Annual GWh": annual.get(unit, 0.0) * capacity * hours_total / 1000.0,
                "Min month": MONTHS[int(np.argmin(factors))],
                "Max month": MONTHS[int(np.argmax(factors))],
            }
        )
    with st.expander("Per-unit summary"):
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
            column_config={
                "Power MW": st.column_config.NumberColumn(format="%.0f"),
                "Annual CF": st.column_config.NumberColumn(format="%.3f"),
                "Annual GWh": st.column_config.NumberColumn(format="%.0f"),
            },
        )
    st.caption(
        f"Fleet hydro energy {energy['Energy GWh'].sum() / 1000:,.2f} TWh a year, "
        f"peaking in {energy.loc[energy['Energy GWh'].idxmax(), 'Month']}."
    )
