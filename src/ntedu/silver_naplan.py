"""ACARA NAPLAN national results, reset scale from 2023 onward."""

from __future__ import annotations

import logging

import pandas as pd

from ntedu.common import canonical_state, parse_number, write_parquet
from ntedu.config import ACARA_RAW, SILVER, SNAPSHOTS

logger = logging.getLogger(__name__)

KEEP_ATTRIBUTES = {
    "All",
    "Indigeneity",
    "ABS remoteness",
    "Indigeneity by ABS remoteness",
    "Parental education",
    "Gender",
}

RENAME = {
    "Calendar year": "calendar_year",
    "Year level": "year_level",
    "Domain": "domain",
    "State/territory": "state_name",
    "Student attribute": "student_attribute",
    "Subgroup": "subgroup",
    "Reporting flag": "reporting_flag",
    "Enrolled students": "enrolled_students",
    "Participation (%)": "participation_pct",
    "Absent (%)": "absent_pct",
    "Exempt (%)": "exempt_pct",
    "Withdrawn (%)": "withdrawn_pct",
    "Average NAPLAN score": "mean_score",
    "Average NAPLAN score confidence interval": "mean_score_moe",
    "NAPLAN score standard deviation": "score_sd",
    "Needs additional support (%)": "needs_additional_support_pct",
    "Developing (%)": "developing_pct",
    "Strong (%)": "strong_pct",
    "Exceeding (%)": "exceeding_pct",
}


def _attach_participation(results: pd.DataFrame, participation: pd.DataFrame) -> pd.DataFrame:
    """The 2026 results sheet moved absence onto a participation sheet."""
    columns = [
        "Calendar year",
        "Year level",
        "Domain",
        "State/territory",
        "Student attribute",
        "Subgroup",
        "Absent (%)",
        "Withdrawn (%)",
        "Participation (%)",
        "Assessed (%)",
    ]
    available = [column for column in columns if column in participation.columns]
    extra = participation[available].drop_duplicates(
        ["Calendar year", "Year level", "Domain", "State/territory", "Student attribute", "Subgroup"]
    )
    merged = results.merge(
        extra,
        on=["Calendar year", "Year level", "Domain", "State/territory", "Student attribute", "Subgroup"],
        how="left",
        suffixes=("", "_participation"),
    )
    for column in ("Absent (%)", "Withdrawn (%)", "Participation (%)"):
        other = f"{column}_participation"
        if column not in merged.columns and other in merged.columns:
            merged[column] = merged[other]
        elif other in merged.columns:
            merged[column] = merged[column].fillna(merged[other])
    return merged


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [column for column in RENAME if column in frame.columns]
    prepared = frame[keep].rename(columns=RENAME).copy()
    prepared = prepared[prepared["student_attribute"].isin(KEEP_ATTRIBUTES)].copy()
    prepared["jurisdiction"] = prepared["state_name"].map(canonical_state)
    numeric = [
        "enrolled_students",
        "participation_pct",
        "absent_pct",
        "exempt_pct",
        "withdrawn_pct",
        "mean_score",
        "mean_score_moe",
        "score_sd",
        "needs_additional_support_pct",
        "developing_pct",
        "strong_pct",
        "exceeding_pct",
        "year_level",
        "calendar_year",
    ]
    for column in numeric:
        if column in prepared.columns:
            prepared[column] = prepared[column].map(parse_number)
    prepared["calendar_year"] = prepared["calendar_year"].astype("Int64")
    prepared["year_level"] = prepared["year_level"].astype("Int64")
    prepared["scale"] = "naplan_reset_2023"
    prepared["proficiency_denominator"] = "assessed_students"
    return prepared.reset_index(drop=True)


def build_naplan_silver() -> pd.DataFrame:
    source = ACARA_RAW / "naplan_2026.xlsx"
    snapshot = SNAPSHOTS / "naplan_results.parquet"
    if source.exists():
        logger.info("Reading NAPLAN national results workbook")
        results = pd.read_excel(source, sheet_name="NAPLAN Results")
        participation = pd.read_excel(source, sheet_name="NAPLAN Participation")
        frame = _attach_participation(results, participation)
        prepared = _prepare(frame)
        write_parquet(prepared, snapshot)
    elif snapshot.exists():
        logger.info("Reading NAPLAN snapshot")
        prepared = pd.read_parquet(snapshot)
    else:
        fallback = ACARA_RAW / "naplan_2024.xlsx"
        if not fallback.exists():
            raise FileNotFoundError("No NAPLAN national results file is available")
        frame = pd.read_excel(fallback, sheet_name="NAPLAN Results")
        prepared = _prepare(frame)
        write_parquet(prepared, snapshot)
    write_parquet(prepared, SILVER / "naplan_results.parquet")
    logger.info(
        "NAPLAN rows %s years %s",
        len(prepared),
        sorted(prepared["calendar_year"].dropna().unique().tolist()),
    )
    return prepared
