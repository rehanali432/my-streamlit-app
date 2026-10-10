"""Evidence Pack PDF generation for PatternProof: Delivery Evidence Coach.

Generates a structured, audit-ready PDF evidence pack using fpdf2.
Includes:
- Mandatory neutral disclaimer on EVERY page footer
- Safe Unicode text sanitization (rupee sign -> INR, Latin-1 fallback)
- Order summary & receipt thumbnail with SHA-256
- Detailed task checklist with thumbnails, capture timestamps, and check results
- Machine-verified vs user-confirmed status indicators
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF
from PIL import Image

FOOTER_DISCLAIMER = (
    "PatternProof organises user-provided evidence. "
    "It does not verify authenticity, decide claims, or provide legal advice."
)


def sanitize_text(text: Any) -> str:
    """Sanitize strings for Latin-1 compatibility in standard PDF fonts."""
    if text is None:
        return ""
    s = str(text)
    # Common replacements
    s = s.replace("₹", "INR ")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("—", " - ").replace("–", " - ")
    s = s.replace("•", "* ")
    # Encode to latin-1 replacing unencodable characters
    clean_bytes = s.encode("latin-1", "replace")
    return clean_bytes.decode("latin-1")


class EvidencePackPDF(FPDF):
    """Custom FPDF subclass enforcing consistent branding and mandatory disclaimers."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=22)

    def header(self):
        # Top banner with orange accent
        self.set_fill_color(255, 92, 31)  # #FF5C1F
        self.rect(0, 0, 210, 4, "F")

    def footer(self):
        self.set_y(-18)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110, 115, 125)
        # Required disclaimer on every page
        self.multi_cell(190, 3.5, FOOTER_DISCLAIMER, align="C")
        self.set_font("Helvetica", "", 7)
        self.cell(190, 4, f"Page {self.page_no()}", align="R")


def generate_evidence_pdf(
    order: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    output_path: str = "uploads/evidence_pack.pdf"
) -> str:
    """Generate the full evidence pack PDF and return the saved file path."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf = EvidencePackPDF()
    pdf.add_page()

    # 1. Title & Header
    pdf.set_y(10)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(25, 30, 45)
    pdf.cell(0, 8, "PatternProof: Delivery Evidence Pack", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 115, 125)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 5, sanitize_text(f"Generated on {now_str} | Structured Evidence Record"), ln=True)
    pdf.ln(3)

    # 2. Order Summary Box
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(220, 225, 235)
    pdf.rect(10, pdf.get_y(), 190, 46, "FD")

    start_box_y = pdf.get_y() + 3
    pdf.set_xy(14, start_box_y)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(255, 92, 31)
    pdf.cell(90, 5, "ORDER INFORMATION")

    pdf.set_xy(105, start_box_y)
    pdf.cell(90, 5, "CLAIM DETAILS")

    # Left Column: Store / Platform / Order ID
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 45, 55)

    y_cur = start_box_y + 6
    pdf.set_xy(14, y_cur)
    pdf.cell(32, 5, "Store:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(58, 5, sanitize_text(order.get("store") or "Unspecified"))

    pdf.set_font("Helvetica", "", 9)
    y_cur += 5.5
    pdf.set_xy(14, y_cur)
    pdf.cell(32, 5, "Platform:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(58, 5, sanitize_text(order.get("platform") or "Unspecified"))

    pdf.set_font("Helvetica", "", 9)
    y_cur += 5.5
    pdf.set_xy(14, y_cur)
    pdf.cell(32, 5, "Order ID:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(58, 5, sanitize_text(order.get("order_id") or "Unspecified"))

    pdf.set_font("Helvetica", "", 9)
    y_cur += 5.5
    pdf.set_xy(14, y_cur)
    pdf.cell(32, 5, "Order Date:")
    pdf.cell(58, 5, sanitize_text(order.get("order_date") or "Unspecified"))

    pdf.set_xy(14, y_cur + 5.5)
    pdf.cell(32, 5, "Total Billed:")
    pdf.set_font("Helvetica", "B", 9)
    total_val = order.get("total_inr")
    total_str = f"INR {total_val:.2f}" if isinstance(total_val, (int, float)) else "Unspecified"
    pdf.cell(58, 5, sanitize_text(total_str))

    # Right Column: Claim type & Items Count
    y_cur_r = start_box_y + 6
    pdf.set_xy(105, y_cur_r)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(30, 5, "Claim Type:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(60, 5, sanitize_text(order.get("claim_type") or "Delivery Issue"))

    items_list = order.get("items", [])
    y_cur_r += 5.5
    pdf.set_xy(105, y_cur_r)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(30, 5, "Billed Items:")
    pdf.cell(60, 5, sanitize_text(f"{len(items_list)} line items identified"))

    # Print first 2 items concisely
    for idx, itm in enumerate(items_list[:2]):
        y_cur_r += 5
        pdf.set_xy(105, y_cur_r)
        name = itm.get("name", "Item")
        qty = itm.get("quantity", 1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(90, 95, 105)
        pdf.cell(85, 4, sanitize_text(f"- {name} (Qty: {qty})"))

    pdf.set_y(start_box_y + 42)
    pdf.ln(3)

    # 3. Readiness Summary Card
    total_tasks = len(tasks)
    passed_count = sum(1 for t in tasks if t.get("status") == "Passed")
    confirmed_count = sum(1 for t in tasks if t.get("status") == "User-confirmed")
    partial_count = sum(1 for t in tasks if t.get("status") == "Partial")
    retake_count = sum(1 for t in tasks if t.get("status") == "Retake")
    open_count = sum(1 for t in tasks if t.get("status") == "Open")

    completed_count = passed_count + confirmed_count
    readiness_pct = int(round((completed_count / total_tasks * 100))) if total_tasks > 0 else 0

    pdf.set_fill_color(238, 242, 246)
    pdf.set_draw_color(200, 210, 225)
    pdf.rect(10, pdf.get_y(), 190, 16, "FD")

    pdf.set_xy(14, pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(25, 30, 45)
    pdf.cell(70, 5, sanitize_text(f"EVIDENCE READINESS: {readiness_pct}% COMPLETE"))

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(60, 65, 75)
    stats_summary = (
        f"Passed: {passed_count} | User-confirmed: {confirmed_count} | "
        f"Partial: {partial_count} | Retake suggested: {retake_count} | Open: {open_count}"
    )
    pdf.set_xy(14, pdf.get_y() + 5.5)
    pdf.cell(180, 4, sanitize_text(stats_summary))

    pdf.set_y(pdf.get_y() + 8)
    pdf.ln(4)

    # 4. Primary Order Assets (Receipt & Product Photo)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(25, 30, 45)
    pdf.cell(0, 6, "1. Primary Order Documentation", ln=True)
    pdf.ln(1)

    assets_y = pdf.get_y()
    box_w = 92
    box_h = 58

    # Receipt Box (Left)
    pdf.set_draw_color(215, 220, 230)
    pdf.set_fill_color(250, 251, 253)
    pdf.rect(10, assets_y, box_w, box_h, "FD")

    pdf.set_xy(14, assets_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(35, 40, 50)
    pdf.cell(85, 4, "Order Receipt Screenshot", ln=True)

    r_path = order.get("receipt_path")
    if r_path and os.path.isfile(r_path):
        try:
            pdf.image(r_path, x=14, y=assets_y + 8, w=35, h=45)
        except Exception:
            pdf.rect(14, assets_y + 8, 35, 45)
            pdf.text(16, assets_y + 25, "Image Preview")
    else:
        pdf.rect(14, assets_y + 8, 35, 45)
        pdf.set_font("Helvetica", "I", 7)
        pdf.text(16, assets_y + 25, "No file uploaded")

    pdf.set_xy(52, assets_y + 10)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(70, 75, 85)
    pdf.cell(45, 3.5, "Original File SHA-256:", ln=True)
    pdf.set_xy(52, assets_y + 14)
    pdf.set_font("Courier", "", 6)
    r_hash = order.get("receipt_hash") or "N/A"
    pdf.multi_cell(48, 2.8, r_hash[:32] + "\n" + r_hash[32:])

    # Product Initial Photo Box (Right)
    pdf.rect(108, assets_y, box_w, box_h, "FD")
    pdf.set_xy(112, assets_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(35, 40, 50)
    pdf.cell(85, 4, "Initial Product Photo", ln=True)

    p_path = order.get("product_photo_path")
    if p_path and os.path.isfile(p_path):
        try:
            pdf.image(p_path, x=112, y=assets_y + 8, w=35, h=45)
        except Exception:
            pdf.rect(112, assets_y + 8, 35, 45)
            pdf.text(114, assets_y + 25, "Image Preview")
    else:
        pdf.rect(112, assets_y + 8, 35, 45)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(120, 125, 135)
        pdf.text(114, assets_y + 25, "Not provided")

    pdf.set_xy(150, assets_y + 10)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(70, 75, 85)
    pdf.cell(45, 3.5, "Original File SHA-256:", ln=True)
    pdf.set_xy(150, assets_y + 14)
    pdf.set_font("Courier", "", 6)
    p_hash = order.get("product_hash") or "N/A"
    pdf.multi_cell(48, 2.8, p_hash[:32] + "\n" + p_hash[32:])

    pdf.set_y(assets_y + box_h + 4)

    # 5. Checklist Tasks (Each with photo thumbnail, SHA-256, verification list)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(25, 30, 45)
    pdf.cell(0, 6, "2. Tailored Photographic Evidence Tasks", ln=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(90, 95, 105)
    pdf.cell(0, 4, "Every photo is evaluated for resolution, sharpness, angle, and specific visible requirements.", ln=True)
    pdf.ln(3)

    for idx, t in enumerate(tasks, start=1):
        # Page break check: task card is roughly 42 mm
        if pdf.get_y() > 225:
            pdf.add_page()

        task_y = pdf.get_y()
        card_h = 44

        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(215, 220, 230)
        pdf.rect(10, task_y, 190, card_h, "FD")

        # Status badge color
        status_val = t.get("status", "Open")
        if status_val == "Passed":
            badge_r, badge_g, badge_b = 20, 140, 60
        elif status_val == "User-confirmed":
            badge_r, badge_g, badge_b = 30, 100, 180
        elif status_val == "Partial":
            badge_r, badge_g, badge_b = 210, 140, 15
        elif status_val == "Retake":
            badge_r, badge_g, badge_b = 210, 50, 40
        else:
            badge_r, badge_g, badge_b = 130, 135, 145

        # Card Title Line
        pdf.set_xy(14, task_y + 3)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(25, 30, 45)
        task_code = t.get("task_code", f"T{idx}")
        title = t.get("title", "")
        pdf.cell(120, 4, sanitize_text(f"{task_code}: {title}"))

        # Status Pill on Right
        pdf.set_xy(145, task_y + 2.5)
        pdf.set_fill_color(badge_r, badge_g, badge_b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7.5)
        status_label = f" {status_val.upper()} "
        if status_val == "User-confirmed":
            status_label = " USER-CONFIRMED "
        pdf.cell(50, 4.5, status_label, align="C", fill=True)

        # Photo thumbnail on left of card
        t_photo = t.get("photo_path")
        if t_photo and os.path.isfile(t_photo):
            try:
                pdf.image(t_photo, x=14, y=task_y + 8, w=28, h=32)
            except Exception:
                pdf.rect(14, task_y + 8, 28, 32)
                pdf.text(16, task_y + 20, "Preview")
        else:
            pdf.set_draw_color(225, 230, 238)
            pdf.rect(14, task_y + 8, 28, 32)
            pdf.set_font("Helvetica", "I", 6.5)
            pdf.set_text_color(140, 145, 155)
            pdf.text(16, task_y + 22, "No photo yet")

        # Center: Shot type, instruction, capture timestamp
        pdf.set_xy(45, task_y + 8)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(70, 75, 85)
        pdf.cell(20, 3.5, "Shot Type:")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.cell(50, 3.5, sanitize_text(t.get("shot_type", "")))

        pdf.set_xy(45, task_y + 12)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(20, 3.5, "Angle:")
        pdf.set_font("Helvetica", "", 7.5)
        pdf.cell(50, 3.5, sanitize_text(t.get("angle", "")))

        # Capture timestamp or source
        cap_str = t.get("captured_at") or "Not recorded"
        pdf.set_xy(45, task_y + 16)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(20, 3.5, "Captured:")
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(50, 3.5, sanitize_text(cap_str))

        # Photo SHA-256 Hash
        p_hash = t.get("photo_hash") or "N/A"
        pdf.set_xy(45, task_y + 20)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.cell(20, 3, "SHA-256:")
        pdf.set_font("Courier", "", 5.5)
        pdf.cell(50, 3, p_hash[:26] + "..." if len(p_hash) > 26 else p_hash)

        # Verification Observations (Right block inside card)
        pdf.set_xy(118, task_y + 8)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(50, 55, 65)
        pdf.cell(75, 3.5, "Verification Evaluation:", ln=True)

        verif_data = t.get("verification")
        checks_list = verif_data.get("checks", []) if isinstance(verif_data, dict) else []

        verif_y = task_y + 12
        if checks_list:
            for chk in checks_list[:3]:  # Top 3 key checks
                pdf.set_xy(118, verif_y)
                chk_st = chk.get("status", "pass")
                chk_name = chk.get("name", "Check")
                chk_detail = chk.get("detail", "")

                if chk_st == "pass":
                    mark = "[PASS]"
                    pdf.set_text_color(20, 130, 50)
                elif chk_st == "warn":
                    mark = "[WARN]"
                    pdf.set_text_color(190, 120, 10)
                else:
                    mark = "[FAIL]"
                    pdf.set_text_color(200, 40, 30)

                pdf.set_font("Helvetica", "B", 6.5)
                pdf.cell(14, 3, mark)
                pdf.set_font("Helvetica", "", 6.5)
                pdf.set_text_color(60, 65, 75)
                summary_line = f"{chk_name}: {chk_detail}"
                pdf.cell(63, 3, sanitize_text(summary_line[:42] + ("..." if len(summary_line) > 42 else "")))
                verif_y += 3.5
        elif status_val == "User-confirmed":
            pdf.set_xy(118, verif_y)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(30, 90, 170)
            pdf.cell(75, 3.5, "Marked as user-confirmed (not machine-verified).")
        else:
            pdf.set_xy(118, verif_y)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(130, 135, 145)
            pdf.cell(75, 3.5, "Awaiting photo upload and evaluation.")

        # Bottom note on card
        pdf.set_xy(45, task_y + 26)
        pdf.set_font("Helvetica", "I", 6.5)
        pdf.set_text_color(100, 105, 115)
        inst = t.get("instruction", "")
        pdf.multi_cell(145, 3, sanitize_text(f"Instruction: {inst[:120]}..."))

        pdf.set_y(task_y + card_h + 3)

    # 6. Closing Note
    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.ln(2)
    pdf.set_fill_color(248, 249, 251)
    pdf.set_draw_color(225, 230, 240)
    pdf.rect(10, pdf.get_y(), 190, 12, "FD")
    pdf.set_xy(14, pdf.get_y() + 3.5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(50, 55, 65)
    pdf.cell(180, 4, sanitize_text("You may wish to share this with the platform's support team."), align="C")

    pdf.output(output_path)
    return output_path
