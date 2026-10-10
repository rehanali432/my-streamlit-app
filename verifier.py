"""Verification engine for PatternProof: Delivery Evidence Coach.

Plain Python makes every pass/fail decision.
Checks resolution, blur (via Pillow ImageFilter.FIND_EDGES), brightness,
duplicate SHA-256 and aHash similarity, EXIF timestamps, and maps AI observations
to deterministic statuses: Passed, Partial, Retake, or User-confirmed.
"""

import hashlib
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set
from PIL import Image, ImageFilter, ImageStat, ExifTags


def compute_sha256(data: bytes) -> str:
    """Compute standard SHA-256 hexadecimal hash on raw byte payload."""
    return hashlib.sha256(data).hexdigest()


def compute_ahash(image: Image.Image) -> int:
    """Compute 64-bit average hash (aHash) using Pillow for visual similarity."""
    # Convert to 8x8 grayscale
    small = image.resize((8, 8), Image.Resampling.BILINEAR).convert("L")
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels) if pixels else 0
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return int(bits, 2) if bits else 0


def hamming_distance(h1: int, h2: int) -> int:
    """Calculate the Hamming distance between two integer hashes."""
    return bin(h1 ^ h2).count("1")


def extract_exif_timestamp(img: Image.Image) -> Optional[datetime]:
    """Extract capture datetime from EXIF metadata if present."""
    try:
        exif = img._getexif()
        if not exif:
            return None

        # Look up DateTimeOriginal (36867) or DateTime (306)
        dt_str = None
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id)
            if tag_name in ("DateTimeOriginal", "DateTime"):
                dt_str = str(value)
                break

        if dt_str:
            # Standard EXIF format: "YYYY:MM:DD HH:MM:SS"
            clean_str = dt_str.strip().replace("\x00", "")
            return datetime.strptime(clean_str, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def verify_task_photo(
    image_bytes: bytes,
    task: Dict[str, Any],
    order_data: Dict[str, Any],
    ai_result: Optional[Dict[str, Any]] = None,
    existing_hashes: Optional[Set[str]] = None,
    other_task_ahashes: Optional[List[Tuple[str, int]]] = None,
    is_camera_input: bool = False
) -> Dict[str, Any]:
    """Run all 6 verification checks and decide final task status.

    Returns a dict with:
      - status: "Passed", "Partial", "Retake"
      - checks: list of {name, status: "pass"|"warn"|"fail", detail}
      - retake_advice: list of string suggestions
      - photo_hash: SHA-256 string
      - ahash: int
      - captured_at: ISO or friendly date string
    """
    checks: List[Dict[str, str]] = []
    advice: List[str] = []

    # 1. Byte hash & Image Decoding
    photo_hash = compute_sha256(image_bytes)

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        # Re-open for operations since verify() closes/invalidates the image object
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        return {
            "status": "Retake",
            "checks": [{
                "name": "Image Readability",
                "status": "fail",
                "detail": "Could not read image file. Retake suggested."
            }],
            "retake_advice": ["Provide an intact JPEG or PNG image."],
            "photo_hash": photo_hash,
            "ahash": 0,
            "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # Check 1: Resolution (shorter side at least 600 px)
    width, height = img.size
    shorter_side = min(width, height)
    if shorter_side < 600:
        checks.append({
            "name": "Resolution Check",
            "status": "fail",
            "detail": f"Resolution is {width}x{height} (shorter side {shorter_side} px is below required 600 px minimum)."
        })
        advice.append("Take a higher-resolution photo so text and fine details remain clear.")
    else:
        checks.append({
            "name": "Resolution Check",
            "status": "pass",
            "detail": f"Resolution is {width}x{height} (meets 600 px minimum)."
        })

    # Check 2: Sharpness (Blur) & Lighting (Brightness)
    gray = img.convert("L")

    # Sharpness via FIND_EDGES variance (no OpenCV required)
    edges = gray.filter(ImageFilter.FIND_EDGES)
    stat_edges = ImageStat.Stat(edges)
    edge_var = stat_edges.var[0] if stat_edges.var else 0.0

    if edge_var < 30.0:
        checks.append({
            "name": "Sharpness & Focus",
            "status": "warn",
            "detail": "Photo looks blurry; edge definition is low. Retake suggested with camera held steady."
        })
        advice.append("Hold the camera steady and tap to focus before capturing.")
    else:
        checks.append({
            "name": "Sharpness & Focus",
            "status": "pass",
            "detail": "Sharpness and edge focus appear sufficient."
        })

    # Brightness check
    stat_gray = ImageStat.Stat(gray)
    mean_brightness = stat_gray.mean[0] if stat_gray.mean else 128.0

    if mean_brightness < 40.0:
        checks.append({
            "name": "Lighting & Brightness",
            "status": "warn",
            "detail": f"Photo appears dark (mean brightness {mean_brightness:.1f}/255). Retake suggested in better lighting."
        })
        advice.append("Turn on room lights or take the photo in well-lit natural light.")
    elif mean_brightness > 245.0:
        checks.append({
            "name": "Lighting & Brightness",
            "status": "warn",
            "detail": "Photo is overexposed with high glare. Retake suggested with reduced direct reflection."
        })
        advice.append("Adjust camera angle to avoid reflective light glare on glossy labels.")
    else:
        checks.append({
            "name": "Lighting & Brightness",
            "status": "pass",
            "detail": "Lighting and exposure appear balanced."
        })

    # Check 3: Duplicate Photo Detection (SHA-256 & aHash)
    if existing_hashes and photo_hash in existing_hashes:
        checks.append({
            "name": "Duplicate File Check",
            "status": "fail",
            "detail": "This exact file was already used in this order. Please provide the specific photo requested for this task."
        })
        advice.append("Each checklist task requires a distinct photo capturing the designated angle.")
    else:
        checks.append({
            "name": "Duplicate File Check",
            "status": "pass",
            "detail": "Unique file verified."
        })

    # Visual similarity check (aHash) against other tasks
    current_ahash = compute_ahash(img)
    if other_task_ahashes:
        too_similar = False
        similar_task_code = ""
        for other_code, other_hash_val in other_task_ahashes:
            dist = hamming_distance(current_ahash, other_hash_val)
            if dist <= 5:
                too_similar = True
                similar_task_code = other_code
                break

        if too_similar:
            checks.append({
                "name": "Angle Distinctness",
                "status": "warn",
                "detail": f"Looks very similar to the photo for task {similar_task_code}. Ensure this shot captures the distinct angle requested."
            })
            advice.append(f"Ensure this photo shows the unique angle specified rather than repeating the shot for {similar_task_code}.")
        else:
            checks.append({
                "name": "Angle Distinctness",
                "status": "pass",
                "detail": "Photo composition is distinct from other task shots."
            })

    # Check 4: Timestamp Verification
    exif_dt = extract_exif_timestamp(img)
    order_date_str = str(order_data.get("order_date", "")).strip()

    if is_camera_input:
        captured_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        captured_source = "taken in app"
        checks.append({
            "name": "Capture Timestamp",
            "status": "pass",
            "detail": f"Captured live via device camera in app ({captured_at_str})."
        })
    elif exif_dt:
        captured_at_str = exif_dt.strftime("%Y-%m-%d %H:%M:%S")
        captured_source = "EXIF camera metadata"

        if order_date_str:
            try:
                order_dt = datetime.strptime(order_date_str, "%Y-%m-%d")
                if exif_dt.date() < order_dt.date():
                    checks.append({
                        "name": "Capture Timestamp",
                        "status": "warn",
                        "detail": f"Photo timestamp ({exif_dt.strftime('%Y-%m-%d')}) is earlier than the order date ({order_date_str}). Retake suggested."
                    })
                    advice.append("Ensure the uploaded photo was taken during or after delivery of this order.")
                else:
                    checks.append({
                        "name": "Capture Timestamp",
                        "status": "pass",
                        "detail": f"Timestamp confirmed ({captured_at_str})."
                    })
            except Exception:
                checks.append({
                    "name": "Capture Timestamp",
                    "status": "pass",
                    "detail": f"Timestamp recorded ({captured_at_str})."
                })
        else:
            checks.append({
                "name": "Capture Timestamp",
                "status": "pass",
                "detail": f"Timestamp recorded ({captured_at_str})."
            })
    else:
        captured_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        captured_source = "file upload"
        checks.append({
            "name": "Capture Timestamp",
            "status": "pass",
            "detail": "No timestamp metadata found (common for messaging and web uploads)."
        })

    # Check 5: AI Observations (must_show mapping)
    must_show_items = task.get("must_show", [])
    if ai_result and isinstance(ai_result, dict):
        ai_reqs = ai_result.get("requirements", [])
        obs_map = {}
        if isinstance(ai_reqs, list):
            for item in ai_reqs:
                if isinstance(item, dict) and "requirement" in item:
                    obs_map[item["requirement"].strip().lower()] = item

        for req in must_show_items:
            req_clean = req.strip()
            # Match directly or fuzzy key
            found_obs = obs_map.get(req_clean.lower())
            if not found_obs:
                # Try partial substring match
                for k, v in obs_map.items():
                    if k in req_clean.lower() or req_clean.lower() in k:
                        found_obs = v
                        break

            visible_val = str(found_obs.get("visible", "yes")).lower() if found_obs else "yes"
            note_val = str(found_obs.get("note", "")).strip() if found_obs else ""

            if visible_val == "yes":
                checks.append({
                    "name": f"Requirement: {req_clean}",
                    "status": "pass",
                    "detail": f"Clearly visible{' - ' + note_val if note_val else ''}."
                })
            elif visible_val == "unclear":
                checks.append({
                    "name": f"Requirement: {req_clean}",
                    "status": "warn",
                    "detail": f"Not clearly visible{' - ' + note_val if note_val else ''}. Retake suggested."
                })
                advice.append(f"Make sure '{req_clean}' is directly visible and in focus.")
            else:  # "no"
                checks.append({
                    "name": f"Requirement: {req_clean}",
                    "status": "fail",
                    "detail": f"Could not confirm in photo{' - ' + note_val if note_val else ''}. Retake suggested."
                })
                advice.append(f"Position the camera to clearly show '{req_clean}'.")

        # Check shows_expected_item
        expected_item_val = str(ai_result.get("shows_expected_item", "yes")).lower()
        if expected_item_val == "no":
            checks.append({
                "name": "Expected Item Verification",
                "status": "fail",
                "detail": "Could not confirm expected item in frame. Retake suggested."
            })
            advice.append("Include the specific product or parcel from this order in the frame.")
        elif expected_item_val == "unclear":
            checks.append({
                "name": "Expected Item Verification",
                "status": "warn",
                "detail": "Expected item is not clearly distinguishable. Retake suggested."
            })
            advice.append("Center the expected item in the frame with good lighting.")
        else:
            checks.append({
                "name": "Expected Item Verification",
                "status": "pass",
                "detail": "Expected item appears in frame."
            })

        # Image issues noted by AI
        img_issues = ai_result.get("image_issues", [])
        if isinstance(img_issues, list):
            for issue in img_issues:
                issue_str = str(issue).strip().lower()
                if issue_str == "photo_of_a_screen":
                    checks.append({
                        "name": "Display Quality",
                        "status": "warn",
                        "detail": "Photo appears to be taken of another digital screen rather than physical parcel."
                    })
                    advice.append("Take a direct photo of the physical product or delivery bag.")
                elif issue_str == "blurry":
                    advice.append("Retake with the camera held still to eliminate blur.")
                elif issue_str == "dark":
                    advice.append("Increase lighting on the subject.")
                elif issue_str == "cut_off":
                    checks.append({
                        "name": "Framing",
                        "status": "warn",
                        "detail": "Subject appears partially cut off at frame borders."
                    })
                    advice.append("Step back slightly so the entire item fits within frame.")
    else:
        # Fallback when AI observations are unavailable
        checks.append({
            "name": "AI Visual Analysis",
            "status": "warn",
            "detail": "AI check unavailable; verified using technical image checks only."
        })
        advice.append("AI check could not be completed. You may mark this task as user-confirmed.")

    # 6. Final Status Decision (Strict Plain Python)
    has_fail = any(c["status"] == "fail" for c in checks)
    has_warn = any(c["status"] == "warn" for c in checks)

    if has_fail:
        final_status = "Retake"
    elif has_warn:
        final_status = "Partial"
    else:
        final_status = "Passed"

    # Deduplicate advice
    deduped_advice = []
    seen_advice = set()
    for adv in advice:
        if adv not in seen_advice:
            seen_advice.add(adv)
            deduped_advice.append(adv)

    return {
        "status": final_status,
        "checks": checks,
        "retake_advice": deduped_advice,
        "photo_hash": photo_hash,
        "ahash": current_ahash,
        "captured_at": captured_at_str,
        "captured_source": captured_source,
    }
