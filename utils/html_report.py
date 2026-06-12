"""Shared HTML building blocks for summary reports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from html import escape

from utils.time_helper import format_timestamp

EXECUTED_AT_FORMAT = "%Y-%m-%d %H:%M:%S"

_BASE_STYLES = """
:root {
  --bg: #f0f4f8;
  --card: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --primary: #0ea5e9;
  --primary-dark: #0369a1;
  --border: #e2e8f0;
  --success: #16a34a;
  --warning: #d97706;
  --danger: #dc2626;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: linear-gradient(160deg, #e0f2fe 0%, var(--bg) 40%, #f8fafc 100%);
  color: var(--text);
  line-height: 1.5;
}
.container { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
.report-header {
  background: linear-gradient(135deg, #0284c7, #0ea5e9 50%, #38bdf8);
  color: #fff;
  border-radius: 16px;
  padding: 2rem 2.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 10px 30px rgba(2, 132, 199, 0.25);
}
.report-header h1 { margin: 0 0 0.25rem; font-size: 2rem; }
.report-header p { margin: 0; opacity: 0.9; }
.report-section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}
.report-section h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  color: var(--primary-dark);
  border-bottom: 2px solid #bae6fd;
  padding-bottom: 0.5rem;
}
.purpose { color: var(--muted); font-size: 0.95rem; margin: 0 0 1.25rem; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  font-size: 0.95rem;
}
.data-table th {
  background: #f1f5f9;
  color: var(--primary-dark);
  text-align: left;
  padding: 0.65rem 0.85rem;
  border-bottom: 2px solid var(--border);
}
.data-table td {
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--border);
}
.data-table tbody tr:hover { background: #f8fafc; }
.weather-badge {
  display: inline-block;
  color: #fff;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
}
.bar-cell { display: flex; align-items: center; gap: 0.75rem; min-width: 140px; }
.bar-cell .bar { height: 8px; border-radius: 4px; min-width: 4px; flex: 1; max-width: 120px; }
.bar-cell span { min-width: 3rem; text-align: right; color: var(--muted); }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}
.stat-card {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem;
}
.stat-label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 0.25rem; }
.stat-value { display: block; font-size: 1.35rem; font-weight: 700; color: var(--primary-dark); }
.info-list { margin: 0.5rem 0 1rem; padding-left: 1.25rem; }
.info-list li { margin: 0.25rem 0; }
.formula {
  background: #f1f5f9;
  border-left: 4px solid var(--primary);
  padding: 0.75rem 1rem;
  border-radius: 0 8px 8px 0;
  font-family: ui-monospace, monospace;
  font-size: 0.9rem;
  margin: 1rem 0;
}
.summary-box {
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-top: 1rem;
}
.summary-box ul { margin: 0; padding-left: 1.25rem; }
.summary-box.info { background: #eff6ff; border: 1px solid #bfdbfe; }
.summary-box.warning { background: #fffbeb; border: 1px solid #fcd34d; }
.summary-box.danger { background: #fef2f2; border: 1px solid #fecaca; }
.summary-box.success { background: #f0fdf4; border: 1px solid #bbf7d0; }
.alert-table .alert-active { background: #fff7ed; }
.alert-table .alert-active td:first-child { color: var(--warning); font-weight: 600; }
.alert-table .alert-clear td { color: var(--muted); }
.temp-high { color: #dc2626; font-weight: 600; }
.temp-low { color: #2563eb; font-weight: 600; }
.period-pill {
  display: inline-block;
  background: #e0f2fe;
  color: var(--primary-dark);
  padding: 0.15rem 0.55rem;
  border-radius: 6px;
  font-size: 0.85rem;
  margin: 0.15rem 0.25rem 0.15rem 0;
}
.generated-at { text-align: center; color: var(--muted); font-size: 0.85rem; margin-top: 2rem; }
"""

_AUTOMATION_QA_STYLES = """
.report-header.automation {
  background: linear-gradient(135deg, #4f46e5, #6366f1 50%, #818cf8);
  box-shadow: 0 10px 30px rgba(79, 70, 229, 0.25);
}
.status-badge {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
}
.status-badge.success { background: #dcfce7; color: #166534; }
.status-badge.danger { background: #fee2e2; color: #991b1b; }
.status-badge.warning { background: #fef3c7; color: #92400e; }
.status-badge.info { background: #e0f2fe; color: #075985; }
.score-card {
  background: linear-gradient(135deg, #f8fafc, #eff6ff);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  margin-top: 1rem;
}
.score-card .score-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--primary-dark);
}
.timeline-passed td:nth-child(2) { color: var(--success); font-weight: 600; }
.timeline-failed td:nth-child(2) { color: var(--danger); font-weight: 600; }
.overview-lines { margin: 1rem 0; }
.overview-line {
  display: flex;
  gap: 0.5rem;
  padding: 0.55rem 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.95rem;
}
.overview-line:last-child { border-bottom: none; }
.overview-label { min-width: 220px; color: var(--muted); font-weight: 600; }
.overview-value { color: var(--text); }
.report-section-group > h2 {
  margin-bottom: 1.25rem;
  font-size: 1.35rem;
}
.section-group-content .report-section {
  border: none;
  box-shadow: none;
  padding: 0 0 1.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
}
.section-group-content .report-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.section-group-content .report-section h3 {
  margin: 0 0 0.5rem;
  font-size: 1.15rem;
  color: var(--primary-dark);
  border-bottom: 2px solid #bae6fd;
  padding-bottom: 0.5rem;
}
"""


def escape_html(value: object) -> str:
    """Escape text for safe HTML output."""
    return escape(str(value), quote=True)


def split_values(value: str) -> list[str]:
    """Split a comma-separated string into trimmed parts."""
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_executed_at(value: str) -> datetime | None:
    """Parse an execution timestamp such as '2026-06-10 21:39:44'."""
    if not value:
        return None
    try:
        return datetime.strptime(value, EXECUTED_AT_FORMAT)
    except ValueError:
        return None


def percentage(count: int, total: int) -> float:
    """Return a percentage rounded to one decimal place."""
    if total == 0:
        return 0.0
    return round((count / total) * 100, 1)


def base_html_styles() -> str:
    """Return shared CSS for weather and QA reports."""
    return _BASE_STYLES


def automation_qa_styles() -> str:
    """Return additional CSS used by the automation QA report."""
    return _AUTOMATION_QA_STYLES


def html_table(
    headers: list[str],
    rows: list[list[str]],
    row_class_fn: Callable[[list[str]], str] | None = None,
) -> str:
    """Render a data table with optional per-row CSS classes."""
    header_html = "".join(f"<th>{escape_html(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        row_class = f' class="{row_class_fn(row)}"' if row_class_fn else ""
        cells = "".join(f"<td>{escape_html(cell)}</td>" for cell in row)
        body_rows.append(f"<tr{row_class}>{cells}</tr>")
    return (
        '<table class="data-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def html_section(
    section_id: str,
    title: str,
    purpose: str,
    content: str,
    heading_level: int = 2,
) -> str:
    """Render a titled report section with purpose text and body content."""
    heading_tag = f"h{heading_level}"
    return (
        f'<section class="report-section" id="{section_id}">'
        f"<{heading_tag}>{escape_html(title)}</{heading_tag}>"
        f'<p class="purpose">{escape_html(purpose)}</p>'
        f"{content}"
        "</section>"
    )


def html_section_group(group_id: str, title: str, content: str) -> str:
    """Render a grouped section that contains nested report sections."""
    return (
        f'<section class="report-section report-section-group" id="{group_id}">'
        f"<h2>{escape_html(title)}</h2>"
        f'<div class="section-group-content">{content}</div>'
        "</section>"
    )


def html_summary_box(items: list[str], tone: str = "info") -> str:
    """Render a colored summary box with bullet points."""
    lines = "".join(f"<li>{escape_html(item)}</li>" for item in items)
    return f'<div class="summary-box {tone}"><ul>{lines}</ul></div>'


def html_stat_cards(items: list[tuple[str, str]]) -> str:
    """Render a responsive grid of label/value stat cards."""
    cards = "".join(
        f'<div class="stat-card"><span class="stat-label">{escape_html(label)}</span>'
        f'<span class="stat-value">{escape_html(value)}</span></div>'
        for label, value in items
    )
    return f'<div class="stat-grid">{cards}</div>'


def html_report_header(
    title: str,
    subtitle: str = "",
    *,
    theme: str = "weather",
) -> str:
    """Render the top report banner."""
    theme_class = " automation" if theme == "automation" else ""
    subtitle_html = f"<p>{escape_html(subtitle)}</p>" if subtitle else ""
    return (
        f'<header class="report-header{theme_class}">'
        f"<h1>{escape_html(title)}</h1>"
        f"{subtitle_html}"
        "</header>"
    )


def html_document(
    title: str,
    header: str,
    sections_html: str,
    *,
    extra_styles: str = "",
) -> str:
    """Assemble a complete HTML report page."""
    generated_at = format_timestamp()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html(title)}</title>
  <style>{base_html_styles()}{extra_styles}</style>
</head>
<body>
  <div class="container">
    {header}
    {sections_html}
    <p class="generated-at">Generated at {generated_at} UTC</p>
  </div>
</body>
</html>"""
