"""Paths and source catalogue for the NT school education pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
BRONZE = DATA / "bronze"
BRONZE_RAW = BRONZE / "raw"
SNAPSHOTS = BRONZE / "snapshots"
SILVER = DATA / "silver"
GOLD = DATA / "gold"
QUALITY = DATA / "quality"
FIGURES = ROOT / "reports" / "figures"
DASHBOARD_DIST = ROOT / "dashboard" / "dist"

NT_RAW = BRONZE_RAW / "nt"
ACARA_RAW = BRONZE_RAW / "acara"
ABS_RAW = BRONZE_RAW / "abs"
ROGS_RAW = BRONZE_RAW / "rogs"
CTG_RAW = BRONZE_RAW / "ctg"

# Published region names were realigned for the 2020 collection.
# Darwin and Barkly kept their boundaries. Alice Springs and Katherine were
# renamed Central and Big Rivers. Arnhem was split: East Arnhem remained, and
# West Arnhem moved into the new Top End region with the former Palmerston and
# Rural region. Harmonised names are for display; comparability flags are not.
REGION_HARMONISED = {
    "alice springs region": "Central",
    "central region": "Central",
    "katherine region": "Big Rivers",
    "big rivers region": "Big Rivers",
    "arnhem region": "East Arnhem",
    "east arnhem region": "East Arnhem",
    "palmerston and rural region": "Top End",
    "top end region": "Top End",
    "darwin region": "Darwin",
    "barkly region": "Barkly",
    "nt government": "Northern Territory",
}

# Regions whose published series can be read across the 2020 rename.
REGION_CONTINUOUS = {"Darwin", "Barkly", "Central", "Big Rivers", "Northern Territory"}

JURISDICTION_ORDER = ["NSW", "Vic", "Qld", "WA", "SA", "Tas", "ACT", "NT", "Aust"]

REMOTENESS_ORDER = [
    "Major cities",
    "Inner regional",
    "Outer regional",
    "Remote",
    "Very remote",
]
