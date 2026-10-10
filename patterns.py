"""Pattern analysis engine for PatternProof (Delivery Order Issues).

All statistics, weekly trends, store frequency, delays, and refund summaries
are computed using deterministic Python code. No AI is used in this module.
Every metric maintains full traceability by listing the incident/order IDs behind it.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Safely parse YYYY-MM-DD date string to a date object."""
    if not date_str or not str(date_str).strip():
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def analyze_patterns(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute observable patterns across delivery order issues.
    
    Returns structured metrics where every statistic is accompanied by
    the exact incident IDs behind it.
    """
    total_count = len(incidents)
    all_ids = [inc["id"] for inc in incidents]

    # 1. Date separation
    dated_incidents = []
    undated_incidents = []

    for inc in incidents:
        d = parse_date(inc.get("order_date"))
        if d:
            dated_incidents.append((d, inc))
        else:
            undated_incidents.append(inc)

    dated_incidents.sort(key=lambda x: (x[0], x[1]["id"]))
    dated_ids = [inc["id"] for _, inc in dated_incidents]
    undated_ids = [inc["id"] for inc in undated_incidents]

    if dated_incidents:
        min_date = dated_incidents[0][0]
        max_date = dated_incidents[-1][0]
        date_span_days = (max_date - min_date).days + 1
        date_range_str = f"{min_date.isoformat()} to {max_date.isoformat()}"
    else:
        min_date = None
        max_date = None
        date_span_days = 0
        date_range_str = "No dates recorded"

    # 2. Financial calculation: total amount_inr affected
    amount_ids = []
    missing_amount_ids = []
    total_amount_inr = 0.0

    for inc in incidents:
        amt = inc.get("amount_inr")
        if amt is not None and str(amt).strip() != "":
            try:
                val = float(amt)
                total_amount_inr += val
                amount_ids.append(inc["id"])
            except (ValueError, TypeError):
                missing_amount_ids.append(inc["id"])
        else:
            missing_amount_ids.append(inc["id"])

    total_stats = {
        "count": total_count,
        "incident_ids": all_ids,
        "dated_count": len(dated_incidents),
        "dated_incident_ids": dated_ids,
        "undated_count": len(undated_incidents),
        "undated_incident_ids": undated_ids,
        "date_range_str": date_range_str,
        "min_date": min_date.isoformat() if min_date else None,
        "max_date": max_date.isoformat() if max_date else None,
        "span_days": date_span_days,
        "total_amount_inr": round(total_amount_inr, 2),
        "amount_incident_ids": amount_ids,
        "missing_amount_count": len(missing_amount_ids),
        "missing_amount_ids": missing_amount_ids,
    }

    # 3. Weekly trend calculation
    if len(dated_incidents) < 3 or not min_date or not max_date:
        weekly_stats = {
            "has_trend": False,
            "trend": "not enough data for a trend",
            "trend_message": "Requires at least 3 dated orders to evaluate a weekly trend.",
            "weeks": [],
            "first_half_avg": 0.0,
            "second_half_avg": 0.0,
            "first_half_count": 0,
            "second_half_count": 0,
            "first_half_ids": [],
            "second_half_ids": [],
        }
    else:
        start_monday = min_date - timedelta(days=min_date.weekday())
        end_sunday = max_date + timedelta(days=(6 - max_date.weekday()))

        weeks_list = []
        current_monday = start_monday
        week_num = 1
        while current_monday <= end_sunday:
            current_sunday = current_monday + timedelta(days=6)
            week_incidents = [
                inc["id"]
                for d, inc in dated_incidents
                if current_monday <= d <= current_sunday
            ]
            weeks_list.append({
                "week_index": week_num,
                "label": f"W{week_num} ({current_monday.strftime('%b %d')} - {current_sunday.strftime('%b %d')})",
                "start": current_monday.isoformat(),
                "end": current_sunday.isoformat(),
                "count": len(week_incidents),
                "incident_ids": week_incidents,
            })
            current_monday += timedelta(days=7)
            week_num += 1

        num_weeks = len(weeks_list)
        if num_weeks < 2:
            trend = "no clear change"
            trend_msg = "All dated records fall within a single week period."
            fh_count = len(dated_incidents)
            sh_count = len(dated_incidents)
            fh_avg = float(fh_count)
            sh_avg = float(sh_count)
            fh_ids = dated_ids
            sh_ids = dated_ids
        else:
            mid = num_weeks // 2
            first_half = weeks_list[:mid]
            second_half = weeks_list[mid:]

            fh_count = sum(w["count"] for w in first_half)
            sh_count = sum(w["count"] for w in second_half)
            fh_avg = round(fh_count / len(first_half), 2)
            sh_avg = round(sh_count / len(second_half), 2)
            fh_ids = [iid for w in first_half for iid in w["incident_ids"]]
            sh_ids = [iid for w in second_half for iid in w["incident_ids"]]

            diff = sh_avg - fh_avg
            if diff > 0.15:
                trend = "increasing"
                trend_msg = f"Average weekly issues increased from {fh_avg} (first half) to {sh_avg} (second half)."
            elif diff < -0.15:
                trend = "decreasing"
                trend_msg = f"Average weekly issues decreased from {fh_avg} (first half) to {sh_avg} (second half)."
            else:
                trend = "no clear change"
                trend_msg = f"Average weekly issues remained steady ({fh_avg} vs {sh_avg})."

        weekly_stats = {
            "has_trend": True,
            "trend": trend,
            "trend_message": trend_msg,
            "weeks": weeks_list,
            "first_half_avg": fh_avg,
            "second_half_avg": sh_avg,
            "first_half_count": fh_count,
            "second_half_count": sh_count,
            "first_half_ids": fh_ids,
            "second_half_ids": sh_ids,
        }

    # 4. Issues by Platform
    platforms_map: Dict[str, Dict[str, Any]] = {}
    for inc in incidents:
        p = inc.get("platform") or "Unspecified"
        if p not in platforms_map:
            platforms_map[p] = {"count": 0, "amount_inr": 0.0, "incident_ids": []}
        platforms_map[p]["count"] += 1
        platforms_map[p]["incident_ids"].append(inc["id"])
        amt = inc.get("amount_inr")
        if amt is not None:
            try:
                platforms_map[p]["amount_inr"] += float(amt)
            except (ValueError, TypeError):
                pass
    for p in platforms_map:
        platforms_map[p]["amount_inr"] = round(platforms_map[p]["amount_inr"], 2)

    # 5. Issues by Issue Type
    issue_types_map: Dict[str, Dict[str, Any]] = {}
    for inc in incidents:
        it = inc.get("issue_type") or "Other"
        if it not in issue_types_map:
            issue_types_map[it] = {"count": 0, "incident_ids": []}
        issue_types_map[it]["count"] += 1
        issue_types_map[it]["incident_ids"].append(inc["id"])

    # 6. Repeat Store: stores with 2+ issues
    stores_map: Dict[str, Dict[str, Any]] = {}
    for inc in incidents:
        s = inc.get("restaurant_or_store") or "Store Not Specified"
        if s not in stores_map:
            stores_map[s] = {"count": 0, "incident_ids": []}
        stores_map[s]["count"] += 1
        stores_map[s]["incident_ids"].append(inc["id"])

    repeat_stores = {
        s: data for s, data in stores_map.items() if data["count"] >= 2
    }
    repeat_store_ids = [iid for s in repeat_stores.values() for iid in s["incident_ids"]]

    repeat_store_stats = {
        "repeat_stores": repeat_stores,
        "repeat_store_count": len(repeat_stores),
        "all_stores": stores_map,
        "repeat_store_ids": repeat_store_ids,
    }

    # 7. Delivery Delay Analysis (actual_minutes - promised_minutes)
    delay_records = []
    for inc in incidents:
        actual = inc.get("actual_minutes")
        promised = inc.get("promised_minutes")
        if actual is not None and promised is not None:
            try:
                act_val = int(actual)
                prom_val = int(promised)
                diff = act_val - prom_val
                if diff > 0:
                    delay_records.append({
                        "id": inc["id"],
                        "store": inc.get("restaurant_or_store") or "",
                        "promised": prom_val,
                        "actual": act_val,
                        "delay_minutes": diff,
                    })
            except (ValueError, TypeError):
                pass

    if delay_records:
        delays = [d["delay_minutes"] for d in delay_records]
        avg_delay = round(sum(delays) / len(delays), 1)
        max_delay = max(delays)
        delay_ids = [d["id"] for d in delay_records]
        max_delay_ids = [d["id"] for d in delay_records if d["delay_minutes"] == max_delay]
        delay_stats = {
            "has_delays": True,
            "delay_count": len(delay_records),
            "average_delay_minutes": avg_delay,
            "max_delay_minutes": max_delay,
            "incident_ids": delay_ids,
            "max_delay_ids": max_delay_ids,
            "records": delay_records,
        }
    else:
        delay_stats = {
            "has_delays": False,
            "delay_count": 0,
            "average_delay_minutes": 0,
            "max_delay_minutes": 0,
            "incident_ids": [],
            "max_delay_ids": [],
            "records": [],
        }

    # 8. Refund Analysis (count of Pending / Denied / Partial, longest pending age)
    refund_counts: Dict[str, Dict[str, Any]] = {
        "Pending": {"count": 0, "incident_ids": []},
        "Denied": {"count": 0, "incident_ids": []},
        "Partial": {"count": 0, "incident_ids": []},
        "Full": {"count": 0, "incident_ids": []},
        "None requested": {"count": 0, "incident_ids": []},
    }

    pending_with_dates = []

    reference_date = max_date or date.today()

    for inc in incidents:
        st_val = inc.get("refund_status") or "None requested"
        if st_val not in refund_counts:
            refund_counts[st_val] = {"count": 0, "incident_ids": []}
        refund_counts[st_val]["count"] += 1
        refund_counts[st_val]["incident_ids"].append(inc["id"])

        if st_val == "Pending":
            d = parse_date(inc.get("order_date"))
            if d:
                age_days = (reference_date - d).days
                pending_with_dates.append({
                    "id": inc["id"],
                    "order_date": d.isoformat(),
                    "age_days": max(0, age_days),
                })

    if pending_with_dates:
        longest_pending_entry = max(pending_with_dates, key=lambda x: x["age_days"])
        longest_pending_days = longest_pending_entry["age_days"]
        longest_pending_ids = [
            x["id"] for x in pending_with_dates if x["age_days"] == longest_pending_days
        ]
    else:
        longest_pending_days = 0
        longest_pending_ids = []

    refund_stats = {
        "counts": refund_counts,
        "pending_count": refund_counts["Pending"]["count"],
        "pending_ids": refund_counts["Pending"]["incident_ids"],
        "denied_count": refund_counts["Denied"]["count"],
        "denied_ids": refund_counts["Denied"]["incident_ids"],
        "partial_count": refund_counts["Partial"]["count"],
        "partial_ids": refund_counts["Partial"]["incident_ids"],
        "longest_pending_days": longest_pending_days,
        "longest_pending_ids": longest_pending_ids,
    }

    # 9. Link Groups
    groups_map: Dict[str, Dict[str, Any]] = {}
    for inc in incidents:
        g = inc.get("link_group") or "Unassigned"
        if g not in groups_map:
            groups_map[g] = {"count": 0, "incident_ids": []}
        groups_map[g]["count"] += 1
        groups_map[g]["incident_ids"].append(inc["id"])

    return {
        "total": total_stats,
        "weekly": weekly_stats,
        "platforms": platforms_map,
        "issue_types": issue_types_map,
        "stores": repeat_store_stats,
        "delays": delay_stats,
        "refunds": refund_stats,
        "link_groups": groups_map,
    }
