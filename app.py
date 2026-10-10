"""PatternProof - Delivery Order Complaint & Evidence Organizer.

Main Streamlit Application (UI Only).
Coordinates db.py, patterns.py, ai.py, report.py, and demo_data.py.
Follows all hard rules: strictly neutral language, traceable order IDs, no blame assignment.
"""

import os
import hashlib
import datetime
import pandas as pd
import streamlit as st

import db
import patterns
import ai
import report
import demo_data
import ai_assistant
import verifier

# Page Configuration
st.set_page_config(
    page_title="PatternProof",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Mandatory Disclaimer constant
DISCLAIMER_TEXT = (
    "PatternProof organises user-provided evidence. "
    "It does not verify authenticity, assign blame, or provide legal advice."
)

# Custom CSS for polished, high-contrast modern UI with #FF5C1F accent
st.markdown(
    """
    <style>
    /* Metric Card Styling */
    .metric-card {
        background-color: #1A1F2C;
        border: 1px solid #2D3748;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .metric-card:hover {
        border-color: #FF5C1F;
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #F8FAFC;
        font-size: 1.6rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .metric-trace {
        color: #FF5C1F;
        font-size: 0.8rem;
        font-weight: 500;
        background: rgba(255, 92, 31, 0.12);
        padding: 3px 8px;
        border-radius: 4px;
        display: inline-block;
    }
    .metric-sub {
        color: #94A3B8;
        font-size: 0.82rem;
        margin-top: 6px;
    }
    /* Neutral Disclaimer Banner */
    .disclaimer-banner {
        background-color: #161B26;
        border-left: 4px solid #FF5C1F;
        padding: 10px 16px;
        border-radius: 4px;
        margin: 12px 0 20px 0;
        font-size: 0.85rem;
        color: #CBD5E1;
    }
    /* Footer */
    .app-footer {
        text-align: center;
        padding: 24px 0 10px 0;
        border-top: 1px solid #2D3748;
        margin-top: 40px;
        font-size: 0.82rem;
        color: #94A3B8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize database
db.init_db()


def get_file_hash(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    return hasher.hexdigest()


# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📦 **PatternProof**")
    st.caption("Delivery Order Evidence & Complaint Organizer")

    # Case Selector
    case_names = db.get_case_names()
    if "current_case" not in st.session_state:
        st.session_state.current_case = case_names[0] if case_names else "Demo Case - Food & Grocery Orders"

    selected_case = st.selectbox(
        "Active Order Record:",
        options=case_names + ["+ Create New Case..."],
        index=case_names.index(st.session_state.current_case) if st.session_state.current_case in case_names else 0,
    )

    if selected_case == "+ Create New Case...":
        new_case_input = st.text_input("Enter New Case Name:")
        if st.button("Set Case", key="btn_create_case", width="stretch"):
            if new_case_input.strip():
                st.session_state.current_case = new_case_input.strip()
                st.rerun()
    else:
        st.session_state.current_case = selected_case

    st.divider()

    # Load Demo Case
    st.markdown("### Demo Actions")
    if st.button("📥 Load Demo Case", width="stretch", help="Load 12 fictional food & grocery order records"):
        count = demo_data.load_demo_case(case_name="Demo Case - Food & Grocery Orders")
        st.session_state.current_case = "Demo Case - Food & Grocery Orders"
        st.success(f"Loaded {count} fictional order records.")
        st.rerun()

    # Delete Data
    with st.expander("🗑️ Delete Data", expanded=False):
        st.warning("Irreversible action. Deletes logged records.")
        confirm_del_case = st.checkbox("Confirm delete active case only")
        if st.button("Delete Active Case Records", type="secondary", width="stretch"):
            if confirm_del_case:
                db.delete_all_incidents(case_name=st.session_state.current_case)
                st.success(f"Records for '{st.session_state.current_case}' deleted.")
                st.rerun()
            else:
                st.error("Please check the confirmation box.")

        confirm_del_all = st.checkbox("Confirm delete ALL cases")
        if st.button("Delete Entire Database", type="secondary", width="stretch"):
            if confirm_del_all:
                db.delete_all_incidents()
                st.success("All database records cleared.")
                st.rerun()
            else:
                st.error("Please check the confirmation box.")

    st.divider()

    # System Status & Local Privacy Note
    api_key_set = bool(ai.get_api_key())
    if api_key_set:
        st.success("🟢 Gemini AI: Configured (ready for receipt transcription)")
    else:
        st.info("🟡 Gemini AI: Not configured (manual entry is active)")

    st.caption("🔒 **Device Privacy**: All screenshots, file hashes, and order records stay strictly stored on this local computer.")


# -------------------------------------------------------------
# MAIN APP HEADER & TABS
# -------------------------------------------------------------
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <div>
            <h1 style="margin-bottom: 2px;">PatternProof</h1>
            <p style="color: #94A3B8; font-size: 1rem; margin-top: 0;">
                Delivery Order Evidence, Timeline & Complaint Report Organizer
            </p>
        </div>
        <div>
            <span style="background: #1A1F2C; border: 1px solid #FF5C1F; color: #F8FAFC; padding: 6px 14px; border-radius: 6px; font-weight: 600;">
                Case: {st.session_state.current_case}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Mandatory disclaimer banner
st.markdown(f'<div class="disclaimer-banner">⚖️ <strong>Notice:</strong> {DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)

# Fetch incidents for current case
incidents = db.get_incidents(case_name=st.session_state.current_case)

# 5 Tabs: Add Incident, Timeline, Patterns, Report, AI Assistant
tab_add, tab_timeline, tab_patterns, tab_report, tab_assistant = st.tabs([
    "➕ Add Incident",
    "📅 Timeline",
    "📊 Patterns",
    "📄 Report",
    "🤖 AI Assistant",
])


# -------------------------------------------------------------
# TAB 1: ADD INCIDENT
# -------------------------------------------------------------
with tab_add:
    st.subheader("Record Delivery Order Evidence")
    st.caption("Upload an order receipt or support chat screenshot. Gemini suggests fields. You review and edit everything before saving.")

    uploaded_file = st.file_uploader(
        "Upload order evidence screenshot (PNG or JPG):",
        type=["png", "jpg", "jpeg"],
        key="order_file_uploader",
    )

    if "ai_suggestion" not in st.session_state:
        st.session_state.ai_suggestion = None
    if "ai_warnings" not in st.session_state:
        st.session_state.ai_warnings = []
    if "uploaded_file_path" not in st.session_state:
        st.session_state.uploaded_file_path = ""
    if "uploaded_file_hash" not in st.session_state:
        st.session_state.uploaded_file_hash = ""

    current_hash = ""
    saved_path = ""

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        current_hash = get_file_hash(file_bytes)
        os.makedirs(demo_data.UPLOADS_DIR, exist_ok=True)
        filename = f"order_{current_hash[:12]}_{uploaded_file.name}"
        saved_path = os.path.join(demo_data.UPLOADS_DIR, filename)

        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        st.session_state.uploaded_file_path = saved_path
        st.session_state.uploaded_file_hash = current_hash

        col_img, col_ai = st.columns([1, 1])
        with col_img:
            st.image(uploaded_file, caption=f"Uploaded: {uploaded_file.name}", width="stretch")
            st.code(f"SHA-256: {current_hash}", language="text")

        with col_ai:
            st.markdown("#### Automated Assistant")
            st.markdown(
                "Gemini reads visible order receipts or chat screenshots and suggests fields. "
                "All suggestions require your review before saving."
            )

            custom_key = st.text_input(
                "Gemini API Key (optional override):",
                type="password",
                value="",
                placeholder="Leave blank to use .env key",
            )

            if st.button("🤖 Read with AI", width="stretch"):
                with st.spinner("Reading screenshot..."):
                    ai_result, friendly_err, tech_err = ai.transcribe_order_screenshot(saved_path, api_key=custom_key)
                    if ai_result:
                        val_warnings = []
                        # 1. Date check: real YYYY-MM-DD and not in future
                        r_date = ai_result.get("order_date")
                        if r_date:
                            try:
                                parsed_d = datetime.date.fromisoformat(r_date.strip())
                                if parsed_d > datetime.date.today():
                                    val_warnings.append(f"Date '{r_date}' is in the future. Field cleared.")
                                    ai_result["order_date"] = None
                            except (ValueError, TypeError):
                                val_warnings.append(f"Date '{r_date}' is not a valid YYYY-MM-DD. Field cleared.")
                                ai_result["order_date"] = None

                        # 2. Issue type check: in allowed list
                        r_issue = ai_result.get("issue_type")
                        if r_issue and r_issue not in db.VALID_ISSUE_TYPES:
                            val_warnings.append(f"Issue type '{r_issue}' is not in allowed list. Field cleared.")
                            ai_result["issue_type"] = None

                        # 3. Amount check: positive number
                        r_amt = ai_result.get("amount_inr")
                        if r_amt is not None:
                            try:
                                num_amt = float(r_amt)
                                if num_amt <= 0:
                                    val_warnings.append("Amount must be a positive number. Field cleared.")
                                    ai_result["amount_inr"] = None
                            except (ValueError, TypeError):
                                val_warnings.append("Amount could not be parsed as a positive number. Field cleared.")
                                ai_result["amount_inr"] = None

                        # 4. Platform check: non-empty string
                        r_plat = ai_result.get("platform")
                        if not r_plat or not str(r_plat).strip():
                            val_warnings.append("Platform name was empty. Field cleared.")
                            ai_result["platform"] = None

                        st.session_state.ai_suggestion = ai_result
                        st.session_state.ai_warnings = val_warnings
                        if val_warnings:
                            st.warning("⚠️ Field Validation Warnings:\n" + "\n".join(f"- {w}" for w in val_warnings))
                        st.success("Screenshot transcribed successfully! Pre-filled fields below for your review.")
                    else:
                        st.warning(friendly_err or "Gemini is slow right now. Please try again, or enter the details manually.")
                        if tech_err:
                            with st.expander("Technical details", expanded=False):
                                st.code(tech_err)

    st.markdown("---")
    st.markdown("### Order Incident Details (Review & Edit)")
    if st.session_state.get("ai_warnings"):
        for w in st.session_state.ai_warnings:
            st.caption(f"⚠️ {w}")

    sug = st.session_state.ai_suggestion or {}
    default_date = sug.get("order_date") or ""
    default_platform = sug.get("platform") or "Swiggy"
    default_store = sug.get("restaurant_or_store") or ""
    default_order_id = sug.get("order_id") or ""
    default_amount = sug.get("amount_inr") if sug.get("amount_inr") is not None else 0.0
    default_issue = sug.get("issue_type") or "Late delivery"
    default_text = sug.get("extracted_text") or ""

    platform_options = ["Swiggy", "Zomato", "Blinkit", "Zepto", "Amazon", "BigBasket", "Instamart", "Other"]
    plat_idx = platform_options.index(default_platform) if default_platform in platform_options else 0

    issue_options = db.VALID_ISSUE_TYPES
    issue_idx = issue_options.index(default_issue) if default_issue in issue_options else 0

    refund_options = db.VALID_REFUND_STATUSES

    with st.form("add_order_incident_form", clear_on_submit=False):
        c1, c2 = st.columns([1, 1])

        with c1:
            case_input = st.text_input("Case Name:", value=st.session_state.current_case)
            date_input = st.text_input("Order Date (YYYY-MM-DD or leave blank if unknown):", value=default_date)
            platform_input = st.selectbox("Platform:", options=platform_options, index=plat_idx)
            store_input = st.text_input("Restaurant or Store:", value=default_store, placeholder="e.g. Spice Bowl Kitchen")
            order_id_input = st.text_input("Order ID (Optional):", value=default_order_id, placeholder="e.g. SW-9021")
            issue_type_input = st.selectbox("Issue Type:", options=issue_options, index=issue_idx)
            amount_input = st.number_input("Amount (INR):", min_value=0.0, value=float(default_amount), step=10.0)

        with c2:
            time_c1, time_c2 = st.columns(2)
            with time_c1:
                promised_min_input = st.number_input("Promised Minutes (Optional):", min_value=0, value=0, step=5)
            with time_c2:
                actual_min_input = st.number_input("Actual Arrival Minutes (Optional):", min_value=0, value=0, step=5)

            refund_status_input = st.selectbox("Refund Status:", options=refund_options, index=0)
            link_group_input = st.text_input("Link Group (Optional):", value="", placeholder="e.g. Spice Bowl Kitchen Order Chain")
            extracted_text_input = st.text_area("Extracted Visible Text:", value=default_text, height=95)
            notes_input = st.text_area("Neutral Notes & Context:", value="Order marked delivered; support interaction recorded.", height=65)

        submit_save = st.form_submit_button("💾 Save Order Incident", width="stretch")

        if submit_save:
            amt_to_save = float(amount_input) if amount_input > 0 else None
            prom_to_save = int(promised_min_input) if promised_min_input > 0 else None
            act_to_save = int(actual_min_input) if actual_min_input > 0 else None

            new_id = db.add_incident(
                case_name=case_input.strip() or st.session_state.current_case,
                order_date=date_input.strip() if date_input.strip() else None,
                platform=platform_input,
                restaurant_or_store=store_input.strip() or "Store Not Specified",
                order_id=order_id_input.strip() if order_id_input.strip() else None,
                issue_type=issue_type_input,
                amount_inr=amt_to_save,
                promised_minutes=prom_to_save,
                actual_minutes=act_to_save,
                refund_status=refund_status_input,
                extracted_text=extracted_text_input,
                notes=notes_input,
                image_path=st.session_state.uploaded_file_path or saved_path,
                file_hash=st.session_state.uploaded_file_hash or current_hash,
                link_group=link_group_input.strip() if link_group_input.strip() else None,
            )
            st.session_state.current_case = case_input.strip() or st.session_state.current_case
            st.session_state.ai_suggestion = None
            st.session_state.uploaded_file_path = ""
            st.session_state.uploaded_file_hash = ""
            st.success(f"Order Incident #{new_id} successfully saved to case '{st.session_state.current_case}'!")
            st.rerun()


# -------------------------------------------------------------
# TAB 2: TIMELINE
# -------------------------------------------------------------
with tab_timeline:
    st.subheader("Chronological Order Issue Timeline")

    if not incidents:
        st.info("No order incidents recorded in this case. Click 'Load Demo Case' in the sidebar or record an incident above.")
    else:
        # Filters: Link Group and Platform
        available_groups = db.get_link_groups(case_name=st.session_state.current_case)
        available_platforms = db.get_platforms(case_name=st.session_state.current_case)

        f_col1, f_col2 = st.columns(2)
        with f_col1:
            selected_group_filter = st.selectbox(
                "Filter by Link Group:",
                options=["All Groups"] + available_groups,
                index=0,
            )
        with f_col2:
            selected_plat_filter = st.selectbox(
                "Filter by Platform:",
                options=["All Platforms"] + available_platforms,
                index=0,
            )

        # Apply filtering
        display_incidents = [
            inc for inc in incidents
            if (selected_group_filter == "All Groups" or inc.get("link_group") == selected_group_filter)
            and (selected_plat_filter == "All Platforms" or inc.get("platform") == selected_plat_filter)
        ]

        # Separate dated vs undated
        dated_incidents = [inc for inc in display_incidents if inc.get("order_date") and inc["order_date"].strip()]
        undated_incidents = [inc for inc in display_incidents if not inc.get("order_date") or not inc["order_date"].strip()]

        # Weekly Bar Chart
        if dated_incidents:
            st.markdown("#### Weekly Issue Frequency")
            analysis_data = patterns.analyze_patterns(dated_incidents)
            weekly_list = analysis_data["weekly"]["weeks"]

            if weekly_list:
                chart_df = pd.DataFrame([
                    {"Week": w["label"], "Reported Issues": w["count"]}
                    for w in weekly_list
                ])
                st.bar_chart(chart_df, x="Week", y="Reported Issues", color="#FF5C1F")

        # Multi-select to assign link groups
        with st.expander("🔗 Assign Selected Orders to a Link Group", expanded=False):
            st.markdown("Group related orders (e.g. recurring issues from the same restaurant or grocery order chain).")
            lg_c1, lg_c2, lg_c3 = st.columns([2, 2, 1])
            with lg_c1:
                selected_ids = st.multiselect(
                    "Select Order Incident IDs:",
                    options=[inc["id"] for inc in display_incidents],
                    format_func=lambda i: f"Order #{i} • {next((x['restaurant_or_store'] for x in display_incidents if x['id'] == i), '')} ({next((x['order_date'] or 'No date' for x in display_incidents if x['id'] == i), '')})",
                )
            with lg_c2:
                target_link_group = st.text_input("Link Group Name:")
            with lg_c3:
                st.write("")
                st.write("")
                if st.button("Apply Link", width="stretch"):
                    if selected_ids and target_link_group.strip():
                        updated_count = db.update_link_groups_for_ids(selected_ids, target_link_group.strip())
                        st.success(f"Assigned {updated_count} incidents to link group '{target_link_group.strip()}'.")
                        st.rerun()
                    else:
                        st.warning("Please choose incidents and specify a group name.")

        # Dated Orders Table
        st.markdown(f"#### Logged Order Issues ({len(dated_incidents)} dated)")
        if dated_incidents:
            rows = []
            for inc in dated_incidents:
                amt_str = f"INR {inc.get('amount_inr'):.2f}" if inc.get("amount_inr") is not None else "-"
                delay_str = f"{inc['actual_minutes'] - inc['promised_minutes']}m delay" if (inc.get("actual_minutes") and inc.get("promised_minutes") and inc["actual_minutes"] > inc["promised_minutes"]) else "-"
                rows.append({
                    "ID": inc["id"],
                    "Order Date": inc["order_date"],
                    "Platform": inc["platform"],
                    "Store / Restaurant": inc["restaurant_or_store"],
                    "Order ID": inc["order_id"] or "-",
                    "Issue Type": inc["issue_type"],
                    "Amount": amt_str,
                    "Delay": delay_str,
                    "Refund Status": inc["refund_status"],
                    "Link Group": inc["link_group"] or "-",
                    "Evidence File": os.path.basename(inc["image_path"]) if inc.get("image_path") else "-",
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        else:
            st.info("No dated orders match the current filters.")

        # Undated Orders Section ("Needs a date")
        if undated_incidents:
            st.markdown("#### ⚠️ Needs a Date")
            st.caption("The following records do not have an order date and are kept separate from chronological timeline statistics:")
            undated_rows = []
            for inc in undated_incidents:
                undated_rows.append({
                    "ID": inc["id"],
                    "Platform": inc["platform"],
                    "Store / Restaurant": inc["restaurant_or_store"],
                    "Order ID": inc["order_id"] or "-",
                    "Issue Type": inc["issue_type"],
                    "Refund Status": inc["refund_status"],
                    "Link Group": inc["link_group"] or "-",
                    "Extracted Text": inc["extracted_text"],
                })
            st.dataframe(pd.DataFrame(undated_rows), width="stretch", hide_index=True)

        # Inspect, Edit, or Delete Single Incident
        st.markdown("---")
        st.markdown("#### ✏️ Inspect, Edit or Delete Incident Record")
        incident_to_manage = st.selectbox(
            "Select Incident to Manage:",
            options=display_incidents,
            format_func=lambda x: f"Incident #{x['id']} • {x['platform']} • {x['restaurant_or_store']} • {x['order_date'] or 'No Date'}",
        )

        if incident_to_manage:
            with st.expander(f"Edit Incident #{incident_to_manage['id']}", expanded=False):
                ed_c1, ed_c2 = st.columns(2)
                with ed_c1:
                    edit_date = st.text_input("Order Date (YYYY-MM-DD or blank):", value=incident_to_manage["order_date"] or "")
                    edit_platform = st.text_input("Platform:", value=incident_to_manage["platform"] or "")
                    edit_store = st.text_input("Store / Restaurant:", value=incident_to_manage["restaurant_or_store"] or "")
                    edit_order_id = st.text_input("Order ID:", value=incident_to_manage["order_id"] or "")
                    edit_issue = st.selectbox("Issue Type:", options=db.VALID_ISSUE_TYPES, index=db.VALID_ISSUE_TYPES.index(incident_to_manage["issue_type"]) if incident_to_manage["issue_type"] in db.VALID_ISSUE_TYPES else 0)
                    edit_amount = st.number_input("Amount (INR):", min_value=0.0, value=float(incident_to_manage["amount_inr"] or 0.0), step=10.0)
                with ed_c2:
                    edit_prom = st.number_input("Promised Minutes:", min_value=0, value=int(incident_to_manage["promised_minutes"] or 0))
                    edit_act = st.number_input("Actual Arrival Minutes:", min_value=0, value=int(incident_to_manage["actual_minutes"] or 0))
                    edit_refund = st.selectbox("Refund Status:", options=db.VALID_REFUND_STATUSES, index=db.VALID_REFUND_STATUSES.index(incident_to_manage["refund_status"]) if incident_to_manage["refund_status"] in db.VALID_REFUND_STATUSES else 0)
                    edit_link = st.text_input("Link Group:", value=incident_to_manage["link_group"] or "")
                    edit_text = st.text_area("Extracted Text:", value=incident_to_manage["extracted_text"] or "", height=80)
                    edit_notes = st.text_area("Context / Notes:", value=incident_to_manage["notes"] or "", height=60)

                if incident_to_manage.get("image_path") and os.path.exists(incident_to_manage["image_path"]):
                    st.image(incident_to_manage["image_path"], caption=f"Evidence: {os.path.basename(incident_to_manage['image_path'])}", width=360)

                st.caption(f"SHA-256 Checksum: `{incident_to_manage.get('file_hash') or 'N/A'}`")

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("💾 Save Changes", key=f"save_{incident_to_manage['id']}", width="stretch"):
                        db.update_incident(
                            incident_id=incident_to_manage["id"],
                            case_name=st.session_state.current_case,
                            order_date=edit_date.strip() if edit_date.strip() else None,
                            platform=edit_platform.strip(),
                            restaurant_or_store=edit_store.strip(),
                            order_id=edit_order_id.strip() if edit_order_id.strip() else None,
                            issue_type=edit_issue,
                            amount_inr=float(edit_amount) if edit_amount > 0 else None,
                            promised_minutes=int(edit_prom) if edit_prom > 0 else None,
                            actual_minutes=int(edit_act) if edit_act > 0 else None,
                            refund_status=edit_refund,
                            extracted_text=edit_text,
                            notes=edit_notes,
                            image_path=incident_to_manage.get("image_path") or "",
                            file_hash=incident_to_manage.get("file_hash") or "",
                            link_group=edit_link.strip() if edit_link.strip() else None,
                        )
                        st.success("Incident record updated.")
                        st.rerun()

                with btn_c2:
                    if st.button("🗑️ Delete This Record", key=f"del_{incident_to_manage['id']}", type="secondary", width="stretch"):
                        db.delete_incident(incident_to_manage["id"])
                        st.success(f"Incident #{incident_to_manage['id']} deleted.")
                        st.rerun()


# -------------------------------------------------------------
# TAB 3: PATTERNS
# -------------------------------------------------------------
with tab_patterns:
    st.subheader("Observable Technical Patterns & Metrics")
    st.caption("All figures are computed using plain Python code. Every card explicitly lists the order incident IDs behind it.")

    if not incidents:
        st.info("No order incidents found in active case. Add incidents or load demo case to view observable patterns.")
    else:
        computed = patterns.analyze_patterns(incidents)

        total_st = computed["total"]
        weekly_st = computed["weekly"]
        platforms_st = computed["platforms"]
        issue_types_st = computed["issue_types"]
        stores_st = computed["stores"]
        delays_st = computed["delays"]
        refunds_st = computed["refunds"]

        # Row 1: Totals, Financial Impact, and Trend
        r1_c1, r1_c2, r1_c3 = st.columns(3)

        with r1_c1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Total Issues & Date Range</div>
                    <div class="metric-value">{total_st['count']} Orders</div>
                    <span class="metric-trace">IDs: {", ".join(str(i) for i in total_st['incident_ids']) or 'None'}</span>
                    <div class="metric-sub">
                        {total_st['date_range_str']} ({total_st['span_days']} days)
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r1_c2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Total Amount Affected</div>
                    <div class="metric-value">INR {total_st['total_amount_inr']:.2f}</div>
                    <span class="metric-trace">Documented IDs: {", ".join(str(i) for i in total_st['amount_incident_ids']) or 'None'}</span>
                    <div class="metric-sub">
                        Missing amount count: {total_st['missing_amount_count']} (IDs: {", ".join(str(i) for i in total_st['missing_amount_ids']) or 'None'})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r1_c3:
            trend_val = weekly_st["trend"].title()
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Weekly Issue Trend</div>
                    <div class="metric-value">{trend_val}</div>
                    <span class="metric-trace">1st Half IDs: {", ".join(str(i) for i in weekly_st['first_half_ids']) or 'None'} | 2nd Half IDs: {", ".join(str(i) for i in weekly_st['second_half_ids']) or 'None'}</span>
                    <div class="metric-sub">
                        1st half avg: {weekly_st['first_half_avg']}/wk vs 2nd half: {weekly_st['second_half_avg']}/wk
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Row 2: Repeat Store, Delays, and Refund Dispute Summary
        r2_c1, r2_c2, r2_c3 = st.columns(3)

        with r2_c1:
            repeat_store_count = stores_st["repeat_store_count"]
            repeat_names = ", ".join(f"{s} ({d['count']})" for s, d in stores_st["repeat_stores"].items()) or "None"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Repeat Stores (2+ Issues)</div>
                    <div class="metric-value">{repeat_store_count} Store(s)</div>
                    <span class="metric-trace">Repeat IDs: {", ".join(str(i) for i in stores_st['repeat_store_ids']) or 'None'}</span>
                    <div class="metric-sub">{repeat_names}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r2_c2:
            if delays_st["has_delays"]:
                delay_val = f"Avg {delays_st['average_delay_minutes']}m / Max {delays_st['max_delay_minutes']}m"
                delay_trace = f"Delay IDs: {', '.join(str(i) for i in delays_st['incident_ids'])}"
                delay_sub = f"{delays_st['delay_count']} delayed order(s) documented past promised delivery arrival time."
            else:
                delay_val = "0 Min"
                delay_trace = "No delay records"
                delay_sub = "No orders documented with actual arrival exceeding promised time."

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Delivery Delays</div>
                    <div class="metric-value">{delay_val}</div>
                    <span class="metric-trace">{delay_trace}</span>
                    <div class="metric-sub">{delay_sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r2_c3:
            rf_summary = f"Pending: {refunds_st['pending_count']} | Denied: {refunds_st['denied_count']} | Partial: {refunds_st['partial_count']}"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Refund Disputes & Status</div>
                    <div class="metric-value">{refunds_st['pending_count']} Pending</div>
                    <span class="metric-trace">Pending IDs: {", ".join(str(i) for i in refunds_st['pending_ids']) or 'None'}</span>
                    <div class="metric-sub">
                        {rf_summary}<br>
                        Longest pending age: {refunds_st['longest_pending_days']} day(s) (IDs: {', '.join(str(i) for i in refunds_st['longest_pending_ids']) or 'None'})
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Row 3: Issues by Platform & by Issue Type
        st.markdown("#### Distribution Across Platforms")
        plat_cols = st.columns(max(1, len(platforms_st)))
        for idx, (plat_name, plat_data) in enumerate(platforms_st.items()):
            with plat_cols[idx % len(plat_cols)]:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-title">{plat_name}</div>
                        <div class="metric-value">{plat_data['count']}</div>
                        <span class="metric-trace">IDs: {", ".join(str(i) for i in plat_data['incident_ids'])}</span>
                        <div class="metric-sub">Total: INR {plat_data['amount_inr']:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("#### Distribution Across Issue Types")
        type_cols = st.columns(min(4, max(1, len(issue_types_st))))
        for idx, (type_name, type_data) in enumerate(issue_types_st.items()):
            with type_cols[idx % len(type_cols)]:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-title">{type_name}</div>
                        <div class="metric-value">{type_data['count']}</div>
                        <span class="metric-trace">IDs: {", ".join(str(i) for i in type_data['incident_ids'])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if total_st["undated_count"] > 0:
            st.info(
                f"ℹ️ {total_st['undated_count']} incident(s) [IDs: {', '.join(str(i) for i in total_st['undated_incident_ids'])}] "
                "lack confirmed order dates and are excluded from weekly trend computations."
            )


# -------------------------------------------------------------
# TAB 4: REPORT
# -------------------------------------------------------------
with tab_report:
    st.subheader("Generate & Export Structured Complaint Evidence Report")
    st.caption("Creates an objective PDF compilation with template text, computed numbers, and full ID traceability.")

    if not incidents:
        st.warning("No incidents available to include in the report. Please add incidents or load the demo case first.")
    else:
        st.markdown(
            f"""
            <div style="background-color: #1A1F2C; border: 1px solid #2D3748; padding: 18px 20px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin-top: 0; color: #FF5C1F;">Report Scope</h4>
                <p style="color: #CBD5E1; margin-bottom: 6px;">
                    <strong>Case / Subject:</strong> {st.session_state.current_case}<br>
                    <strong>Total Order Incidents:</strong> {len(incidents)}<br>
                    <strong>Integrity Verification:</strong> Cryptographic SHA-256 hashes generated for every evidence file.
                </p>
                <div style="font-size: 0.85rem; color: #94A3B8;">
                    {DISCLAIMER_TEXT}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Optional verified complaint draft checkbox
        has_verified_draft = bool(st.session_state.get("last_verified_draft"))
        include_draft = st.checkbox(
            "Include the verified complaint draft in PDF report",
            value=has_verified_draft,
            disabled=not has_verified_draft,
            help="Appends the verified draft message from the AI Assistant tab to the exported report." if has_verified_draft else "Generate a verified complaint draft in the AI Assistant tab first.",
        )

        col_rep1, col_rep2 = st.columns(2)

        with col_rep1:
            if st.button("📄 Generate PDF Report", width="stretch", type="primary"):
                with st.spinner("Compiling traceable evidence report..."):
                    pdf_bytes = report.generate_pdf_report(
                        case_name=st.session_state.current_case,
                        incidents=incidents,
                        complaint_draft=st.session_state.get("last_verified_draft") if include_draft else None,
                    )
                    st.session_state.generated_pdf = pdf_bytes
                    st.success("PDF Report generated successfully!")

        with col_rep2:
            if "generated_pdf" in st.session_state and st.session_state.generated_pdf:
                timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
                safe_case = "".join(c if c.isalnum() else "_" for c in st.session_state.current_case)
                filename = f"PatternProof_Orders_{safe_case}_{timestamp_str}.pdf"

                st.download_button(
                    label="⬇️ Download Evidence Report (PDF)",
                    data=st.session_state.generated_pdf,
                    file_name=filename,
                    mime="application/pdf",
                    width="stretch",
                )

        # Quick preview table
        st.markdown("---")
        st.markdown("#### Evidence Index Preview")
        preview_rows = []
        for inc in incidents:
            amt_str = f"INR {inc.get('amount_inr'):.2f}" if inc.get("amount_inr") is not None else "-"
            preview_rows.append({
                "Incident ID": inc["id"],
                "Date": inc["order_date"] or "Needs Date",
                "Platform": inc["platform"],
                "Store / Restaurant": inc["restaurant_or_store"],
                "Issue Type": inc["issue_type"],
                "Amount": amt_str,
                "Refund": inc["refund_status"],
                "Link Group": inc["link_group"] or "-",
                "Evidence File": os.path.basename(inc["image_path"]) if inc.get("image_path") else "-",
                "SHA-256 Checksum": inc["file_hash"][:16] + "..." if inc.get("file_hash") else "N/A",
            })
        st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)


# -------------------------------------------------------------
# TAB 5: AI ASSISTANT
# -------------------------------------------------------------
with tab_assistant:
    st.subheader("AI Complaint & Evidence Assistant")
    st.caption("Ask questions or generate draft communications based strictly on saved case data. Plain-Python verification checks all claims before display.")

    if not incidents:
        st.info("No order incidents recorded in this case. Please add incidents or load the demo case first.")
    else:
        if "assistant_task" not in st.session_state:
            st.session_state.assistant_task = ""
        if "assistant_result" not in st.session_state:
            st.session_state.assistant_result = None

        st.markdown("#### Quick Preset Tasks")
        presets = [
            "Draft a complaint message to platform support",
            "Summarise this case in 5 lines",
            "Which store or platform has the most issues?",
            "What evidence is missing or weak?",
        ]

        p_col1, p_col2 = st.columns(2)
        task_to_run = None

        with p_col1:
            if st.button("📝 Draft a complaint message to platform support", width="stretch"):
                task_to_run = presets[0]
            if st.button("📋 Summarise this case in 5 lines", width="stretch"):
                task_to_run = presets[1]

        with p_col2:
            if st.button("🏪 Which store or platform has the most issues?", width="stretch"):
                task_to_run = presets[2]
            if st.button("🔍 What evidence is missing or weak?", width="stretch"):
                task_to_run = presets[3]

        st.markdown("---")
        c_col1, c_col2 = st.columns([3, 1])
        with c_col1:
            custom_input = st.text_input(
                "Or enter a custom task / inquiry:",
                placeholder="e.g. List all orders with missing items and their refund status",
                key="custom_task_input_field",
            )
        with c_col2:
            st.write("")
            st.write("")
            if st.button("🚀 Run Task", width="stretch"):
                if custom_input.strip():
                    task_to_run = custom_input.strip()
                else:
                    st.warning("Please enter a question or task.")

        if task_to_run:
            st.session_state.assistant_task = task_to_run
            with st.spinner("Processing task and running plain-Python verification checks..."):
                analysis_data = patterns.analyze_patterns(incidents)
                res = ai_assistant.run_assistant_task(
                    task=task_to_run,
                    incidents=incidents,
                    patterns_data=analysis_data,
                )
                st.session_state.assistant_result = res
                if res.get("success") and "complaint" in task_to_run.lower() and res.get("answer"):
                    st.session_state.last_verified_draft = res["answer"]

        cur_res = st.session_state.assistant_result
        if cur_res:
            st.markdown("---")
            st.markdown(f"### Result for: *\"{st.session_state.assistant_task}\"*")

            if cur_res.get("success") and cur_res.get("answer"):
                label_badge = "📋 Template Answer (No AI)" if cur_res.get("is_template") else "🤖 AI Generated (Verified)"
                st.markdown(
                    f"""
                    <div style="background-color: #1A1F2C; border: 1px solid #FF5C1F; border-radius: 10px; padding: 20px 24px; margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span style="font-weight: 700; color: #FF5C1F; font-size: 1.05rem;">Verified Assistant Response</span>
                            <span style="background: rgba(255, 92, 31, 0.15); color: #FF5C1F; font-size: 0.8rem; font-weight: 600; padding: 4px 10px; border-radius: 4px;">{label_badge}</span>
                        </div>
                        <div style="color: #F8FAFC; white-space: pre-wrap; font-size: 0.95rem; line-height: 1.6;">{cur_res['answer']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                meta_c1, meta_c2 = st.columns(2)
                with meta_c1:
                    cited_str = ", ".join(f"#{i}" for i in cur_res.get("cited_ids", [])) or "None"
                    st.caption(f"📌 **Cited Incident IDs**: `{cited_str}`")
                with meta_c2:
                    nums_str = ", ".join(str(n) for n in cur_res.get("numbers_used", [])) or "None"
                    st.caption(f"🔢 **Verified Numbers Used**: `{nums_str}`")

                if cur_res.get("needs_more_info"):
                    st.info("ℹ️ **Information needed to strengthen case**: " + "; ".join(cur_res["needs_more_info"]))
            else:
                st.error("❌ **Could not verify this answer.** The response failed verification checks after retry and was blocked.")
                if st.button("📋 Load Verified Template Answer Instead", width="stretch"):
                    analysis_data = patterns.analyze_patterns(incidents)
                    tmpl_res = ai_assistant.generate_template_answer(
                        st.session_state.assistant_task, incidents, analysis_data
                    )
                    _, tmpl_checks = verifier.verify_response(
                        raw_json_str=None,
                        parsed_output=tmpl_res,
                        incidents=incidents,
                        patterns_data=analysis_data,
                        task_prompt=st.session_state.assistant_task,
                    )
                    st.session_state.assistant_result = {
                        "success": True,
                        "is_template": True,
                        "answer": tmpl_res["answer"],
                        "cited_ids": tmpl_res["cited_ids"],
                        "numbers_used": tmpl_res["numbers_used"],
                        "needs_more_info": tmpl_res["needs_more_info"],
                        "check_results": tmpl_checks,
                        "error_message": "Loaded verified template answer.",
                    }
                    if "complaint" in st.session_state.assistant_task.lower():
                        st.session_state.last_verified_draft = tmpl_res["answer"]
                    st.rerun()

            # Verification Panel
            st.markdown("#### 🔍 Verification Panel")
            st.caption("Plain-Python verifier executes 6 deterministic checks before allowing output:")
            for check in cur_res.get("check_results", []):
                icon = "✅" if check["passed"] else "❌"
                status_color = "#10B981" if check["passed"] else "#EF4444"
                st.markdown(
                    f"""
                    <div style="background: #151A24; border-left: 4px solid {status_color}; padding: 10px 14px; margin-bottom: 8px; border-radius: 4px;">
                        <span style="font-weight: 600; color: #E2E8F0;">{icon} {check['check_name']}</span>: 
                        <span style="color: #94A3B8; font-size: 0.9rem;">{check['detail']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# -------------------------------------------------------------
# APP FOOTER (MANDATORY ON EVERY PAGE)
# -------------------------------------------------------------
st.markdown(
    f"""
    <div class="app-footer">
        📦 <strong>PatternProof</strong> &bull; {DISCLAIMER_TEXT}
    </div>
    """,
    unsafe_allow_html=True,
)
