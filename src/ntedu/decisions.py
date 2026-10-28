"""Decision metrics for the static page and the Streamlit app.

Every figure is read from ``reports/key_numbers.json``. Status is a reading
rule for this page, not a target published by a department.
"""

from __future__ import annotations

import html
from dataclasses import dataclass


@dataclass(frozen=True)
class MetricCard:
    title: str
    value: str
    trend: str
    gap: str
    status: str
    action: str


@dataclass(frozen=True)
class GapRow:
    metric: str
    nt: str
    benchmark: str
    gap: str
    trend: str
    status: str


def _pp(value: float, digits: int = 1) -> str:
    sign = "\u2212" if value < 0 else "+"
    return f"{sign}{abs(value):.{digits}f} pp"


def _signed(value: float, digits: int, suffix: str) -> str:
    sign = "\u2212" if value < 0 else "+"
    return f"{sign}{abs(value):.{digits}f} {suffix}"


def _plain(value: float, digits: int) -> str:
    sign = "\u2212" if value < 0 else ""
    return f"{sign}{abs(value):.{digits}f}"


def _money(value: float) -> str:
    sign = "\u2212" if value < 0 else "+"
    return f"{sign}${abs(value):,.0f}"


def _status_from_disadvantage(disadvantage: float, *, level: float | None = None) -> str:
    """Concern if the rate is under 50% or the disadvantage exceeds 10 points.

    Watch is a disadvantage above 3 points. On track is the rest. Resource
    comparisons do not use this rule.
    """
    if level is not None and level < 50:
        return "Concern"
    if disadvantage > 10:
        return "Concern"
    if disadvantage > 3:
        return "Watch"
    return "On track"


def _retention(numbers: dict, jurisdiction: str, year: int) -> float:
    for row in numbers["apparent_retention_year7_to_12"]:
        if row["jurisdiction"] == jurisdiction and row["calendar_year"] == year:
            return float(row["arr_indigenous"])
    raise KeyError(f"No Aboriginal retention for {jurisdiction} {year}")


def _term(block: dict, fragment: str) -> dict:
    matches = [term for term in block["terms"] if fragment in term["term"]]
    if len(matches) != 1:
        raise KeyError(fragment)
    return matches[0]


def _p(value: float) -> str:
    if value < 0.001:
        return "<0.001"
    if value < 0.01:
        return f"{value:.3f}"
    return f"{value:.2f}"


def build_decision(numbers: dict) -> tuple[list[MetricCard], list[GapRow], list[str]]:
    gaps = numbers["rogs_years_1_10_all_schools"]
    remote = numbers["remoteness_2025_indigenous_years_1_10"]
    regions = numbers["nt_government_regions_2024"]
    nap = numbers["naplan_2025_year3_reading"]
    nap_years = numbers["naplan_nt_indigenous_year3_reading_by_year"]
    spend = numbers["expenditure_per_fte_government_2023_24"]
    ratio = numbers["student_teacher_ratio_government_2025"]
    trend = numbers["attendance_trend_nt_indigenous"]
    model = numbers["regression_2024_government_schools"]

    slope = _term(trend, "calendar_year")["estimate"]
    very_remote = _term(model, "T.Very Remote")
    remote_term = _term(model, "T.Remote]")
    nt_attend = float(gaps["nt_indigenous_2025"])
    aust_attend = float(gaps["aust_indigenous_2025"])
    attend_gap = nt_attend - aust_attend
    attend_status = _status_from_disadvantage(-attend_gap, level=nt_attend)
    if slope < -1:
        attend_status = "Concern"

    nt_vr = float(remote["nt_very_remote"])
    aust_vr = float(remote["aust_very_remote"])
    vr_gap = nt_vr - aust_vr
    darwin = float(regions["Darwin"]["indigenous"])
    barkly = float(regions["Barkly"]["indigenous"])
    arnhem = float(regions["East Arnhem"]["indigenous"])
    barkly_gap = barkly - darwin
    arnhem_gap = arnhem - darwin

    support = float(nap["nt_indigenous"]["needs_additional_support_pct"])
    support_aust = float(nap["aust_indigenous"]["needs_additional_support_pct"])
    absent = float(nap["nt_indigenous"]["absent_pct"])
    absent_aust = float(nap["aust_indigenous"]["absent_pct"])
    support_vr = float(nap["nt_indigenous_very_remote"]["needs_additional_support_pct"])
    absent_vr = float(nap["nt_indigenous_very_remote"]["absent_pct"])
    support_2023 = float(nap_years["2023"]["needs_additional_support_pct"])
    support_2026 = float(nap_years["2026"]["needs_additional_support_pct"])
    absent_2023 = float(nap_years["2023"]["absent_pct"])
    absent_2026 = float(nap_years["2026"]["absent_pct"])

    nt_ret = _retention(numbers, "NT", 2025)
    nt_ret_2016 = _retention(numbers, "NT", 2016)
    wa_ret = _retention(numbers, "WA", 2025)
    wa_ret_2016 = _retention(numbers, "WA", 2016)
    ret_gap = nt_ret - wa_ret

    nt_ratio = float(ratio["NT"])
    aust_ratio = float(ratio["Aust"])
    ratio_gap = nt_ratio - aust_ratio
    nt_spend = float(spend["total_nt"])
    aust_spend = float(spend["total_aust"])
    spend_gap = nt_spend - aust_spend

    vr_effect = float(very_remote["estimate"])
    remote_effect = float(remote_term["estimate"])
    r_squared = float(model["r_squared"])

    cards = [
        MetricCard(
            title="NT Aboriginal attendance, Years 1–10, 2025",
            value=f"{nt_attend:.1f}%",
            trend=f"Down {_signed(slope, 2, 'pts/yr')} · OLS, {trend['n']} published years",
            gap=f"{_pp(attend_gap)} vs Australia Aboriginal ({aust_attend:.1f}%)",
            status=attend_status,
            action=(
                f"The decline is the Aboriginal series. Non-Indigenous students in the NT attended "
                f"{gaps['nt_non_indigenous_2025']}%, level with Australia ({gaps['aust_non_indigenous_2025']}%)."
            ),
        ),
        MetricCard(
            title="Very remote NT, Aboriginal students, 2025",
            value=f"{nt_vr:.1f}%",
            trend="2025 cross-section only · no annual slope in this block",
            gap=f"{_pp(vr_gap)} vs Australia very remote ({aust_vr:.1f}%)",
            status=_status_from_disadvantage(-vr_gap, level=nt_vr),
            action=(
                f"Outer regional NT already matches Australia "
                f"({remote['nt_outer_regional']}% and {remote['aust_outer_regional']}%). "
                f"The shortfall sits in very remote schools."
            ),
        ),
        MetricCard(
            title="Regional hotspots, government schools, whole of 2024",
            value=f"{arnhem:.1f}% · {barkly:.1f}%",
            trend="Single year · East Arnhem and Barkly Aboriginal attendance",
            gap=f"{_pp(arnhem_gap)} and {_pp(barkly_gap)} vs Darwin ({darwin:.1f}%)",
            status=_status_from_disadvantage(max(-arnhem_gap, -barkly_gap), level=min(arnhem, barkly)),
            action=(
                "East Arnhem and the Barkly are the low regions. Darwin is not. "
                "This is the department’s whole-year collection, not the RoGS semester series."
            ),
        ),
        MetricCard(
            title="Year 3 reading, NT Aboriginal students, 2025",
            value=f"{support:.1f}% need support",
            trend=(
                f"Support share {support_2023:.1f}% in 2023, {support:.1f}% in 2025, {support_2026:.1f}% in 2026. "
                f"Absence {absent_2023:.1f}% in 2023, {absent:.1f}% in 2025, {absent_2026:.1f}% in 2026."
            ),
            gap=(
                f"{_pp(support - support_aust)} vs Australia Aboriginal on need-support; "
                f"absence {_pp(absent - absent_aust)} ({absent:.1f}% vs {absent_aust:.1f}%)"
            ),
            status=_status_from_disadvantage(support - support_aust),
            action=(
                f"In very remote NT, {support_vr:.1f}% of assessed students need support and {absent_vr:.1f}% were absent. "
                "Proficiency excludes students who were absent."
            ),
        ),
        MetricCard(
            title="Indigenous Year 12 apparent retention, 2025",
            value=f"{nt_ret:.1f}%",
            trend=f"Flat: {nt_ret_2016:.1f}% in 2016 and {nt_ret:.1f}% in 2025. WA rose from {wa_ret_2016:.1f}% to {wa_ret:.1f}%.",
            gap=f"{_pp(ret_gap)} vs Western Australia ({wa_ret:.1f}%)",
            status=_status_from_disadvantage(-ret_gap, level=nt_ret),
            action="Same ABS Year 7/8 to Year 12 measure. Apparent retention is not a cohort completion rate.",
        ),
        MetricCard(
            title="Resourcing, NT government schools",
            value=f"{nt_ratio:.1f} students/teacher",
            trend=f"Spend ${nt_spend:,.0f} per student in {spend['dollars']} · single-year snapshots",
            gap=(
                f"{_signed(ratio_gap, 1, 'students')} vs Australia ({aust_ratio:.1f}); "
                f"spend {_money(spend_gap)} vs ${aust_spend:,.0f}"
            ),
            status="On track",
            action="The NT already has fewer students per teacher and spends more per student. Resourcing is not the main lever.",
        ),
        MetricCard(
            title="School regression, government schools, 2024",
            value=f"{_plain(vr_effect, 1)} pp",
            trend=f"R² {r_squared:.3f} · n = {model['n']} · enrolment-weighted, HC1",
            gap=f"{_pp(vr_effect)} very remote vs outer regional, after Indigenous share and bottom SEA",
            status=_status_from_disadvantage(-vr_effect),
            action=(
                f"Remote is not distinguishable from outer regional "
                f"({_plain(remote_effect, 1)} pp, p = {_p(float(remote_term['p_value']))}). "
                "This describes co-movement. It is not a causal estimate, and schools are not ranked."
            ),
        ),
    ]
    rows = [
        GapRow(
            "Aboriginal attendance, Years 1–10, 2025",
            f"{nt_attend:.1f}%",
            f"Australia Aboriginal {aust_attend:.1f}%",
            _pp(attend_gap),
            f"{_signed(slope, 2, 'pts/yr')}",
            attend_status,
        ),
        GapRow(
            "Very remote Aboriginal attendance, 2025",
            f"{nt_vr:.1f}%",
            f"Australia very remote {aust_vr:.1f}%",
            _pp(vr_gap),
            "2025 only",
            _status_from_disadvantage(-vr_gap, level=nt_vr),
        ),
        GapRow(
            "Barkly Aboriginal, government schools, 2024",
            f"{barkly:.1f}%",
            f"Darwin {darwin:.1f}%",
            _pp(barkly_gap),
            "2024 only",
            _status_from_disadvantage(-barkly_gap, level=barkly),
        ),
        GapRow(
            "East Arnhem Aboriginal, government schools, 2024",
            f"{arnhem:.1f}%",
            f"Darwin {darwin:.1f}%",
            _pp(arnhem_gap),
            "2024 only",
            _status_from_disadvantage(-arnhem_gap, level=arnhem),
        ),
        GapRow(
            "Year 3 reading, needs support, Aboriginal, 2025",
            f"{support:.1f}%",
            f"Australia Aboriginal {support_aust:.1f}%",
            _pp(support - support_aust),
            f"{support_2023:.1f}% (2023) to {support_2026:.1f}% (2026)",
            _status_from_disadvantage(support - support_aust),
        ),
        GapRow(
            "Year 3 reading absence, Aboriginal, 2025",
            f"{absent:.1f}%",
            f"Australia Aboriginal {absent_aust:.1f}%",
            _pp(absent - absent_aust),
            f"{absent_2023:.1f}% (2023), {absent:.1f}% (2025), {absent_2026:.1f}% (2026)",
            _status_from_disadvantage(absent - absent_aust),
        ),
        GapRow(
            "Year 12 apparent retention, Aboriginal, 2025",
            f"{nt_ret:.1f}%",
            f"WA {wa_ret:.1f}%",
            _pp(ret_gap),
            f"{nt_ret_2016:.1f}% in 2016, {nt_ret:.1f}% in 2025",
            _status_from_disadvantage(-ret_gap, level=nt_ret),
        ),
        GapRow(
            "Students per teacher, government, 2025",
            f"{nt_ratio:.1f}",
            f"Australia {aust_ratio:.1f}",
            _signed(ratio_gap, 1, "students"),
            "2025 only",
            "On track",
        ),
        GapRow(
            f"Spend per student, government, {spend['dollars']}",
            f"${nt_spend:,.0f}",
            f"Australia ${aust_spend:,.0f}",
            _money(spend_gap),
            spend["dollars"],
            "On track",
        ),
        GapRow(
            "Very remote coefficient, school regression, 2024",
            f"{_plain(vr_effect, 1)} pp",
            "Outer regional, after Indigenous share and bottom SEA",
            _pp(vr_effect),
            f"R² {r_squared:.3f}, n = {model['n']}",
            _status_from_disadvantage(-vr_effect),
        ),
    ]
    recommendations = [
        (
            "Put attendance effort on very remote schools, East Arnhem and the Barkly. "
            f"Very remote Aboriginal attendance is {nt_vr:.1f}%. East Arnhem is {arnhem:.1f}% and the Barkly is {barkly:.1f}%, "
            f"against {darwin:.1f}% in Darwin. Outer regional NT already matches Australia "
            f"({remote['nt_outer_regional']}% and {remote['aust_outer_regional']}%)."
        ),
        (
            "Treat early reading and absence together. "
            f"In 2025, {support:.1f}% of assessed Aboriginal Year 3 students in the NT needed additional reading support, "
            f"and {absent:.1f}% were absent. In very remote NT those figures are {support_vr:.1f}% and {absent_vr:.1f}%. "
            "A support program that ignores who was missing will overstate progress."
        ),
        (
            "Learn from Western Australia’s Year 12 retention path. "
            f"NT Aboriginal apparent retention was {nt_ret_2016:.1f}% in 2016 and {nt_ret:.1f}% in 2025. "
            f"WA moved from {wa_ret_2016:.1f}% to {wa_ret:.1f}% on the same ABS measure. "
            "This is apparent retention, not a cohort rate."
        ),
        (
            "Do not lead with more teachers or more recurrent funding. "
            f"NT government schools have {nt_ratio:.1f} students per teacher, against {aust_ratio:.1f} nationally, "
            f"and spent ${nt_spend:,.0f} per student in {spend['dollars']}, against ${aust_spend:,.0f}. "
            "The attendance gap widened while that resourcing was already higher."
        ),
        (
            "Use the school model as a description of where the gap sits, not as a ranking. "
            f"In {model['n']} government schools, very remote location is still associated with about {abs(vr_effect):.1f} points "
            f"lower attendance after Indigenous enrolment and parental SEA (R² {r_squared:.3f}). "
            f"Remote is not distinguishable from outer regional ({_plain(remote_effect, 1)} points, p = {_p(float(remote_term['p_value']))})."
        ),
    ]
    return cards, rows, recommendations


def _klass(status: str) -> str:
    return {"Concern": "concern", "Watch": "watch", "On track": "ontrack"}[status]


def decision_html(numbers: dict) -> str:
    cards, rows, recommendations = build_decision(numbers)
    card_html = []
    for card in cards:
        kind = _klass(card.status)
        card_html.append(
            "<article class=\"metric {kind}\">"
            "<div class=\"metric-top\"><span class=\"pill {kind}\">{status}</span></div>"
            "<p class=\"value\">{value}</p>"
            "<p class=\"label\">{title}</p>"
            "<p class=\"trend\">{trend}</p>"
            "<p class=\"gap\">{gap}</p>"
            "<p class=\"action\">{action}</p>"
            "</article>".format(
                kind=kind,
                status=html.escape(card.status),
                value=html.escape(card.value),
                title=html.escape(card.title),
                trend=html.escape(card.trend),
                gap=html.escape(card.gap),
                action=html.escape(card.action),
            )
        )
    row_html = []
    for row in rows:
        kind = _klass(row.status)
        row_html.append(
            "<tr>"
            f"<td>{html.escape(row.metric)}</td>"
            f"<td class=\"num\">{html.escape(row.nt)}</td>"
            f"<td>{html.escape(row.benchmark)}</td>"
            f"<td class=\"num\">{html.escape(row.gap)}</td>"
            f"<td>{html.escape(row.trend)}</td>"
            f"<td><span class=\"pill {kind}\">{html.escape(row.status)}</span></td>"
            "</tr>"
        )
    rec_html = "".join(f"<li>{html.escape(item)}</li>" for item in recommendations)
    return (
        "<style>"
        ".decisions{color:#0B2545;font-family:Inter,Segoe UI,Helvetica Neue,Arial,sans-serif;padding:8px 0 12px}"
        ".decisions h2{margin:0;font-size:clamp(26px,3vw,32px);letter-spacing:-0.03em;line-height:1.15;color:#0B2545}"
        ".decisions .take{color:#3E4C59;font-size:14px;line-height:1.45;margin:8px 0 0}"
        ".metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}"
        ".metric{background:#fff;border:1px solid #D5DDE5;border-top:4px solid #9B2C2C;border-radius:14px;padding:14px 16px 16px}"
        ".metric.watch{border-top-color:#A56B00;background:#FFFCF4}"
        ".metric.concern{border-top-color:#9B2C2C;background:#FFF8F7}"
        ".metric.ontrack{border-top-color:#1F7A4D;background:#F4FBF7}"
        ".metric .value{margin:8px 0 0;font-size:clamp(28px,3vw,34px);font-weight:680;letter-spacing:-0.04em;font-variant-numeric:tabular-nums;line-height:1;color:#0B2545}"
        ".metric .label{margin:8px 0 0;font-size:14px;font-weight:680;line-height:1.3}"
        ".metric .trend,.metric .gap{margin:6px 0 0;font-size:13px;line-height:1.4}"
        ".metric .trend{font-weight:560}"
        ".metric .gap{color:#3E4C59}"
        ".metric .action{margin:8px 0 0;font-size:14px;line-height:1.45}"
        ".pill{display:inline-block;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:680;letter-spacing:.06em;text-transform:uppercase}"
        ".pill.concern{background:#F8E8E6;color:#7A1F1A}"
        ".pill.watch{background:#FBF3D5;color:#5C4300}"
        ".pill.ontrack{background:#E7F5EC;color:#0E5C36}"
        ".decision-split{display:grid;grid-template-columns:.9fr 1.1fr;gap:12px;margin-top:12px}"
        ".panel{background:#fff;border:1px solid #D5DDE5;border-radius:14px;padding:16px}"
        ".panel h3{margin:0 0 8px;font-size:18px;letter-spacing:-0.02em;color:#0B2545}"
        ".recs{margin:0;padding-left:18px}"
        ".recs li{margin:0 0 10px;font-size:14px;line-height:1.45}"
        ".table-scroll{overflow-x:auto}"
        "table.gaps{width:100%;border-collapse:collapse;font-size:13px}"
        "table.gaps th{text-align:left;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#3E4C59;border-bottom:2px solid #D5DDE5;padding:6px 8px;white-space:nowrap}"
        "table.gaps td{border-bottom:1px solid #D5DDE5;padding:8px;vertical-align:top}"
        "table.gaps td.num{font-variant-numeric:tabular-nums;white-space:nowrap}"
        "@media (max-width:860px){.metric-grid,.decision-split{grid-template-columns:1fr}}"
        "</style>"
        "<section class=\"decisions wrap\" id=\"decisions\">"
        "<h2>Key decision metrics</h2>"
        "<p class=\"take\">What stakeholders should act on. Each figure is a published cell or a model already in "
        "reports/key_numbers.json. Status is a reading rule for this page: Concern if the rate is under 50%, "
        "the disadvantage is more than 10 points, or the fitted attendance decline is steeper than 1 point a year. "
        "Watch is a disadvantage of 3 to 10 points. On track is within 3 points, or the NT side of a resource "
        "comparison is the better-resourced one. These are not targets set by the NT Department of Education.</p>"
        f"<div class=\"metric-grid\">{''.join(card_html)}</div>"
        "<div class=\"decision-split\">"
        "<section class=\"panel\"><h3>Recommendations</h3><ol class=\"recs\">"
        f"{rec_html}</ol></section>"
        "<section class=\"panel\"><h3>Targets and gaps</h3>"
        "<div class=\"table-scroll\"><table class=\"gaps\">"
        "<thead><tr><th>Metric</th><th>NT</th><th>Benchmark</th><th>Gap</th><th>Trend</th><th>Status</th></tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody></table></div></section>"
        "</div></section>"
    )
