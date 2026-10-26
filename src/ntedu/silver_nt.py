"""Bronze NT Department of Education workbooks to tidy silver tables.

Government-school enrolment and attendance, published each term and as a
whole-of-year collection. Layouts change across years (percent strings versus
proportions, renamed regions, asterisk footnotes). This module detects the
grain from the sheet itself.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from ntedu.common import (
    clean_school_name,
    parse_number,
    parse_rate,
    read_excel_rows,
    write_parquet,
)
from ntedu.config import NT_RAW, REGION_HARMONISED, SILVER

logger = logging.getLogger(__name__)

STAGE_WORDS = {
    "early years",
    "primary years",
    "middle years",
    "senior years",
    "ungraded primary",
    "ungraded secondary",
    "preschool",
    "transition",
}

REMOTENESS_SECTIONS = {
    "outer regional": "Outer Regional",
    "remote": "Remote",
    "very remote": "Very Remote",
}


def _period_from_name(name: str) -> str:
    lower = name.lower()
    if "_t1" in lower or "term_1" in lower or "term1" in lower:
        return "term_1"
    if "_t2" in lower:
        return "term_2"
    if "_t3" in lower:
        return "term_3"
    if "_t4" in lower:
        return "term_4"
    return "whole_year"


def _year_from_name(name: str) -> int:
    match = re.search(r"nt_(\d{4})_", name)
    if not match:
        raise ValueError(f"Cannot read year from {name}")
    return int(match.group(1))


def _cell_text(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    if text.lower() in {"nan", "none"}:
        return ""
    return re.sub(r"\s+", " ", text)


def _is_footnote(text: str) -> bool:
    """True for workbook notes, not for values such as '1 236'."""
    lower = text.lower().strip()
    if len(text) > 140:
        return True
    if lower.startswith(("note", "source", "©")):
        return True
    if re.match(r"^\d+\.\s", lower) or re.match(r"^\([a-z]\)", lower):
        return True
    if "not publishable" in lower or "calculations are based" in lower:
        return True
    return False


def _find_group_header(rows: list[tuple]) -> int | None:
    for index, row in enumerate(rows[:25]):
        texts = [_cell_text(cell).lower() for cell in row]
        if any(("aborig" in text or "indigen" in text) and "non" not in text for text in texts):
            window = " ".join(texts)
            next_window = ""
            if index + 1 < len(rows):
                next_window = " ".join(_cell_text(cell).lower() for cell in rows[index + 1])
            if "attend" in window or "attend" in next_window or "enrol" in next_window:
                return index
    return None


def _group_columns(header: tuple, subhead: tuple) -> dict[str, dict[str, int]]:
    """Map population -> {enrolment, attendance} column indexes."""
    groups: dict[str, int] = {}
    for index, cell in enumerate(header):
        text = _cell_text(cell).lower()
        if not text:
            continue
        if "non" in text and ("aborig" in text or "indig" in text):
            groups["non_indigenous"] = index
        elif "aborig" in text or "indigen" in text:
            groups["indigenous"] = index
        elif text == "total":
            groups["total"] = index
    located: dict[str, dict[str, int]] = {}
    for population, start in groups.items():
        enrolment_col = None
        attendance_col = None
        for col in (start, start + 1):
            if col >= len(subhead):
                continue
            label = _cell_text(subhead[col]).lower()
            if "attend" in label:
                attendance_col = col
            elif "enrol" in label or "rate" not in label and label:
                enrolment_col = col
        if attendance_col is None:
            attendance_col = start + 1
        if enrolment_col is None:
            enrolment_col = start
        located[population] = {"enrolment": enrolment_col, "attendance": attendance_col}
    return located


def _first_numeric_column(row: tuple, columns: dict[str, dict[str, int]]) -> int:
    indexes = [spec[key] for spec in columns.values() for key in spec]
    return min(indexes) if indexes else len(row)


def _row_values(row: tuple, columns: dict[str, dict[str, int]]) -> dict[str, dict[str, float | None]]:
    parsed: dict[str, dict[str, float | None]] = {}
    any_value = False
    for population, spec in columns.items():
        enrolment = parse_number(row[spec["enrolment"]]) if spec["enrolment"] < len(row) else None
        attendance = parse_rate(row[spec["attendance"]]) if spec["attendance"] < len(row) else None
        if enrolment is not None or attendance is not None:
            any_value = True
        parsed[population] = {"enrolment": enrolment, "attendance": attendance}
    if not any_value:
        return {}
    return parsed


def _classify_grain(sections: list[str], labels: list[str]) -> str:
    blob = " ".join(sections + labels).lower()
    if any(key in blob for key in ("outer regional", "very remote")):
        return "remoteness"
    if any(token in blob for token in ("year 1", "year 7", "preschool", "transition", "year 12")):
        return "year_level"
    if "region" in blob:
        return "region"
    return "unknown"


def parse_group_workbook(path: Path) -> pd.DataFrame:
    """Parse a region, remoteness, or year-level workbook into long form."""
    _sheet, rows = read_excel_rows(path)
    header_index = _find_group_header(rows)
    if header_index is None:
        logger.warning("No Indigenous header in %s; skipping (charts-only or unexpected).", path.name)
        return pd.DataFrame()
    subhead = rows[header_index + 1] if header_index + 1 < len(rows) else tuple()
    columns = _group_columns(rows[header_index], subhead)
    if "total" not in columns:
        logger.warning("Could not locate population columns in %s", path.name)
        return pd.DataFrame()
    numeric_start = _first_numeric_column(rows[header_index + 2] if header_index + 2 < len(rows) else rows[header_index], columns)

    records: list[dict] = []
    section = ""
    stage = ""
    band_carry = ""
    file_year = _year_from_name(path.name)
    period = _period_from_name(path.name)
    seen_labels: list[str] = []
    seen_sections: list[str] = []

    for row in rows[header_index + 2 :]:
        texts = [_cell_text(cell) for cell in row]
        if not any(texts):
            continue
        label_probe = [text for text in texts[:numeric_start] if text]
        if any(_is_footnote(text) for text in label_probe):
            break
        values = _row_values(row, columns)
        label_cells = [text for text in texts[:numeric_start] if text]
        if not values:
            header_text = " ".join(label_cells).strip()
            if not header_text:
                continue
            lower = header_text.lower()
            if lower in REMOTENESS_SECTIONS or lower.endswith("region") or lower in {"primary", "secondary"}:
                section = header_text
                seen_sections.append(header_text)
                if lower in {"primary", "secondary"}:
                    stage = header_text.title()
            continue
        row_label = label_cells[-1] if label_cells else ""
        band = label_cells[-2] if len(label_cells) >= 2 else ""
        row_stage = label_cells[-3] if len(label_cells) >= 3 else ""
        if row_stage.lower() in {"primary", "secondary"}:
            stage = row_stage.title()
            if band:
                band_carry = band
        elif band.lower() in {"primary", "secondary"}:
            stage = band.title()
            band = ""
            band_carry = ""
        elif band:
            band_carry = band
        else:
            band = band_carry
        if not row_label:
            continue
        if _is_footnote(row_label):
            break
        seen_labels.append(row_label)
        lower_label = row_label.lower()
        if "total" in lower_label:
            row_kind = "total"
        else:
            row_kind = "detail"
        for population, metrics in values.items():
            records.append(
                {
                    "source_file": path.name,
                    "file_year": file_year,
                    "calendar_year": file_year,
                    "period": period,
                    "section": section,
                    "stage": stage,
                    "band": band,
                    "row_label": row_label,
                    "row_kind": row_kind,
                    "population": population,
                    "enrolment": metrics["enrolment"],
                    "attendance_rate": metrics["attendance"],
                    "suppressed": metrics["enrolment"] is None and metrics["attendance"] is None,
                }
            )
        # stage carried above may be stale; set explicitly from this row when present
    grain = _classify_grain(seen_sections, seen_labels)
    for record in records:
        record["grain"] = grain
        if grain == "remoteness":
            record["remoteness"] = _remoteness_label(record["section"])
            record["region_harmonised"] = _harmonise(record["row_label"])
        elif grain == "region":
            record["remoteness"] = None
            record["region_harmonised"] = _harmonise(record["section"])
        else:
            record["remoteness"] = None
            record["region_harmonised"] = None
        if _is_nt_total(record["row_label"]):
            record["region_harmonised"] = "Northern Territory"
            record["remoteness"] = None
            record["row_kind"] = "total"
            record["section"] = "Northern Territory"
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return frame
    frame["stage"] = frame["stage"].replace("", pd.NA)
    return frame


def _harmonise(label: str) -> str | None:
    if not label:
        return None
    key = re.sub(r"\s+", " ", label).strip().lower()
    if key.endswith(" total"):
        key = key[: -len(" total")].strip()
    return REGION_HARMONISED.get(key)


def _remoteness_label(section: str) -> str | None:
    key = section.strip().lower()
    return REMOTENESS_SECTIONS.get(key)


def _is_nt_total(label: str) -> bool:
    key = re.sub(r"\s+", " ", label).strip().lower()
    return key.startswith("ntg") or "nt government" in key or key in {"northern territory", "nt total"}


def _find_school_header(rows: list[tuple]) -> int | None:
    for index, row in enumerate(rows[:15]):
        texts = [_cell_text(cell).lower() for cell in row]
        if any(text == "school" or text.endswith(" school") and "government" in text for text in texts):
            if any("attend" in text or "enrol" in text for text in texts):
                return index
        if any(text == "school" for text in texts) and any("attend" in text for text in texts):
            return index
    return None


def _years_above(rows: list[tuple], header_index: int, width: int) -> dict[int, int]:
    """Map a column index to the calendar year printed above it."""
    found: dict[int, int] = {}
    for row in rows[max(0, header_index - 3) : header_index]:
        for index, cell in enumerate(row):
            if isinstance(cell, (int, float)) and not isinstance(cell, bool):
                year = int(cell)
                if 2000 <= year <= 2100:
                    found[index] = year
            else:
                text = _cell_text(cell)
                match = re.match(r"^(20\d{2})\b", text)
                if match:
                    found[index] = int(match.group(1))
    # Spread each year across the enrolment and attendance columns beneath it.
    expanded: dict[int, int] = {}
    for index, year in found.items():
        expanded[index] = year
        if index + 1 < width and index + 1 not in found:
            expanded[index + 1] = year
    return expanded


def parse_school_workbook(path: Path) -> pd.DataFrame:
    _sheet, rows = read_excel_rows(path)
    header_index = _find_school_header(rows)
    if header_index is None:
        logger.warning("No school header in %s", path.name)
        return pd.DataFrame()
    header = rows[header_index]
    school_col = next(index for index, cell in enumerate(header) if _cell_text(cell).lower() in {"school", "northern territory government school"})
    file_year = _year_from_name(path.name)
    period = _period_from_name(path.name)
    year_by_col = _years_above(rows, header_index, len(header) + 2)
    pairs: list[tuple[int, int, int]] = []
    attendance_cols = [index for index, cell in enumerate(header) if "attend" in _cell_text(cell).lower()]
    for attendance_col in attendance_cols:
        enrolment_col = attendance_col - 1
        header_year = re.search(r"(20\d{2})", _cell_text(header[attendance_col]))
        year = int(header_year.group(1)) if header_year else None
        year = year or year_by_col.get(attendance_col) or year_by_col.get(enrolment_col)
        if year is None:
            # Left pair is the file year; the comparison pair is the previous year.
            year = file_year if not pairs else file_year - 1
        pairs.append((year, enrolment_col, attendance_col))

    records = []
    for row in rows[header_index + 1 :]:
        if school_col >= len(row):
            continue
        raw_name = _cell_text(row[school_col])
        if not raw_name:
            continue
        if _is_footnote(raw_name) or raw_name.lower().startswith("table "):
            break
        name, markers = clean_school_name(raw_name)
        if not name or name.lower() in {"school", "enrolment", "attendance rate", "average enrolment"}:
            continue
        if name.lower().startswith("northern territory"):
            continue
        for year, enrolment_col, attendance_col in pairs:
            enrolment = parse_number(row[enrolment_col]) if enrolment_col < len(row) else None
            attendance = parse_rate(row[attendance_col]) if attendance_col < len(row) else None
            suppressed = enrolment is None or attendance is None
            records.append(
                {
                    "source_file": path.name,
                    "file_year": file_year,
                    "calendar_year": year,
                    "period": period,
                    "series_role": "primary" if year == file_year else "comparison",
                    "school_name": name,
                    "name_markers": markers,
                    "enrolment": enrolment,
                    "attendance_rate": attendance,
                    "suppressed": suppressed,
                    "sector": "Government",
                    "jurisdiction": "NT",
                }
            )
    return pd.DataFrame.from_records(records)


def _dedupe_schools(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    role_rank = {"primary": 0, "comparison": 1}
    ranked = frame.copy()
    ranked["role_rank"] = ranked["series_role"].map(role_rank).fillna(9)
    ranked = ranked.sort_values(["role_rank", "source_file"])
    ranked = ranked.drop_duplicates(["school_name", "calendar_year", "period"], keep="first")
    return ranked.drop(columns=["role_rank"]).reset_index(drop=True)


def build_nt_silver() -> dict[str, pd.DataFrame]:
    school_frames = []
    group_frames = []
    for path in sorted(NT_RAW.glob("*.xlsx")):
        if "school" in path.name:
            parsed = parse_school_workbook(path)
            logger.info("schools %s -> %s rows", path.name, len(parsed))
            school_frames.append(parsed)
        else:
            parsed = parse_group_workbook(path)
            logger.info("group %s -> %s rows grain=%s", path.name, len(parsed), parsed["grain"].iloc[0] if len(parsed) else "empty")
            group_frames.append(parsed)
    schools = _dedupe_schools(pd.concat(school_frames, ignore_index=True) if school_frames else pd.DataFrame())
    groups = pd.concat([frame for frame in group_frames if not frame.empty], ignore_index=True) if group_frames else pd.DataFrame()
    write_parquet(schools, SILVER / "nt_school_attendance.parquet")
    write_parquet(groups, SILVER / "nt_group_attendance.parquet")
    return {"nt_school_attendance": schools, "nt_group_attendance": groups}
