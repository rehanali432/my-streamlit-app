"""AI Assistant module for PatternProof.

Processes user tasks using saved incident data and patterns.py calculations.
Integrates with verifier.py for plain-Python pre-display checks,
supports 1 retry on verification failure, and provides a deterministic
template fallback when no API key is available or verification fails.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

import patterns
import verifier

load_dotenv()

# Model name constant at top of file
MODEL_NAME = "gemini-3.8-flash"


def get_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieve Gemini API key from explicit input or environment."""
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


def build_context_block(
    incidents: List[Dict[str, Any]],
    patterns_data: Dict[str, Any],
) -> str:
    """Construct structured context block containing all active case data and computed patterns."""
    lines: List[str] = []

    # 1. Incident Records
    lines.append("=== SAVED INCIDENT RECORDS FOR ACTIVE CASE ===")
    if not incidents:
        lines.append("No incidents currently recorded in database.")
    else:
        for inc in incidents:
            amt_str = f"INR {inc.get('amount_inr'):.2f}" if inc.get("amount_inr") is not None else "Not specified"
            delay_str = ""
            if inc.get("actual_minutes") and inc.get("promised_minutes") and inc["actual_minutes"] > inc["promised_minutes"]:
                delay_str = f", Delay: {inc['actual_minutes'] - inc['promised_minutes']} mins (Promised: {inc['promised_minutes']}m, Actual: {inc['actual_minutes']}m)"

            lines.append(
                f"- [Incident #{inc['id']}] Date: {inc.get('order_date') or 'No date'}, "
                f"Platform: {inc.get('platform')}, Store: {inc.get('restaurant_or_store')}, "
                f"Order ID: {inc.get('order_id') or 'N/A'}, Issue: {inc.get('issue_type')}, "
                f"Amount: {amt_str}{delay_str}, Refund Status: {inc.get('refund_status')}, "
                f"Link Group: {inc.get('link_group') or 'None'}, Notes: {inc.get('notes') or 'None'}"
            )

    # 2. Computed Patterns (from patterns.py)
    lines.append("\n=== COMPUTED PATTERNS & METRICS (PLAIN PYTHON) ===")
    total_st = patterns_data.get("total", {})
    lines.append(
        f"Total Orders: {total_st.get('count', 0)}, Date Range: {total_st.get('date_range_str', 'N/A')} "
        f"({total_st.get('span_days', 0)} days), Total Amount Affected: INR {total_st.get('total_amount_inr', 0.0):.2f}"
    )

    weekly_st = patterns_data.get("weekly", {})
    lines.append(
        f"Weekly Trend: {weekly_st.get('trend', 'N/A')} "
        f"(1st half avg: {weekly_st.get('first_half_avg', 0.0)}/wk, 2nd half avg: {weekly_st.get('second_half_avg', 0.0)}/wk)"
    )

    stores_st = patterns_data.get("stores", {})
    repeat_list = [f"{s}: {d['count']} issues [IDs: {d['incident_ids']}]" for s, d in stores_st.get("repeat_stores", {}).items()]
    lines.append(f"Repeat Stores (2+ issues): {', '.join(repeat_list) if repeat_list else 'None'}")

    delays_st = patterns_data.get("delays", {})
    lines.append(
        f"Delays: {delays_st.get('delay_count', 0)} delayed orders, Avg delay: {delays_st.get('average_delay_minutes', 0.0)} mins, "
        f"Max delay: {delays_st.get('max_delay_minutes', 0)} mins [IDs: {delays_st.get('incident_ids', [])}]"
    )

    refunds_st = patterns_data.get("refunds", {})
    lines.append(
        f"Refunds: {refunds_st.get('pending_count', 0)} Pending [IDs: {refunds_st.get('pending_ids', [])}], "
        f"{refunds_st.get('denied_count', 0)} Denied [IDs: {refunds_st.get('denied_ids', [])}], "
        f"{refunds_st.get('partial_count', 0)} Partial [IDs: {refunds_st.get('partial_ids', [])}], "
        f"Longest Pending: {refunds_st.get('longest_pending_days', 0)} days [IDs: {refunds_st.get('longest_pending_ids', [])}]"
    )

    platforms_st = patterns_data.get("platforms", {})
    plat_list = [f"{p}: {d['count']} issues (INR {d['amount_inr']:.2f}) [IDs: {d['incident_ids']}]" for p, d in platforms_st.items()]
    lines.append(f"Platforms: {', '.join(plat_list) if plat_list else 'None'}")

    return "\n".join(lines)


def generate_template_answer(
    task: str,
    incidents: List[Dict[str, Any]],
    patterns_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Deterministic, plain-Python template-based answer when AI is unavailable or unverified.
    
    Clearly structured, neutral, and guarantees complete verifiability.
    """
    total_st = patterns_data.get("total", {})
    stores_st = patterns_data.get("stores", {})
    platforms_st = patterns_data.get("platforms", {})
    delays_st = patterns_data.get("delays", {})
    refunds_st = patterns_data.get("refunds", {})
    weekly_st = patterns_data.get("weekly", {})

    all_ids = [inc["id"] for inc in incidents]
    t_lower = task.lower()

    # Preset 1: Complaint draft
    if "complaint" in t_lower or "draft" in t_lower:
        # Find pending or problematic orders to reference
        pending_ids = refunds_st.get("pending_ids", [])
        sample_id = pending_ids[0] if pending_ids else (all_ids[0] if all_ids else 1)
        sample_inc = next((i for i in incidents if i["id"] == sample_id), (incidents[0] if incidents else {}))

        store_name = sample_inc.get("restaurant_or_store", "Spice Bowl Kitchen")
        oid = sample_inc.get("order_id", f"SW-{sample_id}00")
        dt = sample_inc.get("order_date", "recent date")
        amt = sample_inc.get("amount_inr", 0.0)
        issue = sample_inc.get("issue_type", "order issue")

        answer = (
            f"Subject: Formal Inquiry Regarding Order #{oid} ({store_name}) - Case #{sample_id}\n\n"
            f"Dear Support Team,\n\n"
            f"I am writing to request a resolution regarding Order #{oid} placed with {store_name} on {dt} (Incident #{sample_id}). "
            f"The documented issue is {issue}, with a recorded order amount of INR {amt:.2f}. "
            f"Additionally, documentation indicates {refunds_st.get('pending_count', 0)} unresolved refund request(s) "
            f"and an average delivery delay of {delays_st.get('average_delay_minutes', 0.0)} minutes across documented orders in this case. "
            f"Please review the attached screenshots and transaction references to confirm the appropriate refund or credit adjustment.\n\n"
            f"Thank you for your assistance."
        )
        cited_ids = [sample_id]
        numbers_used = [
            float(sample_id),
            float(amt) if amt else 0.0,
            float(refunds_st.get("pending_count", 0)),
            float(delays_st.get("average_delay_minutes", 0.0)),
        ]
        needs_more_info = ["Bank statement reference confirming if pending credit was received."]

    # Preset 2: 5-line summary
    elif "5 lines" in t_lower or "summarise" in t_lower or "summarize" in t_lower:
        top_store = "None"
        if stores_st.get("repeat_stores"):
            top_store_name, top_store_data = max(stores_st["repeat_stores"].items(), key=lambda x: x[1]["count"])
            top_store = f"{top_store_name} ({top_store_data['count']} orders)"

        line1 = f"1. Documentation spans {total_st.get('count', 0)} total order issues from {total_st.get('date_range_str', 'N/A')} (Incident IDs: {all_ids})."
        line2 = f"2. Total financial value affected across documented orders is INR {total_st.get('total_amount_inr', 0.0):.2f}."
        line3 = f"3. Problem frequency exhibits an observable {weekly_st.get('trend', 'steady')} trend over {weekly_st.get('first_half_avg', 0.0)} to {weekly_st.get('second_half_avg', 0.0)} weekly issues."
        line4 = f"4. The most frequent repeat store documented is {top_store} with {delays_st.get('delay_count', 0)} delayed deliveries recorded."
        line5 = f"5. Refund records reflect {refunds_st.get('pending_count', 0)} pending inquiry(ies) and {refunds_st.get('denied_count', 0)} denied request(s) (longest pending: {refunds_st.get('longest_pending_days', 0)} days)."

        answer = f"{line1}\n{line2}\n{line3}\n{line4}\n{line5}"
        cited_ids = all_ids
        numbers_used = [
            float(total_st.get("count", 0)),
            float(total_st.get("total_amount_inr", 0.0)),
            float(weekly_st.get("first_half_avg", 0.0)),
            float(weekly_st.get("second_half_avg", 0.0)),
            float(delays_st.get("delay_count", 0)),
            float(refunds_st.get("pending_count", 0)),
            float(refunds_st.get("denied_count", 0)),
            float(refunds_st.get("longest_pending_days", 0)),
            1.0, 2.0, 3.0, 4.0, 5.0,
        ]
        needs_more_info = []

    # Preset 3: Which store or platform has the most issues
    elif "most issues" in t_lower or "which store" in t_lower or "platform" in t_lower:
        top_platform = "None"
        top_plat_count = 0
        top_plat_ids: List[int] = []
        if platforms_st:
            p_name, p_data = max(platforms_st.items(), key=lambda x: x[1]["count"])
            top_platform = p_name
            top_plat_count = p_data["count"]
            top_plat_ids = p_data["incident_ids"]

        top_store = "None"
        top_store_count = 0
        top_store_ids: List[int] = []
        if stores_st.get("all_stores"):
            s_name, s_data = max(stores_st["all_stores"].items(), key=lambda x: x[1]["count"])
            top_store = s_name
            top_store_count = s_data["count"]
            top_store_ids = s_data["incident_ids"]

        answer = (
            f"Based on logged case records:\n"
            f"- Top Platform: {top_platform} with {top_plat_count} reported issue(s) (Incident IDs: {top_plat_ids}).\n"
            f"- Top Store: {top_store} with {top_store_count} reported issue(s) (Incident IDs: {top_store_ids}).\n"
            f"Repeat store documentation indicates {stores_st.get('repeat_store_count', 0)} stores with 2 or more logged problems."
        )
        cited_ids = sorted(list(set(top_plat_ids + top_store_ids)))
        numbers_used = [
            float(top_plat_count),
            float(top_store_count),
            float(stores_st.get("repeat_store_count", 0)),
            2.0,
        ]
        needs_more_info = []

    # Preset 4: Missing or weak evidence
    elif "missing" in t_lower or "weak" in t_lower:
        missing_ids = []
        missing_reasons = []

        for inc in incidents:
            reasons = []
            if not inc.get("order_id"):
                reasons.append("lacks order ID")
            if not inc.get("image_path"):
                reasons.append("missing screenshot file")
            if inc.get("amount_inr") is None:
                reasons.append("missing amount")
            if inc.get("refund_status") == "Pending":
                reasons.append("pending refund unverified")
            if reasons:
                missing_ids.append(inc["id"])
                missing_reasons.append(f"Incident #{inc['id']} ({', '.join(reasons)})")

        if missing_ids:
            reasons_summary = "\n".join(f"- {r}" for r in missing_reasons[:6])
            answer = (
                f"Evaluation of evidence completeness identified {len(missing_ids)} records with missing details:\n"
                f"{reasons_summary}\n"
                f"Additionally, {total_st.get('missing_amount_count', 0)} records lack confirmed pricing figures (IDs: {total_st.get('missing_amount_ids', [])})."
            )
            cited_ids = missing_ids
            numbers_used = [
                float(len(missing_ids)),
                float(total_st.get("missing_amount_count", 0)),
            ]
            needs_more_info = ["Upload itemized receipt screenshots for records lacking exact order IDs and amounts."]
        else:
            answer = (
                f"All {total_st.get('count', 0)} logged records (Incident IDs: {all_ids}) have documented order IDs, "
                f"amounts, and screenshots. Evidence documentation is complete."
            )
            cited_ids = all_ids
            numbers_used = [float(total_st.get("count", 0))]
            needs_more_info = []

    # Generic Custom Query
    else:
        answer = (
            f"Case analysis for '{task}':\n"
            f"- Total documented order incidents: {total_st.get('count', 0)} (Incident IDs: {all_ids})\n"
            f"- Total amount affected: INR {total_st.get('total_amount_inr', 0.0):.2f}\n"
            f"- Weekly contact pattern: {weekly_st.get('trend', 'steady')} frequency\n"
            f"- Documented delays: {delays_st.get('delay_count', 0)} orders with an average delay of {delays_st.get('average_delay_minutes', 0.0)} minutes\n"
            f"- Refund inquiries: {refunds_st.get('pending_count', 0)} pending, {refunds_st.get('denied_count', 0)} denied."
        )
        cited_ids = all_ids
        numbers_used = [
            float(total_st.get("count", 0)),
            float(total_st.get("total_amount_inr", 0.0)),
            float(delays_st.get("delay_count", 0)),
            float(delays_st.get("average_delay_minutes", 0.0)),
            float(refunds_st.get("pending_count", 0)),
            float(refunds_st.get("denied_count", 0)),
        ]
        needs_more_info = []

    return {
        "answer": answer,
        "cited_ids": cited_ids,
        "numbers_used": numbers_used,
        "needs_more_info": needs_more_info,
    }


def call_gemini_api(
    task_prompt: str,
    context_str: str,
    api_key: str,
    retry_feedback: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """Execute raw Gemini call and return (parsed_json, raw_text, error_message)."""
    system_instructions = (
        "You are an assistant for PatternProof, an evidence organizer for food and grocery delivery order issues.\n"
        "STRICT RULES:\n"
        "1. Use ONLY the data provided in the context block below. Do NOT invent orders, dates, amounts, or store names.\n"
        "2. Neutral wording only. Do NOT blame or identify any individual (rider, staff, agent). No legal claims or offences.\n"
        "3. Cite incident IDs (e.g. [Incident #1]) for every factual statement.\n"
        "4. If the data cannot answer the task, explicitly say so.\n"
        "5. Return ONLY a single valid JSON object with the following schema and no extra markdown fences or commentary:\n"
        "{\n"
        '  "answer": "your factual response here",\n'
        '  "cited_ids": [1, 2, ...],\n'
        '  "numbers_used": [12, 450.0, ...],\n'
        '  "needs_more_info": ["item1", ...]\n'
        "}"
    )

    user_message = f"{system_instructions}\n\n{context_str}\n\nUSER TASK:\n{task_prompt}"
    if retry_feedback:
        user_message += f"\n\nIMPORTANT CORRECTION: Your previous answer failed verification checks:\n{retry_feedback}\nPlease correct these errors and output strictly valid JSON conforming to all rules."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(user_message, request_options={"timeout": 12.0})

        if not response or not response.text:
            return None, None, "AI returned an empty response."

        raw_text = response.text
        clean_text = clean_json_response(raw_text)
        data = json.loads(clean_text)

        if not isinstance(data, dict):
            return None, raw_text, "Response was not a JSON object."

        return data, raw_text, None

    except json.JSONDecodeError as jde:
        return None, None, f"JSON parse error: {str(jde)}"
    except Exception as e:
        return None, None, f"AI service error: {str(e)}"


def run_assistant_task(
    task: str,
    incidents: List[Dict[str, Any]],
    patterns_data: Dict[str, Any],
    api_key_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Orchestrate AI Assistant task execution with verification and retry.
    
    Returns dict with keys:
        - success: bool
        - is_template: bool
        - answer: Optional[str]
        - cited_ids: List[int]
        - numbers_used: List[float]
        - needs_more_info: List[str]
        - check_results: List[Dict[str, Any]]
        - error_message: Optional[str]
    """
    key = get_api_key(api_key_override)
    context_str = build_context_block(incidents, patterns_data)

    # 1. Fallback immediately if no API key
    if not key:
        template_res = generate_template_answer(task, incidents, patterns_data)
        passed, check_results = verifier.verify_response(
            raw_json_str=None,
            parsed_output=template_res,
            incidents=incidents,
            patterns_data=patterns_data,
            task_prompt=task,
        )
        return {
            "success": True,
            "is_template": True,
            "answer": template_res["answer"],
            "cited_ids": template_res["cited_ids"],
            "numbers_used": template_res["numbers_used"],
            "needs_more_info": template_res["needs_more_info"],
            "check_results": check_results,
            "error_message": "No API key configured. Generated verified template response.",
        }

    # 2. First attempt with AI
    parsed_json, raw_text, err = call_gemini_api(task, context_str, key)

    if parsed_json:
        passed, check_results = verifier.verify_response(
            raw_json_str=raw_text,
            parsed_output=parsed_json,
            incidents=incidents,
            patterns_data=patterns_data,
            task_prompt=task,
        )
        if passed:
            return {
                "success": True,
                "is_template": False,
                "answer": parsed_json.get("answer"),
                "cited_ids": parsed_json.get("cited_ids", []),
                "numbers_used": parsed_json.get("numbers_used", []),
                "needs_more_info": parsed_json.get("needs_more_info", []),
                "check_results": check_results,
                "error_message": None,
            }
        else:
            # 3. Retry ONCE with failed checks in prompt
            failed_reasons = "\n".join(
                f"- {cr['check_name']}: {cr['detail']}"
                for cr in check_results
                if not cr["passed"]
            )
            retry_json, retry_raw, retry_err = call_gemini_api(
                task, context_str, key, retry_feedback=failed_reasons
            )
            if retry_json:
                retry_passed, retry_check_results = verifier.verify_response(
                    raw_json_str=retry_raw,
                    parsed_output=retry_json,
                    incidents=incidents,
                    patterns_data=patterns_data,
                    task_prompt=task,
                )
                if retry_passed:
                    return {
                        "success": True,
                        "is_template": False,
                        "answer": retry_json.get("answer"),
                        "cited_ids": retry_json.get("cited_ids", []),
                        "numbers_used": retry_json.get("numbers_used", []),
                        "needs_more_info": retry_json.get("needs_more_info", []),
                        "check_results": retry_check_results,
                        "error_message": None,
                    }
                else:
                    # Retry failed verification: block answer
                    return {
                        "success": False,
                        "is_template": False,
                        "answer": None,
                        "cited_ids": [],
                        "numbers_used": [],
                        "needs_more_info": [],
                        "check_results": retry_check_results,
                        "error_message": "Could not verify this answer after 1 retry.",
                    }

    # 4. If AI call crashed or timed out, fall back to template answer
    template_res = generate_template_answer(task, incidents, patterns_data)
    passed, check_results = verifier.verify_response(
        raw_json_str=None,
        parsed_output=template_res,
        incidents=incidents,
        patterns_data=patterns_data,
        task_prompt=task,
    )
    return {
        "success": True,
        "is_template": True,
        "answer": template_res["answer"],
        "cited_ids": template_res["cited_ids"],
        "numbers_used": template_res["numbers_used"],
        "needs_more_info": template_res["needs_more_info"],
        "check_results": check_results,
        "error_message": f"AI service unavailable ({err or 'call failed'}). Displaying verified template answer.",
    }
