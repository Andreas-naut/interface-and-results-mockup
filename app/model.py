"""Scenario data model: defaults, session-state wiring and derived quantities.

Everything the tabs edit lives in ``st.session_state`` under the keys defined
here, so each tab reads the same single source of truth and edits made in one
tab show up in the others (hydro monthly profiles feed the generation table's
capacity factors, the generation table drives the overview, and so on).
"""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd
import streamlit as st

COUNTRY = "Ardania"

START_YEAR = 2026
HORIZON = 10
YEARS: list[int] = list(range(START_YEAR, START_YEAR + HORIZON))
YEAR_COLS: list[str] = [str(y) for y in YEARS]

MONTHS: list[str] = list(calendar.month_abbr)[1:]
DAYS_IN_MONTH: list[int] = [calendar.monthrange(2027, m)[1] for m in range(1, 13)]  # non-leap

# Fixed order -> fixed colour slots. Hydro sits first so its slot never moves.
TECHNOLOGIES: list[str] = ["Hydro", "Nuclear", "Coal", "Gas", "Wind", "Solar", "Biomass"]

#: Share of nameplate capacity counted as firm at system peak.
DERATING: dict[str, float] = {
    "Nuclear": 0.90,
    "Coal": 0.88,
    "Gas": 0.92,
    "Biomass": 0.85,
    "Hydro": 0.50,
    "Wind": 0.10,
    "Solar": 0.05,
}

NEIGHBOURS: list[str] = ["Valoria", "Norhavn", "Estmark", "Sudramar"]
DIRECTIONS: list[str] = ["Import", "Export"]

# Session-state keys.
K_AUTH = "authenticated"
K_DEMAND = "demand_df"
K_SEASON = "seasonality_df"
K_DAILY = "daily_params"
K_GEN = "generation_df"
K_HYDRO = "hydro_monthly_df"
K_NTC = "ntc_df"


# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #
BASE_DEMAND_TWH = 42.0


def default_demand() -> pd.DataFrame:
    """One row per projection year: an editable annual growth rate."""
    growth = [0.0, 1.8, 1.9, 2.1, 2.4, 2.6, 2.5, 2.2, 2.0, 1.8]
    return pd.DataFrame({"Year": YEARS, "Growth %": growth})


def default_seasonality() -> pd.DataFrame:
    factors = [1.18, 1.12, 1.05, 0.95, 0.88, 0.83, 0.82, 0.84, 0.92, 1.02, 1.10, 1.16]
    return pd.DataFrame({"Month": MONTHS, "Factor": factors})


def default_daily() -> dict[str, float | int]:
    return {"night": 0.72, "noon": 1.00, "peak": 1.28, "peak_hour": 19}


def default_generation() -> pd.DataFrame:
    rows = [
        ("Aurelia NPP 1", "Nuclear", 0.90, 1100.0, 2026, 12.0),
        ("Aurelia NPP 2", "Nuclear", 0.88, 1100.0, 2031, 12.0),
        ("Dunmoor Coal", "Coal", 0.55, 600.0, 2026, 96.0),
        ("Vantis CCGT", "Gas", 0.45, 850.0, 2026, 78.0),
        ("Kettle Bay OCGT", "Gas", 0.08, 320.0, 2028, 132.0),
        ("Highfell Hydro", "Hydro", np.nan, 480.0, 2026, 2.0),
        ("Silverbeck Hydro", "Hydro", np.nan, 260.0, 2026, 2.0),
        ("Tarnmouth Hydro", "Hydro", np.nan, 150.0, 2029, 3.0),
        ("Brackmere Wind", "Wind", 0.31, 420.0, 2027, 0.0),
        ("North Shoal Wind", "Wind", 0.48, 900.0, 2030, 0.0),
        ("Sunmere Solar", "Solar", 0.15, 550.0, 2028, 0.0),
        ("Eastfield Solar", "Solar", 0.14, 300.0, 2032, 0.0),
        ("Wyeburn Biomass", "Biomass", 0.62, 180.0, 2026, 71.0),
    ]
    return pd.DataFrame(
        rows,
        columns=["name", "type", "capacity_factor", "power_mw", "build_year", "marginal_cost"],
    )


#: Monthly capacity factors for the hydro fleet — a snowmelt-driven reservoir,
#: a rain-driven run-of-river plant, and a smaller alpine scheme.
HYDRO_PROFILES: dict[str, list[float]] = {
    "Highfell Hydro": [0.28, 0.26, 0.32, 0.55, 0.78, 0.82, 0.66, 0.48, 0.40, 0.38, 0.34, 0.30],
    "Silverbeck Hydro": [0.52, 0.50, 0.55, 0.58, 0.60, 0.48, 0.34, 0.28, 0.33, 0.46, 0.55, 0.54],
    "Tarnmouth Hydro": [0.38, 0.35, 0.40, 0.50, 0.62, 0.58, 0.44, 0.32, 0.30, 0.35, 0.40, 0.39],
}
GENERIC_HYDRO_PROFILE: list[float] = [
    0.40, 0.38, 0.42, 0.52, 0.64, 0.60, 0.46, 0.34, 0.33, 0.38, 0.42, 0.41,
]


def default_hydro_monthly(units: list[str] | None = None) -> pd.DataFrame:
    units = units or list(HYDRO_PROFILES)
    data = {"Unit": units}
    for i, month in enumerate(MONTHS):
        data[month] = [HYDRO_PROFILES.get(u, GENERIC_HYDRO_PROFILE)[i] for u in units]
    return pd.DataFrame(data)


def default_ntc() -> pd.DataFrame:
    """MW per year and direction. Steps mark commissioning of new circuits."""
    plans: dict[str, dict[str, list[float]]] = {
        "Valoria": {
            "Import": [1200, 1200, 1200, 1600, 1600, 1600, 2000, 2000, 2000, 2000],
            "Export": [1000, 1000, 1000, 1400, 1400, 1400, 1800, 1800, 1800, 1800],
        },
        "Norhavn": {
            "Import": [700, 700, 700, 700, 1400, 1400, 1400, 1400, 1400, 1400],
            "Export": [700, 700, 700, 700, 1400, 1400, 1400, 1400, 1400, 1400],
        },
        "Estmark": {
            "Import": [450, 450, 450, 450, 450, 900, 900, 900, 900, 900],
            "Export": [400, 400, 400, 400, 400, 800, 800, 800, 800, 800],
        },
        "Sudramar": {
            "Import": [300, 300, 300, 300, 300, 300, 300, 600, 600, 600],
            "Export": [250, 250, 250, 250, 250, 250, 250, 500, 500, 500],
        },
    }
    rows = []
    for neighbour in NEIGHBOURS:
        for direction in DIRECTIONS:
            row = {"Neighbour": neighbour, "Direction": direction}
            row.update(dict(zip(YEAR_COLS, plans[neighbour][direction], strict=True)))
            rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
def init_state() -> None:
    """Seed any missing scenario data. Safe to call on every rerun."""
    defaults = {
        K_DEMAND: default_demand,
        K_SEASON: default_seasonality,
        K_DAILY: default_daily,
        K_GEN: default_generation,
        K_HYDRO: default_hydro_monthly,
        K_NTC: default_ntc,
    }
    for key, factory in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = factory()
    sync_hydro_units()


def reset_scenario() -> None:
    for key in (K_DEMAND, K_SEASON, K_DAILY, K_GEN, K_HYDRO, K_NTC):
        st.session_state.pop(key, None)
    init_state()


def hydro_units() -> list[str]:
    gen = st.session_state[K_GEN]
    names = gen.loc[gen["type"] == "Hydro", "name"].dropna().astype(str)
    return [n for n in names if n.strip()]


def sync_hydro_units() -> None:
    """Keep the monthly hydro table in step with the generation table.

    Units added as ``Hydro`` in the generation tab get a starter profile here;
    units renamed or retyped drop out. Existing edits are preserved.
    """
    units = hydro_units()
    monthly: pd.DataFrame = st.session_state[K_HYDRO]
    known = dict(zip(monthly["Unit"].astype(str), range(len(monthly)), strict=True))

    rows = []
    for unit in units:
        if unit in known:
            rows.append(monthly.iloc[known[unit]])
        else:
            profile = HYDRO_PROFILES.get(unit, GENERIC_HYDRO_PROFILE)
            rows.append(pd.Series({"Unit": unit, **dict(zip(MONTHS, profile, strict=True))}))

    columns = ["Unit", *MONTHS]
    updated = pd.DataFrame(rows, columns=columns).reset_index(drop=True) if rows else pd.DataFrame(columns=columns)
    st.session_state[K_HYDRO] = updated


def hydro_annual_cf() -> dict[str, float]:
    """Energy-weighted annual capacity factor per hydro unit."""
    monthly: pd.DataFrame = st.session_state[K_HYDRO]
    weights = np.array(DAYS_IN_MONTH, dtype=float)
    weights /= weights.sum()
    out: dict[str, float] = {}
    for _, row in monthly.iterrows():
        values = pd.to_numeric(row[MONTHS], errors="coerce").to_numpy(dtype=float)
        values = np.nan_to_num(values, nan=0.0)
        out[str(row["Unit"])] = float((values * weights).sum())
    return out


def apply_hydro_cf(gen: pd.DataFrame) -> pd.DataFrame:
    """Overwrite hydro capacity factors with the value derived from the monthly
    profiles. That column is not the user's to edit for hydro."""
    gen = gen.copy()
    annual = hydro_annual_cf()
    is_hydro = gen["type"] == "Hydro"
    gen.loc[is_hydro, "capacity_factor"] = (
        gen.loc[is_hydro, "name"].astype(str).map(annual).astype(float)
    )
    return gen


# --------------------------------------------------------------------------- #
# Derived quantities
# --------------------------------------------------------------------------- #
def annual_demand() -> pd.DataFrame:
    """Compound the per-year growth rates into an annual energy projection."""
    df = st.session_state[K_DEMAND].copy()
    growth = pd.to_numeric(df["Growth %"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    factors = np.cumprod(1.0 + growth / 100.0)
    return pd.DataFrame({"Year": df["Year"].astype(int), "Demand TWh": BASE_DEMAND_TWH * factors})


def seasonal_shares() -> np.ndarray:
    """Month shares of annual energy, weighted by month length. Sums to 1."""
    factors = pd.to_numeric(st.session_state[K_SEASON]["Factor"], errors="coerce")
    factors = factors.fillna(0.0).to_numpy(dtype=float)
    weighted = np.clip(factors, 0.0, None) * np.array(DAYS_IN_MONTH, dtype=float)
    total = weighted.sum()
    if total <= 0:
        weighted = np.array(DAYS_IN_MONTH, dtype=float)
        total = weighted.sum()
    return weighted / total


def daily_shape(
    night: float, noon: float, peak: float, peak_hour: int, night_hour: int = 3, noon_hour: int = 12
) -> np.ndarray:
    """A 24-value shape through the three anchor levels, normalised to mean 1.

    Anchors are joined with cosine easing and wrap around midnight, so the
    curve is smooth and continuous at every hour.
    """
    anchors = sorted({int(night_hour): night, int(noon_hour): noon, int(peak_hour) % 24: peak}.items())
    values = np.zeros(24, dtype=float)
    count = len(anchors)
    for i in range(count):
        h0, v0 = anchors[i]
        h1, v1 = anchors[(i + 1) % count]
        span = (h1 - h0) % 24 or 24
        for step in range(span + 1):
            ease = 0.5 - 0.5 * np.cos(np.pi * step / span)
            values[(h0 + step) % 24] = v0 + (v1 - v0) * ease
    mean = values.mean()
    return values / mean if mean > 0 else np.ones(24)


def current_daily_shape() -> np.ndarray:
    p = st.session_state[K_DAILY]
    return daily_shape(p["night"], p["noon"], p["peak"], int(p["peak_hour"]))


def peak_demand_mw(year_demand_twh: float) -> float:
    """System peak = the highest hour of the highest month."""
    shares = seasonal_shares()
    shape = current_daily_shape()
    monthly_mwh = year_demand_twh * 1e6 * shares
    hours = np.array(DAYS_IN_MONTH, dtype=float) * 24.0
    return float((monthly_mwh / hours).max() * shape.max())


def demand_projection() -> pd.DataFrame:
    """Annual energy plus the peak and load factor implied by the shapes."""
    df = annual_demand()
    df["Peak MW"] = [peak_demand_mw(v) for v in df["Demand TWh"]]
    df["Load factor %"] = np.where(
        df["Peak MW"] > 0, df["Demand TWh"] * 1e6 / (8760.0 * df["Peak MW"]) * 100.0, 0.0
    )
    return df


def generation_clean() -> pd.DataFrame:
    """The generation table, hydro capacity factors resolved and types coerced."""
    gen = apply_hydro_cf(st.session_state[K_GEN])
    gen = gen[gen["name"].notna() & (gen["name"].astype(str).str.strip() != "")].copy()
    gen["type"] = gen["type"].where(gen["type"].isin(TECHNOLOGIES), "Gas")
    for col, fill in (("capacity_factor", 0.0), ("power_mw", 0.0), ("marginal_cost", 0.0)):
        gen[col] = pd.to_numeric(gen[col], errors="coerce").fillna(fill)
    gen["build_year"] = (
        pd.to_numeric(gen["build_year"], errors="coerce").fillna(START_YEAR).astype(int)
    )
    gen["annual_gwh"] = gen["power_mw"] * gen["capacity_factor"] * 8760 / 1000.0
    gen["firm_mw"] = gen["power_mw"] * gen["type"].map(DERATING).fillna(0.5)
    return gen


def capacity_by_year() -> pd.DataFrame:
    """Long-format cumulative capacity per technology and year (online units)."""
    gen = generation_clean()
    rows = []
    for year in YEARS:
        online = gen[gen["build_year"] <= year]
        by_type = online.groupby("type")["power_mw"].sum()
        for tech in TECHNOLOGIES:
            rows.append({"Year": year, "Technology": tech, "Capacity MW": float(by_type.get(tech, 0.0))})
    return pd.DataFrame(rows)


def supply_projection() -> pd.DataFrame:
    """Annual generation capability and firm capacity of the online fleet."""
    gen = generation_clean()
    rows = []
    for year in YEARS:
        online = gen[gen["build_year"] <= year]
        rows.append(
            {
                "Year": year,
                "Generation TWh": float(online["annual_gwh"].sum()) / 1000.0,
                "Firm MW": float(online["firm_mw"].sum()),
                "Installed MW": float(online["power_mw"].sum()),
            }
        )
    return pd.DataFrame(rows)


def ntc_long() -> pd.DataFrame:
    """NTC table melted to one row per neighbour, direction and year."""
    df: pd.DataFrame = st.session_state[K_NTC].copy()
    present = [c for c in YEAR_COLS if c in df.columns]
    long = df.melt(
        id_vars=["Neighbour", "Direction"],
        value_vars=present,
        var_name="Year",
        value_name="NTC MW",
    )
    long["Year"] = long["Year"].astype(int)
    long["NTC MW"] = pd.to_numeric(long["NTC MW"], errors="coerce").fillna(0.0)
    long["Neighbour"] = long["Neighbour"].astype(str)
    return long


def ntc_totals() -> pd.DataFrame:
    """Total import and export capability per year."""
    long = ntc_long()
    wide = long.pivot_table(
        index="Year", columns="Direction", values="NTC MW", aggfunc="sum", fill_value=0.0
    )
    for direction in DIRECTIONS:
        if direction not in wide.columns:
            wide[direction] = 0.0
    return wide.reset_index()[["Year", *DIRECTIONS]]


def adequacy() -> pd.DataFrame:
    """Firm capacity plus imports against peak demand, per year."""
    demand = demand_projection()
    supply = supply_projection()
    imports = ntc_totals()[["Year", "Import"]].rename(columns={"Import": "Import MW"})
    df = demand.merge(supply, on="Year").merge(imports, on="Year")
    df["Available MW"] = df["Firm MW"] + df["Import MW"]
    df["Margin %"] = np.where(
        df["Peak MW"] > 0, (df["Available MW"] / df["Peak MW"] - 1.0) * 100.0, 0.0
    )
    return df
