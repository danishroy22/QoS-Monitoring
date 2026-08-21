"""PDF generator for Administrator QoS reports."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0f172a")
CYAN = colors.HexColor("#0891b2")
SLATE = colors.HexColor("#334155")
ROW = colors.HexColor("#f1f5f9")
WHITE = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "AdminTitle",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=22,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "AdminSub",
            parent=base["Normal"],
            fontSize=11,
            textColor=SLATE,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "coverMeta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontSize=10,
            textColor=SLATE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "AdminH2",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=13,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "AdminBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "AdminSmall",
            parent=base["Normal"],
            fontSize=8,
            textColor=SLATE,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "AdminCell",
            parent=base["Normal"],
            fontSize=8,
            leading=11,
            textColor=NAVY,
        ),
    }


def _fmt(value: Any, digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}{suffix}"
    return f"{value}{suffix}"


def _table(data: list[list], col_widths=None) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("BACKGROUND", (0, 1), (-1, -1), ROW),
                ("TEXTCOLOR", (0, 1), (-1, -1), NAVY),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW]),
            ]
        )
    )
    return table


def _bar_chart(title: str, labels: list[str], values: list[float | None]) -> Drawing:
    drawing = Drawing(480, 180)
    drawing.add(String(10, 165, title, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 30
    chart.height = 120
    chart.width = 420
    clean = [float(v) if v is not None else 0.0 for v in values]
    chart.data = [clean]
    chart.categoryAxis.categoryNames = [str(l)[:12] for l in labels]
    chart.bars[0].fillColor = CYAN
    chart.valueAxis.valueMin = 0
    chart.categoryAxis.labels.boxAnchor = "ne"
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.fontSize = 7
    drawing.add(chart)
    return drawing


def build_qos_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render the Phase 12 multi-section Administrator QoS PDF."""
    dashboard = payload["dashboard"]
    benchmarks = payload["benchmarks"]
    history = payload["history"]
    heatmap = payload["heatmap"]
    ai = payload["ai"]
    packages = payload.get("packages")
    peak = payload.get("peak") or {}
    root = payload.get("root_cause")
    comparison = payload.get("comparison") or {}
    measurement_config = payload.get("measurement_config") or {}
    servers = payload.get("servers") or []
    metric_stats = payload.get("metric_stats") or {}
    filters = payload.get("filters") or {}
    period = payload.get("period") or {}
    limitations = payload.get("limitations") or []
    days = payload.get("days") or filters.get("days") or 90
    total_tests = payload.get("total_tests", dashboard.kpis.total_tests)
    kpis = dashboard.kpis
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="SmartQoS Administrator QoS Report",
        author="SmartQoS",
    )
    story: list = []
    generated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    # 1. Cover
    story.append(Spacer(1, 40))
    story.append(Paragraph("SmartQoS", styles["title"]))
    story.append(Paragraph("Administrator Broadband QoS Report", styles["subtitle"]))
    story.append(Paragraph("Mauritius · Dissertation measurement platform", styles["coverMeta"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph(f"Generated: {generated}", styles["coverMeta"]))
    story.append(
        Paragraph(
            f"Measurement period: {period.get('from') or 'n/a'} → {period.get('to') or 'n/a'}",
            styles["coverMeta"],
        )
    )
    story.append(Paragraph(f"Tests in scope: {total_tests} (window days={days})", styles["coverMeta"]))
    filt_bits = [
        f"{k}={v}"
        for k, v in filters.items()
        if v not in (None, "", []) and k not in {"days"}
    ]
    story.append(
        Paragraph(
            "Filters: " + (", ".join(filt_bits) if filt_bits else "none (all samples in window)"),
            styles["coverMeta"],
        )
    )
    story.append(Paragraph(f"Focus metric: {filters.get('metric') or 'qos'}", styles["coverMeta"]))
    story.append(Paragraph(f"Comparison mode: {filters.get('comparison') or 'isp_vs_isp'}", styles["coverMeta"]))
    story.append(PageBreak())

    # 2. Executive Summary
    story.append(Paragraph("2. Executive Summary", styles["h2"]))
    story.append(Paragraph(getattr(ai, "market_summary", None) or "No AI summary available.", styles["body"]))
    story.append(
        Paragraph(
            (
                f"Dataset: <b>{total_tests}</b> tests · <b>{kpis.isp_count}</b> ISPs · "
                f"<b>{kpis.region_count}</b> regions · mean QoS {_fmt(kpis.avg_qos_score, 0)}/100 · "
                f"download {_fmt(kpis.avg_download_mbps)} Mbps · upload {_fmt(kpis.avg_upload_mbps)} Mbps · "
                f"ping {_fmt(kpis.avg_ping_ms, 0)} ms · jitter {_fmt(kpis.avg_jitter_ms)} ms · "
                f"loss {_fmt(kpis.avg_packet_loss_pct, 2)}%."
            ),
            styles["body"],
        )
    )
    if root and getattr(root, "summary", None):
        story.append(Paragraph("<b>Pattern note:</b> " + root.summary, styles["body"]))

    # 3. Measurement Methodology
    story.append(Paragraph("3. Measurement Methodology", styles["h2"]))
    story.append(
        Paragraph(
            measurement_config.get("note")
            or "SmartQoS uses a documented, configurable measurement methodology.",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"Configuration version: {measurement_config.get('version', 'n/a')} · "
            f"Throughput mode: {measurement_config.get('throughput_mode', 'n/a')}.",
            styles["body"],
        )
    )
    full = measurement_config.get("full") or {}
    if full:
        meth_rows = [["Parameter", "Full-test value"]]
        for key, value in full.items():
            meth_rows.append([key, str(value)])
        story.append(_table(meth_rows, col_widths=[90 * mm, 70 * mm]))
    rationale = measurement_config.get("rationale") or {}
    if rationale:
        story.append(Paragraph("Selected rationales:", styles["body"]))
        for key, text in list(rationale.items())[:6]:
            story.append(Paragraph(f"<b>{key}</b>: {text}", styles["body"]))

    # 4. Test Configuration
    story.append(Paragraph("4. Test Configuration", styles["h2"]))
    story.append(
        Paragraph(
            f"Report window days={days}. Date from={filters.get('date_from') or '—'}, "
            f"to={filters.get('date_to') or '—'}.",
            styles["body"],
        )
    )
    story.append(Paragraph("Servers used in this filtered set:", styles["body"]))
    srv_rows = [["Server", "Tests", "Operator", "Location"]]
    for item in servers[:15]:
        srv_rows.append(
            [
                str(item.get("server") or "—"),
                str(item.get("tests") or 0),
                str(item.get("operator") or "—"),
                str(item.get("location") or "—"),
            ]
        )
    if len(srv_rows) == 1:
        srv_rows.append(["—", "0", "—", "—"])
    story.append(_table(srv_rows))
    story.append(PageBreak())

    # 5. ISP Performance
    story.append(Paragraph("5. ISP Performance", styles["h2"]))
    rank_rows = [["Rank", "ISP", "Tests", "QoS", "Down", "Up", "Ping", "Jitter", "Loss"]]
    for row in dashboard.leaderboard:
        rank_rows.append(
            [
                str(row.rank or ""),
                row.isp,
                str(row.tests),
                _fmt(row.avg_qos_score, 0),
                _fmt(row.avg_download_mbps),
                _fmt(row.avg_upload_mbps),
                _fmt(row.avg_ping_ms, 0),
                _fmt(row.avg_jitter_ms),
                _fmt(row.avg_packet_loss_pct, 2),
            ]
        )
    if len(rank_rows) == 1:
        rank_rows.append(["—", "No ISP samples", "0", "—", "—", "—", "—", "—", "—"])
    story.append(_table(rank_rows))
    if dashboard.leaderboard:
        story.append(
            _bar_chart(
                "Mean QoS by ISP",
                [r.isp for r in dashboard.leaderboard[:8]],
                [r.avg_qos_score for r in dashboard.leaderboard[:8]],
            )
        )

    # Comparison block
    story.append(Paragraph("Fair comparison snapshot", styles["body"]))
    story.append(Paragraph(str(comparison.get("ranking_note") or ""), styles["body"]))
    cmp_rows = [["ISP", "Tests", "QoS", "Fulfilment"]]
    for row in (comparison.get("isps") or [])[:10]:
        if isinstance(row, dict):
            cmp_rows.append(
                [
                    str(row.get("isp") or "—"),
                    str(row.get("tests") or 0),
                    _fmt(row.get("qos_score"), 0),
                    _fmt(row.get("fulfilment_pct"), 0, "%"),
                ]
            )
    if len(cmp_rows) > 1:
        story.append(_table(cmp_rows))

    # 6. Package Performance
    story.append(Paragraph("6. Package Performance", styles["h2"]))
    pkg_rows = [["ISP", "Package", "Adv↓", "Meas↓", "↓%", "Adv↑", "Meas↑", "↑%", "n"]]
    pkg_list = getattr(packages, "packages", None) or []
    for row in pkg_list[:20]:
        pkg_rows.append(
            [
                row.isp,
                row.package,
                _fmt(row.advertised_download_mbps, 0),
                _fmt(row.avg_download_mbps),
                _fmt(row.avg_download_fulfilment_pct, 0, "%"),
                _fmt(row.advertised_upload_mbps, 0),
                _fmt(row.avg_upload_mbps),
                _fmt(row.avg_upload_fulfilment_pct, 0, "%"),
                str(row.tests),
            ]
        )
    if len(pkg_rows) == 1:
        pkg_rows.append(["—", "No packaged tests", "—", "—", "—", "—", "—", "—", "0"])
    story.append(_table(pkg_rows))
    story.append(PageBreak())

    # 7. Regional Performance + 8. Heatmap
    story.append(Paragraph("7. Regional Performance", styles["h2"]))
    story.append(Paragraph("8. Mauritius Heatmap (tabular)", styles["h2"]))
    heat_rows = [["Region", "Tests", "QoS", "Download", "Ping", "Rating"]]
    for cell in heatmap.cells:
        if cell.tests <= 0:
            continue
        heat_rows.append(
            [
                cell.region,
                str(cell.tests),
                _fmt(cell.avg_qos_score, 0),
                _fmt(cell.avg_download_mbps),
                _fmt(cell.avg_ping_ms, 0),
                cell.rating or "—",
            ]
        )
    if len(heat_rows) == 1:
        heat_rows.append(["—", "0", "—", "—", "—", "—"])
    story.append(_table(heat_rows))
    active_cells = [c for c in heatmap.cells if c.tests > 0][:10]
    if active_cells:
        story.append(
            _bar_chart(
                "Regional mean QoS",
                [c.region for c in active_cells],
                [c.avg_qos_score for c in active_cells],
            )
        )

    # 9–13 metric analyses
    def _metric_section(number: str, title: str, key: str, unit: str) -> None:
        story.append(Paragraph(f"{number}. {title}", styles["h2"]))
        stats = metric_stats.get(key) or {}
        story.append(
            Paragraph(
                (
                    f"n={stats.get('count', 0)} · avg={_fmt(stats.get('avg'))}{unit} · "
                    f"min={_fmt(stats.get('min'))}{unit} · max={_fmt(stats.get('max'))}{unit}."
                ),
                styles["body"],
            )
        )
        # Per-ISP breakdown for this metric
        attr = {
            "download": "avg_download_mbps",
            "upload": "avg_upload_mbps",
            "latency": "avg_ping_ms",
            "jitter": "avg_jitter_ms",
            "packet_loss": "avg_packet_loss_pct",
        }[key]
        rows = [["ISP", "Tests", title]]
        values = []
        labels = []
        for isp_row in dashboard.leaderboard[:12]:
            val = getattr(isp_row, attr)
            rows.append([isp_row.isp, str(isp_row.tests), _fmt(val)])
            labels.append(isp_row.isp)
            values.append(val)
        story.append(_table(rows))
        if labels:
            story.append(_bar_chart(f"{title} by ISP", labels, values))

    _metric_section("9", "Download Analysis", "download", " Mbps")
    _metric_section("10", "Upload Analysis", "upload", " Mbps")
    story.append(PageBreak())
    _metric_section("11", "Latency Analysis", "latency", " ms")
    _metric_section("12", "Jitter Analysis", "jitter", " ms")
    _metric_section("13", "Packet Loss", "packet_loss", "%")

    # 14. QoS Benchmark
    story.append(Paragraph("14. QoS Benchmark", styles["h2"]))
    profile = benchmarks.profile
    story.append(
        Paragraph(
            (
                f"Active profile <b>{profile.name}</b> — Download ≥ {profile.download_mbps} Mbps, "
                f"Upload ≥ {profile.upload_mbps} Mbps, Ping ≤ {profile.ping_ms} ms, "
                f"Jitter ≤ {profile.jitter_ms} ms, Loss ≤ {profile.packet_loss_pct}%, "
                f"QoS ≥ {profile.overall_score}. Thresholds come from the active "
                "benchmark profile."
            ),
            styles["body"],
        )
    )
    if getattr(benchmarks, "disclaimer", None):
        story.append(Paragraph(benchmarks.disclaimer, styles["body"]))
    bench_rows = [["ISP", "Composite", "Down %", "Up %", "Ping %", "Jitter %", "Loss %", "Score %"]]
    for row in benchmarks.rankings:
        by_name = {m.metric: m for m in row.metrics}

        def _c(name: str) -> str:
            metric = by_name.get(name)
            if not metric or metric.compliance_pct is None:
                return "—"
            return f"{metric.compliance_pct:.0f}%"

        bench_rows.append(
            [
                row.isp,
                _fmt(row.composite_score, 0, "%"),
                _c("Download"),
                _c("Upload"),
                _c("Ping"),
                _c("Jitter"),
                _c("Packet Loss"),
                _c("QoS Score"),
            ]
        )
    if len(bench_rows) == 1:
        bench_rows.append(["—", "—", "—", "—", "—", "—", "—", "—"])
    story.append(_table(bench_rows))
    story.append(PageBreak())

    # 15. Peak-Hour Analysis
    story.append(Paragraph("15. Peak-Hour Analysis", styles["h2"]))
    window = peak.get("peak_window") if isinstance(peak, dict) else None
    story.append(
        Paragraph(
            str(peak.get("disclaimer") if isinstance(peak, dict) else "")
            or "Peak-hour analysis compares busy hours against off-peak baselines.",
            styles["body"],
        )
    )
    if window:
        story.append(
            Paragraph(
                f"Detected window: <b>{window.get('label')}</b> · peak n={window.get('tests')} · "
                f"off-peak n={window.get('baseline_tests')} · "
                f"{peak.get('interpretation') if isinstance(peak, dict) else ''}",
                styles["body"],
            )
        )
        peak_rows = [["Metric", "Peak", "Off-peak", "Δ%"]]
        for m in window.get("metrics") or []:
            peak_rows.append(
                [
                    str(m.get("label") or m.get("key")),
                    _fmt(m.get("peak_avg")),
                    _fmt(m.get("baseline_avg")),
                    _fmt(m.get("delta_pct"), 1, "%"),
                ]
            )
        story.append(_table(peak_rows))
    else:
        story.append(Paragraph("No peak window identified for the selected filters.", styles["body"]))
    if root and getattr(root, "summary", None):
        story.append(Paragraph("<b>Root-cause style note:</b> " + root.summary, styles["body"]))

    # Historical trend
    story.append(Paragraph("Historical daily snapshot", styles["body"]))
    hist_rows = [["Period", "Tests", "Down", "Up", "Ping", "QoS"]]
    for point in history.points[-14:]:
        hist_rows.append(
            [
                point.period,
                str(point.tests),
                _fmt(point.avg_download_mbps),
                _fmt(point.avg_upload_mbps),
                _fmt(point.avg_ping_ms, 0),
                _fmt(point.avg_qos_score, 0),
            ]
        )
    if len(hist_rows) == 1:
        hist_rows.append(["—", "0", "—", "—", "—", "—"])
    story.append(_table(hist_rows))

    # 16. AI Analysis
    story.append(Paragraph("16. AI Analysis", styles["h2"]))
    story.append(
        Paragraph(
            f"Provider: {getattr(ai, 'model_provider', 'n/a')}. "
            "Narratives are based on stored aggregates.",
            styles["body"],
        )
    )
    if not getattr(ai, "isps", None):
        story.append(Paragraph("No ISP analysis cards available.", styles["body"]))
    for card in getattr(ai, "isps", []) or []:
        story.append(
            Paragraph(
                f"<b>{card.isp}</b> — {card.rating or 'n/a'} ({card.tests} tests)",
                styles["body"],
            )
        )
        story.append(Paragraph(card.summary, styles["body"]))
        if card.strengths:
            story.append(Paragraph("Strengths: " + "; ".join(card.strengths), styles["body"]))
        if card.weaknesses:
            story.append(Paragraph("Gaps: " + "; ".join(card.weaknesses), styles["body"]))

    # 17. Recommendations
    story.append(Paragraph("17. Recommendations", styles["h2"]))
    recs = list(getattr(ai, "recommendations", None) or [])
    if not recs:
        recs = [
            "Continue scheduled monitoring and expand regional sample coverage.",
            "Re-run this report monthly with the same filters for trend comparability.",
        ]
    for index, rec in enumerate(recs, start=1):
        story.append(Paragraph(f"{index}. {rec}", styles["body"]))

    # 18. Limitations
    story.append(Paragraph("18. Limitations", styles["h2"]))
    for item in limitations:
        story.append(Paragraph(f"• {item}", styles["body"]))

    # 19. Conclusion
    story.append(Paragraph("19. Conclusion", styles["h2"]))
    story.append(
        Paragraph(
            (
                f"This report summarises {total_tests} SmartQoS measurements for the stated period "
                f"and filters. Mean QoS was {_fmt(kpis.avg_qos_score, 0)}/100 with "
                f"{kpis.isp_count} ISP(s) and {kpis.region_count} region(s) represented. "
                "Findings should be interpreted with sample sizes and the limitations above. "
                "Peak-hour and root-cause style notes describe patterns consistent with possible "
                "congestion or utilisation effects but do not independently confirm network cause."
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "Confidential — generated from SmartQoS speed_tests. Consumer measurement APIs were not modified.",
            styles["small"],
        )
    )

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(CYAN)
        canvas.rect(0, A4[1] - 8, A4[0], 8, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(16 * mm, 10 * mm, "SmartQoS · Administrator QoS Report · Phase 12")
        canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
