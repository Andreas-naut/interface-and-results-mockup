"""Load tab — annual projection, monthly seasonality and the daily shape."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app import charts
from app.model import (
    BASE_DEMAND_TWH,
    DAYS_IN_MONTH,
    K_DAILY,
    K_DEMAND,
    K_SEASON,
    MONTHS,
    START_YEAR,
    YEARS,
    current_daily_shape,
    default_daily,
    default_demand,
    default_seasonality,
    demand_projection,
    seasonal_shares,
)
from app.widgets import bump_editor_nonce, editor_key


def render() -> None:
    _annual_section()
    st.divider()
    _seasonality_section()
    st.divider()
    _daily_section()


# --------------------------------------------------------------------------- #
# 10-year projection
# --------------------------------------------------------------------------- #
def _annual_section() -> None:
    st.subheader("Annual load projection")
    st.caption(
        f"Growth compounds off {BASE_DEMAND_TWH:,.0f} TWh in {START_YEAR}. Edit any year's rate "
        "directly, or seed the whole horizon from one growth rate."
    )

    controls, chart_area = st.columns([1, 2.4], gap="large")

    with controls:
        seed = st.slider("Seed growth rate", 0.0, 6.0, 2.0, 0.1, format="%.1f%%", key=editor_key("load_seed"))
        button_cols = st.columns(2)
        if button_cols[0].button("Apply to all", width="stretch", help=f"Set {START_YEAR + 1} onward to the seed rate."):
            df = st.session_state[K_DEMAND].copy()
            df["Growth %"] = [0.0] + [seed] * (len(YEARS) - 1)
            st.session_state[K_DEMAND] = df
            bump_editor_nonce()
            st.rerun()
        if button_cols[1].button("Reset", width="stretch", key="reset_demand"):
            st.session_state[K_DEMAND] = default_demand()
            bump_editor_nonce()
            st.rerun()

        edited = st.data_editor(
            st.session_state[K_DEMAND],
            key=editor_key("demand_editor"),
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "Year": st.column_config.NumberColumn("Year", format="%d", disabled=True),
                "Growth %": st.column_config.NumberColumn(
                    "Growth %", min_value=-10.0, max_value=15.0, step=0.1, format="%.1f"
                ),
            },
        )
        st.session_state[K_DEMAND] = edited

    projection = demand_projection()
    with chart_area:
        st.altair_chart(charts.line(projection, "Year", "Demand TWh", y_title="TWh", fmt=",.2f", height=250))
        st.altair_chart(charts.line(projection, "Year", "Peak MW", y_title="MW", fmt=",.0f", height=190))
        st.caption(
            "Peak follows from the monthly and daily shapes below — change either and this "
            "curve moves without the energy projection changing."
        )

    cagr = (projection["Demand TWh"].iloc[-1] / projection["Demand TWh"].iloc[0]) ** (1 / (len(YEARS) - 1)) - 1
    tiles = st.columns(4, gap="medium")
    tiles[0].metric(f"Demand {YEARS[-1]}", f"{projection['Demand TWh'].iloc[-1]:,.1f} TWh")
    tiles[1].metric("Implied CAGR", f"{cagr * 100:,.2f}%")
    tiles[2].metric(f"Peak {YEARS[-1]}", f"{projection['Peak MW'].iloc[-1]:,.0f} MW")
    tiles[3].metric("Load factor", f"{projection['Load factor %'].iloc[-1]:,.1f}%")


# --------------------------------------------------------------------------- #
# Monthly seasonality
# --------------------------------------------------------------------------- #
def _seasonality_section() -> None:
    st.subheader("Monthly seasonality")
    st.caption(
        "Relative factors, renormalised on use and weighted by month length, so only the shape "
        "matters — the annual total always ties back to the projection above."
    )

    year = st.selectbox("Show energy for", YEARS, index=len(YEARS) - 1, key="season_year")
    projection = demand_projection()
    annual_twh = float(projection.loc[projection["Year"] == year, "Demand TWh"].iloc[0])

    controls, chart_area = st.columns([1, 2.4], gap="large")
    with controls:
        if st.button("Reset seasonality", width="stretch", key="reset_season"):
            st.session_state[K_SEASON] = default_seasonality()
            bump_editor_nonce()
            st.rerun()
        edited = st.data_editor(
            st.session_state[K_SEASON],
            key=editor_key("season_editor"),
            hide_index=True,
            width="stretch",
            height=460,
            column_config={
                "Month": st.column_config.TextColumn("Month", disabled=True),
                "Factor": st.column_config.NumberColumn(
                    "Factor", min_value=0.0, max_value=3.0, step=0.01, format="%.2f"
                ),
            },
        )
        st.session_state[K_SEASON] = edited

    shares = seasonal_shares()
    monthly = pd.DataFrame(
        {
            "Month": MONTHS,
            "Energy TWh": annual_twh * shares,
            "Share %": shares * 100.0,
            "Average MW": annual_twh * 1e6 * shares / (np.array(DAYS_IN_MONTH, dtype=float) * 24.0),
        }
    )

    with chart_area:
        st.altair_chart(
            charts.bars(
                monthly, "Month", "Energy TWh", y_title=f"TWh in {year}", sort=MONTHS, fmt=",.2f", height=300
            )
        )
        peak_month = MONTHS[int(np.argmax(shares))]
        low_month = MONTHS[int(np.argmin(shares))]
        st.caption(
            f"Heaviest month {peak_month} at {shares.max() * 100:,.1f}% of the year, "
            f"lightest {low_month} at {shares.min() * 100:,.1f}%."
        )
        with st.expander("Monthly table"):
            st.dataframe(
                monthly,
                hide_index=True,
                width="stretch",
                column_config={
                    "Energy TWh": st.column_config.NumberColumn(format="%.2f"),
                    "Share %": st.column_config.NumberColumn(format="%.2f"),
                    "Average MW": st.column_config.NumberColumn(format="%.0f"),
                },
            )


# --------------------------------------------------------------------------- #
# Daily profile
# --------------------------------------------------------------------------- #
def _daily_section() -> None:
    st.subheader("Daily load profile")
    st.caption(
        "Three anchors — a night trough at 03:00, a midday level at 12:00 and the evening peak — "
        "joined with cosine easing and wrapped across midnight. The shape is renormalised to a "
        "mean of 1.0, so moving a level redistributes energy within the day rather than adding it."
    )

    params = st.session_state[K_DAILY]
    controls, chart_area = st.columns([1, 2.4], gap="large")

    with controls:
        night = st.slider("Night level (03:00)", 0.30, 1.00, float(params["night"]), 0.01, key=editor_key("night"))
        noon = st.slider("Noon level (12:00)", 0.50, 1.40, float(params["noon"]), 0.01, key=editor_key("noon"))
        peak = st.slider("Peak level", 0.80, 2.00, float(params["peak"]), 0.01, key=editor_key("peak"))
        peak_hour = st.number_input(
            "Peak hour", min_value=0, max_value=23, value=int(params["peak_hour"]), step=1,
            help="Evening peak hour. 19:00 by default.", key=editor_key("peak_hour"),
        )
        st.session_state[K_DAILY] = {"night": night, "noon": noon, "peak": peak, "peak_hour": int(peak_hour)}
        if st.button("Reset profile", width="stretch", key="reset_daily"):
            st.session_state[K_DAILY] = default_daily()
            bump_editor_nonce()
            st.rerun()

    shape = current_daily_shape()
    year = st.session_state.get("season_year", YEARS[-1])
    projection = demand_projection()
    annual_twh = float(projection.loc[projection["Year"] == year, "Demand TWh"].iloc[0])
    shares = seasonal_shares()
    month_index = int(np.argmax(shares))
    average_mw = annual_twh * 1e6 * shares[month_index] / (DAYS_IN_MONTH[month_index] * 24.0)

    hourly = pd.DataFrame(
        {
            "Hour": [f"{h:02d}" for h in range(24)],
            "Shape": shape,
            "MW": shape * average_mw,
        }
    )

    with chart_area:
        st.altair_chart(
            charts.line(
                hourly, "Hour", "MW", y_title="MW", x_title="Hour of day", fmt=",.0f", height=300,
            )
        )
        st.caption(
            f"Peak day in {MONTHS[month_index]} {year}: {hourly['MW'].max():,.0f} MW at "
            f"{int(np.argmax(shape)):02d}:00, trough {hourly['MW'].min():,.0f} MW at "
            f"{int(np.argmin(shape)):02d}:00 — peak-to-trough ratio {shape.max() / max(shape.min(), 1e-9):,.2f}."
        )
        with st.expander("Hourly table"):
            st.dataframe(
                hourly,
                hide_index=True,
                width="stretch",
                column_config={
                    "Shape": st.column_config.NumberColumn(format="%.3f"),
                    "MW": st.column_config.NumberColumn(format="%.0f"),
                },
            )
