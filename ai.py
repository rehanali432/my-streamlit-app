"""AI helper for PatternProof: Delivery Evidence Coach.

Interfaces with Google Gemini for vision and instruction generation.
Enforces:
- API key lookup hierarchy: sidebar override -> st.secrets -> .env
- Image preprocessing: max 1280px, EXIF transpose, JPEG quality 80 in memory
- 60s timeout with exponential backoff [2s, 5s, 10s]
- Deterministic MOCK MODE fallback when key is absent or toggle is enabled
- Neutral observations only: never assigns fault or judges claims
"""

import os
import io
import time
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
from PIL import Image, ImageOps
import streamlit as st

# Load environment variables
load_dotenv()

# Fast Gemini Flash model supporting vision
MODEL_NAME = "gemini-1.5-flash"
REQUEST_TIMEOUT_SECONDS = 60.0
RETRY_DELAYS = [2, 5, 10]


def get_api_key(sidebar_override: Optional[str] = None) -> Optional[str]:
    """Retrieve Gemini API key following strict lookup hierarchy:

    1. Optional sidebar override box
    2. st.secrets["GEMINI_API_KEY"] (safely inside try/except)
    3. System environment / .env
    Strips whitespace and quotes. Never prints or logs the key.
    """
    if sidebar_override and sidebar_override.strip():
        return sidebar_override.strip().strip("'\"")

    try:
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and str(key).strip():
                return str(key).strip().strip("'\"")
    except Exception:
        pass

    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and env_key.strip():
        return env_key.strip().strip("'\"")

    return None


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code blocks and extraneous whitespace from AI response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def preprocess_image_for_gemini(image_input: Any) -> bytes:
    """Preprocess image in-memory for Gemini transmission:

    1. Open with Pillow
    2. Correct EXIF orientation
    3. Convert to RGB
    4. Resize so longest side is at most 1280 px
    5. Save as JPEG quality 80 in memory
    Original bytes and file on disk remain completely untouched.
    """
    if isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, str):
        img = Image.open(image_input)
    elif hasattr(image_input, "read"):
        # UploadedFile or file-like
        image_input.seek(0)
        img = Image.open(io.BytesIO(image_input.read()))
        image_input.seek(0)
    elif isinstance(image_input, Image.Image):
        img = image_input.copy()
    else:
        raise ValueError("Unsupported image input type")

    # Fix EXIF rotation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize so longest side <= 1280 px
    w, h = img.size
    longest = max(w, h)
    if longest > 1280:
        scale = 1280.0 / longest
        new_size = (int(round(w * scale)), int(round(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    out_buf = io.BytesIO()
    img.save(out_buf, format="JPEG", quality=80)
    return out_buf.getvalue()


def _is_retryable_error(error_msg: str) -> bool:
    """Identify network or server rate limit codes suitable for retry."""
    retry_codes = ["504", "503", "429", "deadline", "timeout", "resourceexhausted", "unavailable"]
    low = error_msg.lower()
    return any(c in low for c in retry_codes)


def call_gemini_vision(
    prompt: str,
    image_bytes_list: List[bytes],
    api_key: str,
    spinnerText: str = "Analyzing with AI..."
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Execute Gemini request with retry backoff, timeout, and JSON extraction."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    # Prepare PIL images
    pil_images = []
    for b in image_bytes_list:
        shrunk = preprocess_image_for_gemini(b)
        pil_images.append(Image.open(io.BytesIO(shrunk)))

    last_error = ""

    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if attempt > 0:
            time.sleep(delay)

        try:
            with st.spinner(f"{spinnerText} (attempt {attempt + 1})..."):
                model = genai.GenerativeModel(
                    MODEL_NAME,
                    generation_config={"response_mime_type": "application/json"}
                )
                contents = [prompt] + pil_images
                response = model.generate_content(
                    contents,
                    request_options={"timeout": REQUEST_TIMEOUT_SECONDS}
                )

                if not response or not response.text:
                    last_error = "Empty response received from AI model."
                    continue

                raw = clean_json_response(response.text)
                try:
                    parsed = json.loads(raw)
                    return parsed, None
                except json.JSONDecodeError:
                    # Retry parsing once by stripping extra characters
                    match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group(1))
                        return parsed, None
                    last_error = f"Invalid JSON returned: {raw[:200]}"
                    continue

        except Exception as e:
            err_str = str(e)
            last_error = err_str
            if not _is_retryable_error(err_str):
                # Non-retryable error (e.g. invalid key or bad argument)
                break

    return None, last_error


# =========================================================================
# 1. READ RECEIPT
# =========================================================================

def read_receipt(
    image_bytes: bytes,
    api_key: Optional[str] = None,
    mock: bool = False
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Transcribe order receipt screenshot into structured order data.

    Returns:
    {"readable": bool, "store": str|null, "platform": str|null, "order_id": str|null,
     "order_date": "YYYY-MM-DD"|null, "total_inr": number|null,
     "items": [{"name": str, "quantity": int|null, "price_inr": number|null}]}
    """
    if mock or not api_key:
        return {
            "readable": True,
            "store": "Fresh Basket (demo)",
            "platform": "InstaMart",
            "order_id": "ORD-8921-X",
            "order_date": "2026-10-08",
            "total_inr": 450.0,
            "items": [
                {"name": "Organic Almond Milk 1L", "quantity": 1, "price_inr": 180.0},
                {"name": "Whole Wheat Bread 400g", "quantity": 1, "price_inr": 50.0},
                {"name": "Greek Yogurt Blueberry 200g", "quantity": 2, "price_inr": 220.0}
            ]
        }, None

    prompt = (
        "System: You are an impartial delivery receipt transcriber. "
        "Transcribe or describe ONLY what is visible in the provided receipt image. "
        "Do not guess. Return null or 'unclear' if unsure. Do not identify people. Do not judge anyone. "
        "Return strictly valid JSON matching this schema:\n"
        "{\n"
        '  "readable": true/false,\n'
        '  "store": "Store name or null",\n'
        '  "platform": "Delivery platform name or null",\n'
        '  "order_id": "Order or invoice ID or null",\n'
        '  "order_date": "YYYY-MM-DD or null",\n'
        '  "total_inr": 0.0 or null,\n'
        '  "items": [{"name": "Item name", "quantity": 1, "price_inr": 0.0}]\n'
        "}"
    )

    data, err = call_gemini_vision(prompt, [image_bytes], api_key, "Reading receipt with AI")
    if data:
        return data, None
    return {
        "readable": False,
        "store": None,
        "platform": None,
        "order_id": None,
        "order_date": None,
        "total_inr": None,
        "items": []
    }, err


# =========================================================================
# 2. ANALYSE PRODUCT PHOTO
# =========================================================================

def analyse_product_photo(
    image_bytes: bytes,
    receipt_items: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    mock: bool = False
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Analyze initial photo of the delivered product.

    Returns:
    {"product_description": str, "matches_receipt_item": str|null,
     "packaging_state": str, "visible_text": [str], "visible_issues": [str],
     "photo_quality": {"blurry": bool, "too_dark": bool, "subject_cut_off": bool}}
    """
    if mock or not api_key:
        return {
            "product_description": "Cardboard carton of almond milk showing crushed corner and damaged seam.",
            "matches_receipt_item": "Organic Almond Milk 1L",
            "packaging_state": "Dented and partially torn outer carton",
            "visible_text": ["Pure Harvest", "Best Before", "1L"],
            "visible_issues": ["Crushed top-right corner", "Leakage at top seam"],
            "photo_quality": {
                "blurry": False,
                "too_dark": False,
                "subject_cut_off": False
            }
        }, None

    items_str = json.dumps(receipt_items or [], ensure_ascii=False)
    prompt = (
        "System: You are an impartial visual analyst for delivery packaging. "
        "Describe ONLY what is visible in the product photo. Do not guess. Do not judge or allocate fault. "
        f"Receipt items for context: {items_str}\n"
        "Return strictly valid JSON matching this schema:\n"
        "{\n"
        '  "product_description": "Concise factual description of the item in frame",\n'
        '  "matches_receipt_item": "Matching receipt item name or null",\n'
        '  "packaging_state": "Factual state of packaging (e.g. sealed, opened, crushed, wet)",\n'
        '  "visible_text": ["Visible brand, expiry, or printed words"],\n'
        '  "visible_issues": ["Observable physical anomalies like tear, dent, spill"],\n'
        '  "photo_quality": {"blurry": false, "too_dark": false, "subject_cut_off": false}\n'
        "}"
    )

    data, err = call_gemini_vision(prompt, [image_bytes], api_key, "Analyzing product photo with AI")
    if data:
        return data, None
    return {
        "product_description": "Photo provided by user.",
        "matches_receipt_item": None,
        "packaging_state": "Unspecified",
        "visible_text": [],
        "visible_issues": [],
        "photo_quality": {"blurry": False, "too_dark": False, "subject_cut_off": False}
    }, err


# =========================================================================
# 3. GENERATE TASKS
# =========================================================================

def generate_tasks(
    order_data: Dict[str, Any],
    product_analysis: Optional[Dict[str, Any]],
    claim_type: str,
    api_key: Optional[str] = None,
    mock: bool = False
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Generate 4 to 6 specific photographic evidence tasks tailored to the order.

    Returns:
    {"tasks": [{"task_code": "T1", "shot_type": "...", "title": "...",
                "instruction": "...", "angle": "...", "must_show": ["..."],
                "related_item": "..."}]}
    """
    if mock or not api_key:
        from tasks import get_template_tasks
        mock_tasks = get_template_tasks(claim_type)
        # Tailor slightly to demo item
        for t in mock_tasks:
            t["related_item"] = "Organic Almond Milk 1L"
        return {"tasks": mock_tasks}, None

    order_summary = {
        "store": order_data.get("store"),
        "platform": order_data.get("platform"),
        "order_id": order_data.get("order_id"),
        "items": order_data.get("items", []),
        "claim_type": claim_type,
    }
    order_str = json.dumps(order_summary, ensure_ascii=False)
    analysis_str = json.dumps(product_analysis or {}, ensure_ascii=False)

    prompt = (
        "System: You are an impartial evidence photo checklist coach for consumer delivery orders. "
        "Generate 4 to 6 specific, practical photo tasks that document the delivery issue factually. "
        "Tailor each task to the actual receipt items and the visual details observed. "
        "Instructions must be concrete: specify distance, angle, lighting, and what to place in frame. "
        "Shot types MUST be chosen ONLY from: "
        '["wide_package", "delivery_bag_or_seal", "label_closeup", "expiry_date", '
        '"close_up_issue", "contents_laid_out", "side_angle", "top_down", "size_reference", "item_with_receipt"].\n'
        f"Order details: {order_str}\n"
        f"Product analysis: {analysis_str}\n"
        "Return strictly valid JSON matching this schema:\n"
        "{\n"
        '  "tasks": [\n'
        '    {\n'
        '      "task_code": "T1",\n'
        '      "shot_type": "one of the allowed strings",\n'
        '      "title": "Clear task title",\n'
        '      "instruction": "Concrete step-by-step instruction: distance, angle, lighting",\n'
        '      "angle": "Specific camera angle",\n'
        '      "must_show": ["Requirement 1", "Requirement 2", "Requirement 3"],\n'
        '      "related_item": "Item name from receipt or null"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if attempt > 0:
            time.sleep(delay)
        try:
            with st.spinner(f"Generating custom photo checklist (attempt {attempt + 1})..."):
                model = genai.GenerativeModel(
                    MODEL_NAME,
                    generation_config={"response_mime_type": "application/json"}
                )
                response = model.generate_content(
                    prompt,
                    request_options={"timeout": REQUEST_TIMEOUT_SECONDS}
                )
                if response and response.text:
                    cleaned = clean_json_response(response.text)
                    parsed = json.loads(cleaned)
                    return parsed, None
        except Exception as e:
            if not _is_retryable_error(str(e)):
                return {"tasks": []}, str(e)

    return {"tasks": []}, "AI task generation timed out after retries."


# =========================================================================
# 4. VERIFY PHOTO
# =========================================================================

def verify_photo(
    image_bytes: bytes,
    task: Dict[str, Any],
    order_data: Dict[str, Any],
    api_key: Optional[str] = None,
    mock: bool = False,
    filename: str = ""
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Observe uploaded photo against the task requirements.

    Returns:
    {"requirements": [{"requirement": str, "visible": "yes"|"no"|"unclear", "note": str}],
     "shows_expected_item": "yes"|"no"|"unclear",
     "readable_text": str,
     "image_issues": subset of ["blurry","dark","glare","cut_off","photo_of_a_screen"]}
    """
    must_show = task.get("must_show", [])

    if mock or not api_key:
        # Deterministic simulation based on filename cues
        fn_lower = filename.lower()
        if "good" in fn_lower:
            reqs = [{"requirement": r, "visible": "yes", "note": "Clear view confirmed."} for r in must_show]
            return {
                "requirements": reqs,
                "shows_expected_item": "yes",
                "readable_text": "Batch #4902 EXP 2026",
                "image_issues": []
            }, None
        elif "bad" in fn_lower:
            reqs = []
            for i, r in enumerate(must_show):
                if i == 0:
                    reqs.append({"requirement": r, "visible": "no", "note": "Could not confirm in photo."})
                else:
                    reqs.append({"requirement": r, "visible": "yes", "note": "Visible."})
            return {
                "requirements": reqs,
                "shows_expected_item": "yes",
                "readable_text": "Unclear",
                "image_issues": ["blurry"]
            }, None
        else:
            reqs = []
            for i, r in enumerate(must_show):
                if i == 0:
                    reqs.append({"requirement": r, "visible": "unclear", "note": "Partially obscured."})
                else:
                    reqs.append({"requirement": r, "visible": "yes", "note": "Visible."})
            return {
                "requirements": reqs,
                "shows_expected_item": "yes",
                "readable_text": "Unclear",
                "image_issues": []
            }, None

    task_str = json.dumps({
        "title": task.get("title"),
        "shot_type": task.get("shot_type"),
        "angle": task.get("angle"),
        "must_show": must_show,
        "related_item": task.get("related_item")
    }, ensure_ascii=False)

    prompt = (
        "System: You are an impartial visual verifier. "
        "Observe ONLY what is visible in the provided photo. "
        "Do not guess. Do not decide fault. Use neutral observations. "
        f"Task details: {task_str}\n"
        "Return strictly valid JSON matching this schema:\n"
        "{\n"
        '  "requirements": [\n'
        '    {"requirement": "Exact string from must_show", "visible": "yes"|"no"|"unclear", "note": "Brief observation"}\n'
        '  ],\n'
        '  "shows_expected_item": "yes"|"no"|"unclear",\n'
        '  "readable_text": "Any transcribed text visible or empty string",\n'
        '  "image_issues": ["subset of: blurry, dark, glare, cut_off, photo_of_a_screen"]\n'
        "}\n"
        "The requirements array MUST contain an entry for EVERY item in must_show."
    )

    data, err = call_gemini_vision(prompt, [image_bytes], api_key, "Verifying photo with AI")
    if data:
        return data, None

    # Fallback response on AI error
    fallback_reqs = [{"requirement": r, "visible": "unclear", "note": "AI check unavailable"} for r in must_show]
    return {
        "requirements": fallback_reqs,
        "shows_expected_item": "unclear",
        "readable_text": "",
        "image_issues": []
    }, err
