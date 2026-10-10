"""Demo data generator for PatternProof (Delivery Order Issues).

Loads 12 clearly fictional delivery order issue records over ~6 weeks
across 3 platforms (Swiggy, Zomato, Blinkit) and 4 stores, featuring:
- Repeat late deliveries from the same store
- Rising number of issues per week
- 3 refund disputes (including an older pending refund)
- 2 link groups
- Amounts in INR
- Clean synthetic order receipt screenshots in uploads/
"""

import os
import hashlib
from PIL import Image, ImageDraw
import db

UPLOADS_DIR = "uploads"


def create_demo_order_image(
    filename: str,
    platform: str,
    store: str,
    order_id: str,
    amount: float,
    issue_type: str,
    order_date: str,
) -> tuple[str, str]:
    """Generate a synthetic order receipt screenshot and return (filepath, sha256_hash)."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, filename)

    width, height = 500, 360
    bg_color = (20, 24, 33)
    card_bg = (30, 37, 50)
    text_color = (240, 245, 255)
    sub_color = (150, 165, 185)
    accent_color = (255, 92, 31)

    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # Top Brand / Header bar
    draw.rectangle([(0, 0), (width, 50)], fill=(15, 18, 25))
    draw.rectangle([(0, 48), (width, 50)], fill=accent_color)
    draw.text((16, 16), f"[{platform.upper()}] Order Summary • #{order_id}", fill=text_color)

    # Order details card
    draw.rounded_rectangle([(20, 68), (width - 20, height - 60)], radius=10, fill=card_bg)

    draw.text((36, 85), f"Store: {store}", fill=text_color)
    draw.text((36, 115), f"Order Date: {order_date} | Total Paid: INR {amount:.2f}", fill=sub_color)
    draw.text((36, 145), f"Reported Issue: {issue_type}", fill=accent_color)

    # Order receipt items snippet
    draw.line([(36, 180), (width - 36, 180)], fill=(50, 60, 80), width=1)
    draw.text((36, 195), "Items: 2x Signature Meal, 1x Beverage", fill=text_color)
    draw.text((36, 225), "Support Chat Record: Order marked delivered", fill=sub_color)
    draw.text((36, 255), "Status Note: User requested refund inquiry via app support.", fill=sub_color)

    # Footer banner with mandatory neutrality statement
    draw.rectangle([(0, height - 38), (width, height)], fill=(12, 15, 20))
    draw.text((16, height - 26), "PatternProof Order Evidence Record • Authenticity not verified", fill=(110, 120, 135))

    image.save(filepath, format="PNG")

    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    file_hash = hasher.hexdigest()

    return filepath, file_hash


def load_demo_case(
    case_name: str = "Demo Case - Food & Grocery Orders",
    db_path: str = db.DB_FILE,
) -> int:
    """Populate database with 12 fictional delivery order issue records."""
    db.init_db(db_path)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Clean existing records for this case
    db.delete_all_incidents(case_name=case_name, db_path=db_path)

    demo_orders = [
        # Week 1 (1 issue)
        {
            "order_date": "2024-09-02",
            "platform": "Swiggy",
            "restaurant_or_store": "Spice Bowl Kitchen",
            "order_id": "SW-9021",
            "issue_type": "Late delivery",
            "amount_inr": 450.0,
            "promised_minutes": 30,
            "actual_minutes": 65,
            "refund_status": "None requested",
            "extracted_text": "Order #SW-9021 delivered 35 mins past promised arrival time. Delivery partner arrived at 14:15.",
            "notes": "Order marked delivered 35 minutes late without prior notification.",
            "link_group": "Spice Bowl Kitchen Order Chain",
            "filename": "demo_order_01.png",
        },
        # Week 2 (1 issue)
        {
            "order_date": "2024-09-10",
            "platform": "Blinkit",
            "restaurant_or_store": "Daily Fresh Supermarket",
            "order_id": "BL-4412",
            "issue_type": "Missing item",
            "amount_inr": 620.0,
            "promised_minutes": 15,
            "actual_minutes": 20,
            "refund_status": "Full",
            "extracted_text": "Packet of organic milk (INR 90) missing from delivery bag. Photo attached in support chat.",
            "notes": "Support credited refund of INR 90 after receipt review.",
            "link_group": None,
            "filename": "demo_order_02.png",
        },
        # Week 3 (1 issue - refund dispute pending)
        {
            "order_date": "2024-09-18",
            "platform": "Zomato",
            "restaurant_or_store": "Tandoor Express",
            "order_id": "ZM-7721",
            "issue_type": "Refund not received",
            "amount_inr": 890.0,
            "promised_minutes": 40,
            "actual_minutes": 45,
            "refund_status": "Pending",
            "extracted_text": "Support chat says refund of INR 890 initiated within 5-7 business days. No credit reflected in bank statement.",
            "notes": "Pending refund inquiry active for multiple weeks.",
            "link_group": None,
            "filename": "demo_order_03.png",
        },
        # Week 4 (2 issues)
        {
            "order_date": "2024-09-24",
            "platform": "Swiggy",
            "restaurant_or_store": "Spice Bowl Kitchen",
            "order_id": "SW-9204",
            "issue_type": "Late delivery",
            "amount_inr": 540.0,
            "promised_minutes": 35,
            "actual_minutes": 80,
            "refund_status": "None requested",
            "extracted_text": "Estimated delivery time was 20:10. Order delivered at 20:55. Total delay 45 minutes.",
            "notes": "Second delayed order from the same restaurant.",
            "link_group": "Spice Bowl Kitchen Order Chain",
            "filename": "demo_order_04.png",
        },
        {
            "order_date": "2024-09-27",
            "platform": "Blinkit",
            "restaurant_or_store": "Green Leaf Organics",
            "order_id": "BL-4890",
            "issue_type": "Damaged/spoiled",
            "amount_inr": 380.0,
            "promised_minutes": 12,
            "actual_minutes": 15,
            "refund_status": "Partial",
            "extracted_text": "Fruit container crushed upon arrival. Support provided INR 150 voucher.",
            "notes": "Partial resolution via platform coupon.",
            "link_group": "Blinkit Grocery Dispute #882",
            "filename": "demo_order_05.png",
        },
        # Week 5 (3 issues)
        {
            "order_date": "2024-10-02",
            "platform": "Zomato",
            "restaurant_or_store": "Tandoor Express",
            "order_id": "ZM-8012",
            "issue_type": "Refund denied",
            "amount_inr": 720.0,
            "promised_minutes": 35,
            "actual_minutes": 40,
            "refund_status": "Denied",
            "extracted_text": "Missing side dishes reported. Support bot replied: 'Order meets delivery criteria, refund request denied.'",
            "notes": "Automated refund refusal recorded in support chat screenshot.",
            "link_group": None,
            "filename": "demo_order_06.png",
        },
        {
            "order_date": "2024-10-03",
            "platform": "Blinkit",
            "restaurant_or_store": "Green Leaf Organics",
            "order_id": "BL-5120",
            "issue_type": "Wrong item",
            "amount_inr": 490.0,
            "promised_minutes": 15,
            "actual_minutes": 18,
            "refund_status": "Full",
            "extracted_text": "Received regular wheat bread instead of sourdough bread ordered. Refund processed.",
            "notes": "Full refund credited after barcode photo submitted.",
            "link_group": "Blinkit Grocery Dispute #882",
            "filename": "demo_order_07.png",
        },
        {
            "order_date": "2024-10-05",
            "platform": "Swiggy",
            "restaurant_or_store": "Spice Bowl Kitchen",
            "order_id": "SW-9441",
            "issue_type": "Late delivery",
            "amount_inr": 510.0,
            "promised_minutes": 25,
            "actual_minutes": 70,
            "refund_status": "None requested",
            "extracted_text": "Promised 25 mins. Rider reached restaurant after 40 mins. Delivered 45 mins late.",
            "notes": "Third delayed order from Spice Bowl Kitchen.",
            "link_group": "Spice Bowl Kitchen Order Chain",
            "filename": "demo_order_08.png",
        },
        # Week 6 (4 issues)
        {
            "order_date": "2024-10-09",
            "platform": "Blinkit",
            "restaurant_or_store": "Daily Fresh Supermarket",
            "order_id": "BL-5390",
            "issue_type": "Missing item",
            "amount_inr": 950.0,
            "promised_minutes": 15,
            "actual_minutes": 16,
            "refund_status": "Pending",
            "extracted_text": "Detergent bottle omitted from tote. Support ticket #9901 created, awaiting resolution.",
            "notes": "Refund status shown as pending verification.",
            "link_group": None,
            "filename": "demo_order_09.png",
        },
        {
            "order_date": "2024-10-10",
            "platform": "Zomato",
            "restaurant_or_store": "Spice Bowl Kitchen",
            "order_id": "ZM-8302",
            "issue_type": "Wrong item",
            "amount_inr": 680.0,
            "promised_minutes": 30,
            "actual_minutes": 35,
            "refund_status": "Partial",
            "extracted_text": "Received chicken gravy instead of paneer dish. Support provided partial INR 300 credit.",
            "notes": "Partial refund issued following dish mismatch.",
            "link_group": "Spice Bowl Kitchen Order Chain",
            "filename": "demo_order_10.png",
        },
        {
            "order_date": "2024-10-12",
            "platform": "Swiggy",
            "restaurant_or_store": "Spice Bowl Kitchen",
            "order_id": "SW-9610",
            "issue_type": "Late delivery",
            "amount_inr": 590.0,
            "promised_minutes": 30,
            "actual_minutes": 90,
            "refund_status": "None requested",
            "extracted_text": "Promised delivery window 30 mins. Actual arrival time 90 mins (60 min delay).",
            "notes": "Fourth delayed order from Spice Bowl Kitchen.",
            "link_group": "Spice Bowl Kitchen Order Chain",
            "filename": "demo_order_11.png",
        },
        {
            "order_date": "2024-10-13",
            "platform": "Swiggy",
            "restaurant_or_store": "Daily Fresh Supermarket",
            "order_id": "SW-9688",
            "issue_type": "Support unresponsive",
            "amount_inr": 420.0,
            "promised_minutes": 25,
            "actual_minutes": 30,
            "refund_status": "Pending",
            "extracted_text": "Chat session timed out repeatedly when reporting leaking beverage container.",
            "notes": "Support chat unresolved, refund status marked pending.",
            "link_group": None,
            "filename": "demo_order_12.png",
        },
    ]

    count = 0
    for item in demo_orders:
        img_path, f_hash = create_demo_order_image(
            filename=item["filename"],
            platform=item["platform"],
            store=item["restaurant_or_store"],
            order_id=item["order_id"],
            amount=item["amount_inr"],
            issue_type=item["issue_type"],
            order_date=item["order_date"],
        )
        db.add_incident(
            case_name=case_name,
            order_date=item["order_date"],
            platform=item["platform"],
            restaurant_or_store=item["restaurant_or_store"],
            order_id=item["order_id"],
            issue_type=item["issue_type"],
            amount_inr=item["amount_inr"],
            promised_minutes=item["promised_minutes"],
            actual_minutes=item["actual_minutes"],
            refund_status=item["refund_status"],
            extracted_text=item["extracted_text"],
            notes=item["notes"],
            image_path=img_path,
            file_hash=f_hash,
            link_group=item["link_group"],
            db_path=db_path,
        )
        count += 1

    return count


if __name__ == "__main__":
    loaded = load_demo_case()
    print(f"Loaded {loaded} demo delivery order incidents into database.")
