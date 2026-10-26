"""Data-quality checks. Fail the build when a published value has been corrupted."""

from __future__ import annotations

import json
import logging

import pandas as pd

from ntedu.config import GOLD, QUALITY, SILVER

logger = logging.getLogger(__name__)


class QualityError(RuntimeError):
    pass


def _expect_close(actual: float, expected: float, tolerance: float, label: str, failures: list[str]) -> None:
    if actual is None or pd.isna(actual) or abs(actual - expected) > tolerance:
        failures.append(f"{label}: got {actual}, expected {expected} ± {tolerance}")


def run_quality() -> dict:
    failures: list[str] = []
    schools = pd.read_parquet(SILVER / "nt_school_attendance.parquet")
    groups = pd.read_parquet(SILVER / "nt_group_attendance.parquet")
    rogs = pd.read_parquet(SILVER / "rogs_attendance.parquet")
    naplan = pd.read_parquet(SILVER / "naplan_results.parquet")
    ctg = pd.read_parquet(SILVER / "ctg_outcome5.parquet")
    matched = pd.read_parquet(SILVER / "nt_school_matched.parquet")

    rates = schools["attendance_rate"].dropna()
    if not rates.empty and ((rates < 0) | (rates > 1)).any():
        failures.append("School attendance rates fall outside 0–1")
    if schools["enrolment"].dropna().lt(0).any():
        failures.append("Negative enrolments in school attendance")

    zuccoli = schools[
        schools["school_name"].eq("Zuccoli Primary School")
        & schools["calendar_year"].eq(2024)
        & schools["period"].eq("whole_year")
    ]
    if zuccoli.empty:
        failures.append("Zuccoli Primary School 2024 whole-year row is missing")
    else:
        _expect_close(float(zuccoli["enrolment"].iloc[0]), 595, 0.1, "Zuccoli 2024 enrolment", failures)
        _expect_close(float(zuccoli["attendance_rate"].iloc[0]), 0.910, 0.001, "Zuccoli 2024 attendance", failures)

    barkly = groups[
        groups["grain"].eq("region")
        & groups["section"].str.contains("Barkly", case=False, na=False)
        & groups["row_label"].str.contains("Region Total", case=False, na=False)
        & groups["calendar_year"].eq(2024)
        & groups["population"].eq("total")
        & groups["period"].eq("whole_year")
    ]
    if barkly.empty:
        failures.append("Barkly 2024 region total is missing")
    else:
        _expect_close(float(barkly["attendance_rate"].iloc[0]), 0.448, 0.002, "Barkly 2024 attendance", failures)

    nt_2025 = rogs[
        rogs["jurisdiction"].eq("NT")
        & rogs["sector"].eq("All schools")
        & rogs["population"].str.startswith("All students")
        & rogs["year_span"].eq("Years 1-10")
        & rogs["calendar_year"].eq(2025)
    ]
    if nt_2025.empty:
        failures.append("RoGS NT 2025 Years 1–10 attendance is missing")
    else:
        _expect_close(float(nt_2025["attendance_rate"].iloc[0]), 0.769, 0.001, "RoGS NT 2025 Years 1-10", failures)

    indig = rogs[
        rogs["jurisdiction"].eq("NT")
        & rogs["sector"].eq("All schools")
        & rogs["population"].str.contains("Aboriginal", case=False, na=False)
        & rogs["year_span"].eq("Years 1-10")
        & rogs["calendar_year"].eq(2025)
    ]
    if indig.empty:
        failures.append("RoGS NT Indigenous 2025 Years 1–10 attendance is missing")
    else:
        _expect_close(float(indig["attendance_rate"].iloc[0]), 0.583, 0.001, "RoGS NT Indigenous 2025", failures)

    ctg_row = ctg[
        ctg["table_number"].eq("SE5a.1")
        & ctg["jurisdiction"].eq("NT")
        & ctg["year_label"].astype(str).eq("2025")
        & ctg["description_3"].eq("Years 1-10")
        & ctg["indigenous_status"].str.contains("Aboriginal", case=False, na=False)
    ]
    if ctg_row.empty:
        failures.append("Closing the Gap NT Indigenous attendance 2025 is missing")
    else:
        _expect_close(float(ctg_row["value"].iloc[0]), 58.3, 0.05, "CtG NT Indigenous attendance 2025", failures)

    nt_naplan = naplan[
        naplan["jurisdiction"].eq("NT")
        & naplan["calendar_year"].eq(2024)
        & naplan["year_level"].eq(3)
        & naplan["domain"].eq("Reading")
        & naplan["subgroup"].eq("Indigenous")
    ]
    if nt_naplan.empty:
        failures.append("NAPLAN NT Indigenous Year 3 reading 2024 is missing")
    else:
        _expect_close(float(nt_naplan["mean_score"].iloc[0]), 242.8, 0.5, "NT Indigenous Y3 reading 2024", failures)
        _expect_close(float(nt_naplan["absent_pct"].iloc[0]), 32.6, 0.2, "NT Indigenous Y3 reading absence 2024", failures)

    primary = matched[matched["series_role"].eq("primary") & matched["period"].eq("whole_year") & matched["calendar_year"].eq(2024)]
    if primary.empty:
        failures.append("No 2024 whole-year schools to assess the ACARA match")
    else:
        match_rate = float(primary["acara_id"].notna().mean())
        if match_rate < 0.75:
            failures.append(f"2024 ACARA match rate {match_rate:.1%} is below 75%")

    if not (GOLD / "school_year.parquet").exists():
        failures.append("Gold school_year mart was not written")

    report = {
        "checks": 8,
        "failures": failures,
        "school_rows": int(len(schools)),
        "group_rows": int(len(groups)),
        "naplan_rows": int(len(naplan)),
        "match_rate_2024": None if primary.empty else float(primary["acara_id"].notna().mean()),
    }
    QUALITY.mkdir(parents=True, exist_ok=True)
    (QUALITY / "report.json").write_text(json.dumps(report, indent=2))
    if failures:
        raise QualityError("; ".join(failures))
    logger.info("Quality checks passed (%s school rows)", len(schools))
    return report
