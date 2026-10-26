"""Publication charts for the insight report. Numbers come from the gold tables."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

INK = "#1c2b2a"
OCHRE = "#c46b2d"
TEAL = "#1f6f6a"
SAND = "#f6f1e7"
RED = "#9c3b2e"
BLUE = "#2c5f8a"
GOLD = "#c6a15b"
GRID = "#d9d1c3"

GEO_COLOURS = {
    "Outer Regional": TEAL,
    "Remote": OCHRE,
    "Very Remote": RED,
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": INK,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "font.size": 11,
            "axes.titlesize": 13,
            "figure.dpi": 140,
            "savefig.dpi": 140,
            "savefig.bbox": "tight",
        }
    )


def _percent_axis(axis, start: float, stop: float) -> None:
    axis.set_ylim(start, stop)
    ticks = np.arange(start, stop + 1, 10)
    axis.set_yticks(ticks)
    axis.set_yticklabels([f"{int(tick)}%" for tick in ticks])


def attendance_trend(series: pd.DataFrame, path: Path) -> None:
    _style()
    figure, axis = plt.subplots(figsize=(9.2, 5.2))
    styles = {
        ("NT", "Aboriginal and Torres Strait Islander students"): (RED, "NT, Aboriginal and Torres Strait Islander"),
        ("Aust", "Aboriginal and Torres Strait Islander students"): (OCHRE, "Australia, Aboriginal and Torres Strait Islander"),
        ("NT", "All students"): (TEAL, "NT, all students"),
        ("Aust", "All students"): (BLUE, "Australia, all students"),
        ("NT", "Non-Indigenous students"): (GOLD, "NT, non-Indigenous"),
        ("Aust", "Non-Indigenous students"): ("#7d8b8a", "Australia, non-Indigenous"),
    }
    for (jurisdiction, population), (colour, label) in styles.items():
        subset = series[(series["jurisdiction"] == jurisdiction) & (series["population"] == population)].sort_values("calendar_year")
        axis.plot(
            subset["calendar_year"],
            subset["attendance_rate"] * 100,
            color=colour,
            marker="o",
            linewidth=2.0,
            markersize=4.5,
            label=label,
        )
    _percent_axis(axis, 50, 100)
    axis.set_xlim(2015.5, 2025.5)
    axis.set_xlabel("Year")
    axis.set_ylabel("Attendance rate, Years 1–10")
    axis.set_title("NT attendance fell, and the fall was concentrated among Aboriginal students")
    axis.legend(frameon=False, fontsize=8.5, loc="lower left")
    axis.annotate(
        "2020 not published",
        xy=(2020, 62),
        xytext=(2018.2, 54),
        fontsize=8,
        color="#5c6766",
        arrowprops={"arrowstyle": "-", "color": "#5c6766"},
    )
    figure.savefig(path)
    plt.close(figure)


def remoteness_bars(frame: pd.DataFrame, path: Path) -> None:
    _style()
    order = ["Outer regional", "Remote", "Very remote"]
    jurisdictions = ["NT", "WA", "Qld", "Aust"]
    colours = {"NT": RED, "WA": OCHRE, "Qld": TEAL, "Aust": BLUE}
    figure, axis = plt.subplots(figsize=(9.2, 5.2))
    width = 0.18
    positions = np.arange(len(order))
    for index, jurisdiction in enumerate(jurisdictions):
        values = []
        for remoteness in order:
            row = frame[(frame["jurisdiction"] == jurisdiction) & (frame["remoteness"] == remoteness)]
            values.append(float(row["attendance_rate"].iloc[0]) * 100 if len(row) else np.nan)
        axis.bar(positions + (index - 1.5) * width, values, width=width, color=colours[jurisdiction], label=jurisdiction if jurisdiction != "Aust" else "Australia")
    axis.set_xticks(positions)
    axis.set_xticklabels(order)
    _percent_axis(axis, 0, 100)
    axis.set_ylabel("Attendance rate, Years 1–10, 2025")
    axis.set_title("In very remote Australia, Aboriginal students' attendance is lowest in the NT")
    axis.legend(frameon=False, ncol=4)
    figure.savefig(path)
    plt.close(figure)


def region_bars(frame: pd.DataFrame, path: Path) -> None:
    _style()
    order = ["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]
    figure, axis = plt.subplots(figsize=(9.2, 5.2))
    positions = np.arange(len(order))
    width = 0.36
    indigenous = [float(frame[(frame["region"] == region) & (frame["population"] == "indigenous")]["attendance_rate"].iloc[0]) * 100 for region in order]
    other = [float(frame[(frame["region"] == region) & (frame["population"] == "non_indigenous")]["attendance_rate"].iloc[0]) * 100 for region in order]
    axis.bar(positions - width / 2, indigenous, width=width, color=RED, label="Aboriginal")
    axis.bar(positions + width / 2, other, width=width, color=TEAL, label="Non-Aboriginal")
    axis.set_xticks(positions)
    axis.set_xticklabels(order)
    _percent_axis(axis, 0, 100)
    axis.set_ylabel("Attendance rate, whole of 2024")
    axis.set_title("Government schools: Darwin is a different system from Barkly and East Arnhem")
    axis.legend(frameon=False)
    figure.savefig(path)
    plt.close(figure)


def school_scatter(frame: pd.DataFrame, path: Path) -> None:
    _style()
    figure, axis = plt.subplots(figsize=(9.2, 5.6))
    for geolocation, colour in GEO_COLOURS.items():
        subset = frame[frame["geolocation"] == geolocation]
        axis.scatter(
            subset["indigenous_pct"],
            subset["attendance_rate"] * 100,
            s=np.clip(subset["enrolment"] / 4, 18, 220),
            color=colour,
            alpha=0.78,
            linewidths=0,
            label=geolocation,
        )
    axis.set_xlabel("Aboriginal and Torres Strait Islander enrolment (%)")
    axis.set_ylabel("Attendance rate, 2024")
    _percent_axis(axis, 0, 100)
    axis.set_xlim(-2, 105)
    axis.set_title("Inside the NT, attendance tracks Indigenous enrolment and remoteness together")
    axis.legend(frameon=False, title="ACARA geolocation")
    figure.savefig(path)
    plt.close(figure)


def naplan_bars(frame: pd.DataFrame, path: Path) -> None:
    _style()
    labels = [
        ("Aust", "All", "Australia\nall students"),
        ("NT", "All", "NT\nall students"),
        ("Aust", "Indigenous", "Australia\nIndigenous"),
        ("NT", "Indigenous", "NT\nIndigenous"),
        ("Aust", "Indigenous very remote", "Australia\nIndigenous,\nvery remote"),
        ("NT", "Indigenous very remote", "NT\nIndigenous,\nvery remote"),
    ]
    figure, axis = plt.subplots(figsize=(9.4, 5.2))
    values = []
    colours = []
    palette = [BLUE, TEAL, OCHRE, RED, GOLD, "#6b2d3c"]
    for (jurisdiction, subgroup, _label), colour in zip(labels, palette, strict=True):
        row = frame[(frame["jurisdiction"] == jurisdiction) & (frame["subgroup"] == subgroup)]
        values.append(float(row["needs_additional_support_pct"].iloc[0]))
        colours.append(colour)
    axis.bar(np.arange(len(labels)), values, color=colours)
    axis.set_xticks(np.arange(len(labels)))
    axis.set_xticklabels([label for *_, label in labels], fontsize=8.5)
    _percent_axis(axis, 0, 100)
    axis.set_ylabel("Students needing additional support")
    axis.set_title("Year 3 reading, 2025: share in the lowest NAPLAN proficiency level")
    figure.savefig(path)
    plt.close(figure)


def retention_bars(frame: pd.DataFrame, path: Path) -> None:
    _style()
    order = ["NT", "WA", "Qld", "SA"]
    figure, axis = plt.subplots(figsize=(8.6, 5.0))
    positions = np.arange(len(order))
    width = 0.36
    indigenous = [float(frame[(frame["jurisdiction"] == code) & (frame["calendar_year"] == 2025)]["arr_indigenous"].iloc[0]) * 100 for code in order]
    other = [float(frame[(frame["jurisdiction"] == code) & (frame["calendar_year"] == 2025)]["arr_non_indigenous"].iloc[0]) * 100 for code in order]
    axis.bar(positions - width / 2, indigenous, width=width, color=RED, label="Aboriginal and Torres Strait Islander")
    axis.bar(positions + width / 2, other, width=width, color=TEAL, label="Non-Indigenous")
    axis.set_xticks(positions)
    axis.set_xticklabels(order)
    _percent_axis(axis, 0, 100)
    axis.set_ylabel("Apparent retention, Year 7/8 to Year 12")
    axis.set_title("2025 apparent retention: the NT Year 12 gap is not the national pattern")
    axis.legend(frameon=False, fontsize=9)
    figure.savefig(path)
    plt.close(figure)
