"""PDF report generator for PatternProof (Delivery Order Complaints & Issues).

Builds structured, objective evidence reports using template text and computed figures.
Includes the mandatory per-page disclaimer, full incident/order ID traceability,
and an evidence integrity index with SHA-256 hashes.
"""

import os
import datetime
from typing import List, Dict, Any, Optional
from fpdf import FPDF
import patterns

MANDATORY_DISCLAIMER = (
    "PatternProof organises user-provided evidence. "
    "It does not verify authenticity, assign blame, or provide legal advice."
)


def sanitize_pdf_text(text: Optional[str]) -> str:
    """Sanitize text to guarantee PDF compatibility without crashing on unsupported unicode or emojis."""
    if not text:
        return ""
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "--",
        "\u2013": "-",
        "\u2026": "...",
        "\u2022": "*",
        "\u00a0": " ",
        "\u20b9": "INR ",  # Rupee symbol
        "\u2122": "(TM)",
        "\u00ae": "(R)",
        "\u00a9": "(C)",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)

    sanitized = text.encode("latin-1", errors="replace").decode("latin-1")
    return sanitized


class OrderComplaintReportPDF(FPDF):
    """Custom FPDF document with standard headers and mandatory per-page disclaimers."""

    def __init__(self, case_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.case_name = case_name
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(130, 140, 155)
            self.cell(
                0,
                6,
                sanitize_pdf_text(f"PatternProof Order Evidence Report • Case: {self.case_name}"),
                border=0,
                align="L",
            )
            self.ln(7)

    def footer(self):
        self.set_y(-18)
        self.set_font("helvetica", "I", 7.2)
        self.set_text_color(115, 125, 135)
        self.cell(
            0,
            4,
            MANDATORY_DISCLAIMER,
            border=0,
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_font("helvetica", "", 7.5)
        self.set_text_color(140, 145, 155)
        self.cell(0, 4, f"Page {self.page_no()}", border=0, align="C")


def generate_pdf_report(
    case_name: str,
    incidents: List[Dict[str, Any]],
    output_path: Optional[str] = None,
) -> bytes:
    """Generate a structured complaint evidence report PDF and return the PDF bytes."""
    metrics = patterns.analyze_patterns(incidents)
    pdf = OrderComplaintReportPDF(case_name=case_name, orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    # Brand Title Header
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(255, 92, 31)  # #FF5C1F Brand Orange
    pdf.cell(0, 10, "PatternProof Order Complaint Evidence Report", ln=True)

    # Metadata subtitle
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(40, 45, 55)
    pdf.cell(0, 6, sanitize_pdf_text(f"Case / Subject: {case_name}"), ln=True)

    gen_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(100, 110, 120)
    pdf.cell(0, 5, f"Generated: {gen_time} | Scope: User-provided order & chat screenshots", ln=True)
    pdf.ln(3)

    # Mandatory Disclaimer Box
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(210, 215, 225)
    pdf.set_text_color(70, 75, 85)
    pdf.set_font("helvetica", "B", 8.5)
    pdf.rect(15, pdf.get_y(), 180, 14, style="FD")
    pdf.set_xy(18, pdf.get_y() + 2)
    pdf.multi_cell(174, 4.5, sanitize_pdf_text(f"NOTICE: {MANDATORY_DISCLAIMER}"))
    pdf.set_y(pdf.get_y() + 5)

    # 1. Objective Case Summary (Template text based on computed metrics)
    total_st = metrics["total"]
    weekly_st = metrics["weekly"]
    platforms_st = metrics["platforms"]
    delays_st = metrics["delays"]
    refunds_st = metrics["refunds"]
    stores_st = metrics["stores"]

    plat_summary = ", ".join(f"{p} ({d['count']})" for p, d in platforms_st.items()) or "None"
    summary_text = (
        f"This document compiles {total_st['count']} logged delivery order issue(s) spanning "
        f"{total_st['date_range_str']} across {len(platforms_st)} platform(s): {plat_summary}. "
        f"Total amount affected across documented orders is INR {total_st['total_amount_inr']:.2f}. "
        f"Chronological evaluation reflects an observable {weekly_st['trend']} weekly problem frequency. "
        f"Documentation records {delays_st['delay_count']} delayed order(s) with an average delay of "
        f"{delays_st['average_delay_minutes']} minutes (maximum {delays_st['max_delay_minutes']} minutes). "
        f"Refund tracking shows {refunds_st['pending_count']} pending inquiry(ies), "
        f"{refunds_st['denied_count']} denied refund(s), and {refunds_st['partial_count']} partial resolution(s). "
        f"Every statistic maintains complete traceability to the individual order records indexed below."
    )

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(25, 30, 40)
    pdf.cell(0, 7, "1. Objective Case Summary", ln=True)

    pdf.set_font("helvetica", "", 9)
    pdf.set_text_color(55, 60, 70)
    pdf.multi_cell(180, 5, sanitize_pdf_text(summary_text))
    pdf.ln(4)

    # 2. Observable Patterns & Traceable Metrics Table
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(25, 30, 40)
    pdf.cell(0, 7, "2. Observable Patterns & Traceable Metrics", ln=True)

    metrics_rows = [
        (
            "Total Issues Documented",
            f"{total_st['count']} order issue(s)",
            f"IDs: {', '.join(str(i) for i in total_st['incident_ids']) or 'None'}",
        ),
        (
            "Date Range & Time Span",
            f"{total_st['date_range_str']} ({total_st['span_days']} days)",
            f"Dated IDs: {', '.join(str(i) for i in total_st['dated_incident_ids']) or 'None'}",
        ),
        (
            "Total Amount Affected",
            f"INR {total_st['total_amount_inr']:.2f}",
            f"Documented IDs: {', '.join(str(i) for i in total_st['amount_incident_ids']) or 'None'}",
        ),
        (
            "Weekly Frequency Trend",
            f"{weekly_st['trend'].upper()} (1st half: {weekly_st['first_half_avg']}/wk | 2nd half: {weekly_st['second_half_avg']}/wk)",
            f"1st half IDs: {', '.join(str(i) for i in weekly_st['first_half_ids']) or 'None'} | 2nd half IDs: {', '.join(str(i) for i in weekly_st['second_half_ids']) or 'None'}",
        ),
        (
            "Delivery Delays",
            f"Avg delay: {delays_st['average_delay_minutes']} min | Max delay: {delays_st['max_delay_minutes']} min",
            f"Delay IDs: {', '.join(str(i) for i in delays_st['incident_ids']) or 'None'}",
        ),
        (
            "Refund Status Breakdown",
            f"Pending: {refunds_st['pending_count']} | Denied: {refunds_st['denied_count']} | Partial: {refunds_st['partial_count']}",
            f"Pending IDs: {', '.join(str(i) for i in refunds_st['pending_ids']) or 'None'}",
        ),
        (
            "Longest Pending Refund",
            f"{refunds_st['longest_pending_days']} day(s) pending since order date",
            f"IDs: {', '.join(str(i) for i in refunds_st['longest_pending_ids']) or 'None'}",
        ),
    ]

    # Repeat stores
    for store_name, s_data in stores_st["repeat_stores"].items():
        metrics_rows.append((
            f"Repeat Store: {store_name}",
            f"{s_data['count']} reported issue(s)",
            f"IDs: {', '.join(str(i) for i in s_data['incident_ids'])}",
        ))

    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(235, 239, 245)
    pdf.set_draw_color(200, 205, 215)
    pdf.cell(50, 6, "Metric", border=1, fill=True)
    pdf.cell(65, 6, "Observable Value", border=1, fill=True)
    pdf.cell(65, 6, "Traceable Order IDs", border=1, fill=True, ln=True)

    pdf.set_font("helvetica", "", 7.5)
    for title, val, ids_str in metrics_rows:
        pdf.cell(50, 6, sanitize_pdf_text(title), border=1)
        pdf.cell(65, 6, sanitize_pdf_text(val), border=1)
        pdf.cell(65, 6, sanitize_pdf_text(ids_str), border=1, ln=True)

    pdf.ln(5)

    # 3. Chronological Order Timeline Table
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(25, 30, 40)
    pdf.cell(0, 7, "3. Chronological Order Issue Timeline", ln=True)

    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_fill_color(235, 239, 245)
    pdf.cell(10, 6, "ID", border=1, fill=True, align="C")
    pdf.cell(18, 6, "Date", border=1, fill=True)
    pdf.cell(20, 6, "Platform", border=1, fill=True)
    pdf.cell(32, 6, "Store / Restaurant", border=1, fill=True)
    pdf.cell(26, 6, "Issue Type", border=1, fill=True)
    pdf.cell(18, 6, "Amount", border=1, fill=True)
    pdf.cell(20, 6, "Refund", border=1, fill=True)
    pdf.cell(36, 6, "Link Group", border=1, fill=True, ln=True)

    pdf.set_font("helvetica", "", 7)
    for inc in incidents:
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_font("helvetica", "B", 7.5)
            pdf.set_fill_color(235, 239, 245)
            pdf.cell(10, 6, "ID", border=1, fill=True, align="C")
            pdf.cell(18, 6, "Date", border=1, fill=True)
            pdf.cell(20, 6, "Platform", border=1, fill=True)
            pdf.cell(32, 6, "Store / Restaurant", border=1, fill=True)
            pdf.cell(26, 6, "Issue Type", border=1, fill=True)
            pdf.cell(18, 6, "Amount", border=1, fill=True)
            pdf.cell(20, 6, "Refund", border=1, fill=True)
            pdf.cell(36, 6, "Link Group", border=1, fill=True, ln=True)
            pdf.set_font("helvetica", "", 7)

        d_str = inc.get("order_date") or "Needs Date"
        plat = (inc.get("platform") or "Other")[:10]
        store = (inc.get("restaurant_or_store") or "Store")[:18]
        issue = (inc.get("issue_type") or "Other")[:15]
        amt_str = f"INR {inc.get('amount_inr'):.0f}" if inc.get("amount_inr") is not None else "-"
        refund = (inc.get("refund_status") or "-")[:10]
        link_grp = (inc.get("link_group") or "-")[:20]

        pdf.cell(10, 5.5, str(inc.get("id")), border=1, align="C")
        pdf.cell(18, 5.5, sanitize_pdf_text(d_str), border=1)
        pdf.cell(20, 5.5, sanitize_pdf_text(plat), border=1)
        pdf.cell(32, 5.5, sanitize_pdf_text(store), border=1)
        pdf.cell(26, 5.5, sanitize_pdf_text(issue), border=1)
        pdf.cell(18, 5.5, sanitize_pdf_text(amt_str), border=1)
        pdf.cell(20, 5.5, sanitize_pdf_text(refund), border=1)
        pdf.cell(36, 5.5, sanitize_pdf_text(link_grp), border=1, ln=True)

    pdf.ln(5)

    # 4. Evidence File Index (Cryptographic Hash Integrity)
    if pdf.get_y() > 230:
        pdf.add_page()

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(25, 30, 40)
    pdf.cell(0, 7, "4. Evidence File & Integrity Index", ln=True)

    pdf.set_font("helvetica", "B", 7.5)
    pdf.set_fill_color(235, 239, 245)
    pdf.cell(12, 6, "ID", border=1, fill=True, align="C")
    pdf.cell(42, 6, "Evidence Screenshot File", border=1, fill=True)
    pdf.cell(126, 6, "File SHA-256 Checksum", border=1, fill=True, ln=True)

    pdf.set_font("helvetica", "", 6.8)
    for inc in incidents:
        if pdf.get_y() > 265:
            pdf.add_page()
            pdf.set_font("helvetica", "B", 7.5)
            pdf.set_fill_color(235, 239, 245)
            pdf.cell(12, 6, "ID", border=1, fill=True, align="C")
            pdf.cell(42, 6, "Evidence Screenshot File", border=1, fill=True)
            pdf.cell(126, 6, "File SHA-256 Checksum", border=1, fill=True, ln=True)
            pdf.set_font("helvetica", "", 6.8)

        img_p = inc.get("image_path") or "No file uploaded"
        fname = os.path.basename(img_p)[:25]
        fhash = inc.get("file_hash") or "N/A"

        pdf.cell(12, 5.5, str(inc.get("id")), border=1, align="C")
        pdf.cell(42, 5.5, sanitize_pdf_text(fname), border=1)
        pdf.cell(126, 5.5, sanitize_pdf_text(fhash), border=1, ln=True)

    pdf.ln(6)

    # Closing Note
    if pdf.get_y() > 240:
        pdf.add_page()

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(210, 218, 230)
    curr_y = pdf.get_y()
    pdf.rect(15, curr_y, 180, 16, style="FD")
    pdf.set_xy(18, curr_y + 3)
    pdf.set_font("helvetica", "I", 8.2)
    pdf.set_text_color(60, 65, 75)
    pdf.multi_cell(
        174,
        4.5,
        "Closing Note: You may wish to share this with the platform's support team or the National Consumer Helpline (1915).",
    )

    pdf_bytes = bytes(pdf.output())

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes
