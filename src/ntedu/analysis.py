"""Statistical summaries. Every figure in the report is computed from gold or silver tables."""

from __future__ import annotations

import json
import logging

import pandas as pd
import statsmodels.formula.api as smf

from ntedu.config import FIGURES, GOLD, SILVER
from ntedu.figures import (
    attendance_trend,
    naplan_bars,
    region_bars,
    remoteness_bars,
    retention_bars,
    school_scatter,
)

logger = logging.getLogger(__name__)


def _pp(rate: float | None) -> float | None:
    if rate is None or pd.isna(rate):
        return None
    return round(float(rate) * 100, 1)


def _record(model, label: str) -> dict:
    rows = []
    for name in model.params.index:
        rows.append(
            {
                "term": str(name),
                "estimate": round(float(model.params[name]), 3),
                "std_error": round(float(model.bse[name]), 3),
                "p_value": float(model.pvalues[name]),
                "ci_low": round(float(model.conf_int().loc[name, 0]), 3),
                "ci_high": round(float(model.conf_int().loc[name, 1]), 3),
            }
        )
    return {
        "label": label,
        "n": int(model.nobs),
        "r_squared": round(float(model.rsquared), 3),
        "terms": rows,
    }


def _weighted_corr(frame: pd.DataFrame, left: str, right: str, weight: str) -> float | None:
    subset = frame[[left, right, weight]].dropna()
    if len(subset) < 5:
        return None
    weights = subset[weight].to_numpy()
    x = subset[left].to_numpy()
    y = subset[right].to_numpy()
    mean_x = np_average(x, weights)
    mean_y = np_average(y, weights)
    cov = np_average((x - mean_x) * (y - mean_y), weights)
    var_x = np_average((x - mean_x) ** 2, weights)
    var_y = np_average((y - mean_y) ** 2, weights)
    if var_x <= 0 or var_y <= 0:
        return None
    return round(float(cov / (var_x**0.5 * var_y**0.5)), 3)


def np_average(values, weights):
    import numpy as np

    return float(np.average(values, weights=weights))


def run_analysis() -> dict:
    FIGURES.mkdir(parents=True, exist_ok=True)
    rogs = pd.read_parquet(SILVER / "rogs_attendance.parquet")
    remoteness = pd.read_parquet(SILVER / "rogs_attendance_remoteness.parquet")
    regions = pd.read_parquet(GOLD / "nt_region_year.parquet")
    schools = pd.read_parquet(GOLD / "school_year.parquet")
    naplan = pd.read_parquet(SILVER / "naplan_results.parquet")
    ctg = pd.read_parquet(SILVER / "ctg_outcome5.parquet")
    retention = pd.read_parquet(SILVER / "abs_apparent_retention.parquet")
    enrolment = pd.read_parquet(SILVER / "abs_enrolment.parquet")
    ratios = pd.read_parquet(SILVER / "abs_student_teacher_ratio.parquet")
    expenditure = pd.read_parquet(SILVER / "rogs_expenditure.parquet")
    counts = pd.read_parquet(SILVER / "abs_school_counts.parquet")
    state_year = pd.read_parquet(SILVER / "acara_state_year.parquet")

    attendance = rogs[
        (rogs["sector"] == "All schools")
        & (rogs["year_span"] == "Years 1-10")
        & (rogs["jurisdiction"].isin(["NT", "Aust"]))
    ].copy()
    attendance_trend(attendance, FIGURES / "01_attendance_trend.png")

    remote_focus = remoteness[
        (remoteness["calendar_year"] == 2025)
        & (remoteness["sector"] == "All schools")
        & (remoteness["year_span"] == "Years 1-10")
        & (remoteness["population"].str.contains("Aboriginal", na=False))
        & (remoteness["jurisdiction"].isin(["NT", "WA", "Qld", "Aust"]))
    ].copy()
    remoteness_bars(remote_focus, FIGURES / "02_remoteness_indigenous.png")

    region_2024 = regions[
        (regions["calendar_year"] == 2024)
        & (regions["period"] == "whole_year")
        & (regions["region"].isin(["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]))
    ].copy()
    region_bars(region_2024, FIGURES / "03_nt_regions_2024.png")

    model_frame = schools[
        (schools["calendar_year"] == 2024)
        & (schools["period"] == "whole_year")
        & (schools["attendance_rate"].notna())
        & (schools["enrolment"].fillna(0) >= 20)
        & (schools["indigenous_pct"].notna())
        & (schools["bottom_sea_pct"].notna())
        & (schools["geolocation"].isin(["Outer Regional", "Remote", "Very Remote"]))
        & (schools["acara_id"].notna())
    ].copy()
    model_frame["attendance_pp"] = model_frame["attendance_rate"] * 100
    school_scatter(model_frame, FIGURES / "04_school_scatter_2024.png")

    formula = (
        "attendance_pp ~ indigenous_pct + bottom_sea_pct + "
        "C(geolocation, Treatment(reference='Outer Regional'))"
    )
    fitted = smf.wls(formula, data=model_frame, weights=model_frame["enrolment"]).fit(cov_type="HC1")
    very_remote = model_frame[model_frame["geolocation"] == "Very Remote"]
    fitted_remote = None
    if len(very_remote) >= 25:
        fitted_remote = smf.wls(
            "attendance_pp ~ indigenous_pct + bottom_sea_pct",
            data=very_remote,
            weights=very_remote["enrolment"],
        ).fit(cov_type="HC1")

    trend = attendance[
        (attendance["jurisdiction"] == "NT")
        & (attendance["population"].str.contains("Aboriginal", na=False))
        & (attendance["attendance_rate"].notna())
    ][["calendar_year", "attendance_rate"]].copy()
    trend["rate_pp"] = trend["attendance_rate"] * 100
    trend_model = smf.ols("rate_pp ~ calendar_year", data=trend).fit()

    naplan_slice = naplan[
        (naplan["calendar_year"] == 2025)
        & (naplan["year_level"] == 3)
        & (naplan["domain"] == "Reading")
        & (naplan["subgroup"].isin(["All", "Indigenous", "Non-Indigenous", "Indigenous very remote", "Very remote"]))
        & (naplan["jurisdiction"].isin(["NT", "Aust"]))
    ].copy()
    naplan_bars(naplan_slice, FIGURES / "05_naplan_year3_reading_2025.png")

    retention_slice = retention[
        (retention["year_range"] == "Year 7/8 - Year 12")
        & (retention["sector"] == "All affiliations")
        & (retention["sex"] == "Persons")
        & (retention["jurisdiction"].isin(["NT", "WA", "Qld", "SA"]))
        & (retention["calendar_year"] == 2025)
    ].copy()
    retention_bars(retention_slice, FIGURES / "06_apparent_retention_2025.png")

    def rate(jurisdiction: str, population_contains: str, year: int) -> float | None:
        row = attendance[
            (attendance["jurisdiction"] == jurisdiction)
            & (attendance["population"].str.contains(population_contains, na=False))
            & (attendance["calendar_year"] == year)
        ]
        if row.empty or pd.isna(row["attendance_rate"].iloc[0]):
            return None
        return float(row["attendance_rate"].iloc[0])

    def remote_rate(jurisdiction: str, population_contains: str, area: str, sector: str = "All schools") -> float | None:
        row = remoteness[
            (remoteness["calendar_year"] == 2025)
            & (remoteness["sector"] == sector)
            & (remoteness["year_span"] == "Years 1-10")
            & (remoteness["jurisdiction"] == jurisdiction)
            & (remoteness["remoteness"] == area)
            & (remoteness["population"].str.contains(population_contains, na=False))
        ]
        if row.empty or pd.isna(row["attendance_rate"].iloc[0]):
            return None
        return float(row["attendance_rate"].iloc[0])

    def naplan_cell(year: int, year_level: int, domain: str, subgroup: str, jurisdiction: str) -> dict:
        row = naplan[
            (naplan["calendar_year"] == year)
            & (naplan["year_level"] == year_level)
            & (naplan["domain"] == domain)
            & (naplan["subgroup"] == subgroup)
            & (naplan["jurisdiction"] == jurisdiction)
        ]
        if row.empty:
            return {}
        item = row.iloc[0]
        return {
            "mean_score": round(float(item["mean_score"]), 1) if pd.notna(item["mean_score"]) else None,
            "moe": round(float(item["mean_score_moe"]), 1) if pd.notna(item["mean_score_moe"]) else None,
            "needs_additional_support_pct": round(float(item["needs_additional_support_pct"]), 1)
            if pd.notna(item["needs_additional_support_pct"])
            else None,
            "absent_pct": round(float(item["absent_pct"]), 1) if pd.notna(item["absent_pct"]) else None,
            "participation_pct": round(float(item["participation_pct"]), 1) if pd.notna(item["participation_pct"]) else None,
            "enrolled_students": None if pd.isna(item["enrolled_students"]) else int(round(float(item["enrolled_students"]))),
        }

    ctg_actual = ctg[
        (ctg["table_number"] == "CtG5A.1")
        & (ctg["description_7"] == "Actual")
        & (ctg["unit"] == "%")
        & (ctg["indigenous_status"].str.contains("Aboriginal", na=False))
        & (ctg["remoteness"].fillna("All areas") == "All areas")
        & (ctg["sex"].fillna("All people").str.contains("All", na=False))
        & (ctg["year_label"].isin(["2016", "2021"]))
    ][["year_label", "jurisdiction", "value"]].drop_duplicates()
    ctg_path = ctg[
        (ctg["table_number"] == "CtG5A.1")
        & (ctg["description_7"].isin(["Linear regression estimates", "Trajectory"]))
        & (ctg["unit"] == "%")
        & (ctg["year_label"] == "2031")
        & (ctg["indigenous_status"].str.contains("Aboriginal", na=False))
        & (ctg["remoteness"].fillna("All areas") == "All areas")
    ][["description_7", "jurisdiction", "value"]].drop_duplicates()

    schools_2024 = schools[
        (schools["calendar_year"] == 2024) & (schools["period"] == "whole_year") & (schools["attendance_rate"].notna())
    ]
    weighted_attendance = float(
        (schools_2024["attendance_rate"] * schools_2024["enrolment"]).sum() / schools_2024["enrolment"].sum()
    )
    low = schools_2024[schools_2024["attendance_rate"] < 0.60]
    very_low = schools_2024[schools_2024["attendance_rate"] < 0.50]

    enrolment_nt = enrolment[enrolment["jurisdiction"] == "NT"].groupby("calendar_year", as_index=False).agg(
        fte_all=("fte_all", "sum"),
        fte_indigenous=("fte_indigenous", "sum"),
    )
    enrolment_nt["indigenous_share"] = enrolment_nt["fte_indigenous"] / enrolment_nt["fte_all"]
    national = enrolment.groupby("calendar_year", as_index=False).agg(fte_all=("fte_all", "sum"), fte_indigenous=("fte_indigenous", "sum"))
    national["indigenous_share"] = national["fte_indigenous"] / national["fte_all"]

    ratio_2025 = ratios[
        (ratios["calendar_year"] == 2025)
        & (ratios["school_level"] == "All Levels")
        & (ratios["sector"] == "Government")
        & (ratios["jurisdiction"].isin(["NT", "Aust"]))
    ]

    spend = expenditure[
        (expenditure["financial_year"] == "2023-24")
        & (expenditure["component"] == "Australian, state and territory government expenditure")
        & (expenditure["jurisdiction"].isin(["NT", "Aust"]))
    ]
    cwealth = expenditure[
        (expenditure["financial_year"] == "2023-24")
        & (expenditure["component"] == "Australian Government payments")
        & (expenditure["jurisdiction"].isin(["NT", "Aust"]))
    ]

    nt_schools_2025 = counts[(counts["calendar_year"] == 2025) & (counts["jurisdiction"] == "NT")]["school_count"].sum()
    profile_2025 = state_year[(state_year["calendar_year"] == 2025) & (state_year["state"] == "NT")]

    residuals = model_frame.copy()
    residuals["predicted_pp"] = fitted.predict(residuals)
    residuals["residual_pp"] = residuals["attendance_pp"] - residuals["predicted_pp"]
    notable = residuals[residuals["enrolment"] >= 40].copy()
    below = notable.nsmallest(5, "residual_pp")
    above = notable.nlargest(5, "residual_pp")

    def school_brief(frame: pd.DataFrame) -> list[dict]:
        rows = []
        for item in frame.itertuples(index=False):
            rows.append(
                {
                    "school_name": item.school_name,
                    "geolocation": item.geolocation,
                    "enrolment": round(float(item.enrolment), 0),
                    "attendance_pct": round(float(item.attendance_rate) * 100, 1),
                    "indigenous_pct": round(float(item.indigenous_pct), 1),
                    "bottom_sea_pct": round(float(item.bottom_sea_pct), 1),
                    "residual_pp": round(float(item.residual_pp), 1),
                }
            )
        return rows

    key = {
        "sources_note": "Rates are proportions in source tables and percentage points in this file.",
        "rogs_years_1_10_all_schools": {
            "nt_all_2016": _pp(rate("NT", "All students", 2016)),
            "nt_all_2019": _pp(rate("NT", "All students", 2019)),
            "nt_all_2022": _pp(rate("NT", "All students", 2022)),
            "nt_all_2025": _pp(rate("NT", "All students", 2025)),
            "aust_all_2016": _pp(rate("Aust", "All students", 2016)),
            "aust_all_2025": _pp(rate("Aust", "All students", 2025)),
            "nt_indigenous_2016": _pp(rate("NT", "Aboriginal", 2016)),
            "nt_indigenous_2019": _pp(rate("NT", "Aboriginal", 2019)),
            "nt_indigenous_2022": _pp(rate("NT", "Aboriginal", 2022)),
            "nt_indigenous_2025": _pp(rate("NT", "Aboriginal", 2025)),
            "aust_indigenous_2016": _pp(rate("Aust", "Aboriginal", 2016)),
            "aust_indigenous_2025": _pp(rate("Aust", "Aboriginal", 2025)),
            "nt_non_indigenous_2016": _pp(rate("NT", "Non-Indigenous", 2016)),
            "nt_non_indigenous_2025": _pp(rate("NT", "Non-Indigenous", 2025)),
            "aust_non_indigenous_2025": _pp(rate("Aust", "Non-Indigenous", 2025)),
            "year_2020": "not published in RoGS Table 4A.19",
        },
        "attendance_trend_nt_indigenous": _record(trend_model, "OLS, NT Indigenous Years 1-10 attendance on year, published years only"),
        "remoteness_2025_indigenous_years_1_10": {
            "nt_outer_regional": _pp(remote_rate("NT", "Aboriginal", "Outer regional")),
            "nt_remote": _pp(remote_rate("NT", "Aboriginal", "Remote")),
            "nt_very_remote": _pp(remote_rate("NT", "Aboriginal", "Very remote")),
            "aust_outer_regional": _pp(remote_rate("Aust", "Aboriginal", "Outer regional")),
            "aust_remote": _pp(remote_rate("Aust", "Aboriginal", "Remote")),
            "aust_very_remote": _pp(remote_rate("Aust", "Aboriginal", "Very remote")),
            "nt_very_remote_all_students": _pp(remote_rate("NT", "All students", "Very remote")),
            "aust_very_remote_all_students": _pp(remote_rate("Aust", "All students", "Very remote")),
            "nt_very_remote_non_indigenous": _pp(remote_rate("NT", "Non-Indigenous", "Very remote")),
            "aust_very_remote_non_indigenous": _pp(remote_rate("Aust", "Non-Indigenous", "Very remote")),
            "qld_very_remote_indigenous": _pp(remote_rate("Qld", "Aboriginal", "Very remote")),
            "wa_very_remote_indigenous": _pp(remote_rate("WA", "Aboriginal", "Very remote")),
        },
        "nt_government_regions_2024": {
            region: {
                **{
                    population: _pp(
                        float(
                            region_2024[
                                (region_2024["region"] == region) & (region_2024["population"] == population)
                            ]["attendance_rate"].iloc[0]
                        )
                    )
                    for population in ("indigenous", "non_indigenous", "total")
                },
                "enrolment": round(
                    float(
                        region_2024[
                            (region_2024["region"] == region) & (region_2024["population"] == "total")
                        ]["enrolment"].iloc[0]
                    ),
                    0,
                ),
            }
            for region in ["Darwin", "Top End", "Central", "Big Rivers", "East Arnhem", "Barkly"]
        },
        "nt_government_2024_school_panel": {
            "schools_with_published_attendance": int(len(schools_2024)),
            "enrolment_weighted_attendance_pct": round(weighted_attendance * 100, 1),
            "enrolment_in_schools_under_60_pct": round(float(low["enrolment"].sum() / schools_2024["enrolment"].sum()) * 100, 1),
            "schools_under_50_pct": int(len(very_low)),
            "enrolment_weighted_correlation_attendance_indigenous_pct": _weighted_corr(
                model_frame, "attendance_pp", "indigenous_pct", "enrolment"
            ),
            "enrolment_weighted_correlation_attendance_bottom_sea": _weighted_corr(
                model_frame, "attendance_pp", "bottom_sea_pct", "enrolment"
            ),
            "enrolment_weighted_correlation_attendance_icsea": _weighted_corr(
                model_frame.assign(icsea=model_frame["icsea"]),
                "attendance_pp",
                "icsea",
                "enrolment",
            ),
        },
        "regression_2024_government_schools": _record(
            fitted,
            "WLS, 2024 government schools with published attendance, enrolment >= 20, HC1 standard errors. "
            "Outcome is attendance in percentage points. Bottom SEA quarter is the share of students in the lowest parental SEA quarter.",
        ),
        "regression_2024_very_remote_only": None if fitted_remote is None else _record(
            fitted_remote,
            "Same specification inside Very Remote schools only, so the Indigenous coefficient is not just a remoteness proxy.",
        ),
        "schools_below_prediction": school_brief(below),
        "schools_above_prediction": school_brief(above),
        "naplan_2025_year3_reading": {
            "nt_all": naplan_cell(2025, 3, "Reading", "All", "NT"),
            "aust_all": naplan_cell(2025, 3, "Reading", "All", "Aust"),
            "nt_indigenous": naplan_cell(2025, 3, "Reading", "Indigenous", "NT"),
            "aust_indigenous": naplan_cell(2025, 3, "Reading", "Indigenous", "Aust"),
            "nt_indigenous_very_remote": naplan_cell(2025, 3, "Reading", "Indigenous very remote", "NT"),
            "aust_indigenous_very_remote": naplan_cell(2025, 3, "Reading", "Indigenous very remote", "Aust"),
            "nt_non_indigenous": naplan_cell(2025, 3, "Reading", "Non-Indigenous", "NT"),
            "aust_non_indigenous": naplan_cell(2025, 3, "Reading", "Non-Indigenous", "Aust"),
        },
        "naplan_2025_year9_reading": {
            "nt_indigenous": naplan_cell(2025, 9, "Reading", "Indigenous", "NT"),
            "aust_indigenous": naplan_cell(2025, 9, "Reading", "Indigenous", "Aust"),
            "nt_all": naplan_cell(2025, 9, "Reading", "All", "NT"),
            "aust_all": naplan_cell(2025, 9, "Reading", "All", "Aust"),
        },
        "naplan_2025_year3_numeracy": {
            "nt_indigenous": naplan_cell(2025, 3, "Numeracy", "Indigenous", "NT"),
            "aust_indigenous": naplan_cell(2025, 3, "Numeracy", "Indigenous", "Aust"),
            "nt_indigenous_very_remote": naplan_cell(2025, 3, "Numeracy", "Indigenous very remote", "NT"),
        },
        "naplan_nt_indigenous_year3_reading_by_year": {
            str(year): naplan_cell(year, 3, "Reading", "Indigenous", "NT") for year in (2023, 2024, 2025, 2026)
        },
        "closing_the_gap_year12": {
            "actual": ctg_actual.to_dict(orient="records"),
            "path_2031": ctg_path.to_dict(orient="records"),
            "target_national": 96.0,
        },
        "apparent_retention_year7_to_12": retention[
            (retention["year_range"] == "Year 7/8 - Year 12")
            & (retention["sector"] == "All affiliations")
            & (retention["sex"] == "Persons")
            & (retention["jurisdiction"].isin(["NT", "WA", "Qld", "SA"]))
            & (retention["calendar_year"].isin([2016, 2021, 2025]))
        ][["calendar_year", "jurisdiction", "arr_indigenous", "arr_non_indigenous", "arr_all"]]
        .assign(
            arr_indigenous=lambda frame: (frame["arr_indigenous"] * 100).round(1),
            arr_non_indigenous=lambda frame: (frame["arr_non_indigenous"] * 100).round(1),
            arr_all=lambda frame: (frame["arr_all"] * 100).round(1),
        )
        .to_dict(orient="records"),
        "enrolment_fte": {
            "nt_2016": _enrolment_point(enrolment_nt, 2016),
            "nt_2025": _enrolment_point(enrolment_nt, 2025),
            "states_sum_2025": _enrolment_point(national, 2025),
        },
        "student_teacher_ratio_government_2025": {
            row.jurisdiction: round(float(row.student_teacher_ratio), 2) for row in ratio_2025.itertuples(index=False)
        },
        "expenditure_per_fte_government_2023_24": {
            "total_nt": _money(spend, "NT"),
            "total_aust": _money(spend, "Aust"),
            "australian_government_nt": _money(cwealth, "NT"),
            "australian_government_aust": _money(cwealth, "Aust"),
            "dollars": "2023-24",
        },
        "nt_school_count_abs_2025": None if pd.isna(nt_schools_2025) else int(nt_schools_2025),
        "acara_nt_2025": profile_2025.to_dict(orient="records"),
        "model_schools": int(len(model_frame)),
    }
    destination = FIGURES.parent / "key_numbers.json"
    destination.write_text(json.dumps(_json_ready(key), indent=2, allow_nan=False))
    logger.info("Wrote %s and figures in %s", destination, FIGURES)
    return key


def _enrolment_point(frame: pd.DataFrame, year: int) -> dict | None:
    row = frame[frame["calendar_year"] == year]
    if row.empty:
        return None
    item = row.iloc[0]
    return {
        "fte_all": round(float(item["fte_all"]), 0),
        "fte_indigenous": round(float(item["fte_indigenous"]), 0),
        "indigenous_share_pct": round(float(item["indigenous_share"]) * 100, 1),
    }


def _money(frame: pd.DataFrame, jurisdiction: str) -> float | None:
    row = frame[frame["jurisdiction"] == jurisdiction]
    if row.empty or pd.isna(row["expenditure_per_fte"].iloc[0]):
        return None
    return round(float(row["expenditure_per_fte"].iloc[0]), 0)


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, float) and pd.isna(value):
        return None
    if hasattr(value, "item"):
        return _json_ready(value.item())
    return value
