"""Demo mode and synthetic asset generation for PatternProof.

Generates fictional receipts, damaged product drawings, and test photos
using Pillow alone (no external fonts required). Enables full end-to-end testing
without requiring any Gemini API key or external images.
"""

import os
import io
import hashlib
from datetime import datetime
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFilter

import db
import ai
import tasks

UPLOADS_DIR = "uploads"


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash for byte data."""
    return hashlib.sha256(data).hexdigest()


def generate_demo_receipt_image() -> bytes:
    """Generate a crisp synthetic receipt image using Pillow (640x900 px)."""
    width, height = 640, 920
    img = Image.new("RGB", (width, height), color=(248, 249, 250))
    draw = ImageDraw.Draw(img)

    # Outer receipt border
    draw.rectangle([20, 20, width - 20, height - 20], outline=(180, 185, 195), width=3)

    # Header decorative banner
    draw.rectangle([25, 25, width - 25, 100], fill=(235, 238, 245))
    draw.text((width // 2 - 120, 40), "FRESH BASKET (DEMO)", fill=(20, 30, 50))
    draw.text((width // 2 - 90, 65), "Platform: InstaMart Express", fill=(80, 90, 110))

    # Divider line
    draw.line([40, 120, width - 40, 120], fill=(200, 205, 215), width=2)

    # Order Metadata
    draw.text((45, 140), "ORDER ID: ORD-8921-X", fill=(30, 30, 30))
    draw.text((45, 165), "ORDER DATE: 2026-10-08 14:22 IST", fill=(60, 60, 60))
    draw.text((45, 190), "DELIVERY STATUS: Completed", fill=(0, 130, 60))

    # Table Header
    draw.rectangle([40, 225, width - 40, 260], fill=(225, 230, 240))
    draw.text((50, 235), "ITEM DESCRIPTION", fill=(30, 40, 60))
    draw.text((420, 235), "QTY", fill=(30, 40, 60))
    draw.text((500, 235), "PRICE (INR)", fill=(30, 40, 60))

    # Line Items
    items = [
        ("1. Organic Almond Milk 1L", "1", "180.00"),
        ("2. Whole Wheat Bread 400g", "1", "50.00"),
        ("3. Greek Yogurt Blueberry 200g", "2", "220.00"),
    ]

    y = 280
    for name, qty, price in items:
        draw.text((50, y), name, fill=(40, 40, 40))
        draw.text((430, y), qty, fill=(40, 40, 40))
        draw.text((510, y), price, fill=(40, 40, 40))
        y += 45

    # Totals Divider
    draw.line([40, y + 10, width - 40, y + 10], fill=(200, 205, 215), width=2)

    y += 30
    draw.text((360, y), "Subtotal:", fill=(70, 70, 70))
    draw.text((510, y), "INR 450.00", fill=(70, 70, 70))
    y += 30
    draw.text((360, y), "Delivery Fee:", fill=(70, 70, 70))
    draw.text((510, y), "INR 0.00", fill=(70, 70, 70))
    y += 35

    # Highlight Total Box
    draw.rectangle([340, y - 5, width - 40, y + 35], fill=(255, 92, 31))
    draw.text((355, y + 8), "TOTAL PAID:", fill=(255, 255, 255))
    draw.text((495, y + 8), "INR 450.00", fill=(255, 255, 255))

    # Privacy tip indicator on demo receipt
    y += 75
    draw.rectangle([40, y, width - 40, y + 50], fill=(240, 244, 250), outline=(200, 210, 225))
    draw.text((50, y + 15), "[REDACTED] Customer address and phone hidden", fill=(100, 110, 130))

    # Barcode representation
    y += 85
    draw.text((width // 2 - 80, y), "* BARCODE 8921-X *", fill=(100, 100, 100))
    y += 25
    for bar_x in range(60, width - 60, 8):
        bar_w = 3 if (bar_x % 16 == 0 or bar_x % 24 == 0) else 1
        draw.line([bar_x, y, bar_x, y + 50], fill=(40, 40, 40), width=bar_w)

    # Footer note
    y += 70
    draw.text((width // 2 - 130, y), "PatternProof Simulated Evidence Asset", fill=(130, 140, 150))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def generate_demo_product_image() -> bytes:
    """Generate a synthetic product photo showing a damaged almond milk carton (800x800 px)."""
    width, height = 800, 800
    img = Image.new("RGB", (width, height), color=(38, 44, 58))
    draw = ImageDraw.Draw(img)

    # Countertop surface
    draw.rectangle([40, 520, width - 40, height - 40], fill=(50, 58, 76))

    # Product box body (Almond Milk Carton)
    carton_coords = [220, 180, 560, 660]
    draw.rectangle(carton_coords, fill=(245, 240, 228), outline=(180, 170, 150), width=4)

    # Carton gable top roof
    roof_polygon = [(220, 180), (390, 80), (560, 180)]
    draw.polygon(roof_polygon, fill=(230, 220, 205), outline=(170, 160, 140))

    # Plastic cap
    draw.rectangle([360, 50, 420, 85], fill=(255, 92, 31), outline=(200, 60, 10), width=2)

    # Brand Label on carton
    draw.rectangle([250, 240, 530, 400], fill=(215, 235, 225), outline=(160, 190, 175), width=2)
    draw.text((275, 260), "PURE HARVEST", fill=(20, 80, 50))
    draw.text((275, 290), "ORGANIC ALMOND MILK", fill=(10, 40, 25))
    draw.text((275, 330), "1 LITRE - UNSWEETENED", fill=(60, 100, 80))
    draw.text((275, 360), "BATCH: #4902  EXP: 2026-10-24", fill=(80, 60, 40))

    # Nutrition / barcode small panel
    draw.rectangle([250, 430, 380, 600], fill=(255, 255, 255), outline=(200, 200, 200))
    draw.text((260, 445), "Nutrition Facts", fill=(40, 40, 40))
    for line_y in range(480, 580, 12):
        draw.line([260, line_y, 370, line_y], fill=(120, 120, 120), width=1)

    # VISIBLE DAMAGE: Crushed & torn top-right corner
    crush_coords = [(480, 140), (560, 140), (570, 260), (470, 220)]
    draw.polygon(crush_coords, fill=(190, 170, 150), outline=(140, 110, 90), width=3)

    # Crease lines and leak spots
    draw.line([490, 150, 540, 230], fill=(100, 70, 50), width=3)
    draw.line([520, 160, 480, 210], fill=(90, 60, 40), width=2)
    draw.line([540, 200, 580, 240], fill=(80, 50, 30), width=3)

    # Spillage indication
    draw.ellipse([540, 640, 660, 700], fill=(225, 220, 205), outline=(190, 180, 160))
    draw.text((555, 660), "Visible Spill", fill=(100, 90, 70))

    # Red visual marker box calling out the issue
    draw.rectangle([450, 120, 600, 270], outline=(255, 92, 31), width=3)
    draw.text((460, 95), "VISIBLE DAMAGE", fill=(255, 92, 31))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_demo_task_image(kind: str = "good", shot_label: str = "Wide Package") -> Tuple[str, bytes]:
    """Create sample test photo for verification testing (800x800 px).

    kind='good': Sharp, well-lit, distinct details (passes verifier).
    kind='bad': Blurred edges or dark lighting (flags retake advice).
    """
    width, height = 800, 800

    if kind == "bad":
        # Low contrast dark image that is heavily blurred
        img = Image.new("RGB", (width, height), color=(25, 28, 35))
        draw = ImageDraw.Draw(img)
        draw.rectangle([200, 200, 600, 600], fill=(45, 50, 60))
        draw.text((250, 380), f"BLURRED / DARK: {shot_label}", fill=(80, 90, 100))
        # Apply heavy blur to fail edge variance check
        for _ in range(4):
            img = img.filter(ImageFilter.BLUR)
        filename = "bad_1.jpg"
    else:
        # Crisp, high contrast, sharp edges
        img = Image.new("RGB", (width, height), color=(240, 242, 245))
        draw = ImageDraw.Draw(img)
        # Background elements with clear lines
        draw.rectangle([40, 40, width - 40, height - 40], outline=(70, 80, 100), width=4)
        draw.rectangle([150, 150, 650, 650], fill=(255, 255, 255), outline=(30, 40, 50), width=4)
        draw.rectangle([180, 180, 620, 260], fill=(255, 92, 31))
        draw.text((200, 210), f"TASK EVIDENCE: {shot_label}", fill=(255, 255, 255))
        draw.text((200, 290), "ITEM: Organic Almond Milk 1L", fill=(20, 20, 20))
        draw.text((200, 330), "CLEAR VISIBILITY TEST - PASSED", fill=(0, 120, 50))
        draw.text((200, 370), "BATCH: #4902  EXP: 2026-10-24", fill=(50, 50, 50))

        # Sharp high-frequency grid pattern ensuring high edge variance
        for grid_x in range(200, 600, 20):
            draw.line([grid_x, 420, grid_x, 580], fill=(40, 50, 60), width=2)
        for grid_y in range(420, 580, 20):
            draw.line([200, grid_y, 600, grid_y], fill=(40, 50, 60), width=2)

        filename = "good_1.jpg"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return filename, buf.getvalue()


def load_demo_order() -> int:
    """Create a complete demo order and 4 checklist tasks in SQLite.

    Returns the new order row ID.
    """
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # 1. Generate receipt
    receipt_bytes = generate_demo_receipt_image()
    receipt_path = os.path.join(UPLOADS_DIR, "demo_receipt.jpg")
    with open(receipt_path, "wb") as f:
        f.write(receipt_bytes)
    receipt_hash = compute_hash(receipt_bytes)

    # 2. Generate product photo
    product_bytes = generate_demo_product_image()
    product_path = os.path.join(UPLOADS_DIR, "demo_product.jpg")
    with open(product_path, "wb") as f:
        f.write(product_bytes)
    product_hash = compute_hash(product_bytes)

    # 3. Order metadata
    order_dict = {
        "store": "Fresh Basket (demo)",
        "platform": "InstaMart",
        "order_id": "ORD-8921-X",
        "order_date": "2026-10-08",
        "total_inr": 450.0,
        "items": [
            {"name": "Organic Almond Milk 1L", "quantity": 1, "price_inr": 180.0},
            {"name": "Whole Wheat Bread 400g", "quantity": 1, "price_inr": 50.0},
            {"name": "Greek Yogurt Blueberry 200g", "quantity": 2, "price_inr": 220.0}
        ],
        "claim_type": "Damaged item",
        "receipt_path": receipt_path,
        "receipt_hash": receipt_hash,
        "product_photo_path": product_path,
        "product_hash": product_hash,
        "product_analysis": {
            "product_description": "Cardboard carton of almond milk showing crushed corner and seal compromise.",
            "matches_receipt_item": "Organic Almond Milk 1L",
            "packaging_state": "Dented and partially torn outer carton",
            "visible_text": ["Pure Harvest", "Best Before", "1L"],
            "visible_issues": ["Crushed top-right corner", "Leakage at top seam"],
            "photo_quality": {"blurry": False, "too_dark": False, "subject_cut_off": False}
        }
    }

    # Save order to DB
    order_row_id = db.save_order(order_dict)

    # 4. Generate & validate 4 tasks
    ai_tasks_resp, _ = ai.generate_tasks(order_dict, order_dict["product_analysis"], "Damaged item", mock=True)
    validated = tasks.validate_ai_tasks(ai_tasks_resp.get("tasks", []), "Damaged item", order_dict)

    # Save tasks to DB
    db.save_tasks(order_row_id, validated)

    return order_row_id
