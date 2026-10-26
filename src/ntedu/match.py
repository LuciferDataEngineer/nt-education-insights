"""Link NT government schools to the ACARA school profile for the same year."""

from __future__ import annotations

import logging

import pandas as pd
from rapidfuzz import fuzz, process

from ntedu.common import normalise_name, write_parquet
from ntedu.config import SILVER

logger = logging.getLogger(__name__)

# Published names that do not token-match cleanly.
ALIASES = {
    "alice springs school of the air": "alice springs school of the air",
    "katherine school of the air": "katherine school of the air",
    "northern territory school of distance education": "northern territory school of distance education",
    "n t school of distance education": "northern territory school of distance education",
    "top end school of flexible learning": "top end school of flexible learning",
}


def _candidate_frame(profile: pd.DataFrame) -> pd.DataFrame:
    frame = profile.copy()
    frame["name_key"] = frame["school_name"].map(normalise_name)
    # Prefer the rolled reporting entity when ACARA splits campuses.
    if "campus_type" in frame.columns:
        preferred = frame["campus_type"].fillna("").str.contains("Single|Head", case=False)
        if preferred.any():
            frame = frame[preferred | frame["campus_type"].isna()].copy()
    return frame


def match_schools(attendance: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    candidates = _candidate_frame(profile)
    by_year: dict[int, pd.DataFrame] = {
        int(year): group.reset_index(drop=True)
        for year, group in candidates.groupby("calendar_year")
    }
    keys_by_year = {
        year: {row.name_key: row.acara_id for row in group.itertuples(index=False)}
        for year, group in by_year.items()
    }
    # Government schools are the right pool; keep a full-sector fallback.
    gov_by_year = {
        year: group[group["sector"].eq("Government")].reset_index(drop=True)
        for year, group in by_year.items()
    }

    matched_rows = []
    for row in attendance.itertuples(index=False):
        year = int(row.calendar_year)
        key = ALIASES.get(normalise_name(row.school_name), normalise_name(row.school_name))
        pool = gov_by_year.get(year)
        full = by_year.get(year)
        acara_id = None
        method = "unmatched"
        score = 0.0
        if year in keys_by_year and key in keys_by_year[year] and pool is not None:
            gov_keys = set(pool["name_key"])
            if key in gov_keys:
                acara_id = pool.loc[pool["name_key"].eq(key), "acara_id"].iloc[0]
                method = "exact_government"
                score = 100.0
            else:
                acara_id = keys_by_year[year][key]
                method = "exact_any_sector"
                score = 100.0
        elif pool is not None and len(pool):
            choice = process.extractOne(
                key,
                pool["name_key"].tolist(),
                scorer=fuzz.token_sort_ratio,
            )
            if choice and choice[1] >= 92:
                acara_id = pool.loc[pool["name_key"].eq(choice[0]), "acara_id"].iloc[0]
                method = "fuzzy_government"
                score = float(choice[1])
            elif full is not None and len(full):
                choice = process.extractOne(
                    key,
                    full["name_key"].tolist(),
                    scorer=fuzz.token_sort_ratio,
                )
                if choice and choice[1] >= 94:
                    acara_id = full.loc[full["name_key"].eq(choice[0]), "acara_id"].iloc[0]
                    method = "fuzzy_any_sector"
                    score = float(choice[1])
        matched_rows.append({"acara_id": acara_id, "match_method": method, "match_score": score})

    matched = pd.concat([attendance.reset_index(drop=True), pd.DataFrame(matched_rows)], axis=1)
    profile_keep = [
        "calendar_year",
        "acara_id",
        "school_name",
        "suburb",
        "sector",
        "school_type",
        "geolocation",
        "icsea",
        "icsea_percentile",
        "bottom_sea_pct",
        "top_sea_pct",
        "enrolments",
        "indigenous_pct",
        "lbote_pct",
        "teaching_staff_fte",
    ]
    profile_keep = [column for column in profile_keep if column in profile.columns]
    profile_year = profile[profile_keep].rename(columns={"school_name": "acara_school_name", "sector": "acara_sector", "enrolments": "acara_enrolments"})
    merged = matched.merge(profile_year, on=["calendar_year", "acara_id"], how="left")
    write_parquet(merged, SILVER / "nt_school_matched.parquet")
    primary = merged[merged["series_role"].eq("primary") & merged["period"].eq("whole_year")]
    if len(primary):
        rate = primary["acara_id"].notna().mean()
        logger.info("Whole-year primary school match rate %.1f%% (%s schools)", 100 * rate, primary["acara_id"].notna().sum())
        unmatched = sorted(primary.loc[primary["acara_id"].isna(), "school_name"].unique())
        if unmatched:
            logger.info("Unmatched primary schools (%s): %s", len(unmatched), "; ".join(unmatched[:25]))
    return merged
