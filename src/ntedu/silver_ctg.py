"""Closing the Gap outcome 5 (learning potential) dashboard extract."""

from __future__ import annotations

import logging

import pandas as pd

from ntedu.common import parse_number, write_parquet
from ntedu.config import CTG_RAW, SILVER

logger = logging.getLogger(__name__)

JURISDICTIONS = {
    "NSW": "NSW",
    "Vic": "Vic",
    "Qld": "Qld",
    "WA": "WA",
    "SA": "SA",
    "Tas": "Tas",
    "ACT": "ACT",
    "NT": "NT",
    "Aust": "Aust",
}


def build_ctg_silver() -> pd.DataFrame:
    path = CTG_RAW / "ctg05_learning_potential_202603.csv"
    frame = pd.read_csv(path)
    id_columns = [
        "Table_Number",
        "Year",
        "Measure",
        "Age",
        "Sex",
        "Indigenous_Status",
        "Remoteness",
        "Description1",
        "Description2",
        "Description3",
        "Description4",
        "Description7",
        "Data_Source",
        "Unit",
    ]
    existing = [column for column in id_columns if column in frame.columns]
    long = frame.melt(
        id_vars=existing,
        value_vars=list(JURISDICTIONS),
        var_name="jurisdiction_raw",
        value_name="value_raw",
    )
    long["jurisdiction"] = long["jurisdiction_raw"].map(JURISDICTIONS)
    long["value"] = long["value_raw"].map(parse_number)
    long["value_suppressed"] = long["value"].isna() & long["value_raw"].notna()
    # Shares are published as percents. Trajectory rows use the same unit.
    long["value_proportion"] = long["value"].map(lambda number: None if number is None or pd.isna(number) else number / 100.0)
    long = long.drop(columns=["jurisdiction_raw", "value_raw"])
    long = long.rename(
        columns={
            "Table_Number": "table_number",
            "Year": "year_label",
            "Measure": "measure",
            "Age": "age",
            "Sex": "sex",
            "Indigenous_Status": "indigenous_status",
            "Remoteness": "remoteness",
            "Description1": "description_1",
            "Description2": "description_2",
            "Description3": "description_3",
            "Description4": "description_4",
            "Description7": "description_7",
            "Data_Source": "data_source",
            "Unit": "unit",
        }
    )
    write_parquet(long, SILVER / "ctg_outcome5.parquet")
    logger.info("Closing the Gap outcome 5 rows %s", len(long))
    return long
