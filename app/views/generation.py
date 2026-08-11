"""Generation tab — the editable unit list."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import charts
from app.model import (
    DERATING,
    K_GEN,
    START_YEAR,
    TECHNOLOGIES,
    YEARS,
    apply_hydro_cf,
    default_generation,
    generation_clean,
    sync_hydro_units,
)
from app.widgets import bump_editor_nonce, editor_key

_COLUMNS = ["name", "type", "capacity_factor", "power_mw", "build_year", "marginal_cost"]


def render() -> None:
    st.subheader("Generation fleet")
    st.caption(
        "Add, remove and edit units directly in the table. Hydro capacity factors are greyed out "
        "here — they come from the monthly profiles on the **Hydro** tab, which is the only place "
        "they can be changed."
    )

    if st.button("Reset fleet", key="reset_gen", help="Restore the default unit list."):
        st.session_state[K_GEN] = default_generation()
        sync_hydro_units()
        bump_editor_nonce()
        st.rerun()

    display = apply_hydro_cf(st.session_state[K_GEN])[_COLUMNS]
    edited = st.data_editor(
        display,
        key=editor_key("gen_editor"),
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        height=460,
        column_config={
            "name": st.column_config.TextColumn("Name", required=True, width="medium"),
            "type": st.column_config.SelectboxColumn("Type", options=TECHNOLOGIES, required=True),
            "capacity_factor": st.column_config.NumberColumn(
                "Capacity factor",
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                format="%.3f",
                help="Annual average. Derived from the monthly profile for hydro units.",
            ),
            "power_mw": st.column_config.NumberColumn("Power", min_value=0.0, step=10.0, format="%.0f MW"),
            "build_year": st.column_config.NumberColumn(
                "Build year", min_value=1950, max_value=2100, step=1, format="%d",
                help=f"A unit counts towards a year once its build year has passed. Horizon starts {START_YEAR}.",
            ),
            "marginal_cost": st.column_config.NumberColumn(
                "Marginal cost", min_value=0.0, step=1.0, format="%.1f €/MWh"
            ),
        },
    )

    st.session_state[K_GEN] = edited.copy()
    sync_hydro_units()
    resolved = apply_hydro_cf(st.session_state[K_GEN])
    overridden = _hydro_overrides(edited, resolved)
    st.session_state[K_GEN] = resolved

    if overridden:
        st.info(
            "Capacity factor is not editable for hydro — "
            f"{', '.join(overridden)} kept the value derived from the monthly profiles.",
            icon="💧",
        )

    gen = generation_clean()
    if gen.empty:
        st.warning("No units in the fleet. Add a row above to see the summary.", icon="⚠️")
        return

    _summary_tiles(gen)
    st.divider()

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"**Installed capacity by technology** — units online in {YEARS[-1]}")
        by_tech = (
            gen[gen["build_year"] <= YEARS[-1]]
            .groupby("type", as_index=False)["power_mw"]
            .sum()
            .rename(columns={"type": "Technology", "power_mw": "Capacity MW"})
        )
        st.altair_chart(charts.bars(by_tech, "Technology", "Capacity MW", y_title="MW", height=300))
    with right:
        st.markdown("**Expected annual generation by unit**")
        by_unit = gen.rename(columns={"name": "Unit", "annual_gwh": "Generation GWh"})[["Unit", "Generation GWh"]]
        st.altair_chart(charts.hbars(by_unit, "Unit", "Generation GWh", x_title="GWh", height=max(300, 24 * len(by_unit))))

    with st.expander("Derived figures per unit"):
        table = gen.rename(
            columns={
                "name": "Name",
                "type": "Type",
                "capacity_factor": "Capacity factor",
                "power_mw": "Power MW",
                "build_year": "Build year",
                "marginal_cost": "Marginal cost",
                "annual_gwh": "Annual GWh",
                "firm_mw": "Firm MW",
            }
        )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Capacity factor": st.column_config.NumberColumn(format="%.3f"),
                "Power MW": st.column_config.NumberColumn(format="%.0f"),
                "Build year": st.column_config.NumberColumn(format="%d"),
                "Marginal cost": st.column_config.NumberColumn(format="%.1f"),
                "Annual GWh": st.column_config.NumberColumn(format="%.0f"),
                "Firm MW": st.column_config.NumberColumn(format="%.0f", help="Power × technology derating."),
            },
        )
        st.caption(
            "Derating at system peak — "
            + ", ".join(f"{tech} {share:.0%}" for tech, share in DERATING.items())
            + "."
        )


def _hydro_overrides(edited: pd.DataFrame, resolved: pd.DataFrame) -> list[str]:
    """Names of hydro units whose typed-in capacity factor was replaced."""
    is_hydro = edited["type"] == "Hydro"
    typed = pd.to_numeric(edited.loc[is_hydro, "capacity_factor"], errors="coerce")
    derived = pd.to_numeric(resolved.loc[is_hydro, "capacity_factor"], errors="coerce")
    differs = typed.notna() & derived.notna() & ((typed - derived).abs() > 0.005)
    return [str(n) for n in edited.loc[is_hydro][differs]["name"]]


def _summary_tiles(gen: pd.DataFrame) -> None:
    online_now = gen[gen["build_year"] <= START_YEAR]
    online_end = gen[gen["build_year"] <= YEARS[-1]]
    weighted_cost = (
        (online_end["marginal_cost"] * online_end["annual_gwh"]).sum() / online_end["annual_gwh"].sum()
        if online_end["annual_gwh"].sum() > 0
        else 0.0
    )
    tiles = st.columns(4, gap="medium")
    tiles[0].metric("Units", f"{len(gen)}", delta=f"{len(online_end) - len(online_now)} added over horizon")
    tiles[1].metric(
        f"Capacity {YEARS[-1]}",
        f"{online_end['power_mw'].sum():,.0f} MW",
        delta=f"{online_end['power_mw'].sum() - online_now['power_mw'].sum():,.0f} MW",
    )
    tiles[2].metric(f"Generation {YEARS[-1]}", f"{online_end['annual_gwh'].sum() / 1000:,.1f} TWh")
    tiles[3].metric("Energy-weighted marginal cost", f"{weighted_cost:,.1f} €/MWh")
