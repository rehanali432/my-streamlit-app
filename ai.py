"""AI transcription and field suggestion module for PatternProof.

Uses Google Gemini to read order screenshots, receipts, and support chat records.
Transcribes visible text and suggests order date, platform, store name, order ID,
amount in INR, and issue type. The AI is used ONLY to transcribe visible text.
The user reviews and edits everything before saving.
"""

import os
import json
import re
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables
load_dotenv()

# Model name constant at the top of the file
MODEL_NAME = "gemini-3.8-flash"

VALID_ISSUE_TYPES = [
    "Late delivery",
    "Missing item",
    "Wrong item",
    "Damaged/spoiled",
    "Refund not received",
    "Refund denied",
    "Support unresponsive",
    "Other",
]


def get_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieve API key from argument, environment, or .env."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    return os.environ.get("GEMINI_API_KEY", "").strip() or None


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code fences and extraneous whitespace from AI response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def transcribe_order_screenshot(
    image_path: str,
    api_key: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Send screenshot image to Gemini to extract visible text and suggest order details.
    
    Returns:
        (result_dict, error_message)
    """
    key = get_api_key(api_key)
    if not key:
        return None, "No GEMINI_API_KEY found. Manual entry is active."

    if not os.path.exists(image_path):
        return None, f"Image file not found: {image_path}"

    prompt = (
        "Transcribe only visible text from this order receipt or support chat screenshot. "
        "Do not blame, judge, or identify any delivery partner, restaurant staff, or support agent. "
        "Do not guess or assume details that are not visible. Return null for fields you are unsure of. "
        "Return ONLY a valid JSON object with the following keys and no extra formatting or commentary:\n"
        "{\n"
        '  "extracted_text": str,\n'
        '  "order_date": "YYYY-MM-DD" or null,\n'
        '  "platform": str or null,\n'
        '  "restaurant_or_store": str or null,\n'
        '  "order_id": str or null,\n'
        '  "amount_inr": number or null,\n'
        '  "issue_type": "Late delivery" | "Missing item" | "Wrong item" | "Damaged/spoiled" | "Refund not received" | "Refund denied" | "Support unresponsive" | "Other" or null\n'
        "}"
    )

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(MODEL_NAME)

        with Image.open(image_path) as img:
            response = model.generate_content([prompt, img], request_options={"timeout": 12.0})

        if not response or not response.text:
            return None, "AI response was empty."

        clean_text = clean_json_response(response.text)
        data = json.loads(clean_text)

        # Validate issue type
        issue_val = data.get("issue_type")
        if issue_val not in VALID_ISSUE_TYPES:
            issue_val = None

        amt_val = data.get("amount_inr")
        if amt_val is not None:
            try:
                amt_val = float(amt_val)
            except (ValueError, TypeError):
                amt_val = None

        result = {
            "extracted_text": str(data.get("extracted_text") or ""),
            "order_date": data.get("order_date") if isinstance(data.get("order_date"), str) and len(data.get("order_date")) == 10 else None,
            "platform": str(data.get("platform")) if data.get("platform") else None,
            "restaurant_or_store": str(data.get("restaurant_or_store")) if data.get("restaurant_or_store") else None,
            "order_id": str(data.get("order_id")) if data.get("order_id") else None,
            "amount_inr": amt_val,
            "issue_type": issue_val,
        }
        return result, None

    except json.JSONDecodeError as jde:
        return None, f"Failed to parse AI response as JSON: {jde}"
    except Exception as e:
        return None, f"AI transcription error: {str(e)}"
