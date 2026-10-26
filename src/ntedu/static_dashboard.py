"""Self-contained HTML dashboard. Opens in a browser with no server."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.io as pio

from ntedu.charts import (
    attendance_trend,
    naplan_support,
    region_comparison,
    remoteness_comparison,
    retention_chart,
    school_map,
    school_scatter,
    year_level_attendance,
)
from ntedu.config import DASHBOARD_DIST, FIGURES, GOLD, SILVER

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Northern Territory school education</title>
<style>
  :root {{
    --ink: #1c2b2a;
    --muted: #5c6766;
    --sand: #f6f1e7;
    --line: #e4dccb;
    --teal: #1f6f6a;
    --red: #9c3b2e;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    color: var(--ink);
    background: var(--sand);
    font-family: "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
  }}
  header, main {{ width: min(1100px, calc(100% - 32px)); margin: 0 auto; }}
  header {{ padding: 40px 0 8px; }}
  h1 {{ font-size: clamp(32px, 5vw, 48px); line-height: 1.05; margin: 0 0 12px; letter-spacing: -0.03em; }}
  h2 {{ font-size: 22px; margin: 0 0 8px; }}
  .lede {{ font-size: 19px; line-height: 1.45; max-width: 46rem; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 28px 0; }}
  .kpi {{ background: white; border: 1px solid var(--line); padding: 14px 16px; }}
  .kpi b {{ display: block; font-size: 28px; letter-spacing: -0.03em; }}
  .kpi span {{ color: var(--muted); font-size: 13px; font-family: "Avenir Next", "Segoe UI", sans-serif; }}
  section {{ background: white; border: 1px solid var(--line); padding: 8px 12px 18px; margin: 0 0 16px; }}
  .note {{ color: var(--muted); font-size: 14px; line-height: 1.45; font-family: "Avenir Next", "Segoe UI", sans-serif; }}
  footer {{ width: min(1100px, calc(100% - 32px)); margin: 8px auto 40px; color: var(--muted); font-size: 13px; line-height: 1.5; font-family: "Avenir Next", "Segoe UI", sans-serif; }}
  @media (max-width: 800px) {{ .kpis {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<header>
  <p class="note">Public data only · retrieved 26 October 2026 · government and national collections</p>
  <h1>School education in the Northern Territory is two systems, not one.</h1>
  <p class="lede">{lede}</p>
  <div class="kpis">
    {kpis}
  </div>
</header>
<main>
  {sections}
</main>
<footer>
  Attendance rates in the national chart are RoGS Table 4A.19, all schools, Years 1–10. Semester 1 collection; 2020 was not published.
  NT region rates are Department of Education government schools, whole of 2024, and are not the same measure.
  NAPLAN proficiency shares are among assessed students. Students who were absent are excluded from the mean and from the proficiency denominator.
  School points are NT government schools joined to the ACARA profile. Cells suppressed by the department (enrolment under 12, or distance education without an attendance collection) are omitted, not treated as zero.
  This page is a descriptive account of published aggregates. It is not a community-controlled dataset and it is not a ranking of schools.
</footer>
</body>
</html>
"""


def _kpi(value: str, label: str) -> str:
    return f'<div class="kpi"><b>{value}</b><span>{label}</span></div>'


def _section(title: str, note: str, html: str) -> str:
    return f"<section><h2>{title}</h2><p class='note'>{note}</p>{html}</section>"


def _load_numbers() -> dict:
    text = (FIGURES.parent / "key_numbers.json").read_text(encoding="utf-8")
    return json.loads(text.replace(": NaN", ": null").replace(": nan", ": null"))


def build_static_dashboard() -> Path:
    numbers = _load_numbers()
    rogs = pd.read_parquet(SILVER / "rogs_attendance.parquet")
    attendance = rogs[(rogs["sector"] == "All schools") & (rogs["year_span"] == "Years 1-10") & (rogs["jurisdiction"].isin(["NT", "Aust"]))]
    remoteness = pd.read_parquet(SILVER / "rogs_attendance_remoteness.parquet")
    remote = remoteness[
        (remoteness["calendar_year"] == 2025)
        & (remoteness["sector"] == "All schools")
        & (remoteness["year_span"] == "Years 1-10")
        & (remoteness["population"].str.contains("Aboriginal", na=False))
        & (remoteness["jurisdiction"].isin(["NT", "WA", "Qld", "Aust"]))
    ]
    regions = pd.read_parquet(GOLD / "nt_region_year.parquet")
    region = regions[
        (regions["calendar_year"] == 2024)
        & (regions["period"] == "whole_year")
        & (regions["region"].isin(["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]))
    ]
    schools = pd.read_parquet(GOLD / "school_year.parquet")
    schools = schools[
        (schools["calendar_year"] == 2024)
        & (schools["period"] == "whole_year")
        & (schools["attendance_rate"].notna())
        & (schools["indigenous_pct"].notna())
    ]
    naplan = pd.read_parquet(SILVER / "naplan_results.parquet")
    naplan = naplan[
        (naplan["calendar_year"] == 2025)
        & (naplan["year_level"] == 3)
        & (naplan["domain"] == "Reading")
        & (naplan["jurisdiction"].isin(["NT", "Aust"]))
    ]
    retention = pd.read_parquet(SILVER / "abs_apparent_retention.parquet")
    retention = retention[
        (retention["year_range"] == "Year 7/8 - Year 12")
        & (retention["sector"] == "All affiliations")
        & (retention["sex"] == "Persons")
        & (retention["calendar_year"] == 2025)
        & (retention["jurisdiction"].isin(["NT", "WA", "Qld", "SA"]))
    ]
    levels = pd.read_parquet(GOLD / "nt_yearlevel_year.parquet")
    levels = levels[
        (levels["calendar_year"] == 2024)
        & (levels["period"] == "term_4")
        & (levels["row_kind"] == "detail")
        & (levels["population"].isin(["indigenous", "non_indigenous"]))
        & (levels["year_level"].astype(str).str.startswith(("Year", "Pre", "Tran")))
    ]
    figures = [
        ("The national attendance gap widened, and it is an Aboriginal gap", "RoGS, all schools. Non-Indigenous attendance in the NT matches Australia.", attendance_trend(attendance)),
        ("Outer regional NT looks like the rest of the country. Very remote NT does not.", "Aboriginal and Torres Strait Islander students, Years 1–10, 2025.", remoteness_comparison(remote)),
        ("Inside government schools, Barkly and East Arnhem are not on the Darwin scale.", "Whole-year 2024. Region boundaries from 2020.", region_comparison(region)),
        ("School by school, attendance falls as Indigenous enrolment rises.", "Marker size is enrolment. Distance-education schools without an attendance rate are excluded.", school_scatter(schools)),
        ("The low rates are in the centre, the Barkly, Arnhem Land and the remote Top End.", "2024 government schools with a published attendance rate and an ACARA coordinate.", school_map(schools)),
        ("NAPLAN: most Aboriginal Year 3 students in the NT are in the lowest reading level.", "Proficiency is among students who were assessed. Absence is on the hover.", naplan_support(naplan)),
        ("Year 12 apparent retention has not moved in the NT while it has in Western Australia.", "ABS capped apparent retention, all affiliations, persons, 2025. Not a true cohort rate.", retention_chart(retention)),
        (
            "Inside government schools, Aboriginal attendance falls again in the middle years.",
            "Term 4 2024. The department did not publish a whole-year year-level table for 2024. Enrolment is on the hover: Aboriginal Year 12 is a much smaller group than Year 10.",
            year_level_attendance(levels),
        ),
    ]
    blocks = []
    include_js = True
    for title, note, figure in figures:
        html = pio.to_html(figure, full_html=False, include_plotlyjs=include_js, config={"displayModeBar": False})
        include_js = False
        blocks.append(_section(title, note, html))
    gaps = numbers["rogs_years_1_10_all_schools"]
    remote_numbers = numbers["remoteness_2025_indigenous_years_1_10"]
    nap = numbers["naplan_2025_year3_reading"]["nt_indigenous"]
    y12 = next(row for row in numbers["closing_the_gap_year12"]["actual"] if row["jurisdiction"] == "NT" and row["year_label"] == "2021")
    spend = numbers["expenditure_per_fte_government_2023_24"]["total_nt"]
    lede = (
        f"In 2025, Aboriginal and Torres Strait Islander students in the NT attended {gaps['nt_indigenous_2025']}% of the time "
        f"in Years 1–10, down from {gaps['nt_indigenous_2016']}% in 2016. Non-Indigenous students in the NT attended "
        f"{gaps['nt_non_indigenous_2025']}%, the same as Australia ({gaps['aust_non_indigenous_2025']}%). "
        f"In outer regional areas the Aboriginal attendance rate matches the national figure. In very remote NT it is "
        f"{remote_numbers['nt_very_remote']}%."
    )
    kpis = "".join(
        [
            _kpi(f"{gaps['nt_indigenous_2025']}%", "NT Aboriginal attendance, Years 1–10, 2025"),
            _kpi(f"{gaps['nt_indigenous_2016'] - gaps['nt_indigenous_2025']:.1f} pp", "Decline since 2016"),
            _kpi(f"{remote_numbers['nt_very_remote']}%", "Very remote NT, Aboriginal students, 2025"),
            _kpi(f"{nap['needs_additional_support_pct']}%", "NT Aboriginal Year 3 reading, needs support, 2025"),
            _kpi(f"{y12['value']}%", "NT Year 12 or equivalent, ages 20–24, 2021"),
            _kpi(f"${spend:,.0f}", "Government recurrent funding per student, NT, 2023–24"),
            _kpi(f"{numbers['student_teacher_ratio_government_2025']['NT']}", "NT government students per teacher, 2025"),
            _kpi(f"{numbers['enrolment_fte']['nt_2025']['indigenous_share_pct']}%", "NT students who are Indigenous, 2025"),
        ]
    )
    # Eight KPIs read better as two rows of four. The grid is four columns.
    DASHBOARD_DIST.mkdir(parents=True, exist_ok=True)
    destination = DASHBOARD_DIST / "index.html"
    destination.write_text(TEMPLATE.format(lede=lede, kpis=kpis, sections="\n".join(blocks)), encoding="utf-8")
    return destination
