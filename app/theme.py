"""Colour tokens and Altair styling helpers.

The app commits to a single (light) look, pinned in ``.streamlit/config.toml``,
so every value below is the light-surface step of the reference palette. Series
hues are assigned in fixed slot order and never cycled: a scale is always built
with an explicit ``domain``, so adding or filtering a category cannot repaint
the ones that stay.
"""

from __future__ import annotations

import altair as alt

# --- surfaces & ink ---------------------------------------------------------
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# --- categorical slots, in fixed order --------------------------------------
SERIES = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]

# --- single-hue sequential ramp (blue), light -> dark ------------------------
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf", "#184f95", "#0d366b"]

# --- status (reserved; never used as a series colour) -----------------------
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def color_scale(domain: list[str]) -> alt.Scale:
    """A categorical scale that pins each member to its own slot for good."""
    return alt.Scale(domain=list(domain), range=SERIES[: len(domain)])


def finalize(chart: alt.Chart, height: int = 280) -> alt.Chart:
    """Apply chart-level chrome. Call once, on the outermost chart."""
    return (
        chart.properties(height=height, width="container")
        .configure_view(strokeWidth=0, fill=SURFACE)
        .configure_axis(
            labelFont=FONT,
            titleFont=FONT,
            labelColor=INK_MUTED,
            titleColor=INK_SECONDARY,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            gridColor=GRID,
            gridWidth=1,
            domainColor=AXIS,
            tickColor=AXIS,
            tickSize=4,
            labelPadding=6,
        )
        .configure_legend(
            labelFont=FONT,
            titleFont=FONT,
            labelColor=INK_SECONDARY,
            titleColor=INK_SECONDARY,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            symbolType="square",
            symbolSize=90,
            orient="top",
            direction="horizontal",
            offset=8,
        )
        .configure_text(font=FONT, color=INK_SECONDARY, fontSize=11)
        .configure_title(font=FONT, color=INK_PRIMARY, fontSize=13, anchor="start")
    )
