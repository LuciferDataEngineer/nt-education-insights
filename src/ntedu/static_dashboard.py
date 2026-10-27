"""Self-contained HTML dashboard. Opens in a browser with no server."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.io as pio

from ntedu.charts import (
    attendance_trend,
    funding_comparison,
    naplan_support,
    region_comparison,
    remoteness_comparison,
    retention_trend,
    school_scatter,
)
from ntedu.config import DASHBOARD_DIST, FIGURES, GOLD, SILVER
from ntedu.decisions import decision_html

REPO = "https://github.com/LuciferDataEngineer/nt-education-insights"
README = f"{REPO}/blob/main/README.md"
INSIGHTS = f"{REPO}/blob/main/INSIGHTS.md"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Northern Territory school education</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@420;560;680&display=swap" rel="stylesheet"/>
<style>
  :root {{
    --ink: #0B2545;
    --muted: #3E4C59;
    --bg: #F4F6F8;
    --card: #ffffff;
    --line: #D5DDE5;
    --navy: #0B2545;
    --teal: #0F6E6E;
    --terracotta: #A84E1E;
    --grey: #4A5560;
    --concern: #9B2C2C;
    --watch: #A56B00;
    --good: #1F7A4D;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    color: var(--ink);
    background: var(--bg);
    font-family: Inter, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 16px;
    line-height: 1.45;
  }}
  .wrap {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; }}
  header.band {{
    background: var(--navy);
    color: #ffffff;
    padding: 36px 0 28px;
    border-bottom: 6px solid var(--terracotta);
  }}
  .eyebrow {{
    margin: 0 0 10px;
    color: #F3D7C8;
    font-size: 12px;
    font-weight: 680;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }}
  h1 {{
    margin: 0;
    max-width: 18ch;
    font-size: clamp(34px, 5vw, 52px);
    line-height: 1.02;
    letter-spacing: -0.038em;
    font-weight: 680;
    color: #ffffff;
  }}
  .lede {{ max-width: 42rem; margin: 14px 0 0; color: #E7EEF6; font-size: 18px; line-height: 1.45; }}
  .key {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    list-style: none;
    margin: 22px 0 0;
    padding: 0;
    color: #F4F7FB;
    font-size: 13px;
    font-weight: 560;
  }}
  .key li {{ display: flex; align-items: center; gap: 8px; }}
  .swatch {{ width: 14px; height: 14px; border-radius: 3px; display: inline-block; }}
  .decisions {{ padding: 28px 0 8px; }}
  .decisions h2 {{
    margin: 0;
    font-size: clamp(26px, 3vw, 32px);
    letter-spacing: -0.03em;
    line-height: 1.15;
  }}
  .metric-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 16px;
  }}
  .metric {{
    background: var(--card);
    border: 1px solid var(--line);
    border-top: 4px solid var(--concern);
    border-radius: 14px;
    padding: 14px 16px 16px;
  }}
  .metric.watch {{ border-top-color: var(--watch); background: #FFFCF4; }}
  .metric.concern {{ border-top-color: var(--concern); background: #FFF8F7; }}
  .metric.ontrack {{ border-top-color: var(--good); background: #F4FBF7; }}
  .metric .value {{
    margin: 8px 0 0;
    font-size: clamp(28px, 3vw, 34px);
    font-weight: 680;
    letter-spacing: -0.04em;
    font-variant-numeric: tabular-nums;
    line-height: 1;
    color: var(--ink);
  }}
  .metric .label {{ margin: 8px 0 0; font-size: 14px; font-weight: 680; line-height: 1.3; }}
  .metric .trend, .metric .gap {{ margin: 6px 0 0; font-size: 13px; line-height: 1.4; }}
  .metric .trend {{ color: var(--ink); font-weight: 560; }}
  .metric .gap {{ color: var(--muted); }}
  .metric .action {{ margin: 8px 0 0; font-size: 14px; line-height: 1.45; }}
  .pill {{
    display: inline-block;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 680;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  .pill.concern {{ background: #F8E8E6; color: #7A1F1A; }}
  .pill.watch {{ background: #FBF3D5; color: #5C4300; }}
  .pill.ontrack {{ background: #E7F5EC; color: #0E5C36; }}
  .decision-split {{
    display: grid;
    grid-template-columns: 0.9fr 1.1fr;
    gap: 12px;
    margin-top: 12px;
  }}
  .panel {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px;
  }}
  .panel h3 {{ margin: 0 0 8px; font-size: 18px; letter-spacing: -0.02em; }}
  .recs {{ margin: 0; padding-left: 18px; }}
  .recs li {{ margin: 0 0 10px; font-size: 14px; line-height: 1.45; }}
  .table-scroll {{ overflow-x: auto; }}
  table.gaps {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.gaps th {{
    text-align: left;
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted);
    border-bottom: 2px solid var(--line);
    padding: 6px 8px;
    white-space: nowrap;
  }}
  table.gaps td {{
    border-bottom: 1px solid var(--line);
    padding: 8px;
    vertical-align: top;
  }}
  table.gaps td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 12px 0 20px;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px 16px 6px;
    min-width: 0;
  }}
  .card.wide {{ grid-column: 1 / -1; }}
  .card h2 {{ margin: 0; font-size: 18px; letter-spacing: -0.02em; line-height: 1.25; font-weight: 680; }}
  .take {{ margin: 6px 0 2px; color: var(--muted); font-size: 14px; line-height: 1.45; }}
  .chart {{ width: 100%; min-width: 0; }}
  .chart .plotly-graph-div, .chart .js-plotly-plot {{ width: 100% !important; }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
  }}
  .legend li {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--ink);
  }}
  .legend i {{
    display: inline-block;
    flex: 0 0 auto;
  }}
  .legend i.line {{ width: 18px; height: 3px; border-radius: 2px; }}
  .legend i.dash {{ width: 18px; height: 0; border-top: 2px dashed; background: transparent; }}
  .legend i.bar {{ width: 11px; height: 11px; border-radius: 2px; }}
  .legend i.dot {{ width: 11px; height: 11px; border-radius: 50%; }}
  .note-card h2 {{ margin-bottom: 8px; }}
  .note-card ul {{ margin: 0; padding-left: 18px; color: var(--muted); font-size: 14px; }}
  .note-card li {{ margin: 0 0 8px; }}
  footer {{
    padding: 8px 0 48px;
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
  }}
  footer h2 {{ margin: 0 0 8px; color: var(--ink); font-size: 16px; letter-spacing: -0.02em; }}
  footer ul {{ margin: 0 0 12px; padding-left: 18px; }}
  footer a {{ color: var(--navy); }}
  .links {{ display: flex; flex-wrap: wrap; gap: 14px; margin: 12px 0; font-weight: 680; }}
  @media (max-width: 860px) {{
    .metric-grid, .decision-split, .grid {{ grid-template-columns: 1fr; }}
    .card.wide {{ grid-column: auto; }}
    header.band {{ padding-top: 24px; }}
    .lede {{ font-size: 16px; }}
  }}
</style>
</head>
<body>
<header class="band">
  <div class="wrap">
    <p class="eyebrow">Northern Territory school education · public data · 26 October 2026</p>
    <h1>The attendance gap is an Aboriginal gap.</h1>
    <p class="lede">{lede}</p>
    <ul class="key">
      <li><i class="swatch" style="background:#A84E1E"></i>NT Aboriginal</li>
      <li><i class="swatch" style="background:#0F6E6E"></i>NT non-Indigenous</li>
      <li><i class="swatch" style="background:#4A5560"></i>Australia</li>
      <li><i class="swatch" style="background:#0B2545"></i>WA retention, outer regional schools, NT resourcing</li>
      <li><i class="swatch" style="background:#1F7A4D"></i>On track</li>
      <li><i class="swatch" style="background:#C58A12"></i>Watch</li>
      <li><i class="swatch" style="background:#9B2C2C"></i>Concern</li>
    </ul>
  </div>
</header>
{decision}
<main class="wrap grid">
  {sections}
</main>
<footer class="wrap">
  <h2>About the data</h2>
  <ul>
    <li><a href="https://www.pc.gov.au/ongoing/report-on-government-services/2026/child-care-education-and-training/school-education">Report on Government Services 2026</a>, attendance Tables 4A.16 and 4A.19 and expenditure Table 4A.32. Semester 1, all schools, Years 1–10. 2020 attendance was not published.</li>
    <li><a href="https://education.nt.gov.au/education/statistics-research-and-reports/enrolment-and-attendance">NT Department of Education</a> government schools, whole of 2024 for regions and the school scatter. That collection is not the RoGS semester series. Do not subtract one from the other.</li>
    <li><a href="https://www.acara.edu.au/reporting/national-report-on-schooling-in-australia/data-portal">ACARA</a> school profile, location and NAPLAN national results. Proficiency uses assessed students. Students who were absent are excluded from that share.</li>
    <li><a href="https://www.abs.gov.au/statistics/people/education/schools/2025">ABS Schools, 2025</a>, Table 64a, capped apparent retention from Year 7/8 to Year 12. It is not a true cohort completion rate. <a href="https://www.pc.gov.au/closing-the-gap-data/dashboard/se/outcome-area5">Closing the Gap Outcome 5</a> is a separate census measure.</li>
  </ul>
  <p class="links">
    <a href="{repo}">Repository</a>
    <a href="{readme}">README</a>
    <a href="{insights}">INSIGHTS.md</a>
  </p>
  <p>Suppressed cells stay missing. They are not filled with zero, and schools are not ranked. This is a reading of tables governments already publish, not a community-controlled dataset.</p>
</footer>
</body>
</html>
"""


def _load_numbers() -> dict:
    text = (FIGURES.parent / "key_numbers.json").read_text(encoding="utf-8")
    return json.loads(text.replace(": NaN", ": null").replace(": nan", ": null"))


def _section(title: str, takeaway: str, html: str, *, wide: bool = False) -> str:
    klass = "card wide" if wide else "card"
    return f'<section class="{klass}"><h2>{title}</h2><p class="take">{takeaway}</p><div class="chart">{html}</div></section>'


def _legend_html(figure) -> str:
    items: list[str] = []
    for trace in figure.data:
        name = getattr(trace, "name", None)
        if not name or getattr(trace, "showlegend", True) is False:
            continue
        color = "#0B2545"
        kind = "bar" if getattr(trace, "type", "") == "bar" else "line"
        marker = getattr(trace, "marker", None)
        line = getattr(trace, "line", None)
        marker_color = getattr(marker, "color", None) if marker is not None else None
        line_color = getattr(line, "color", None) if line is not None else None
        if isinstance(marker_color, str):
            color = marker_color
        elif isinstance(line_color, str):
            color = line_color
        mode = getattr(trace, "mode", "") or ""
        if kind == "line" and "lines" not in mode and "markers" in mode:
            kind = "dot"
        if kind == "line" and getattr(line, "dash", None) == "dash":
            kind = "dash"
        style = f"border-top-color:{color}" if kind == "dash" else f"background:{color}"
        items.append(f'<li><i class="{kind}" style="{style}"></i>{name}</li>')
    if not items:
        return ""
    return f'<ul class="legend">{"".join(items)}</ul>'


def _figure_html(figure, *, include_js: bool, div_id: str) -> str:
    legend = _legend_html(figure)
    margin = figure.layout.margin
    figure.update_layout(
        showlegend=False,
        margin=dict(l=margin.l, r=margin.r, t=12, b=margin.b),
    )
    html = pio.to_html(
        figure,
        full_html=False,
        include_plotlyjs=include_js,
        div_id=div_id,
        config={"displayModeBar": False, "responsive": True},
        default_width="100%",
        default_height="100%",
    )
    return legend + html


def build_static_dashboard() -> Path:
    numbers = _load_numbers()
    gaps = numbers["rogs_years_1_10_all_schools"]
    remote_numbers = numbers["remoteness_2025_indigenous_years_1_10"]
    regions_2024 = numbers["nt_government_regions_2024"]
    nap = numbers["naplan_2025_year3_reading"]
    spend = numbers["expenditure_per_fte_government_2023_24"]
    panel = numbers["nt_government_2024_school_panel"]
    retention_rows = pd.DataFrame(numbers["apparent_retention_year7_to_12"])
    nt_ret = retention_rows[retention_rows["jurisdiction"] == "NT"].set_index("calendar_year")
    wa_ret = retention_rows[retention_rows["jurisdiction"] == "WA"].set_index("calendar_year")

    rogs = pd.read_parquet(SILVER / "rogs_attendance.parquet")
    attendance = rogs[
        (rogs["sector"] == "All schools")
        & (rogs["year_span"] == "Years 1-10")
        & (rogs["jurisdiction"].isin(["NT", "Aust"]))
        & (rogs["population"].isin(["Aboriginal and Torres Strait Islander students", "Non-Indigenous students"]))
    ]
    remoteness = pd.read_parquet(SILVER / "rogs_attendance_remoteness.parquet")
    remote = remoteness[
        (remoteness["calendar_year"] == 2025)
        & (remoteness["sector"] == "All schools")
        & (remoteness["year_span"] == "Years 1-10")
        & (remoteness["population"].str.contains("Aboriginal", na=False))
        & (remoteness["jurisdiction"].isin(["NT", "Aust"]))
    ]
    regions = pd.read_parquet(GOLD / "nt_region_year.parquet")
    region = regions[
        (regions["calendar_year"] == 2024)
        & (regions["period"] == "whole_year")
        & (regions["region"].isin(["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]))
        & (regions["population"].isin(["indigenous", "non_indigenous"]))
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
        & (retention["jurisdiction"].isin(["NT", "WA"]))
    ]

    nt_ret_2016 = float(nt_ret.loc[2016, "arr_indigenous"])
    nt_ret_2025 = float(nt_ret.loc[2025, "arr_indigenous"])
    wa_ret_2016 = float(wa_ret.loc[2016, "arr_indigenous"])
    wa_ret_2025 = float(wa_ret.loc[2025, "arr_indigenous"])
    charts = [
        (
            True,
            "NT Aboriginal attendance fell. Non-Indigenous attendance did not.",
            "Years 1–10, all schools. Solid lines are the Northern Territory. Dashed lines are Australia. "
            f"Non-Indigenous students in the NT attended {gaps['nt_non_indigenous_2025']}%, "
            f"against {gaps['aust_non_indigenous_2025']}% nationally.",
            attendance_trend(attendance),
        ),
        (
            False,
            "Outer regional NT matches Australia. Very remote NT does not.",
            f"Aboriginal and Torres Strait Islander students, 2025. Very remote NT is {remote_numbers['nt_very_remote']}%, "
            f"against {remote_numbers['aust_very_remote']}% nationally. "
            f"WA very remote is {remote_numbers['wa_very_remote_indigenous']}%; "
            f"Queensland is {remote_numbers['qld_very_remote_indigenous']}%.",
            remoteness_comparison(remote),
        ),
        (
            False,
            "Darwin is not the Barkly, and it is not East Arnhem.",
            f"Government schools, whole of 2024. Aboriginal attendance is {regions_2024['Darwin']['indigenous']}% in Darwin, "
            f"{regions_2024['Barkly']['indigenous']}% in the Barkly and {regions_2024['East Arnhem']['indigenous']}% in East Arnhem. "
            "Non-Indigenous rates stay high in every region.",
            region_comparison(region),
        ),
        (
            True,
            "Attendance falls as the Aboriginal share of a school rises.",
            "Each point is a government school in 2024 with a published rate. Marker size is enrolment. "
            f"Weighted by enrolment, attendance and Indigenous enrolment move together "
            f"(correlation {panel['enrolment_weighted_correlation_attendance_indigenous_pct']:.2f}). "
            "Suppressed schools are left off the chart, not drawn at zero.",
            school_scatter(schools),
        ),
        (
            False,
            "Most assessed Aboriginal Year 3 students in the NT need reading support.",
            f"{nap['nt_indigenous']['needs_additional_support_pct']}% of assessed Aboriginal students, "
            f"and {nap['nt_indigenous_very_remote']['needs_additional_support_pct']}% in very remote NT, "
            f"where {nap['nt_indigenous_very_remote']['absent_pct']}% were absent. "
            "The proficiency share ignores students who were absent. Hover a bar for the absence rate.",
            naplan_support(naplan),
        ),
        (
            False,
            "NT Aboriginal retention has stayed near 35%. Western Australia’s has not.",
            f"ABS apparent retention, Year 7/8 to Year 12. NT Aboriginal students: "
            f"{nt_ret_2016:.1f}% in 2016 and {nt_ret_2025:.1f}% in 2025. "
            f"WA moved from {wa_ret_2016:.1f}% to {wa_ret_2025:.1f}%. "
            "This is not a true cohort completion rate.",
            retention_trend(retention),
        ),
        (
            False,
            "The NT already spends more per student than Australia.",
            f"Government recurrent funding per student, {spend['dollars']}. "
            f"NT ${spend['total_nt']:,.0f}, Australia ${spend['total_aust']:,.0f}. "
            "The higher spend has not closed the attendance gap.",
            funding_comparison(spend["total_nt"], spend["total_aust"]),
        ),
    ]
    note = (
        '<section class="card note-card"><h2>How to read the rates</h2><ul>'
        "<li>National attendance is Semester 1, all schools. Territory regions and schools are government schools for the whole year.</li>"
        "<li>A blank is a suppressed cell, usually enrolment under 12. It is not a zero.</li>"
        "<li>NAPLAN proficiency excludes students who were absent. In very remote NT that is a large share of the cohort.</li>"
        "</ul></section>"
    )
    blocks = []
    include_js = True
    for index, (wide, title, takeaway, figure) in enumerate(charts, start=1):
        html = _figure_html(figure, include_js=include_js, div_id=f"chart-{index}")
        include_js = False
        blocks.append(_section(title, takeaway, html, wide=wide))
        if len(blocks) == 6:
            blocks.append(note)
    lede = (
        f"In 2025, Aboriginal and Torres Strait Islander students in the NT attended {gaps['nt_indigenous_2025']}% "
        f"of Years 1–10, down from {gaps['nt_indigenous_2016']}% in 2016. Non-Indigenous students in the NT attended "
        f"{gaps['nt_non_indigenous_2025']}%, level with Australia ({gaps['aust_non_indigenous_2025']}%)."
    )
    DASHBOARD_DIST.mkdir(parents=True, exist_ok=True)
    destination = DASHBOARD_DIST / "index.html"
    destination.write_text(
        TEMPLATE.format(
            lede=lede,
            decision=decision_html(numbers),
            sections="\n".join(blocks),
            repo=REPO,
            readme=README,
            insights=INSIGHTS,
        ),
        encoding="utf-8",
    )
    return destination
