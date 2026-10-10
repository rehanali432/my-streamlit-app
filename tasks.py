"""Checklist task definitions and validation for PatternProof.

Manages claim types, template shot types, and ensures strict Python validation
over AI-generated photography checklists.
"""

from typing import List, Dict, Any, Optional

CLAIM_TYPES: List[str] = [
    "Damaged item",
    "Spoiled or expired item",
    "Wrong item delivered",
    "Missing item",
    "Short quantity",
]

VALID_SHOT_TYPES: List[str] = [
    "wide_package",
    "delivery_bag_or_seal",
    "label_closeup",
    "expiry_date",
    "close_up_issue",
    "contents_laid_out",
    "side_angle",
    "top_down",
    "size_reference",
    "item_with_receipt",
]

# Standard template tasks per claim type (used as deterministic baseline and fallback)
TEMPLATE_TASKS: Dict[str, List[Dict[str, Any]]] = {
    "Damaged item": [
        {
            "shot_type": "wide_package",
            "title": "Full view of outer delivery package",
            "instruction": "Place parcel on a flat, well-lit surface. Step back 1 metre to capture the complete parcel and surrounding condition.",
            "angle": "Wide eye-level angle",
            "must_show": ["Entire outer carton or bag", "Delivery label", "External packaging condition"],
        },
        {
            "shot_type": "close_up_issue",
            "title": "Close-up of visible damage or leak",
            "instruction": "Hold camera 20-30 cm from the affected area. Ensure sharp focus on any crush, tear, puncture, or leak.",
            "angle": "Close-up 45-degree angle",
            "must_show": ["Specific damaged section", "Puncture, tear, or crushed surface", "Clear detail without motion blur"],
        },
        {
            "shot_type": "label_closeup",
            "title": "Product brand and label details",
            "instruction": "Capture the front product label clearly showing product name, barcode, and batch info with no lighting glare.",
            "angle": "Direct frontal view",
            "must_show": ["Product name and brand", "Barcode or batch number", "Net weight or volume"],
        },
        {
            "shot_type": "item_with_receipt",
            "title": "Damaged product beside order receipt",
            "instruction": "Place the damaged item directly next to the printed invoice or order receipt screenshot on another screen.",
            "angle": "Overview 45-degree angle",
            "must_show": ["Product and receipt in single frame", "Order ID or store name on receipt", "Damaged area visible"],
        },
    ],
    "Spoiled or expired item": [
        {
            "shot_type": "expiry_date",
            "title": "Expiry date and batch code close-up",
            "instruction": "Focus closely on the stamped Best Before, Expiry, or Manufacturing date code. Ensure text is sharp and readable.",
            "angle": "Macro close-up perpendicular to date stamp",
            "must_show": ["Printed expiry or Best Before date", "Batch or lot code", "Adjacent container panel"],
        },
        {
            "shot_type": "label_closeup",
            "title": "Front product label and details",
            "instruction": "Take a clear shot of the product front face showing brand, exact item title, and packaging specification.",
            "angle": "Direct frontal eye-level",
            "must_show": ["Brand name and product title", "Pack size or volume", "Container front face"],
        },
        {
            "shot_type": "close_up_issue",
            "title": "Visible texture or seal concern",
            "instruction": "Capture a well-lit close-up of any discoloration, mold, unusual texture, or broken seal.",
            "angle": "Close-up 45-degree angle under bright light",
            "must_show": ["Observed physical condition", "Inner seal or cap", "Surface texture"],
        },
        {
            "shot_type": "wide_package",
            "title": "Complete product container",
            "instruction": "Capture the full container or package showing its overall condition and safety cap.",
            "angle": "Eye-level 3/4 overview",
            "must_show": ["Complete product bottle or box", "Cap and safety seal", "Overall container state"],
        },
    ],
    "Wrong item delivered": [
        {
            "shot_type": "label_closeup",
            "title": "Front label of received item",
            "instruction": "Capture a sharp photo of the received item's label showing the exact brand, variant, flavor, and size.",
            "angle": "Direct frontal view",
            "must_show": ["Product title and flavor/variant", "Brand name", "Net quantity or weight"],
        },
        {
            "shot_type": "contents_laid_out",
            "title": "All delivered items laid out",
            "instruction": "Lay out all items received in this order side by side on a clean flat surface in one wide photo.",
            "angle": "Top-down overhead view",
            "must_show": ["All delivered items in one frame", "Clean background", "No items stacked or hidden"],
        },
        {
            "shot_type": "item_with_receipt",
            "title": "Received item alongside order receipt",
            "instruction": "Position the delivered item beside the printed order invoice or digital receipt.",
            "angle": "45-degree overview angle",
            "must_show": ["Received item and receipt together", "Receipt item listing", "Order identifier"],
        },
        {
            "shot_type": "wide_package",
            "title": "Outer delivery parcel and address slip",
            "instruction": "Capture the outer delivery bag or carton showing any platform stickers or address labels.",
            "angle": "Wide eye-level shot",
            "must_show": ["Delivery bag or box", "Shipping slip or barcode sticker", "Packaging condition"],
        },
    ],
    "Missing item": [
        {
            "shot_type": "delivery_bag_or_seal",
            "title": "Delivery bag seal and tape condition",
            "instruction": "Photograph the delivery package opening, tape, handles, or tamper-evident seal showing its condition upon arrival.",
            "angle": "Close-up on bag opening and seals",
            "must_show": ["Package seal or tape line", "Opening flap or handles", "Delivery sticker or label"],
        },
        {
            "shot_type": "contents_laid_out",
            "title": "All received items laid out in frame",
            "instruction": "Place every item that actually arrived onto a flat surface in a single unstacked row or grid.",
            "angle": "Top-down bird's-eye view",
            "must_show": ["Every delivered item clearly visible", "Nothing stacked or hidden", "Clean surface"],
        },
        {
            "shot_type": "item_with_receipt",
            "title": "Received items alongside delivery receipt",
            "instruction": "Place all received goods next to the printed order invoice or delivery slip showing the itemized list.",
            "angle": "Wide overhead 45-degree view",
            "must_show": ["Received goods beside invoice", "Itemized list on invoice", "Order ID on receipt"],
        },
        {
            "shot_type": "top_down",
            "title": "Interior of empty delivery bag or box",
            "instruction": "Look directly down into the opened delivery package showing that no additional items remain inside.",
            "angle": "Direct top-down vertical shot",
            "must_show": ["Interior base of package", "Open flaps of bag or box", "Clear empty compartment"],
        },
    ],
    "Short quantity": [
        {
            "shot_type": "delivery_bag_or_seal",
            "title": "Delivery package seal and condition",
            "instruction": "Photograph the outer package seals and closure tape showing whether it arrived intact or altered.",
            "angle": "Close-up of package seal and seams",
            "must_show": ["Package seal or tape seams", "Delivery label", "Condition of bag opening"],
        },
        {
            "shot_type": "contents_laid_out",
            "title": "All received units laid out side-by-side",
            "instruction": "Place all units of the affected item side-by-side so the exact quantity received is clearly countable.",
            "angle": "Top-down view",
            "must_show": ["All units of the item in one row", "Individual packages visible", "Count clearly readable"],
        },
        {
            "shot_type": "item_with_receipt",
            "title": "Received units next to receipt quantity",
            "instruction": "Place the received units directly next to the printed receipt highlighting the billed quantity.",
            "angle": "45-degree angle overview",
            "must_show": ["Received units next to receipt", "Billed quantity line on receipt", "Order ID visible"],
        },
        {
            "shot_type": "top_down",
            "title": "Interior view of delivery package",
            "instruction": "Take an overhead shot into the delivery bag or box showing that no remaining units were left inside.",
            "angle": "Direct top-down view",
            "must_show": ["Interior of container", "Base of delivery bag", "Clear interior space"],
        },
    ],
}


def get_template_tasks(claim_type: str) -> List[Dict[str, Any]]:
    """Return a deep copy of template tasks for the given claim type."""
    templates = TEMPLATE_TASKS.get(claim_type, TEMPLATE_TASKS["Damaged item"])
    result = []
    for idx, t in enumerate(templates, start=1):
        result.append({
            "task_code": f"T{idx}",
            "shot_type": t["shot_type"],
            "title": t["title"],
            "instruction": t["instruction"],
            "angle": t["angle"],
            "must_show": list(t["must_show"]),
            "related_item": None,
            "status": "Open",
            "attempts": 0,
        })
    return result


def validate_ai_tasks(
    raw_tasks: Optional[List[Dict[str, Any]]],
    claim_type: str,
    order_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Validate and sanitize tasks returned by AI or fallback.

    Hard rules enforced by plain Python:
    1. Keep only tasks with shot_type in VALID_SHOT_TYPES.
    2. Enforce 2 to 4 must_show items.
    3. Require non-empty instruction and title.
    4. Remove duplicate shot types.
    5. Cap total tasks at 6.
    6. If fewer than 4 valid remain, or the claim type's primary template shot is absent,
       top up from standard templates.
    7. Renumber cleanly as T1, T2, ...
    """
    templates = get_template_tasks(claim_type)
    primary_template_shot = templates[0]["shot_type"] if templates else "wide_package"

    valid_tasks: List[Dict[str, Any]] = []
    seen_shots = set()

    if isinstance(raw_tasks, list):
        for candidate in raw_tasks:
            if not isinstance(candidate, dict):
                continue

            shot_type = candidate.get("shot_type", "").strip()
            if shot_type not in VALID_SHOT_TYPES:
                continue

            if shot_type in seen_shots:
                continue

            instruction = str(candidate.get("instruction", "")).strip()
            title = str(candidate.get("title", "")).strip()
            if not instruction or not title:
                continue

            angle = str(candidate.get("angle", "Eye level")).strip() or "Eye level"

            must_show_raw = candidate.get("must_show", [])
            if isinstance(must_show_raw, str):
                must_show_list = [s.strip() for s in must_show_raw.split(",") if s.strip()]
            elif isinstance(must_show_raw, list):
                must_show_list = [str(s).strip() for s in must_show_raw if str(s).strip()]
            else:
                must_show_list = []

            # Keep between 2 and 4 must_show items
            if len(must_show_list) < 2:
                # Supplement with standard requirement
                must_show_list.append("Item clearly placed in frame")
                must_show_list.append("Clear lighting without glare")
            elif len(must_show_list) > 4:
                must_show_list = must_show_list[:4]

            related_item = candidate.get("related_item")
            if related_item:
                related_item = str(related_item).strip()

            seen_shots.add(shot_type)
            valid_tasks.append({
                "shot_type": shot_type,
                "title": title,
                "instruction": instruction,
                "angle": angle,
                "must_show": must_show_list,
                "related_item": related_item,
                "status": "Open",
                "attempts": 0,
            })

            if len(valid_tasks) >= 6:
                break

    # Check if primary template shot is present
    has_primary = any(t["shot_type"] == primary_template_shot for t in valid_tasks)
    if not has_primary and templates:
        # Prepend the primary template task
        primary_task = dict(templates[0])
        valid_tasks.insert(0, primary_task)
        seen_shots.add(primary_task["shot_type"])

    # If fewer than 4 valid tasks remain, top up from templates
    if len(valid_tasks) < 4:
        for tpl in templates:
            if tpl["shot_type"] not in seen_shots:
                valid_tasks.append(dict(tpl))
                seen_shots.add(tpl["shot_type"])
                if len(valid_tasks) >= 4:
                    break

    # Cap at 6 tasks maximum
    final_tasks = valid_tasks[:6]

    # Re-assign sequential task codes T1..Tn
    for i, t in enumerate(final_tasks, start=1):
        t["task_code"] = f"T{i}"

    return final_tasks
