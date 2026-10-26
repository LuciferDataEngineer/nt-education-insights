"""ABS Schools, 2025 tidy tables from the data-table sheets."""

from __future__ import annotations

import logging

import pandas as pd

from ntedu.common import canonical_state, clean_abs_label, parse_number, write_parquet
from ntedu.config import ABS_RAW, SILVER

logger = logging.getLogger(__name__)


def _table(filename: str, sheet: str) -> pd.DataFrame:
    frame = pd.read_excel(ABS_RAW / filename, sheet_name=sheet, header=3)
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame[pd.to_numeric(frame["Year"], errors="coerce").notna()].copy()
    frame["Year"] = frame["Year"].astype(int)
    return frame


def _strip_code(series: pd.Series) -> pd.Series:
    return series.map(lambda value: clean_abs_label(value) or None)


def build_abs_silver() -> dict[str, pd.DataFrame]:
    enrolment = _table("table_43a_fte_students_2006_2025.xlsx", "Table 2 Data table")
    enrolment["jurisdiction"] = enrolment["State/Territory"].map(canonical_state)
    enrolment["sector"] = _strip_code(enrolment["Affiliation (Gov/Non-gov)"])
    enrolment["sex"] = _strip_code(enrolment["Sex"])
    enrolment["grade"] = _strip_code(enrolment["Year (Grade)"])
    for column in (
        "FTE Aboriginal and Torres Strait Islander Students",
        "FTE Non-Indigenous Students",
        "FTE All Students",
    ):
        enrolment[column] = enrolment[column].map(parse_number)
    enrolment_year = (
        enrolment.dropna(subset=["jurisdiction"])
        .groupby(["Year", "jurisdiction", "sector"], as_index=False)
        .agg(
            fte_indigenous=("FTE Aboriginal and Torres Strait Islander Students", "sum"),
            fte_non_indigenous=("FTE Non-Indigenous Students", "sum"),
            fte_all=("FTE All Students", "sum"),
        )
        .rename(columns={"Year": "calendar_year"})
    )
    enrolment_year["indigenous_share"] = enrolment_year["fte_indigenous"] / enrolment_year["fte_all"]

    ratios = _table("table_53a_student_teacher_ratios.xlsx", "Table 1 Data table")
    ratios["jurisdiction"] = ratios["State/Territory"].map(canonical_state)
    ratios["sector"] = _strip_code(ratios["Affiliation"])
    ratios["school_level"] = _strip_code(ratios["School Level"])
    ratios["student_teacher_ratio"] = ratios["FTE Student to FTE Teaching Staff Ratio"].map(parse_number)
    ratios = ratios.dropna(subset=["jurisdiction"]).rename(columns={"Year": "calendar_year"})
    ratios = ratios[["calendar_year", "jurisdiction", "sector", "school_level", "student_teacher_ratio"]]

    retention = _table("table_64a_apparent_retention.xlsx", "Table 1 Data table")
    retention["jurisdiction"] = retention["State/Territory"].map(canonical_state)
    retention["sector"] = _strip_code(retention["Affiliation"])
    retention["sex"] = _strip_code(retention["Sex"])
    retention["year_range"] = _strip_code(retention["Year Range"])
    retention["arr_indigenous"] = retention["Aboriginal and Torres Strait Islander ARR"].map(parse_number)
    retention["arr_non_indigenous"] = retention["Non-Indigenous ARR"].map(parse_number)
    retention["arr_all"] = retention["All ARR"].map(parse_number)
    # ABS publishes these rates as percents. Values of 100 are already on that scale.
    for column in ("arr_indigenous", "arr_non_indigenous", "arr_all"):
        retention[column] = retention[column].map(lambda value: None if value is None or pd.isna(value) else (value / 100.0 if value > 1.5 else value))
    retention = retention.dropna(subset=["jurisdiction"]).rename(columns={"Year": "calendar_year"})
    retention = retention[
        [
            "calendar_year",
            "jurisdiction",
            "sector",
            "sex",
            "year_range",
            "arr_indigenous",
            "arr_non_indigenous",
            "arr_all",
        ]
    ]

    remoteness = _table("table_46a_fte_remoteness_2025.xlsx", "Table 2 Data table")
    remoteness["jurisdiction"] = remoteness["State/Territory"].map(canonical_state)
    remoteness["sector"] = _strip_code(remoteness["Affiliation"])
    remoteness["remoteness"] = _strip_code(remoteness["ASGS Remoteness Classification"])
    remoteness["fte_students"] = remoteness["Total Student Count (FTE)"].map(parse_number)
    remoteness = remoteness.dropna(subset=["jurisdiction"]).rename(columns={"Year": "calendar_year"})
    remoteness = remoteness[["calendar_year", "jurisdiction", "sector", "remoteness", "fte_students"]]

    schools = _table("table_35b_schools_2010_2025.xlsx", "Table 3 Data table")
    schools["jurisdiction"] = schools["State/Territory"].map(canonical_state)
    schools["sector"] = _strip_code(schools["Affiliation (Gov/Non-gov)"])
    schools["school_type"] = _strip_code(schools["School Type"])
    schools["school_count"] = schools["School Count"].map(parse_number)
    schools = schools.dropna(subset=["jurisdiction"]).rename(columns={"Year": "calendar_year"})
    schools = (
        schools.groupby(["calendar_year", "jurisdiction", "sector", "school_type"], as_index=False)["school_count"]
        .sum()
    )

    write_parquet(enrolment_year, SILVER / "abs_enrolment.parquet")
    write_parquet(ratios, SILVER / "abs_student_teacher_ratio.parquet")
    write_parquet(retention, SILVER / "abs_apparent_retention.parquet")
    write_parquet(remoteness, SILVER / "abs_remoteness_enrolment.parquet")
    write_parquet(schools, SILVER / "abs_school_counts.parquet")
    logger.info(
        "ABS enrolment %s ratios %s retention %s remoteness %s schools %s",
        len(enrolment_year),
        len(ratios),
        len(retention),
        len(remoteness),
        len(schools),
    )
    return {
        "abs_enrolment": enrolment_year,
        "abs_student_teacher_ratio": ratios,
        "abs_apparent_retention": retention,
        "abs_remoteness_enrolment": remoteness,
        "abs_school_counts": schools,
    }
