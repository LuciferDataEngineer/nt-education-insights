"""Plotly figures shared by the Streamlit app and the static dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

INK = "#1c2b2a"
TEAL = "#1f6f6a"
OCHRE = "#c46b2d"
RED = "#9c3b2e"
BLUE = "#2c5f8a"
GOLD = "#c6a15b"
SAND = "#f7f3eb"

GEO_COLOURS = {"Outer Regional": TEAL, "Remote": OCHRE, "Very Remote": RED}


def _layout(title: str, y_title: str, height: int = 460, y_range: list[float] | None = None) -> dict:
    yaxis: dict = {"title": y_title, "gridcolor": "#e6e0d4"}
    if y_range is not None:
        yaxis["range"] = y_range
    return dict(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16, color=INK)),
        height=height,
        margin=dict(l=56, r=24, t=72, b=48),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color=INK, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=yaxis,
    )


def attendance_trend(frame: pd.DataFrame) -> go.Figure:
    styles = [
        ("NT", "Aboriginal and Torres Strait Islander students", RED, "NT, Aboriginal and Torres Strait Islander"),
        ("Aust", "Aboriginal and Torres Strait Islander students", OCHRE, "Australia, Aboriginal and Torres Strait Islander"),
        ("NT", "All students", TEAL, "NT, all students"),
        ("Aust", "All students", BLUE, "Australia, all students"),
        ("NT", "Non-Indigenous students", GOLD, "NT, non-Indigenous"),
        ("Aust", "Non-Indigenous students", "#7d8b8a", "Australia, non-Indigenous"),
    ]
    figure = go.Figure()
    for jurisdiction, population, colour, label in styles:
        subset = frame[(frame["jurisdiction"] == jurisdiction) & (frame["population"] == population)].sort_values("calendar_year")
        figure.add_trace(
            go.Scatter(
                x=subset["calendar_year"],
                y=subset["attendance_rate"] * 100,
                mode="lines+markers",
                name=label,
                line=dict(color=colour, width=2.4),
                hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
            )
        )
    figure.update_layout(**_layout("Attendance, Years 1–10, all schools", "Attendance rate (%)", y_range=[40, 100]))
    figure.update_xaxes(dtick=1, gridcolor="#e6e0d4")
    return figure


def remoteness_comparison(frame: pd.DataFrame) -> go.Figure:
    order = ["Outer regional", "Remote", "Very remote"]
    colours = {"NT": RED, "WA": OCHRE, "Qld": TEAL, "Aust": BLUE}
    names = {"NT": "NT", "WA": "WA", "Qld": "Qld", "Aust": "Australia"}
    figure = go.Figure()
    for jurisdiction in ["NT", "WA", "Qld", "Aust"]:
        subset = frame[frame["jurisdiction"] == jurisdiction].set_index("remoteness").reindex(order)
        figure.add_trace(
            go.Bar(
                name=names[jurisdiction],
                x=order,
                y=subset["attendance_rate"] * 100,
                marker_color=colours[jurisdiction],
                hovertemplate="%{x}<br>" + names[jurisdiction] + ": %{y:.1f}%<extra></extra>",
            )
        )
    figure.update_layout(
        **_layout("Aboriginal and Torres Strait Islander attendance by remoteness, 2025", "Attendance rate (%)", y_range=[30, 100]),
        barmode="group",
    )
    return figure


def region_comparison(frame: pd.DataFrame) -> go.Figure:
    order = ["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]
    figure = go.Figure()
    for population, colour, label in (
        ("indigenous", RED, "Aboriginal"),
        ("non_indigenous", TEAL, "Non-Aboriginal"),
    ):
        subset = frame[frame["population"] == population].set_index("region").reindex(order)
        figure.add_trace(
            go.Bar(
                name=label,
                x=order,
                y=subset["attendance_rate"] * 100,
                marker_color=colour,
                customdata=subset["enrolment"],
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<br>Group enrolment: %{customdata:,.0f}<extra></extra>",
            )
        )
    figure.update_layout(**_layout("NT government schools by region, whole of 2024", "Attendance rate (%)", y_range=[25, 100]), barmode="group")
    return figure


def school_scatter(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for geolocation, colour in GEO_COLOURS.items():
        subset = frame[frame["geolocation"] == geolocation]
        figure.add_trace(
            go.Scatter(
                x=subset["indigenous_pct"],
                y=subset["attendance_rate"] * 100,
                mode="markers",
                name=geolocation,
                marker=dict(
                    color=colour,
                    size=(subset["enrolment"].clip(upper=800) / 28).fillna(8),
                    line=dict(width=0),
                    opacity=0.8,
                ),
                text=subset["school_name"],
                customdata=subset[["enrolment", "bottom_sea_pct", "icsea"]],
                hovertemplate=(
                    "%{text}<br>Indigenous enrolment %{x:.0f}%"
                    "<br>Attendance %{y:.1f}%"
                    "<br>Enrolment %{customdata[0]:.0f}"
                    "<br>Bottom SEA quarter %{customdata[1]:.0f}%"
                    "<br>ICSEA %{customdata[2]:.0f}<extra>" + geolocation + "</extra>"
                ),
            )
        )
    figure.update_layout(**_layout("Government schools, 2024 whole year", "Attendance rate (%)", y_range=[0, 100]))
    figure.update_xaxes(title="Aboriginal and Torres Strait Islander enrolment (%)", range=[-2, 105], gridcolor="#e6e0d4")
    return figure


def school_map(frame: pd.DataFrame) -> go.Figure:
    plotted = frame.dropna(subset=["latitude", "longitude", "attendance_rate"]).copy()
    figure = go.Figure(
        go.Scattergeo(
            lat=plotted["latitude"],
            lon=plotted["longitude"],
            mode="markers",
            text=plotted["school_name"],
            marker=dict(
                size=(plotted["enrolment"].clip(upper=900) / 35).clip(lower=6),
                color=plotted["attendance_rate"] * 100,
                colorscale=[[0, RED], [0.55, OCHRE], [1, TEAL]],
                cmin=30,
                cmax=95,
                colorbar=dict(title="Attendance %", thickness=12),
                line=dict(width=0),
            ),
            customdata=plotted[["attendance_rate", "enrolment", "geolocation", "indigenous_pct"]],
            hovertemplate=(
                "%{text}<br>%{customdata[2]}"
                "<br>Attendance %{customdata[0]:.1%}"
                "<br>Enrolment %{customdata[1]:.0f}"
                "<br>Indigenous enrolment %{customdata[3]:.0f}%<extra></extra>"
            ),
        )
    )
    figure.update_geos(
        projection_type="mercator",
        center=dict(lat=-18.5, lon=133.5),
        lataxis_range=[-26.5, -10.5],
        lonaxis_range=[128.5, 138.5],
        showland=True,
        landcolor=SAND,
        showocean=True,
        oceancolor="#d5e4e2",
        showcountries=True,
        countrycolor=INK,
        showlakes=False,
        resolution=50,
    )
    figure.update_layout(
        title=dict(text="Where attendance is low is not where Darwin is", x=0, xanchor="left"),
        height=560,
        margin=dict(l=0, r=0, t=56, b=0),
        paper_bgcolor="white",
        font=dict(color=INK),
    )
    return figure


def naplan_support(frame: pd.DataFrame) -> go.Figure:
    order = [
        ("Aust", "All", "Australia, all"),
        ("NT", "Non-Indigenous", "NT, non-Indigenous"),
        ("Aust", "Indigenous", "Australia, Indigenous"),
        ("NT", "All", "NT, all"),
        ("NT", "Indigenous", "NT, Indigenous"),
        ("NT", "Indigenous very remote", "NT, Indigenous, very remote"),
    ]
    labels = []
    values = []
    absences = []
    for jurisdiction, subgroup, label in order:
        row = frame[(frame["jurisdiction"] == jurisdiction) & (frame["subgroup"] == subgroup)]
        if row.empty:
            continue
        labels.append(label)
        values.append(float(row["needs_additional_support_pct"].iloc[0]))
        absences.append(float(row["absent_pct"].iloc[0]))
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=[BLUE, GOLD, OCHRE, TEAL, RED, "#6b2d3c"],
            customdata=absences,
            hovertemplate="%{x}<br>Needs additional support %{y:.1f}%<br>Absent %{customdata:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(
        **_layout("Year 3 reading, 2025, lowest proficiency level", "Students needing additional support (%)", y_range=[0, 100])
    )
    return figure


def retention_chart(frame: pd.DataFrame) -> go.Figure:
    order = ["NT", "WA", "Qld", "SA"]
    figure = go.Figure()
    for column, colour, label in (
        ("arr_indigenous", RED, "Aboriginal and Torres Strait Islander"),
        ("arr_non_indigenous", TEAL, "Non-Indigenous"),
    ):
        subset = frame.set_index("jurisdiction").reindex(order)
        figure.add_trace(
            go.Bar(
                name=label,
                x=order,
                y=subset[column] * 100,
                marker_color=colour,
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<extra></extra>",
            )
        )
    figure.update_layout(**_layout("Apparent retention, Year 7/8 to Year 12, 2025", "Apparent retention (%)", y_range=[0, 100]), barmode="group")
    return figure


YEAR_LEVEL_ORDER = [
    "Preschool",
    "Transition",
    "Year 1",
    "Year 2",
    "Year 3",
    "Year 4",
    "Year 5",
    "Year 6",
    "Year 7",
    "Year 8",
    "Year 9",
    "Year 10",
    "Year 11",
    "Year 12",
]


def year_level_attendance(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for population, colour, label in (
        ("indigenous", RED, "Aboriginal"),
        ("non_indigenous", TEAL, "Non-Aboriginal"),
    ):
        subset = frame[frame["population"] == population].drop_duplicates("year_level").set_index("year_level").reindex(YEAR_LEVEL_ORDER)
        figure.add_trace(
            go.Scatter(
                x=YEAR_LEVEL_ORDER,
                y=subset["attendance_rate"] * 100,
                mode="lines+markers",
                name=label,
                line=dict(color=colour, width=2.4),
                customdata=subset["enrolment"],
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<br>Enrolment %{customdata:,.0f}<extra></extra>",
            )
        )
    figure.update_layout(**_layout("Government schools by year level", "Attendance rate (%)", y_range=[40, 100]))
    return figure
