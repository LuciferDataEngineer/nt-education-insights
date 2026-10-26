"""Interactive view of the Northern Territory school education marts.

Run from the repository root:

    streamlit run dashboard/app.py --server.port 8765
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ntedu.charts import (  # noqa: E402
    attendance_trend,
    funding_comparison,
    naplan_support,
    region_comparison,
    remoteness_comparison,
    retention_chart,
    retention_trend,
    school_map,
    school_scatter,
    year_level_attendance,
)
from ntedu.config import FIGURES, GOLD, SILVER  # noqa: E402

REGIONS = ["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]
GEO_ORDER = ["Outer Regional", "Remote", "Very Remote"]


def _load_numbers() -> dict:
    path = FIGURES.parent / "key_numbers.json"
    text = path.read_text(encoding="utf-8").replace(": NaN", ": null").replace(": nan", ": null")
    return json.loads(text)


@st.cache_data(show_spinner="Reading the attendance marts")
def load_frames() -> dict[str, pd.DataFrame]:
    required = [
        SILVER / "rogs_attendance.parquet",
        SILVER / "rogs_attendance_remoteness.parquet",
        GOLD / "nt_region_year.parquet",
        GOLD / "school_year.parquet",
        GOLD / "nt_yearlevel_year.parquet",
        SILVER / "naplan_results.parquet",
        SILVER / "abs_apparent_retention.parquet",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing marts: " + ", ".join(missing))
    rogs = pd.read_parquet(SILVER / "rogs_attendance.parquet")
    remoteness = pd.read_parquet(SILVER / "rogs_attendance_remoteness.parquet")
    return {
        "attendance": rogs[
            (rogs["sector"] == "All schools")
            & (rogs["year_span"] == "Years 1-10")
            & (rogs["jurisdiction"].isin(["NT", "Aust"]))
        ],
        "remoteness": remoteness[
            (remoteness["sector"] == "All schools")
            & (remoteness["year_span"] == "Years 1-10")
            & (remoteness["population"].str.contains("Aboriginal", na=False))
            & (remoteness["jurisdiction"].isin(["NT", "WA", "Qld", "Aust"]))
        ],
        "regions": pd.read_parquet(GOLD / "nt_region_year.parquet"),
        "schools": pd.read_parquet(GOLD / "school_year.parquet"),
        "levels": pd.read_parquet(GOLD / "nt_yearlevel_year.parquet"),
        "naplan": pd.read_parquet(SILVER / "naplan_results.parquet"),
        "retention": pd.read_parquet(SILVER / "abs_apparent_retention.parquet"),
    }


def _weighted(frame: pd.DataFrame, column: str) -> float | None:
    usable = frame.dropna(subset=[column, "enrolment"])
    usable = usable[usable["enrolment"] > 0]
    if usable.empty:
        return None
    return float((usable[column] * usable["enrolment"]).sum() / usable["enrolment"].sum())


def _pct(value: float | None, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{digits}f}%"


def _show(figure: go.Figure) -> None:
    st.plotly_chart(figure, width="stretch")


def _schools_view(schools: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Government schools")
    st.sidebar.caption("These filters change the school chart, the map, and the table. National charts are not filtered.")
    years = sorted(int(year) for year in schools["calendar_year"].unique())
    default_year = 2024 if 2024 in years else years[-1]
    year = st.sidebar.selectbox("Year", years, index=years.index(default_year))
    periods = sorted(schools.loc[schools["calendar_year"].eq(year), "period"].unique())
    period_labels = {"whole_year": "Whole year", "term_1": "Term 1", "term_3": "Term 3", "term_4": "Term 4"}
    default_period = "whole_year" if "whole_year" in periods else periods[-1]
    period = st.sidebar.selectbox(
        "Collection",
        periods,
        index=periods.index(default_period),
        format_func=lambda item: period_labels.get(item, item),
    )
    geos = [item for item in GEO_ORDER if item in set(schools["geolocation"].dropna())]
    chosen_geo = st.sidebar.multiselect("Remoteness", geos, default=geos)
    types = sorted(item for item in schools["school_type"].dropna().unique())
    chosen_types = st.sidebar.multiselect("School type", types, default=types)
    query = st.sidebar.text_input("School name contains")
    view = schools[schools["calendar_year"].eq(year) & schools["period"].eq(period)].copy()
    if chosen_geo:
        view = view[view["geolocation"].isin(chosen_geo) | view["geolocation"].isna()]
    else:
        view = view.iloc[0:0]
    if chosen_types:
        view = view[view["school_type"].isin(chosen_types) | view["school_type"].isna()]
    else:
        view = view.iloc[0:0]
    if query.strip():
        view = view[view["school_name"].str.contains(query.strip(), case=False, na=False)]
    return view


def _headline(numbers: dict) -> None:
    gaps = numbers["rogs_years_1_10_all_schools"]
    remote = numbers["remoteness_2025_indigenous_years_1_10"]
    spend = numbers["expenditure_per_fte_government_2023_24"]
    kept = pd.DataFrame(numbers["apparent_retention_year7_to_12"])
    nt_now = float(kept[(kept["jurisdiction"] == "NT") & (kept["calendar_year"] == 2025)]["arr_indigenous"].iloc[0])
    nt_then = float(kept[(kept["jurisdiction"] == "NT") & (kept["calendar_year"] == 2016)]["arr_indigenous"].iloc[0])
    wa_now = float(kept[(kept["jurisdiction"] == "WA") & (kept["calendar_year"] == 2025)]["arr_indigenous"].iloc[0])
    drop = gaps["nt_indigenous_2016"] - gaps["nt_indigenous_2025"]
    columns = st.columns(4)
    columns[0].metric(
        "NT Aboriginal attendance, 2025",
        f"{gaps['nt_indigenous_2025']}%",
        delta=f"{-drop:.1f} pp since 2016",
        delta_color="inverse",
    )
    columns[1].metric(
        "Very remote NT, Aboriginal",
        f"{remote['nt_very_remote']}%",
        delta=f"{remote['nt_very_remote'] - remote['aust_very_remote']:.1f} pp vs Australia",
        delta_color="inverse",
    )
    columns[2].metric(
        "NT Aboriginal Year 12 retention",
        f"{nt_now:.1f}%",
        delta=f"{wa_now - nt_now:.1f} pp behind WA",
        delta_color="off",
    )
    columns[3].metric(
        f"Funding per student, {spend['dollars']}",
        f"${spend['total_nt']:,.0f}",
        delta=f"${spend['total_nt'] - spend['total_aust']:,.0f} vs Australia",
        delta_color="off",
    )
    st.caption(
        f"Years 1–10, all schools. Non-Indigenous students in the NT attended {gaps['nt_non_indigenous_2025']}%, "
        f"level with Australia ({gaps['aust_non_indigenous_2025']}%). "
        f"NT Aboriginal apparent retention was {nt_then:.1f}% in 2016. "
        "The school filters in the sidebar do not change these four figures."
    )


def _kpi_row(view: pd.DataFrame) -> None:
    published = view[view["attendance_rate"].notna()]
    weighted = _weighted(published, "attendance_rate")
    indigenous = _weighted(view.dropna(subset=["indigenous_pct"]), "indigenous_pct")
    under_50 = published[published["attendance_rate"] < 0.50]
    enrolment = float(published["enrolment"].sum()) if not published.empty else 0.0
    low_share = None
    if enrolment:
        low_share = float(under_50["enrolment"].sum() / enrolment * 100)
    columns = st.columns(4)
    columns[0].metric("Schools with a published rate", f"{len(published):,}")
    columns[1].metric("Enrolment-weighted attendance", _pct(None if weighted is None else weighted * 100))
    columns[2].metric("Enrolment in schools under 50%", _pct(low_share))
    columns[3].metric("Indigenous enrolment, weighted", _pct(indigenous))


def _attendance_tab(frames: dict[str, pd.DataFrame], numbers: dict) -> None:
    gaps = numbers["rogs_years_1_10_all_schools"]
    st.markdown(
        f"Aboriginal and Torres Strait Islander attendance in the NT was **{gaps['nt_indigenous_2025']}%** "
        f"in 2025, down from **{gaps['nt_indigenous_2016']}%** in 2016. Non-Indigenous students in the NT "
        f"attended **{gaps['nt_non_indigenous_2025']}%**, against **{gaps['aust_non_indigenous_2025']}%** nationally."
    )
    _show(attendance_trend(frames["attendance"]))
    st.caption(
        "RoGS Table 4A.19, Semester 1, Years 1–10. Solid lines are the NT. Dashed lines are Australia. "
        "2020 was not published. All-student series are omitted so the Aboriginal and non-Indigenous lines can be read."
    )
    remote_numbers = numbers["remoteness_2025_indigenous_years_1_10"]
    remote = frames["remoteness"][
        (frames["remoteness"]["calendar_year"] == 2025) & (frames["remoteness"]["jurisdiction"].isin(["NT", "Aust"]))
    ]
    _show(remoteness_comparison(remote))
    st.caption(
        "Table 4A.16, Aboriginal and Torres Strait Islander students, 2025. "
        f"WA very remote is {remote_numbers['wa_very_remote_indigenous']}%; "
        f"Queensland is {remote_numbers['qld_very_remote_indigenous']}%."
    )

    regions = frames["regions"]
    region_years = sorted(int(year) for year in regions["calendar_year"].unique())
    left, right = st.columns([1, 3])
    with left:
        region_year = st.selectbox("Region year", region_years, index=region_years.index(2024))
        region_periods = sorted(regions.loc[regions["calendar_year"].eq(region_year), "period"].unique())
        region_period = st.selectbox(
            "Region collection",
            region_periods,
            index=region_periods.index("whole_year") if "whole_year" in region_periods else 0,
            format_func=lambda item: {"whole_year": "Whole year", "term_1": "Term 1", "term_3": "Term 3", "term_4": "Term 4"}.get(item, item),
        )
    chosen = regions[
        regions["calendar_year"].eq(region_year)
        & regions["period"].eq(region_period)
        & regions["region"].isin(REGIONS)
        & regions["population"].isin(["indigenous", "non_indigenous"])
    ]
    with right:
        if chosen.empty:
            st.info("The department did not publish that region collection.")
        else:
            _show(region_comparison(chosen))
    if chosen["comparable_with_2020_boundaries"].eq(False).any():
        st.warning("East Arnhem and Top End changed boundaries in 2020. Years before 2020 are not the same geography.")

    levels = frames["levels"]
    level_years = sorted(int(year) for year in levels["calendar_year"].unique())
    level_year = st.selectbox("Year-level year", level_years, index=level_years.index(2024) if 2024 in level_years else len(level_years) - 1)
    level_periods = sorted(levels.loc[levels["calendar_year"].eq(level_year), "period"].unique())
    preferred = "whole_year" if "whole_year" in level_periods else level_periods[-1]
    level_period = st.selectbox(
        "Year-level collection",
        level_periods,
        index=list(level_periods).index(preferred),
        format_func=lambda item: {"whole_year": "Whole year", "term_1": "Term 1", "term_3": "Term 3", "term_4": "Term 4"}.get(item, item),
    )
    level_rows = levels[
        levels["calendar_year"].eq(level_year)
        & levels["period"].eq(level_period)
        & levels["row_kind"].eq("detail")
        & levels["population"].isin(["indigenous", "non_indigenous"])
    ]
    if level_rows.empty:
        st.info("No year-level rows for that collection.")
    else:
        _show(year_level_attendance(level_rows))
        st.caption("NT Department of Education, government schools. Hover a point for the enrolment behind the rate. 2024 is Term 4, not the whole year.")


def _schools_tab(view: pd.DataFrame) -> None:
    _kpi_row(view)
    if view.empty:
        st.info("No government schools match these filters. Widen remoteness, school type, or the name search.")
        return
    published = view[view["attendance_rate"].notna() & view["indigenous_pct"].notna()]
    if published.empty:
        st.warning("These schools are in the enrolment file, but every attendance rate or Indigenous share is suppressed.")
    else:
        _show(school_scatter(published))
        located = published.dropna(subset=["latitude", "longitude"])
        if located.empty:
            st.info("None of the filtered schools have an ACARA coordinate, so the map is empty.")
        else:
            _show(school_map(located))
            st.caption("Marker colour is the attendance rate. Schools the department suppressed, and distance-education schools without a rate, are omitted.")
    table = view.copy()
    table["Attendance %"] = (table["attendance_rate"] * 100).round(1)
    table["Indigenous %"] = table["indigenous_pct"].round(1)
    table["Bottom SEA quarter %"] = table["bottom_sea_pct"].round(1)
    table["Enrolment"] = table["enrolment"].round(0)
    show = table[
        [
            "school_name",
            "suburb",
            "geolocation",
            "school_type",
            "Enrolment",
            "Attendance %",
            "Indigenous %",
            "icsea",
            "Bottom SEA quarter %",
            "match_method",
        ]
    ].rename(
        columns={
            "school_name": "School",
            "suburb": "Suburb",
            "geolocation": "Remoteness",
            "school_type": "Type",
            "icsea": "ICSEA",
            "match_method": "ACARA match",
        }
    )
    show = show.sort_values("Attendance %", na_position="last")
    st.dataframe(show, width="stretch", hide_index=True)
    suppressed = int(view["attendance_rate"].isna().sum())
    if suppressed:
        st.caption(f"{suppressed} schools in this filter have no published attendance rate. Suppression is not zero.")


def _naplan_tab(naplan: pd.DataFrame, numbers: dict) -> None:
    reading = numbers["naplan_2025_year3_reading"]
    st.markdown(
        f"In 2025, **{reading['nt_indigenous']['needs_additional_support_pct']}%** of assessed Aboriginal Year 3 "
        f"students in the NT were in the lowest reading level. **{reading['nt_indigenous']['absent_pct']}%** were absent. "
        f"In very remote areas the support share was **{reading['nt_indigenous_very_remote']['needs_additional_support_pct']}%** "
        f"and absence was **{reading['nt_indigenous_very_remote']['absent_pct']}%**."
    )
    focus = naplan[
        (naplan["calendar_year"] == 2025)
        & (naplan["year_level"] == 3)
        & (naplan["domain"] == "Reading")
        & (naplan["jurisdiction"].isin(["NT", "Aust"]))
    ]
    _show(naplan_support(focus))
    st.caption("Proficiency shares use assessed students as the denominator. Absence is a separate rate. Means exclude students who were absent.")

    years = sorted(int(year) for year in naplan["calendar_year"].unique())
    domains = ["Reading", "Numeracy", "Writing", "Spelling", "Grammar and Punctuation"]
    c1, c2, c3 = st.columns(3)
    year = c1.selectbox("NAPLAN year", years, index=years.index(2025) if 2025 in years else 0)
    level = c2.selectbox("Year level", [3, 5, 7, 9], index=0)
    domain = c3.selectbox("Domain", domains, index=0)
    subgroups = ["Indigenous", "Non-Indigenous", "All", "Indigenous very remote", "Very remote"]
    subset = naplan[
        naplan["calendar_year"].eq(year)
        & naplan["year_level"].eq(level)
        & naplan["domain"].eq(domain)
        & naplan["jurisdiction"].isin(["NT", "Aust"])
        & naplan["subgroup"].isin(subgroups)
    ]
    if subset.empty:
        st.info("ACARA did not publish that domain for this year and year level.")
        return
    order = [(jurisdiction, subgroup) for jurisdiction in ["NT", "Aust"] for subgroup in subgroups]
    rows = []
    for jurisdiction, subgroup in order:
        hit = subset[(subset["jurisdiction"] == jurisdiction) & (subset["subgroup"] == subgroup)]
        if hit.empty or pd.isna(hit["needs_additional_support_pct"].iloc[0]):
            continue
        rows.append(
            {
                "Group": f"{jurisdiction}, {subgroup}",
                "Needs additional support %": round(float(hit["needs_additional_support_pct"].iloc[0]), 1),
                "Absent %": None if pd.isna(hit["absent_pct"].iloc[0]) else round(float(hit["absent_pct"].iloc[0]), 1),
                "Mean": None if pd.isna(hit["mean_score"].iloc[0]) else round(float(hit["mean_score"].iloc[0]), 1),
                "Margin of error": None if pd.isna(hit["mean_score_moe"].iloc[0]) else round(float(hit["mean_score_moe"].iloc[0]), 1),
                "Enrolled": None if pd.isna(hit["enrolled_students"].iloc[0]) else int(hit["enrolled_students"].iloc[0]),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _gap_tab(retention: pd.DataFrame, numbers: dict) -> None:
    series = retention[
        (retention["year_range"] == "Year 7/8 - Year 12")
        & (retention["sector"] == "All affiliations")
        & (retention["sex"] == "Persons")
        & (retention["jurisdiction"].isin(["NT", "WA"]))
    ]
    _show(retention_trend(series))
    st.caption("ABS Schools, Table 64a, Aboriginal apparent retention from Year 7/8 to Year 12. The NT line stays near 35% while Western Australia rises. Not a true cohort rate.")
    latest = series[series["calendar_year"] == 2025]
    others = retention[
        (retention["year_range"] == "Year 7/8 - Year 12")
        & (retention["sector"] == "All affiliations")
        & (retention["sex"] == "Persons")
        & (retention["calendar_year"] == 2025)
        & (retention["jurisdiction"].isin(["NT", "WA", "Qld", "SA"]))
    ]
    _show(retention_chart(others if not others.empty else latest))
    st.caption("Same measure in 2025, Aboriginal and non-Indigenous, for the jurisdictions nearest the comparison.")
    spend = numbers["expenditure_per_fte_government_2023_24"]
    _show(funding_comparison(spend["total_nt"], spend["total_aust"]))
    st.caption(f"RoGS Table 4A.32, government recurrent funding per FTE student, {spend['dollars']}.")
    actual = pd.DataFrame(numbers["closing_the_gap_year12"]["actual"])
    actual = actual[actual["year_label"].isin(["2016", "2021"])]
    pivot = actual.pivot(index="jurisdiction", columns="year_label", values="value").reindex(
        ["NT", "WA", "SA", "Qld", "Tas", "NSW", "Vic", "ACT", "Aust"]
    )
    st.subheader("Year 12 or equivalent, ages 20–24")
    st.dataframe(pivot.round(1), width="stretch")
    target = numbers["closing_the_gap_year12"]["target_national"]
    nt_path = next(
        row["value"]
        for row in numbers["closing_the_gap_year12"]["path_2031"]
        if row["jurisdiction"] == "NT" and row.get("description_7") == "Linear regression estimates"
    )
    st.markdown(
        f"The national Closing the Gap target is **{target}%** by 2031. "
        f"The Commission's linear estimate for the NT, on the census series, is **{nt_path}%**."
    )
    kept = pd.DataFrame(numbers["apparent_retention_year7_to_12"])
    nt = kept[kept["jurisdiction"] == "NT"].sort_values("calendar_year")
    wa = kept[kept["jurisdiction"] == "WA"].sort_values("calendar_year")
    st.markdown(
        "NT Aboriginal apparent retention was "
        + ", ".join(f"**{row.arr_indigenous}%** in {int(row.calendar_year)}" for row in nt.itertuples())
        + ". Western Australia moved from "
        + " to ".join(f"**{row.arr_indigenous}%**" for row in wa.itertuples())
        + " over the same years."
    )


def _model_note(numbers: dict) -> None:
    model = numbers["regression_2024_government_schools"]
    with st.expander("What the school regression does and does not say"):
        st.write(model["label"])
        terms = pd.DataFrame(model["terms"])
        terms["estimate"] = terms["estimate"].round(3)
        terms["std_error"] = terms["std_error"].round(3)
        terms["p_value"] = terms["p_value"].map(lambda value: f"{value:.3g}")
        st.dataframe(terms, width="stretch", hide_index=True)
        st.caption(
            f"n = {model['n']}, R² = {model['r_squared']}. "
            "Weighted by enrolment, HC1 standard errors. This is a description of published school aggregates, not a causal estimate and not a ranking."
        )


def main() -> None:
    st.set_page_config(
        page_title="NT school education",
        page_icon=":material/school:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("The attendance gap is an Aboriginal gap")
    st.caption(
        "Public collections only. Retrieved 26 October 2026. "
        "Government attendance is the NT Department of Education. National comparisons are RoGS, ABS, ACARA NAPLAN, and Closing the Gap."
    )
    try:
        frames = load_frames()
        numbers = _load_numbers()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.markdown("Rebuild the marts from the repository root with `python -m ntedu.cli all`.")
        return
    except json.JSONDecodeError as exc:
        st.error(f"reports/key_numbers.json could not be read ({exc}).")
        st.markdown("Regenerate it with `python -m ntedu.cli analysis`.")
        return

    view = _schools_view(frames["schools"])
    _headline(numbers)
    territory, schools, naplan, gap = st.tabs(["Territory and Australia", "Schools", "NAPLAN", "Year 12 and Closing the Gap"])
    with territory:
        _attendance_tab(frames, numbers)
    with schools:
        _schools_tab(view)
        _model_note(numbers)
    with naplan:
        _naplan_tab(frames["naplan"], numbers)
    with gap:
        _gap_tab(frames["retention"], numbers)

    st.divider()
    st.caption(
        "Cells marked np by the department (usually enrolment under 12) are null, not zero. "
        "RoGS attendance is Semester 1 for all schools. NT region and school rates are government schools and a different calendar. "
        "Do not subtract one from the other. School names are joined to ACARA with exact and fuzzy matching; the 2024 whole-year match rate is 95.4%. "
        "This dashboard restates published aggregates. It is not a community-controlled dataset and it does not rank schools."
    )


if __name__ == "__main__":
    main()
