"""The static dashboard is generated from the marts and carries the published headline."""

from ntedu.static_dashboard import build_static_dashboard


def test_static_dashboard_contains_the_2025_attendance_rate():
    path = build_static_dashboard()
    html = path.read_text(encoding="utf-8")
    assert path.name == "index.html"
    assert "58.3%" in html
    assert "45.8%" in html
    assert "Key decision metrics" in html
    assert "1.19 pts/yr" in html
    assert "What stakeholders should act on" in html
    assert "plotly" in html.lower()
    assert len(html) > 100_000
