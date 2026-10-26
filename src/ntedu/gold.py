"""Assemble gold marts with DuckDB over the silver parquet layer."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ntedu.config import GOLD, ROOT, SILVER
from ntedu.match import match_schools

logger = logging.getLogger(__name__)

SQL_PATH = Path(__file__).parent / "sql" / "gold.sql"

SILVER_TABLES = {
    "nt_school_matched": SILVER / "nt_school_matched.parquet",
    "nt_group_attendance": SILVER / "nt_group_attendance.parquet",
    "acara_location": SILVER / "acara_school_location_nt.parquet",
    "rogs_attendance": SILVER / "rogs_attendance.parquet",
    "naplan_results": SILVER / "naplan_results.parquet",
}


def build_gold(attendance, profile) -> None:
    matched = match_schools(attendance, profile)
    if matched.empty:
        raise RuntimeError("School match produced no rows")
    GOLD.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    for name, path in SILVER_TABLES.items():
        connection.execute(
            f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path.as_posix()}')"
        )
    connection.execute(SQL_PATH.read_text())
    exports = {
        "school_year": "school_year.parquet",
        "nt_region_year": "nt_region_year.parquet",
        "nt_remoteness_year": "nt_remoteness_year.parquet",
        "nt_yearlevel_year": "nt_yearlevel_year.parquet",
        "jurisdiction_attendance": "jurisdiction_attendance.parquet",
        "naplan_focus": "naplan_focus.parquet",
    }
    for table, filename in exports.items():
        destination = GOLD / filename
        connection.execute(
            f"COPY (SELECT * FROM {table}) TO '{destination.as_posix()}' (FORMAT PARQUET)"
        )
        count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        logger.info("gold %s rows %s", table, count)
    connection.close()
    logger.info("Gold marts written under %s", GOLD.relative_to(ROOT))
