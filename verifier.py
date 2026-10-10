"""Verifier module for PatternProof AI Assistant.

Performs strict, plain-Python verification of AI-generated responses
before they are shown to the user. No AI is used in this module.

Checks performed:
1. JSON parsed correctly.
2. Every ID in cited_ids exists in the active case database.
3. Every number in numbers_used matches a value from the incidents or patterns.py.
4. Every number written in the answer text is in the allowed set (excluding date/order fragments).
5. Banned-word scan (fraud, scam, cheat, guilty, criminal, liable, illegal, harass, blame).
6. Complaint drafts must cite at least one order and not assign fault or blame.
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple

BANNED_WORDS = [
    "fraud",
    "scam",
    "cheat",
    "guilty",
    "criminal",
    "liable",
    "illegal",
    "harass",
    "blame",
]

FAULT_PHRASES = [
    "at fault",
    "fault of",
    "is to blame",
    "caused by your rider",
    "caused by your driver",
    "delivery boy's fault",
    "partner's fault",
    "restaurant is guilty",
    "your fault",
]


def extract_allowed_numbers(
    incidents: List[Dict[str, Any]],
    patterns_data: Dict[str, Any],
) -> Set[float]:
    """Collect all valid numerical values from incidents and patterns.py."""
    allowed: Set[float] = set()

    # 1. Structural counts
    total_st = patterns_data.get("total", {})
    allowed.add(float(total_st.get("count", len(incidents))))
    allowed.add(float(total_st.get("dated_count", 0)))
    allowed.add(float(total_st.get("undated_count", 0)))
    allowed.add(float(total_st.get("span_days", 0)))
    allowed.add(float(total_st.get("missing_amount_count", 0)))
    total_amt = total_st.get("total_amount_inr")
    if total_amt is not None:
        allowed.add(round(float(total_amt), 2))
        allowed.add(float(int(total_amt)))

    # 2. Weekly statistics
    weekly_st = patterns_data.get("weekly", {})
    allowed.add(float(weekly_st.get("first_half_avg", 0.0)))
    allowed.add(float(weekly_st.get("second_half_avg", 0.0)))
    allowed.add(float(weekly_st.get("first_half_count", 0)))
    allowed.add(float(weekly_st.get("second_half_count", 0)))
    for w in weekly_st.get("weeks", []):
        allowed.add(float(w.get("count", 0)))
        allowed.add(float(w.get("week_index", 0)))

    # 3. Platform numbers
    platforms_st = patterns_data.get("platforms", {})
    allowed.add(float(len(platforms_st)))
    for p_name, p_data in platforms_st.items():
        allowed.add(float(p_data.get("count", 0)))
        p_amt = p_data.get("amount_inr")
        if p_amt is not None:
            allowed.add(round(float(p_amt), 2))
            allowed.add(float(int(p_amt)))

    # 4. Issue types
    issue_types_st = patterns_data.get("issue_types", {})
    allowed.add(float(len(issue_types_st)))
    for it_name, it_data in issue_types_st.items():
        allowed.add(float(it_data.get("count", 0)))

    # 5. Stores
    stores_st = patterns_data.get("stores", {})
    allowed.add(float(stores_st.get("repeat_store_count", 0)))
    for s_name, s_data in stores_st.get("all_stores", {}).items():
        allowed.add(float(s_data.get("count", 0)))

    # 6. Delays
    delays_st = patterns_data.get("delays", {})
    allowed.add(float(delays_st.get("delay_count", 0)))
    allowed.add(float(delays_st.get("average_delay_minutes", 0.0)))
    allowed.add(float(delays_st.get("max_delay_minutes", 0)))
    for rec in delays_st.get("records", []):
        allowed.add(float(rec.get("promised", 0)))
        allowed.add(float(rec.get("actual", 0)))
        allowed.add(float(rec.get("delay_minutes", 0)))

    # 7. Refunds
    refunds_st = patterns_data.get("refunds", {})
    allowed.add(float(refunds_st.get("pending_count", 0)))
    allowed.add(float(refunds_st.get("denied_count", 0)))
    allowed.add(float(refunds_st.get("partial_count", 0)))
    allowed.add(float(refunds_st.get("longest_pending_days", 0)))
    for rf_name, rf_data in refunds_st.get("counts", {}).items():
        allowed.add(float(rf_data.get("count", 0)))

    # 8. Individual incident values & IDs
    for inc in incidents:
        allowed.add(float(inc.get("id", 0)))
        amt = inc.get("amount_inr")
        if amt is not None:
            try:
                val = float(amt)
                allowed.add(round(val, 2))
                allowed.add(float(int(val)))
            except (ValueError, TypeError):
                pass
        prom = inc.get("promised_minutes")
        if prom is not None:
            allowed.add(float(prom))
        act = inc.get("actual_minutes")
        if act is not None:
            allowed.add(float(act))
            if prom is not None and act > prom:
                allowed.add(float(act - prom))

    # Add standard small counts (e.g. 0, 1, 2, 5 for lines)
    allowed.update({0.0, 1.0, 2.0, 3.0, 4.0, 5.0})

    return allowed


def extract_numbers_from_text(
    text: str,
    incidents: List[Dict[str, Any]],
) -> List[float]:
    """Extract numbers from text, filtering out dates and order ID fragments."""
    # Build list of date substrings to remove from number search
    clean_text = text

    # Remove YYYY-MM-DD patterns
    date_matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", clean_text)
    for dm in date_matches:
        clean_text = clean_text.replace(dm, " ")

    # Remove order IDs like SW-9021, BL-4412, etc.
    for inc in incidents:
        oid = inc.get("order_id")
        if oid:
            clean_text = clean_text.replace(oid, " ")
            # Also remove numerical suffix if standalone
            num_part = re.sub(r"\D", "", oid)
            if num_part:
                clean_text = re.sub(rf"\b{re.escape(num_part)}\b", " ", clean_text)

    # Extract all remaining numbers (integers and decimals)
    found_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", clean_text)
    extracted: List[float] = []
    for tok in found_tokens:
        try:
            val = float(tok)
            # Ignore year numbers (e.g., 2024, 2025, 2026)
            if 2020 <= val <= 2030:
                continue
            extracted.append(val)
        except ValueError:
            pass

    return extracted


def verify_response(
    raw_json_str: Optional[str],
    parsed_output: Optional[Dict[str, Any]],
    incidents: List[Dict[str, Any]],
    patterns_data: Dict[str, Any],
    task_prompt: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """Run the 6 required verification checks on the AI output.
    
    Returns:
        (all_passed: bool, check_results: list of {check_name, passed, detail})
    """
    check_results: List[Dict[str, Any]] = []

    # Check 1: JSON parsed correctly
    if not isinstance(parsed_output, dict):
        check_results.append({
            "check_name": "1. Valid JSON Output",
            "passed": False,
            "detail": "Failed to parse AI output into a valid JSON object.",
        })
        return False, check_results

    has_required_keys = all(
        k in parsed_output for k in ["answer", "cited_ids", "numbers_used"]
    )
    if not has_required_keys:
        check_results.append({
            "check_name": "1. Valid JSON Output",
            "passed": False,
            "detail": "JSON is missing one of required keys: answer, cited_ids, numbers_used.",
        })
        return False, check_results

    check_results.append({
        "check_name": "1. Valid JSON Output",
        "passed": True,
        "detail": "Response is valid JSON with answer, cited_ids, and numbers_used.",
    })

    answer_text = str(parsed_output.get("answer") or "").strip()
    cited_ids = parsed_output.get("cited_ids") or []
    numbers_used = parsed_output.get("numbers_used") or []

    # Check 2: Every ID in cited_ids exists in the database
    valid_db_ids = {inc["id"] for inc in incidents}
    invalid_ids = [iid for iid in cited_ids if iid not in valid_db_ids]

    if invalid_ids:
        check_results.append({
            "check_name": "2. Database ID Traceability",
            "passed": False,
            "detail": f"Cited incident IDs {invalid_ids} do not exist in the active case.",
        })
    elif not cited_ids and len(incidents) > 0 and len(answer_text) > 40:
        # If there are incidents but none were cited in a substantial answer
        check_results.append({
            "check_name": "2. Database ID Traceability",
            "passed": False,
            "detail": "No incident IDs were cited for factual statements.",
        })
    else:
        cited_str = ", ".join(str(i) for i in cited_ids) if cited_ids else "None"
        check_results.append({
            "check_name": "2. Database ID Traceability",
            "passed": True,
            "detail": f"All cited incident IDs [{cited_str}] exist in active records.",
        })

    # Check 3: Every number in numbers_used matches a value from incidents or patterns.py
    allowed_numbers = extract_allowed_numbers(incidents, patterns_data)
    unmatched_used_numbers = []
    for num in numbers_used:
        try:
            val = float(num)
            # Check with round match
            if not any(abs(val - a) < 0.05 for a in allowed_numbers):
                unmatched_used_numbers.append(num)
        except (ValueError, TypeError):
            unmatched_used_numbers.append(num)

    if unmatched_used_numbers:
        check_results.append({
            "check_name": "3. numbers_used Data Consistency",
            "passed": False,
            "detail": f"Numbers {unmatched_used_numbers} do not match any computed metric or incident value.",
        })
    else:
        check_results.append({
            "check_name": "3. numbers_used Data Consistency",
            "passed": True,
            "detail": f"All {len(numbers_used)} reported numbers exist in verifiable case metrics.",
        })

    # Check 4: Every number written in the answer text is also in the allowed set
    text_numbers = extract_numbers_from_text(answer_text, incidents)
    unallowed_text_numbers = []
    for tn in text_numbers:
        # Check against allowed numbers (including cited_ids)
        if not any(abs(tn - a) < 0.05 for a in allowed_numbers):
            unallowed_text_numbers.append(tn)

    if unallowed_text_numbers:
        check_results.append({
            "check_name": "4. Answer Text Number Verification",
            "passed": False,
            "detail": f"Text contains unverified numbers: {unallowed_text_numbers}.",
        })
    else:
        check_results.append({
            "check_name": "4. Answer Text Number Verification",
            "passed": True,
            "detail": "All numbers appearing in text correspond to known case data.",
        })

    # Check 5: Banned-word scan
    banned_pattern = re.compile(
        r"\b(" + "|".join(BANNED_WORDS) + r")\w*\b",
        re.IGNORECASE,
    )
    banned_matches = banned_pattern.findall(answer_text)
    if banned_matches:
        check_results.append({
            "check_name": "5. Banned-Word & Neutrality Scan",
            "passed": False,
            "detail": f"Found non-neutral prohibited term(s): {list(set(banned_matches))}.",
        })
    else:
        check_results.append({
            "check_name": "5. Banned-Word & Neutrality Scan",
            "passed": True,
            "detail": "Zero prohibited terms detected (neutral wording maintained).",
        })

    # Check 6: Complaint drafts must mention at least one cited order and not assign blame/fault
    is_complaint_task = any(
        kw in task_prompt.lower()
        for kw in ["complaint", "draft", "support message", "support team"]
    )
    if is_complaint_task:
        has_order_mention = (
            len(cited_ids) > 0
            or any(
                inc.get("order_id") and inc["order_id"] in answer_text
                for inc in incidents
            )
            or bool(re.search(r"\b(order|incident)\s*#?\d+\b", answer_text, re.IGNORECASE))
        )
        has_fault_phrase = any(fp in answer_text.lower() for fp in FAULT_PHRASES)

        if not has_order_mention:
            check_results.append({
                "check_name": "6. Complaint Draft Compliance",
                "passed": False,
                "detail": "Complaint draft does not reference any specific order ID or record ID.",
            })
        elif has_fault_phrase:
            check_results.append({
                "check_name": "6. Complaint Draft Compliance",
                "passed": False,
                "detail": "Draft contains accusatory language assigning personal fault.",
            })
        else:
            check_results.append({
                "check_name": "6. Complaint Draft Compliance",
                "passed": True,
                "detail": "Draft references documented orders with objective, neutral phrasing.",
            })
    else:
        check_results.append({
            "check_name": "6. Complaint Draft Compliance",
            "passed": True,
            "detail": "Not a complaint draft task; neutrality guidelines satisfied.",
        })

    all_passed = all(cr["passed"] for cr in check_results)
    return all_passed, check_results
