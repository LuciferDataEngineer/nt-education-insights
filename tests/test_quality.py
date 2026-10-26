"""The committed marts still match the published cells the pipeline was checked against."""

import pandas as pd

from ntedu.config import GOLD, SILVER
from ntedu.quality import run_quality


def test_quality_suite_passes_on_committed_marts():
    report = run_quality()
    assert report["failures"] == []
    assert report["match_rate_2024"] >= 0.90
    assert report["school_rows"] > 1000
    assert report["naplan_rows"] > 1000


def test_barkly_and_darwin_are_not_the_same_system():
    regions = pd.read_parquet(GOLD / "nt_region_year.parquet")
    whole = regions[
        regions["calendar_year"].eq(2024)
        & regions["period"].eq("whole_year")
        & regions["population"].eq("indigenous")
    ].set_index("region")
    assert whole.loc["Darwin", "attendance_rate"] > 0.70
    assert whole.loc["Barkly", "attendance_rate"] < 0.45
    assert whole.loc["East Arnhem", "attendance_rate"] < 0.45


def test_naplan_absence_is_kept_separate_from_proficiency():
    naplan = pd.read_parquet(SILVER / "naplan_results.parquet")
    row = naplan[
        naplan["jurisdiction"].eq("NT")
        & naplan["calendar_year"].eq(2025)
        & naplan["year_level"].eq(3)
        & naplan["domain"].eq("Reading")
        & naplan["subgroup"].eq("Indigenous very remote")
    ].iloc[0]
    assert row["needs_additional_support_pct"] > 80
    assert row["absent_pct"] > 30
    assert row["proficiency_denominator"] == "assessed_students"
