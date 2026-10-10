"""AI transcription and field suggestion module for PatternProof.

Uses Google Gemini to read order screenshots, receipts, and support chat records.
Transcribes visible text and suggests order date, platform, store name, order ID,
amount in INR, and issue type.

Includes:
- Automatic in-memory image shrinking (max 1280px, JPEG quality 80)
- 60s request timeout
- Exponential backoff retry (2s, 5s, 10s) on 504, 503, 429, and timeouts
- Graceful error messaging with technical detail separation
"""

import os
import io
import time
import json
import re
from typing import Optional, Tuple, Dict, Any, List
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables
load_dotenv()

# Model name constant at the top of the file
MODEL_NAME = "gemini-3.8-flash"

# Timeout and retry configuration
REQUEST_TIMEOUT_SECONDS = 60.0
RETRY_DELAYS = [2, 5, 10]

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


def optimize_image_for_gemini(image_path: str) -> Image.Image:
    """Shrink image for Gemini to avoid network latency and 504 timeouts.
    
    Converts to RGB, resizes so the longest side is at most 1280 px,
    and saves as JPEG quality 80 in memory.
    """
    with Image.open(image_path) as orig_img:
        img = orig_img.convert("RGB")
        max_dim = max(img.width, img.height)
        if max_dim > 1280:
            scale = 1280.0 / max_dim
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        return Image.open(buf)


def is_retryable_error(exc: Exception) -> bool:
    """Determine if error is a transient failure (504, 503, 429, timeout) eligible for retry."""
    if isinstance(exc, json.JSONDecodeError):
        return False

    err_str = str(exc).lower()

    # Do NOT retry on invalid key, auth errors, or client invalid requests
    non_retryable = [
        "api_key_invalid",
        "invalid_api_key",
        "invalid api key",
        "api key not valid",
        "unauthenticated",
        "401",
        "403",
        "400",
        "jsondecodeerror",
    ]
    if any(nr in err_str for nr in non_retryable):
        return False

    # Retry on 504, 503, 429, deadline, timeout, unavailable, resource_exhausted
    retryable = [
        "504",
        "503",
        "429",
        "deadline",
        "timeout",
        "timed out",
        "resource_exhausted",
        "unavailable",
    ]
    return any(r in err_str for r in retryable)


def call_gemini_with_retry(
    model: genai.GenerativeModel,
    contents: Any,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
    delays: Optional[List[int]] = None,
) -> Tuple[Optional[Any], Optional[Exception]]:
    """Execute Gemini request with up to 3 retries (waits 2s, 5s, 10s) on 504/503/429/timeout."""
    retry_list = delays if delays is not None else RETRY_DELAYS
    attempts = 1 + len(retry_list)
    last_exc: Optional[Exception] = None

    for attempt in range(attempts):
        try:
            response = model.generate_content(contents, request_options={"timeout": timeout})
            return response, None
        except Exception as e:
            last_exc = e
            if attempt < len(retry_list) and is_retryable_error(e):
                time.sleep(retry_list[attempt])
                continue
            break

    return None, last_exc


def transcribe_order_screenshot(
    image_path: str,
    api_key: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """Send optimized screenshot to Gemini to extract visible text and suggest order details.
    
    Returns:
        (result_dict, user_friendly_message, technical_details)
    """
    key = get_api_key(api_key)
    if not key:
        return None, "No GEMINI_API_KEY found. Manual entry is active.", None

    if not os.path.exists(image_path):
        return None, f"Image file not found: {image_path}", None

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
        # Preprocess and shrink image in memory
        optimized_image = optimize_image_for_gemini(image_path)

        genai.configure(api_key=key)
        model = genai.GenerativeModel(MODEL_NAME)

        # Call with 60s timeout and retries (2s, 5s, 10s)
        response, exc = call_gemini_with_retry(
            model=model,
            contents=[prompt, optimized_image],
            timeout=REQUEST_TIMEOUT_SECONDS,
            delays=RETRY_DELAYS,
        )

        if exc is not None:
            if is_retryable_error(exc):
                return (
                    None,
                    "Gemini is slow right now. Please try again, or enter the details manually.",
                    str(exc),
                )
            return (
                None,
                "Could not transcribe screenshot with AI. Manual entry is active.",
                str(exc),
            )

        if not response or not response.text:
            return None, "AI response was empty. Manual entry is active.", None

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
        return result, None, None

    except json.JSONDecodeError as jde:
        return None, "Failed to parse AI response. Manual entry is active.", str(jde)
    except Exception as e:
        return None, "AI service error. Manual entry is active.", str(e)
