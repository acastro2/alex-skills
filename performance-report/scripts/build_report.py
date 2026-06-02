#!/usr/bin/env python3
"""Hydrate an HTML template with collected performance data to produce the final report."""

import argparse
import json
import sys
from datetime import datetime, date
from pathlib import Path

CHART_PALETTE = [
    "#2563eb", "#ef4444", "#10b981", "#8b5cf6", "#6366f1",
    "#9ca3af", "#f59e0b", "#d1d5db", "#ec4899", "#14b8a6", "#0ea5e9",
]

ADO_BASE_URL = "https://dev.azure.com/CuroFinTech/Tiger/_workitems/edit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_iso(s: str) -> datetime:
    if not s:
        return datetime.min
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.min


def month_key(dt: datetime) -> str:
    """Return e.g. 'Dec 2025'."""
    if dt == datetime.min:
        return "Unknown"
    return dt.strftime("%b %Y")


def month_sort_key(label: str) -> tuple:
    try:
        d = datetime.strptime(label, "%b %Y")
        return (d.year, d.month)
    except ValueError:
        return (9999, 99)


def ordered_months(start: date, end: date) -> list[str]:
    """Generate month labels between start (inclusive) and end (exclusive)."""
    months = []
    y, m = start.year, start.month
    while (y, m) < (end.year, end.month):
        months.append(datetime(y, m, 1).strftime("%b %Y"))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def period_label(start: date, end: date) -> str:
    # end is exclusive, so display the last included month
    last_y, last_m = end.year, end.month - 1
    if last_m < 1:
        last_m = 12
        last_y -= 1
    s = datetime(start.year, start.month, 1).strftime("%B %Y")
    e = datetime(last_y, last_m, 1).strftime("%B %Y")
    return f"{s} \u2013 {e}"


def color_for(idx: int) -> str:
    return CHART_PALETTE[idx % len(CHART_PALETTE)]


def safe_sp(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def pct(part: float, total: float) -> str:
    if total == 0:
        return "0"
    return f"{part / total * 100:.0f}"


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path: str) -> list | dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def build(args):
    prs = load_json(args.prs)
    reviews = load_json(args.reviews)
    ado_items = load_json(args.ado)
    categories = load_json(args.categories)

    cat_assignments = categories.get("assignments", {})
    cat_list = categories.get("categories", [])
    overhead_cats = set(categories.get("overhead_categories", []))
    tag_colors = categories.get("tag_colors", {})

    start = date.fromisoformat(args.period_start)
    end = date.fromisoformat(args.period_end)
    months = ordered_months(start, end)

    # -- attach parsed dates & categories -----------------------------------
    for pr in prs:
        pr["_dt"] = parse_iso(pr.get("closedAt", ""))
        pr["_month"] = month_key(pr["_dt"])
        pr["_cat"] = cat_assignments.get(f"PR:{pr['repository']['name']}#{pr['number']}", "Uncategorized")

    for item in ado_items:
        dt = parse_iso(item.get("changedDate") or item.get("createdDate", ""))
        item["_dt"] = dt
        item["_month"] = month_key(dt)
        item["_cat"] = cat_assignments.get(f"ADO:{item['id']}", "Uncategorized")
        item["_sp"] = safe_sp(item.get("storyPoints"))

    for rv in reviews:
        rv["_dt"] = parse_iso(rv.get("closedAt", ""))
        rv["_month"] = month_key(rv["_dt"])

    # -- KPIs ---------------------------------------------------------------
    kpi_merged_prs = len(prs)
    kpi_closed_stories = len(ado_items)
    kpi_sp = sum(i["_sp"] for i in ado_items)
    kpi_additions = sum(pr.get("additions", 0) or 0 for pr in prs)
    kpi_deletions = sum(pr.get("deletions", 0) or 0 for pr in prs)
    kpi_files = sum(pr.get("changedFiles", 0) or 0 for pr in prs)
    kpi_repos = len({pr["repository"]["nameWithOwner"] for pr in prs})

    # -- monthly aggregation ------------------------------------------------
    monthly_stories = {m: 0 for m in months}
    monthly_sp = {m: 0.0 for m in months}
    monthly_prs = {m: 0 for m in months}
    monthly_additions = {m: 0 for m in months}
    monthly_deletions = {m: 0 for m in months}

    for item in ado_items:
        m = item["_month"]
        if m in monthly_stories:
            monthly_stories[m] += 1
            monthly_sp[m] += item["_sp"]

    for pr in prs:
        m = pr["_month"]
        if m in monthly_prs:
            monthly_prs[m] += 1
            monthly_additions[m] += pr.get("additions", 0) or 0
            monthly_deletions[m] += pr.get("deletions", 0) or 0

    # -- category aggregation -----------------------------------------------
    all_cats = sorted(set(cat_list) | {i["_cat"] for i in ado_items} | {p["_cat"] for p in prs})

    cat_stories = {c: 0 for c in all_cats}
    cat_sp = {c: 0.0 for c in all_cats}
    cat_prs = {c: 0 for c in all_cats}

    for item in ado_items:
        cat_stories[item["_cat"]] += 1
        cat_sp[item["_cat"]] += item["_sp"]

    for pr in prs:
        cat_prs[pr["_cat"]] += 1

    # delivery vs overhead
    delivery_stories = sum(v for c, v in cat_stories.items() if c not in overhead_cats)
    delivery_sp = sum(v for c, v in cat_sp.items() if c not in overhead_cats)
    overhead_stories = sum(v for c, v in cat_stories.items() if c in overhead_cats)
    overhead_sp = sum(v for c, v in cat_sp.items() if c in overhead_cats)
    total_stories = delivery_stories + overhead_stories
    total_sp = delivery_sp + overhead_sp

    delivery_desc = ", ".join(sorted(c for c in all_cats if c not in overhead_cats and (cat_stories[c] or cat_prs[c])))
    overhead_desc = ", ".join(sorted(c for c in all_cats if c in overhead_cats and (cat_stories[c] or cat_prs[c])))

    # -- heatmap data (category x month) ------------------------------------
    heatmap_stories = {c: {m: 0 for m in months} for c in all_cats}
    heatmap_prs = {c: {m: 0 for m in months} for c in all_cats}

    for item in ado_items:
        if item["_month"] in heatmap_stories.get(item["_cat"], {}):
            heatmap_stories[item["_cat"]][item["_month"]] += 1

    for pr in prs:
        if pr["_month"] in heatmap_prs.get(pr["_cat"], {}):
            heatmap_prs[pr["_cat"]][pr["_month"]] += 1

    # -- color mapping for charts -------------------------------------------
    cat_color_map = {}
    for idx, c in enumerate(all_cats):
        cat_color_map[c] = color_for(idx)

    # -- build tag HTML helper ----------------------------------------------
    def tag_html(cat: str) -> str:
        css_class = tag_colors.get(cat, "")
        if css_class:
            return f'<span class="tag tag-{css_class}">{escape_html(cat)}</span>'
        return f'<span class="tag">{escape_html(cat)}</span>'

    # -- HTML table rows: PRs -----------------------------------------------
    sorted_prs = sorted(prs, key=lambda p: p["_dt"])
    pr_rows = []
    for pr in sorted_prs:
        repo = pr["repository"]["name"]
        num = pr["number"]
        title = escape_html(pr.get("title", ""))
        url = pr.get("url", "#")
        additions = pr.get("additions", 0) or 0
        deletions = pr.get("deletions", 0) or 0
        files = pr.get("changedFiles", 0) or 0
        closed = pr["_dt"].strftime("%Y-%m-%d") if pr["_dt"] != datetime.min else ""
        cat = pr["_cat"]
        pr_rows.append(
            f"<tr>"
            f'<td><a href="{url}" target="_blank">{repo}#{num}</a></td>'
            f"<td>{title}</td>"
            f"<td>{closed}</td>"
            f'<td class="num">+{additions}</td>'
            f'<td class="num">-{deletions}</td>'
            f'<td class="num">{files}</td>'
            f"<td>{tag_html(cat)}</td>"
            f"</tr>"
        )
    pr_rows.append(
        f'<tr class="total-row">'
        f"<td colspan=\"3\"><strong>Total ({len(sorted_prs)} PRs)</strong></td>"
        f'<td class="num"><strong>+{kpi_additions}</strong></td>'
        f'<td class="num"><strong>-{kpi_deletions}</strong></td>'
        f'<td class="num"><strong>{kpi_files}</strong></td>'
        f"<td></td>"
        f"</tr>"
    )

    # -- HTML table rows: ADO -----------------------------------------------
    sorted_ado = sorted(ado_items, key=lambda i: i["_dt"])
    ado_rows = []
    for item in sorted_ado:
        aid = item["id"]
        title = escape_html(item.get("title", ""))
        state = item.get("state", "")
        sp = item["_sp"]
        sp_display = f"{sp:g}" if sp else "—"
        changed = item["_dt"].strftime("%Y-%m-%d") if item["_dt"] != datetime.min else ""
        cat = item["_cat"]
        url = f"{ADO_BASE_URL}/{aid}"
        ado_rows.append(
            f"<tr>"
            f'<td><a href="{url}" target="_blank">{aid}</a></td>'
            f"<td>{title}</td>"
            f"<td>{state}</td>"
            f'<td class="num">{sp_display}</td>'
            f"<td>{changed}</td>"
            f"<td>{tag_html(cat)}</td>"
            f"</tr>"
        )
    total_sp_display = f"{kpi_sp:g}"
    ado_rows.append(
        f'<tr class="total-row">'
        f"<td colspan=\"3\"><strong>Total ({len(sorted_ado)} items)</strong></td>"
        f'<td class="num"><strong>{total_sp_display}</strong></td>'
        f"<td></td><td></td>"
        f"</tr>"
    )

    # -- monthly trend rows -------------------------------------------------
    trend_rows = []
    for m in months:
        trend_rows.append(
            f"<tr>"
            f"<td>{m}</td>"
            f'<td class="num">{monthly_stories[m]}</td>'
            f'<td class="num">{monthly_sp[m]:g}</td>'
            f'<td class="num">{monthly_prs[m]}</td>'
            f'<td class="num">+{monthly_additions[m]}</td>'
            f'<td class="num">-{monthly_deletions[m]}</td>'
            f"</tr>"
        )
    trend_rows.append(
        f'<tr class="total-row">'
        f"<td><strong>Total</strong></td>"
        f'<td class="num"><strong>{kpi_closed_stories}</strong></td>'
        f'<td class="num"><strong>{kpi_sp:g}</strong></td>'
        f'<td class="num"><strong>{kpi_merged_prs}</strong></td>'
        f'<td class="num"><strong>+{kpi_additions}</strong></td>'
        f'<td class="num"><strong>-{kpi_deletions}</strong></td>'
        f"</tr>"
    )

    # -- category table rows ------------------------------------------------
    category_rows = []
    for c in all_cats:
        if not cat_stories[c] and not cat_prs[c]:
            continue
        is_oh = "Yes" if c in overhead_cats else ""
        category_rows.append(
            f"<tr>"
            f"<td>{tag_html(c)}</td>"
            f'<td class="num">{cat_stories[c]}</td>'
            f'<td class="num">{cat_sp[c]:g}</td>'
            f'<td class="num">{cat_prs[c]}</td>'
            f"<td>{is_oh}</td>"
            f"</tr>"
        )

    # -- heatmap rows -------------------------------------------------------
    def heatmap_rows_html(data: dict) -> str:
        rows = []
        for c in all_cats:
            vals = [data[c].get(m, 0) for m in months]
            if not any(vals):
                continue
            cells = "".join(
                f'<td class="num heatmap-{min(v, 5)}">{v if v else ""}</td>' for v in vals
            )
            rows.append(f"<tr><td>{escape_html(c)}</td>{cells}</tr>")
        return "\n".join(rows)

    # -- chart data ---------------------------------------------------------
    chart_month_labels = json.dumps(months)
    chart_monthly_stories = json.dumps([monthly_stories[m] for m in months])
    chart_monthly_prs = json.dumps([monthly_prs[m] for m in months])
    chart_monthly_sp = json.dumps([monthly_sp[m] for m in months])
    chart_loc_additions = json.dumps([monthly_additions[m] for m in months])
    chart_loc_deletions = json.dumps([monthly_deletions[m] for m in months])

    # category charts (ADO)
    active_cats_ado = [c for c in all_cats if cat_stories[c]]
    chart_ado_cat_labels = json.dumps(active_cats_ado)
    chart_ado_cat_data = json.dumps([cat_stories[c] for c in active_cats_ado])
    chart_ado_cat_colors = json.dumps([cat_color_map[c] for c in active_cats_ado])

    # category charts (PRs)
    active_cats_pr = [c for c in all_cats if cat_prs[c]]
    chart_pr_cat_labels = json.dumps(active_cats_pr)
    chart_pr_cat_data = json.dumps([cat_prs[c] for c in active_cats_pr])
    chart_pr_cat_colors = json.dumps([cat_color_map[c] for c in active_cats_pr])

    # delivery/overhead donut
    chart_deloh_labels = json.dumps(["Delivery", "Overhead"])
    chart_deloh_data = json.dumps([delivery_sp, overhead_sp])

    # stacked bar datasets (stories per category per month)
    stacked_datasets = []
    for c in all_cats:
        vals = [heatmap_stories[c].get(m, 0) for m in months]
        if not any(vals):
            continue
        stacked_datasets.append({
            "label": c,
            "data": vals,
            "backgroundColor": cat_color_map[c],
        })
    chart_stacked_datasets = json.dumps(stacked_datasets)

    # -- optional sections --------------------------------------------------
    m365_html = ""
    if args.m365_html:
        m365_html = Path(args.m365_html).read_text(encoding="utf-8")

    observations_html = "<p>No observations provided.</p>"
    if args.observations_html:
        observations_html = Path(args.observations_html).read_text(encoding="utf-8")

    # -- hydrate template ---------------------------------------------------
    template = Path(args.template).read_text(encoding="utf-8")

    replacements = {
        "PERSON_NAME": args.person_name,
        "EMAIL": args.email,
        "PERIOD_LABEL": period_label(start, end),
        "GENERATED_DATE": date.today().strftime("%B %d, %Y"),
        "KPI_MERGED_PRS": str(kpi_merged_prs),
        "KPI_CLOSED_STORIES": str(kpi_closed_stories),
        "KPI_STORY_POINTS": f"{kpi_sp:g}",
        "KPI_REPOS": str(kpi_repos),
        "KPI_LINES_ADDED": f"{kpi_additions:,}",
        "KPI_LINES_DELETED": f"{kpi_deletions:,}",
        "KPI_FILES_CHANGED": f"{kpi_files:,}",
        "OBSERVATIONS_HTML": observations_html,
        "MONTHLY_TREND_TABLE_ROWS": "\n".join(trend_rows),
        "CATEGORY_TABLE_ROWS": "\n".join(category_rows),
        "DELIVERY_STORIES": str(delivery_stories),
        "DELIVERY_SP": f"{delivery_sp:g}",
        "DELIVERY_PCT": pct(delivery_sp, total_sp),
        "OVERHEAD_STORIES": str(overhead_stories),
        "OVERHEAD_SP": f"{overhead_sp:g}",
        "OVERHEAD_PCT": pct(overhead_sp, total_sp),
        "DELIVERY_DESCRIPTION": delivery_desc,
        "OVERHEAD_DESCRIPTION": overhead_desc,
        "CATEGORY_HEATMAP_STORIES_ROWS": heatmap_rows_html(heatmap_stories),
        "CATEGORY_HEATMAP_PRS_ROWS": heatmap_rows_html(heatmap_prs),
        "PR_TABLE_ROWS": "\n".join(pr_rows),
        "ADO_TABLE_ROWS": "\n".join(ado_rows),
        "M365_SECTION_HTML": m365_html,
        "CHART_MONTH_LABELS": chart_month_labels,
        "CHART_MONTHLY_STORIES": chart_monthly_stories,
        "CHART_MONTHLY_PRS": chart_monthly_prs,
        "CHART_MONTHLY_SP": chart_monthly_sp,
        "CHART_ADO_CAT_LABELS": chart_ado_cat_labels,
        "CHART_ADO_CAT_DATA": chart_ado_cat_data,
        "CHART_ADO_CAT_COLORS": chart_ado_cat_colors,
        "CHART_PR_CAT_LABELS": chart_pr_cat_labels,
        "CHART_PR_CAT_DATA": chart_pr_cat_data,
        "CHART_PR_CAT_COLORS": chart_pr_cat_colors,
        "CHART_DELOH_LABELS": chart_deloh_labels,
        "CHART_DELOH_DATA": chart_deloh_data,
        "CHART_STACKED_DATASETS": chart_stacked_datasets,
        "CHART_LOC_ADDITIONS": chart_loc_additions,
        "CHART_LOC_DELETIONS": chart_loc_deletions,
    }

    for key, value in replacements.items():
        template = template.replace(f"{{{{{key}}}}}", value)

    Path(args.output).write_text(template, encoding="utf-8")
    print(f"Report written to {args.output}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build performance report HTML from collected data.")
    parser.add_argument("--prs", required=True, help="Path to prs_authored.json")
    parser.add_argument("--reviews", required=True, help="Path to prs_reviewed.json")
    parser.add_argument("--ado", required=True, help="Path to ado_items.json")
    parser.add_argument("--categories", required=True, help="Path to categories.json")
    parser.add_argument("--template", required=True, help="Path to HTML template")
    parser.add_argument("--person-name", required=True, help="Full name of the person")
    parser.add_argument("--email", required=True, help="Email address")
    parser.add_argument("--period-start", required=True, help="Period start date (YYYY-MM-DD)")
    parser.add_argument("--period-end", required=True, help="Period end date (YYYY-MM-DD)")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--m365-html", default=None, help="Optional path to M365 section HTML")
    parser.add_argument("--observations-html", default=None, help="Optional path to observations HTML")
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
