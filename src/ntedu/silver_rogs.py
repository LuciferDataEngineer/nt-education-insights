"""Productivity Commission Report on Government Services, school education.

Parses the jurisdiction columns of the published Excel tables. Suppressed
cells ('..') stay null.
"""

from __future__ import annotations

import logging
import re

import pandas as pd

from ntedu.common import canonical_jurisdiction, financial_year_label, parse_number, write_parquet, year_from_label
from ntedu.config import ROGS_RAW, SILVER

logger = logging.getLogger(__name__)

WORKBOOK = ROGS_RAW / "rogs_2026_school_education.xlsx"


def _load(sheet: str) -> pd.DataFrame:
    frame = pd.read_excel(WORKBOOK, sheet_name=sheet, header=None)
    return frame


def _jurisdiction_columns(header: pd.Series) -> dict[int, str]:
    found = {}
    for index, value in header.items():
        code = canonical_jurisdiction(value)
        if code:
            found[int(index)] = code
    return found


def _label(value) -> str:
    if pd.isna(value):
        return ""
    text = re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()
    return text.replace("–", "-").replace("—", "-")


def parse_attendance_timeseries(sheet: str, sector: str) -> pd.DataFrame:
    """Tables 4A.17–4A.19: population, year span, year, then jurisdictions."""
    frame = _load(sheet)
    jurisdictions = _jurisdiction_columns(frame.iloc[1])
    records = []
    population = ""
    year_span = ""
    for _, row in frame.iloc[2:].iterrows():
        first = _label(row[0])
        second = _label(row[1])
        third = row[2]
        if first.lower().startswith(("(a)", "(b)", "(c)", "source")):
            break
        if first:
            population = first
        if second:
            year_span = second
        year = year_from_label(third)
        if year is None or not population:
            continue
        for column, code in jurisdictions.items():
            records.append(
                {
                    "table_id": sheet.replace("Table ", ""),
                    "sector": sector,
                    "population": population,
                    "year_span": year_span,
                    "calendar_year": year,
                    "jurisdiction": code,
                    "attendance_rate": None if parse_number(row[column]) is None else parse_number(row[column]) / 100.0
                    if parse_number(row[column]) > 1.5
                    else parse_number(row[column]),
                    "unit": "proportion",
                }
            )
    return pd.DataFrame.from_records(records)


def _rate_from_cell(value) -> float | None:
    number = parse_number(value)
    if number is None:
        return None
    if number > 1.5:
        return number / 100.0
    return number


def parse_remoteness_cross_section(sheet: str) -> pd.DataFrame:
    """Table 4A.16: year, sector, population, year span, remoteness."""
    frame = _load(sheet)
    jurisdictions = _jurisdiction_columns(frame.iloc[1])
    records = []
    year = None
    sector = ""
    population = ""
    year_span = ""
    for _, row in frame.iloc[2:].iterrows():
        labels = [_label(row[index]) for index in range(0, 6)]
        if labels[0].lower().startswith(("(a)", "source")):
            break
        if year_from_label(labels[0]):
            year = year_from_label(labels[0])
        if labels[1]:
            sector = labels[1]
        if labels[2]:
            population = labels[2]
        if labels[3]:
            year_span = labels[3]
        remoteness = labels[4]
        if not remoteness or year is None:
            continue
        for column, code in jurisdictions.items():
            records.append(
                {
                    "table_id": sheet.replace("Table ", ""),
                    "calendar_year": year,
                    "sector": sector,
                    "population": population,
                    "year_span": year_span,
                    "remoteness": remoteness,
                    "jurisdiction": code,
                    "attendance_rate": _rate_from_cell(row[column]),
                }
            )
    return pd.DataFrame.from_records(records)


def parse_expenditure() -> pd.DataFrame:
    """Table 4A.32 real recurrent expenditure per FTE student, government schools."""
    frame = _load("Table 4A.32")
    jurisdictions = _jurisdiction_columns(frame.iloc[1])
    records = []
    sector = ""
    component = ""
    for _, row in frame.iloc[2:].iterrows():
        first = _label(row[0])
        second = _label(row[1])
        measure = _label(row[2])
        year_label = financial_year_label(row[4])
        if first.lower().startswith(("(a)", "source")):
            break
        if first:
            sector = first
            component = ""
        if second:
            component = second
        if measure and not year_label:
            component = measure
        if year_label is None or not sector:
            continue
        if "government schools" not in sector.lower():
            continue
        if sector.lower().startswith("non-government"):
            continue
        for column, code in jurisdictions.items():
            amount = parse_number(row[column])
            records.append(
                {
                    "table_id": "4A.32",
                    "sector": "Government",
                    "component": component,
                    "financial_year": year_label,
                    "dollars": "2023-24",
                    "jurisdiction": code,
                    "expenditure_per_fte": amount,
                }
            )
    return pd.DataFrame.from_records(records)


def build_rogs_silver() -> dict[str, pd.DataFrame]:
    if not WORKBOOK.exists():
        raise FileNotFoundError(WORKBOOK)
    attendance = pd.concat(
        [
            parse_attendance_timeseries("Table 4A.19", "All schools"),
            parse_attendance_timeseries("Table 4A.17", "Government"),
            parse_attendance_timeseries("Table 4A.18", "Non-government"),
        ],
        ignore_index=True,
    )
    remoteness = parse_remoteness_cross_section("Table 4A.16")
    expenditure = parse_expenditure()
    write_parquet(attendance, SILVER / "rogs_attendance.parquet")
    write_parquet(remoteness, SILVER / "rogs_attendance_remoteness.parquet")
    write_parquet(expenditure, SILVER / "rogs_expenditure.parquet")
    logger.info(
        "RoGS attendance %s remoteness %s expenditure %s",
        len(attendance),
        len(remoteness),
        len(expenditure),
    )
    return {
        "rogs_attendance": attendance,
        "rogs_attendance_remoteness": remoteness,
        "rogs_expenditure": expenditure,
    }
