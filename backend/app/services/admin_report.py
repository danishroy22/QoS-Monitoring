"""Professional PDF generator for Administrator QoS reports (Phase 18)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
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
            spaceAfter=16,
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
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ROW]),
            ]
        )
    )
    return table


def build_qos_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render a professional A4 QoS report from admin analytics + AI."""
    dashboard = payload["dashboard"]
    benchmarks = payload["benchmarks"]
    history = payload["history"]
    heatmap = payload["heatmap"]
    ai = payload["ai"]
    days = payload.get("days") or 90
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

    story.append(Paragraph("SmartQoS Administrator Portal", styles["title"]))
    story.append(Paragraph("Mauritius Broadband QoS Report", styles["subtitle"]))
    story.append(
        Paragraph(
            f"Window: last {days} days · Generated {generated}",
            styles["small"],
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Executive Summary", styles["h2"]))
    story.append(Paragraph(ai.market_summary, styles["body"]))
    story.append(
        Paragraph(
            (
                f"Dataset: {kpis.total_tests} tests across {kpis.isp_count} ISPs and "
                f"{kpis.region_count} regions. Mean QoS { _fmt(kpis.avg_qos_score, 0) }/100 · "
                f"Download {_fmt(kpis.avg_download_mbps)} Mbps · Upload {_fmt(kpis.avg_upload_mbps)} Mbps · "
                f"Ping {_fmt(kpis.avg_ping_ms, 0)} ms."
            ),
            styles["body"],
        )
    )

    story.append(Paragraph("2. ISP Rankings", styles["h2"]))
    rank_header = ["Rank", "ISP", "Tests", "QoS", "Down", "Up", "Ping", "Jitter", "Loss"]
    rank_rows = [rank_header]
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

    story.append(Paragraph("3. QoS Benchmark Comparison", styles["h2"]))
    profile = benchmarks.profile
    story.append(
        Paragraph(
            (
                f"Ideal Broadband Profile — Download ≥ {profile.download_mbps} Mbps, "
                f"Upload ≥ {profile.upload_mbps} Mbps, Ping ≤ {profile.ping_ms} ms, "
                f"Jitter ≤ {profile.jitter_ms} ms, Loss ≤ {profile.packet_loss_pct}%, "
                f"QoS ≥ {profile.overall_score}."
            ),
            styles["body"],
        )
    )
    bench_header = ["ISP", "Composite", "Down %", "Up %", "Ping %", "Jitter %", "Loss %", "Score %"]
    bench_rows = [bench_header]
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

    story.append(Paragraph("4. Historical Trend Snapshot", styles["h2"]))
    hist_header = ["Period", "Tests", "Down", "Up", "Ping", "QoS"]
    hist_rows = [hist_header]
    points = history.points[-12:]
    for point in points:
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

    story.append(Paragraph("5. Mauritius Regional Heatmap", styles["h2"]))
    heat_header = ["Region", "Tests", "QoS", "Download", "Ping", "Rating"]
    heat_rows = [heat_header]
    for cell in heatmap.cells:
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
    story.append(_table(heat_rows))

    story.append(Paragraph("6. AI ISP Analysis", styles["h2"]))
    if not ai.isps:
        story.append(Paragraph("No ISP analysis is available yet.", styles["body"]))
    for card in ai.isps:
        story.append(Paragraph(f"<b>{card.isp}</b> — {card.rating or 'n/a'} ({card.tests} tests)", styles["body"]))
        story.append(Paragraph(card.summary, styles["body"]))
        if card.strengths:
            story.append(Paragraph("Strengths: " + "; ".join(card.strengths), styles["body"]))
        if card.weaknesses:
            story.append(Paragraph("Gaps: " + "; ".join(card.weaknesses), styles["body"]))

    story.append(Paragraph("7. Recommendations", styles["h2"]))
    if ai.recommendations:
        for index, rec in enumerate(ai.recommendations, start=1):
            story.append(Paragraph(f"{index}. {rec}", styles["body"]))
    else:
        story.append(Paragraph("Continue scheduled monitoring and re-run this report monthly.", styles["body"]))

    story.append(Spacer(1, 16))
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
        canvas.drawString(16 * mm, 10 * mm, "SmartQoS · Administrator QoS Report")
        canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
