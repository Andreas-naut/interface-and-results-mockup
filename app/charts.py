"""Altair chart builders.

Each builder returns a finished, styled chart: thin marks, a recessive grid, a
hover layer, and a legend whenever more than one series is on screen. Multi
series charts take an explicit ``domain`` so a colour always belongs to an
entity rather than to its position in the data.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from app.theme import AXIS, GRID, INK_SECONDARY, SERIES, SURFACE, color_scale, finalize


def _x(field: str, title: str | None, *, temporal_ordinal: bool = True) -> alt.X:
    kind = "O" if temporal_ordinal else "N"
    return alt.X(f"{field}:{kind}", title=title, axis=alt.Axis(labelAngle=0, grid=False))


def line(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    y_title: str | None = None,
    x_title: str | None = None,
    fmt: str = ",.1f",
    color: str = SERIES[0],
    height: int = 260,
) -> alt.Chart:
    """Single-series line with a hover crosshair. No legend — the title names it."""
    base = alt.Chart(df)
    hover = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")

    line_mark = base.mark_line(color=color, strokeWidth=2, interpolate="monotone").encode(
        _x(x, x_title), alt.Y(f"{y}:Q", title=y_title or y, scale=alt.Scale(zero=True, nice=True))
    )
    rule = (
        base.mark_rule(color=AXIS, strokeWidth=1)
        .encode(_x(x, None), opacity=alt.condition(hover, alt.value(1), alt.value(0)))
        .add_params(hover)
    )
    points = base.mark_point(
        color=color, size=90, filled=True, stroke=SURFACE, strokeWidth=2
    ).encode(
        _x(x, None),
        alt.Y(f"{y}:Q"),
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip(f"{x}:O", title=x), alt.Tooltip(f"{y}:Q", title=y_title or y, format=fmt)],
    )
    return finalize(rule + line_mark + points, height)


def multi_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    series: str,
    domain: list[str],
    *,
    y_title: str | None = None,
    x_title: str | None = None,
    fmt: str = ",.2f",
    height: int = 300,
) -> alt.Chart:
    """One line per series, legend always on, shared hover tooltip."""
    base = alt.Chart(df)
    hover = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    color = alt.Color(f"{series}:N", scale=color_scale(domain), title=None, sort=domain)

    lines = base.mark_line(strokeWidth=2, interpolate="monotone").encode(
        _x(x, x_title), alt.Y(f"{y}:Q", title=y_title or y, scale=alt.Scale(zero=True, nice=True)), color
    )
    rule = (
        base.mark_rule(color=AXIS, strokeWidth=1)
        .encode(
            _x(x, None),
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip(f"{x}:O", title=x)]
            + [
                alt.Tooltip(f"{name}:Q", title=name, format=fmt)
                for name in _pivot_fields(df, series, domain)
            ],
        )
        .transform_pivot(series, value=y, groupby=[x])
        .add_params(hover)
    )
    points = base.mark_point(size=80, filled=True, stroke=SURFACE, strokeWidth=2).encode(
        _x(x, None),
        alt.Y(f"{y}:Q"),
        color,
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    )
    return finalize(lines + points + rule, height)


def _pivot_fields(df: pd.DataFrame, series: str, domain: list[str]) -> list[str]:
    present = set(df[series].astype(str))
    return [name for name in domain if name in present]


def bars(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    y_title: str | None = None,
    x_title: str | None = None,
    fmt: str = ",.0f",
    color: str = SERIES[0],
    sort: str | list[str] | None = "-y",
    label: bool = True,
    height: int = 260,
) -> alt.Chart:
    """Single-series bars, data-end rounded, values labelled directly."""
    encode_x = alt.X(f"{x}:N", title=x_title, sort=sort, axis=alt.Axis(labelAngle=0, grid=False))
    base = alt.Chart(df).encode(encode_x)
    bar = base.mark_bar(color=color, cornerRadiusEnd=4, stroke=SURFACE, strokeWidth=2).encode(
        alt.Y(f"{y}:Q", title=y_title or y, scale=alt.Scale(zero=True, nice=True)),
        tooltip=[alt.Tooltip(f"{x}:N", title=x), alt.Tooltip(f"{y}:Q", title=y_title or y, format=fmt)],
    )
    if not label:
        return finalize(bar, height)
    text = base.mark_text(dy=-8, color=INK_SECONDARY, fontSize=11).encode(
        alt.Y(f"{y}:Q"), text=alt.Text(f"{y}:Q", format=fmt)
    )
    return finalize(bar + text, height)


def hbars(
    df: pd.DataFrame,
    y: str,
    x: str,
    *,
    x_title: str | None = None,
    fmt: str = ",.0f",
    color: str = SERIES[0],
    height: int = 320,
) -> alt.Chart:
    """Horizontal bars, ranked — the readable form when categories are names."""
    order = df.sort_values(x, ascending=False)[y].astype(str).tolist()
    base = alt.Chart(df).encode(alt.Y(f"{y}:N", title=None, sort=order, axis=alt.Axis(grid=False)))
    bar = base.mark_bar(color=color, cornerRadiusEnd=4, stroke=SURFACE, strokeWidth=2, height=14).encode(
        alt.X(f"{x}:Q", title=x_title or x, scale=alt.Scale(zero=True, nice=True)),
        tooltip=[alt.Tooltip(f"{y}:N", title=y), alt.Tooltip(f"{x}:Q", title=x_title or x, format=fmt)],
    )
    text = base.mark_text(dx=6, align="left", color=INK_SECONDARY, fontSize=11).encode(
        alt.X(f"{x}:Q"), text=alt.Text(f"{x}:Q", format=fmt)
    )
    return finalize(bar + text, height)


def stacked_bars(
    df: pd.DataFrame,
    x: str,
    y: str,
    series: str,
    domain: list[str],
    *,
    y_title: str | None = None,
    x_title: str | None = None,
    fmt: str = ",.0f",
    height: int = 320,
) -> alt.Chart:
    """Stacked bars with a 2px surface ring separating adjacent fills."""
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, stroke=SURFACE, strokeWidth=2)
        .encode(
            _x(x, x_title),
            alt.Y(f"{y}:Q", title=y_title or y, stack="zero", scale=alt.Scale(nice=True)),
            alt.Color(f"{series}:N", scale=color_scale(domain), title=None, sort=domain),
            order=alt.Order(f"{series}:N", sort="ascending"),
            tooltip=[
                alt.Tooltip(f"{x}:O", title=x),
                alt.Tooltip(f"{series}:N", title=series),
                alt.Tooltip(f"{y}:Q", title=y_title or y, format=fmt),
            ],
        )
    )
    return finalize(chart, height)


def heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    value: str,
    *,
    x_order: list[str] | None = None,
    y_order: list[str] | None = None,
    fmt: str = ".2f",
    height: int = 220,
) -> alt.Chart:
    """Sequential single-hue cell grid — magnitude, so one hue light to dark."""
    from app.theme import SEQ_BLUE

    chart = (
        alt.Chart(df)
        .mark_rect(stroke=SURFACE, strokeWidth=2, cornerRadius=3)
        .encode(
            alt.X(f"{x}:N", title=None, sort=x_order, axis=alt.Axis(labelAngle=0, grid=False)),
            alt.Y(f"{y}:N", title=None, sort=y_order, axis=alt.Axis(grid=False)),
            alt.Color(
                f"{value}:Q",
                title=value,
                scale=alt.Scale(range=SEQ_BLUE, domain=[0, float(max(df[value].max(), 0.01))]),
                legend=alt.Legend(gradientLength=140),
            ),
            tooltip=[
                alt.Tooltip(f"{y}:N", title=y),
                alt.Tooltip(f"{x}:N", title=x),
                alt.Tooltip(f"{value}:Q", title=value, format=fmt),
            ],
        )
    )
    return finalize(chart, height)


def reference_line(df: pd.DataFrame, x: str, y: str, *, label: str) -> alt.Chart:
    """A dashed comparison line for layering behind a primary series."""
    return (
        alt.Chart(df)
        .mark_line(color=GRID, strokeWidth=2, strokeDash=[4, 3], interpolate="monotone")
        .encode(_x(x, None), alt.Y(f"{y}:Q", title=label))
    )
