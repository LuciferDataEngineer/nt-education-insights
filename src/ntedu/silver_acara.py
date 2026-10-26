"""ACARA My School profile and location extracts.

School Profile 2008–2025 is large. The pipeline keeps a NT school-year snapshot
and a state-year summary so later runs do not need the 30 MB workbook.
"""

from __future__ import annotations

import logging

import pandas as pd

from ntedu.common import parse_number, parse_percent_points, write_parquet
from ntedu.config import ACARA_RAW, SILVER, SNAPSHOTS

logger = logging.getLogger(__name__)

PROFILE_COLUMNS = [
    "Calendar Year",
    "ACARA SML ID",
    "School Name",
    "Suburb",
    "State",
    "Postcode",
    "School Sector",
    "School Type",
    "Campus Type",
    "Rolled Reporting Description",
    "Year Range",
    "Geolocation",
    "ICSEA",
    "ICSEA Percentile",
    "Bottom SEA Quarter (%)",
    "Lower Middle SEA Quarter (%)",
    "Upper Middle SEA Quarter (%)",
    "Top SEA Quarter (%)",
    "Full Time Equivalent Teaching Staff",
    "Total Enrolments",
    "Full Time Equivalent Enrolments",
    "Indigenous Enrolments (%)",
    "Language Background Other Than English - Yes (%)",
]

RENAME = {
    "Calendar Year": "calendar_year",
    "ACARA SML ID": "acara_id",
    "School Name": "school_name",
    "Suburb": "suburb",
    "State": "state",
    "Postcode": "postcode",
    "School Sector": "sector",
    "School Type": "school_type",
    "Campus Type": "campus_type",
    "Rolled Reporting Description": "rolled_reporting",
    "Year Range": "year_range",
    "Geolocation": "geolocation",
    "ICSEA": "icsea",
    "ICSEA Percentile": "icsea_percentile",
    "Bottom SEA Quarter (%)": "bottom_sea_pct",
    "Lower Middle SEA Quarter (%)": "lower_middle_sea_pct",
    "Upper Middle SEA Quarter (%)": "upper_middle_sea_pct",
    "Top SEA Quarter (%)": "top_sea_pct",
    "Full Time Equivalent Teaching Staff": "teaching_staff_fte",
    "Total Enrolments": "enrolments",
    "Full Time Equivalent Enrolments": "enrolments_fte",
    "Indigenous Enrolments (%)": "indigenous_pct",
    "Language Background Other Than English - Yes (%)": "lbote_pct",
}


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [column for column in PROFILE_COLUMNS if column in frame.columns]
    prepared = frame[keep].rename(columns=RENAME).copy()
    prepared["calendar_year"] = pd.to_numeric(prepared["calendar_year"], errors="coerce").astype("Int64")
    for column in (
        "icsea",
        "icsea_percentile",
        "bottom_sea_pct",
        "lower_middle_sea_pct",
        "upper_middle_sea_pct",
        "top_sea_pct",
        "teaching_staff_fte",
        "enrolments",
        "enrolments_fte",
        "indigenous_pct",
        "lbote_pct",
    ):
        if column not in prepared.columns:
            continue
        if column.endswith("_pct") or column in {"bottom_sea_pct", "lower_middle_sea_pct", "upper_middle_sea_pct", "top_sea_pct", "indigenous_pct", "lbote_pct"}:
            prepared[column] = prepared[column].map(parse_percent_points)
        else:
            prepared[column] = prepared[column].map(parse_number)
    prepared["state"] = prepared["state"].astype(str).str.strip()
    prepared["school_name"] = prepared["school_name"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    prepared = prepared.dropna(subset=["calendar_year", "acara_id", "school_name"])
    return prepared


def _state_summary(profile: pd.DataFrame) -> pd.DataFrame:
    frame = profile.copy()
    frame["enrolment_weight"] = frame["enrolments"].fillna(0)
    rows = []
    for (year, state), group in frame.groupby(["calendar_year", "state"], dropna=False):
        weight = group["enrolment_weight"]
        weighted = weight.sum()

        def wavg(column: str) -> float | None:
            values = group[column]
            mask = values.notna() & weight.gt(0)
            if not mask.any():
                return None
            return float((values[mask] * weight[mask]).sum() / weight[mask].sum())

        rows.append(
            {
                "calendar_year": int(year),
                "state": state,
                "schools": int(len(group)),
                "enrolments": float(weighted) if weighted else None,
                "indigenous_pct_weighted": wavg("indigenous_pct"),
                "icsea_weighted": wavg("icsea"),
                "bottom_sea_pct_weighted": wavg("bottom_sea_pct"),
                "very_remote_enrolment_share": (
                    float(weight[group["geolocation"].eq("Very Remote")].sum() / weighted) if weighted else None
                ),
                "remote_enrolment_share": (
                    float(weight[group["geolocation"].isin(["Remote", "Very Remote"])].sum() / weighted) if weighted else None
                ),
                "government_enrolment_share": (
                    float(weight[group["sector"].eq("Government")].sum() / weighted) if weighted else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _load_profile() -> pd.DataFrame:
    historical = ACARA_RAW / "school_profile_2008_2025.xlsx"
    snapshot = SNAPSHOTS / "acara_profile_nt.parquet"
    if historical.exists():
        logger.info("Reading historical school profile workbook")
        frame = pd.read_excel(historical, sheet_name="SchoolProfile 2008-2025")
        prepared = _prepare(frame)
        summary = _state_summary(prepared)
        nt = prepared[prepared["state"].eq("NT")].reset_index(drop=True)
        write_parquet(nt, snapshot)
        write_parquet(summary, SNAPSHOTS / "acara_state_year.parquet")
        return nt
    if snapshot.exists():
        logger.info("Reading NT school profile snapshot")
        return pd.read_parquet(snapshot)
    latest = ACARA_RAW / "school_profile_2025.xlsx"
    if latest.exists():
        frame = pd.read_excel(latest, sheet_name="SchoolProfile 2025")
        return _prepare(frame)
    raise FileNotFoundError("No ACARA school profile source is available")


def _load_location() -> pd.DataFrame:
    path = ACARA_RAW / "school_location_2025.xlsx"
    snapshot = SNAPSHOTS / "acara_location_nt.parquet"
    if path.exists():
        frame = pd.read_excel(path, sheet_name="SchoolLocations 2025")
        nt = frame[frame["State"].eq("NT")].copy()
        nt = nt.rename(
            columns={
                "ACARA SML ID": "acara_id",
                "School Name": "school_name",
                "Suburb": "suburb",
                "School Sector": "sector",
                "School Type": "school_type",
                "Latitude": "latitude",
                "Longitude": "longitude",
                "ABS Remoteness Area Name": "abs_remoteness",
                "Local Government Area Name": "lga_name",
                "Statistical Area 2 Name": "sa2_name",
                "Statistical Area 3 Name": "sa3_name",
                "Campus Type": "campus_type",
            }
        )
        keep = [
            "acara_id",
            "school_name",
            "suburb",
            "sector",
            "school_type",
            "campus_type",
            "latitude",
            "longitude",
            "abs_remoteness",
            "lga_name",
            "sa2_name",
            "sa3_name",
        ]
        nt = nt[keep]
        nt["latitude"] = pd.to_numeric(nt["latitude"], errors="coerce")
        nt["longitude"] = pd.to_numeric(nt["longitude"], errors="coerce")
        write_parquet(nt, snapshot)
        return nt
    if snapshot.exists():
        return pd.read_parquet(snapshot)
    raise FileNotFoundError("No ACARA school location source is available")


def build_acara_silver() -> dict[str, pd.DataFrame]:
    profile = _load_profile()
    location = _load_location()
    summary_path = SNAPSHOTS / "acara_state_year.parquet"
    summary = pd.read_parquet(summary_path) if summary_path.exists() else _state_summary(profile)
    write_parquet(profile, SILVER / "acara_school_profile_nt.parquet")
    write_parquet(location, SILVER / "acara_school_location_nt.parquet")
    write_parquet(summary, SILVER / "acara_state_year.parquet")
    logger.info("ACARA NT profile rows %s; location rows %s", len(profile), len(location))
    return {
        "acara_school_profile_nt": profile,
        "acara_school_location_nt": location,
        "acara_state_year": summary,
    }
