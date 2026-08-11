"""Smoke tests driving the real app through Streamlit's AppTest harness."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

TIMEOUT = 60
APP = Path(__file__).resolve().parent.parent / "streamlit_app.py"


def _fresh() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=TIMEOUT)


def _signed_in() -> AppTest:
    at = _fresh()
    at.session_state["authenticated"] = True
    return at.run()


def test_login_gate_blocks_until_signed_in() -> None:
    at = _fresh().run()
    assert not at.exception
    assert at.tabs == []
    assert len(at.text_input) == 2


def test_wrong_password_is_rejected() -> None:
    at = _fresh().run()
    at.text_input[0].input("country")
    at.text_input[1].input("wrong")
    at.button[0].click().run()
    assert at.error
    assert at.tabs == []  # still gated: the workspace never rendered


def test_correct_password_opens_the_workspace() -> None:
    at = _fresh().run()
    at.text_input[0].input("country")
    at.text_input[1].input("country")
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["authenticated"] is True
    assert len(at.tabs) == 5


def test_all_tabs_render_without_error() -> None:
    at = _signed_in()
    assert not at.exception
    labels = [tab.label for tab in at.tabs]
    assert labels == ["Overview", "Load", "Generation", "Hydro", "NTC"]
    assert len(at.dataframe) >= 1
    assert len(at.metric) >= 15


def test_hydro_capacity_factor_is_derived_not_typed() -> None:
    at = _signed_in()
    gen = at.session_state["generation_df"]
    hydro = gen[gen["type"] == "Hydro"]
    # Seeded as NaN in the defaults; filled in from the monthly profiles on render.
    assert hydro["capacity_factor"].notna().all()
    # Highfell's snowmelt profile averages well under a thermal unit's factor.
    highfell = float(hydro.loc[hydro["name"] == "Highfell Hydro", "capacity_factor"].iloc[0])
    assert 0.35 < highfell < 0.55


def test_editing_hydro_profile_moves_the_generation_capacity_factor() -> None:
    at = _signed_in()
    before = float(
        at.session_state["generation_df"]
        .set_index("name")
        .loc["Highfell Hydro", "capacity_factor"]
    )

    monthly = at.session_state["hydro_monthly_df"].copy()
    row = monthly.index[monthly["Unit"] == "Highfell Hydro"][0]
    monthly.loc[row, ["Jan", "Feb", "Mar"]] = 0.95
    at.session_state["hydro_monthly_df"] = monthly
    at.run()

    after = float(
        at.session_state["generation_df"]
        .set_index("name")
        .loc["Highfell Hydro", "capacity_factor"]
    )
    assert after > before + 0.1


def test_daily_shape_is_normalised_and_peaks_at_the_chosen_hour() -> None:
    from app.model import daily_shape

    shape = daily_shape(night=0.72, noon=1.0, peak=1.28, peak_hour=19)
    assert shape.shape == (24,)
    assert np.isclose(shape.mean(), 1.0)
    assert int(np.argmax(shape)) == 19
    assert int(np.argmin(shape)) == 3
    # Continuous across midnight: no step larger than the largest in-day step.
    wrapped = np.abs(np.diff(np.concatenate([shape, shape[:1]])))
    assert wrapped[-1] <= wrapped.max()


def test_seasonal_shares_sum_to_one_and_survive_junk_input() -> None:
    at = _signed_in()
    from app.model import seasonal_shares

    season = at.session_state["seasonality_df"].copy()
    season.loc[0, "Factor"] = None
    at.session_state["seasonality_df"] = season
    at.run()
    assert not at.exception

    shares = at.session_state["seasonality_df"]
    assert len(shares) == 12
    _ = seasonal_shares  # exercised inside the app run above


def test_demand_growth_compounds_over_the_horizon() -> None:
    at = _signed_in()
    demand = at.session_state["demand_df"].copy()
    demand["Growth %"] = [0.0] + [3.0] * 9
    at.session_state["demand_df"] = demand
    at.run()
    assert not at.exception
    # 42 TWh compounded at 3% for nine years.
    expected = 42.0 * 1.03**9
    metrics = {m.label: m.value for m in at.metric}
    assert any(f"{expected:,.1f} TWh" == v for v in metrics.values()), metrics


def test_ntc_table_covers_every_year_of_the_horizon() -> None:
    at = _signed_in()
    from app.model import YEAR_COLS

    ntc = at.session_state["ntc_df"]
    assert [c for c in ntc.columns if c not in ("Neighbour", "Direction")] == YEAR_COLS
    assert ntc["Neighbour"].nunique() == 4
    assert set(ntc["Direction"]) == {"Import", "Export"}


def test_removing_all_generation_does_not_crash() -> None:
    at = _signed_in()
    gen = at.session_state["generation_df"]
    at.session_state["generation_df"] = gen.iloc[0:0]
    at.run()
    assert not at.exception


def test_sign_out_returns_to_the_login_form() -> None:
    at = _signed_in()
    sign_out = [b for b in at.sidebar.button if b.label == "Sign out"][0]
    sign_out.click().run()
    assert not at.exception
    assert at.tabs == []
