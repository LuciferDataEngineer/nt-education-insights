"""Plotly figures shared by the Streamlit app and the static dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

INK = "#0B2545"
MUTED = "#3E4C59"
GRID = "#E2E8EE"
NAVY = "#0B2545"
TEAL = "#0F6E6E"
TERRACOTTA = "#A84E1E"
GREY = "#4A5560"
GREY_SOFT = "#6A7580"
DEEP = "#8C3A22"
STEEL = "#3D6F8F"
CONCERN = "#9B2C2C"
WATCH = "#C58A12"
GOOD = "#1F7A4D"
# Names kept so a population series stays one colour: terracotta is NT Aboriginal, grey is Australia.
CRIMSON = TERRACOTTA
ROSE = GREY
SLATE = GREY_SOFT
OCHRE = TERRACOTTA
SAND = "#F4F6F8"

GEO_COLOURS = {"Outer Regional": NAVY, "Remote": STEEL, "Very Remote": DEEP}

FONT = "Inter, Segoe UI, Helvetica Neue, Arial, sans-serif"


def _base(
    height: int = 420,
    *,
    legend: str = "top",
    left: int = 56,
    right: int = 16,
    top: int | None = None,
    bottom: int | None = None,
) -> dict:
    show = legend != "none"
    if top is None:
        top = 52 if show else 12
    if bottom is None:
        bottom = 40
    return dict(
        height=height,
        margin=dict(l=left, r=right, t=top, b=bottom),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=FONT, color=INK, size=13),
        showlegend=show,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            x=0,
            xanchor="left",
            font=dict(size=12, color=INK),
            bgcolor="rgba(0,0,0,0)",
            itemclick=False,
            itemdoubleclick=False,
        ),
        hovermode="closest",
        hoverlabel=dict(bgcolor="white", font_size=13, font_family=FONT, font_color=INK),
        autosize=True,
    )


def _axes(figure: go.Figure, y_title: str, y_range: list[float] | None = None) -> None:
    yaxis: dict = {"title": y_title, "gridcolor": GRID, "zeroline": False, "automargin": True, "title_standoff": 8}
    if y_range is not None:
        yaxis["range"] = y_range
    figure.update_yaxes(**yaxis)
    figure.update_xaxes(gridcolor="rgba(0,0,0,0)", automargin=True, zeroline=False)


def attendance_trend(frame: pd.DataFrame) -> go.Figure:
    """Years 1–10 attendance. NT series are solid; Australia is dashed and lighter."""
    styles = [
        ("NT", "Aboriginal and Torres Strait Islander students", CRIMSON, "NT Aboriginal", True),
        ("NT", "Non-Indigenous students", TEAL, "NT non-Indigenous", True),
        ("Aust", "Aboriginal and Torres Strait Islander students", ROSE, "Australia Aboriginal", False),
        ("Aust", "Non-Indigenous students", SLATE, "Australia non-Indigenous", False),
    ]
    figure = go.Figure()
    for jurisdiction, population, colour, label, highlight in styles:
        subset = frame[(frame["jurisdiction"] == jurisdiction) & (frame["population"] == population)].sort_values("calendar_year")
        figure.add_trace(
            go.Scatter(
                x=subset["calendar_year"],
                y=subset["attendance_rate"] * 100,
                mode="lines+markers",
                name=label,
                connectgaps=False,
                line=dict(color=colour, width=3.2 if highlight else 1.8, dash="solid" if highlight else "dash"),
                marker=dict(size=8 if highlight else 5, color=colour, line=dict(width=0)),
                hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
            )
        )
    figure.update_layout(**_base(440, top=64, bottom=36))
    _axes(figure, "Attendance rate (%)", [36, 100])
    figure.update_xaxes(dtick=1, range=[2015.6, 2025.4])
    figure.add_vline(x=2020, line_width=1, line_dash="dot", line_color="#c5ced6")
    figure.add_annotation(
        x=2020,
        y=42,
        text="2020 · no data, COVID",
        showarrow=False,
        yanchor="middle",
        font=dict(size=11, color=MUTED, family=FONT),
    )
    return figure


def remoteness_comparison(frame: pd.DataFrame) -> go.Figure:
    order = ["Outer regional", "Remote", "Very remote"]
    colours = {"NT": TERRACOTTA, "Aust": GREY, "WA": NAVY, "Qld": TEAL}
    names = {
        "NT": "NT Aboriginal",
        "Aust": "Australia Aboriginal",
        "WA": "WA Aboriginal",
        "Qld": "Qld Aboriginal",
    }
    present = [code for code in ["NT", "Aust", "WA", "Qld"] if code in set(frame["jurisdiction"])]
    figure = go.Figure()
    for jurisdiction in present:
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
    figure.update_layout(**_base(400, top=48, bottom=36), barmode="group", bargap=0.28)
    _axes(figure, "Attendance rate (%)", [0, 100])
    return figure


def region_comparison(frame: pd.DataFrame) -> go.Figure:
    indigenous = frame[frame["population"] == "indigenous"].dropna(subset=["attendance_rate"]).drop_duplicates("region")
    order = indigenous.sort_values("attendance_rate", ascending=True)["region"].tolist()
    if not order:
        order = ["Barkly", "East Arnhem", "Big Rivers", "Central", "Top End", "Darwin"]
    figure = go.Figure()
    for population, colour, label in (
        ("non_indigenous", TEAL, "Non-Indigenous"),
        ("indigenous", CRIMSON, "Aboriginal"),
    ):
        subset = frame[frame["population"] == population].drop_duplicates("region").set_index("region").reindex(order)
        figure.add_trace(
            go.Bar(
                name=label,
                y=order,
                x=subset["attendance_rate"] * 100,
                orientation="h",
                marker_color=colour,
                customdata=subset["enrolment"],
                hovertemplate="%{y}<br>" + label + ": %{x:.1f}%<br>Enrolment %{customdata:,.0f}<extra></extra>",
            )
        )
    figure.update_layout(**_base(420, left=108, right=20, top=48, bottom=36), barmode="group", bargap=0.32)
    figure.update_xaxes(title="Attendance rate (%)", range=[0, 100], gridcolor=GRID, zeroline=False, automargin=True)
    figure.update_yaxes(automargin=True)
    return figure


def school_scatter(frame: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for geolocation, colour in GEO_COLOURS.items():
        subset = frame[frame["geolocation"] == geolocation]
        if subset.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=subset["indigenous_pct"],
                y=subset["attendance_rate"] * 100,
                mode="markers",
                name=geolocation,
                marker=dict(
                    color=colour,
                    size=(subset["enrolment"].clip(upper=800) / 22).fillna(8),
                    line=dict(width=0.6, color="white"),
                    opacity=0.88,
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
    figure.update_layout(**_base(460, top=48, bottom=48))
    _axes(figure, "Attendance rate (%)", [0, 100])
    figure.update_xaxes(title="Aboriginal and Torres Strait Islander enrolment (%)", range=[-2, 105], gridcolor=GRID)
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
                size=(plotted["enrolment"].clip(upper=900) / 35).clip(lower=7),
                color=plotted["attendance_rate"] * 100,
                colorscale=[[0, CONCERN], [0.55, WATCH], [1, GOOD]],
                cmin=30,
                cmax=95,
                colorbar=dict(title="Attendance %", thickness=12, len=0.6),
                line=dict(width=0.4, color="white"),
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
        oceancolor="#d7e4e1",
        showcountries=True,
        countrycolor=INK,
        showlakes=False,
        resolution=50,
    )
    figure.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="white",
        font=dict(family=FONT, color=INK),
        autosize=True,
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
    labels: list[str] = []
    values: list[float] = []
    absences: list[float] = []
    colours: list[str] = []
    for jurisdiction, subgroup, label in order:
        row = frame[(frame["jurisdiction"] == jurisdiction) & (frame["subgroup"] == subgroup)]
        if row.empty or pd.isna(row["needs_additional_support_pct"].iloc[0]):
            continue
        labels.append(label)
        values.append(float(row["needs_additional_support_pct"].iloc[0]))
        absent = row["absent_pct"].iloc[0]
        absences.append(float(absent) if pd.notna(absent) else float("nan"))
        if "very remote" in label:
            colours.append(DEEP)
        elif label == "NT, Indigenous":
            colours.append(CRIMSON)
        elif "non-Indigenous" in label:
            colours.append(TEAL)
        else:
            colours.append(SLATE)
    figure = go.Figure(
        go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker_color=colours,
            customdata=absences,
            text=values,
            texttemplate="%{x:.0f}%",
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=12, color=INK),
            hovertemplate="%{y}<br>Needs additional support %{x:.1f}%<br>Absent %{customdata:.1f}%<extra></extra>",
        )
    )
    figure.update_layout(**_base(380, legend="none", left=168, right=36, top=8, bottom=40))
    figure.update_xaxes(title="Needs additional support (%)", range=[0, 118], gridcolor=GRID, zeroline=False, automargin=True)
    figure.update_yaxes(automargin=True)
    return figure


def retention_chart(frame: pd.DataFrame) -> go.Figure:
    order = [code for code in ["NT", "WA", "Qld", "SA"] if code in set(frame["jurisdiction"])]
    figure = go.Figure()
    for column, colour, label in (
        ("arr_indigenous", CRIMSON, "Aboriginal"),
        ("arr_non_indigenous", TEAL, "Non-Indigenous"),
    ):
        subset = frame.drop_duplicates("jurisdiction").set_index("jurisdiction").reindex(order)
        figure.add_trace(
            go.Bar(
                name=label,
                x=order,
                y=subset[column] * 100,
                marker_color=colour,
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<extra></extra>",
            )
        )
    figure.update_layout(**_base(380, top=48, bottom=36), barmode="group")
    _axes(figure, "Apparent retention (%)", [0, 100])
    return figure


def retention_trend(frame: pd.DataFrame) -> go.Figure:
    """Aboriginal apparent retention over time. Expects NT and WA rows."""
    styles = [("NT", CRIMSON, "NT Aboriginal", True), ("WA", NAVY, "WA Aboriginal", False)]
    figure = go.Figure()
    for jurisdiction, colour, label, highlight in styles:
        subset = frame[frame["jurisdiction"] == jurisdiction].sort_values("calendar_year")
        if subset.empty:
            continue
        figure.add_trace(
            go.Scatter(
                x=subset["calendar_year"],
                y=subset["arr_indigenous"] * 100,
                mode="lines+markers",
                name=label,
                line=dict(color=colour, width=3.2 if highlight else 2.2),
                marker=dict(size=7 if highlight else 5, color=colour),
                hovertemplate="%{x}: %{y:.1f}%<extra>" + label + "</extra>",
            )
        )
    figure.update_layout(**_base(380, top=48, bottom=36))
    _axes(figure, "Apparent retention (%)", [20, 80])
    figure.update_xaxes(dtick=2)
    return figure


def funding_comparison(nt_dollars: float, australia_dollars: float) -> go.Figure:
    labels = ["Northern Territory", "Australia"]
    values = [nt_dollars, australia_dollars]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=[NAVY, GREY],
            text=[f"${value:,.0f}" for value in values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=13, color=INK),
            hovertemplate="%{x}<br>$%{y:,.0f} per student<extra></extra>",
            width=0.45,
        )
    )
    ceiling = max(values) * 1.28
    figure.update_layout(**_base(340, legend="none", top=28, bottom=36))
    figure.update_yaxes(
        title="Dollars per student",
        range=[0, ceiling],
        gridcolor=GRID,
        zeroline=False,
        tickprefix="$",
        separatethousands=True,
    )
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
        ("indigenous", CRIMSON, "Aboriginal"),
        ("non_indigenous", TEAL, "Non-Indigenous"),
    ):
        subset = frame[frame["population"] == population].drop_duplicates("year_level").set_index("year_level").reindex(YEAR_LEVEL_ORDER)
        figure.add_trace(
            go.Scatter(
                x=YEAR_LEVEL_ORDER,
                y=subset["attendance_rate"] * 100,
                mode="lines+markers",
                name=label,
                line=dict(color=colour, width=2.8),
                marker=dict(size=7, color=colour),
                customdata=subset["enrolment"],
                hovertemplate="%{x}<br>" + label + ": %{y:.1f}%<br>Enrolment %{customdata:,.0f}<extra></extra>",
            )
        )
    figure.update_layout(**_base(440, top=48, bottom=72))
    _axes(figure, "Attendance rate (%)", [40, 100])
    figure.update_xaxes(tickangle=-40)
    return figure
