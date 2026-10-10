"""PatternProof: Delivery Evidence Coach.

Streamlit application guiding customers through capturing structured photographic
evidence for delivery order disputes.
"""

import os
import io
import json
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List

import streamlit as st
import pandas as pd
from PIL import Image

import db
import ai
import tasks
import verifier
import report
import demo

# Page Configuration
st.set_page_config(
    page_title="PatternProof: Delivery Evidence Coach",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mandatory Neutral Disclaimer
FOOTER_DISCLAIMER = (
    "PatternProof organises user-provided evidence. "
    "It does not verify authenticity, decide claims, or provide legal advice."
)

# Custom CSS for dark theme with #FF5C1F accent
CUSTOM_CSS = """
<style>
    /* Global accent and styles */
    :root {
        --accent-orange: #FF5C1F;
        --bg-dark: #0E1117;
        --card-bg: #1A1F2C;
        --card-border: #2B3245;
        --text-primary: #E0E6ED;
        --text-muted: #8E9BAE;
    }

    /* Main container adjustments */
    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-primary);
    }

    /* Header styling */
    .app-header {
        padding: 1rem 0 1.5rem 0;
        border-bottom: 1px solid var(--card-border);
        margin-bottom: 1.5rem;
    }
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #FFFFFF;
        margin: 0;
    }
    .app-title span {
        color: var(--accent-orange);
    }
    .app-subtitle {
        color: var(--text-muted);
        font-size: 1rem;
        margin-top: 0.3rem;
    }

    /* Card containers */
    .evidence-card {
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }

    /* Badge styles */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .badge-passed {
        background-color: rgba(46, 204, 113, 0.15);
        color: #2ECC71;
        border: 1px solid #2ECC71;
    }
    .badge-partial {
        background-color: rgba(243, 156, 18, 0.15);
        color: #F39C12;
        border: 1px solid #F39C12;
    }
    .badge-retake {
        background-color: rgba(231, 76, 60, 0.15);
        color: #E74C3C;
        border: 1px solid #E74C3C;
    }
    .badge-confirmed {
        background-color: rgba(52, 152, 219, 0.15);
        color: #3498DB;
        border: 1px solid #3498DB;
    }
    .badge-open {
        background-color: rgba(142, 155, 174, 0.15);
        color: #8E9BAE;
        border: 1px solid #8E9BAE;
    }
    .badge-demo {
        background-color: rgba(255, 92, 31, 0.2);
        color: var(--accent-orange);
        border: 1px solid var(--accent-orange);
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* Retake advice box */
    .retake-box {
        background-color: rgba(231, 76, 60, 0.08);
        border-left: 4px solid #E74C3C;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-top: 0.75rem;
    }

    /* Instruction callout */
    .instruction-callout {
        background-color: #151923;
        border: 1px solid #262D3D;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.95rem;
    }

    /* Footer */
    .footer-disclaimer {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.82rem;
        padding: 2rem 0 1rem 0;
        border-top: 1px solid var(--card-border);
        margin-top: 2.5rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def init_session_state() -> None:
    """Initialize application session state keys."""
    db.init_db()
    if "current_order_id" not in st.session_state:
        st.session_state["current_order_id"] = None

    if "receipt_uploader_nonce" not in st.session_state:
        st.session_state["receipt_uploader_nonce"] = 0

    if "product_uploader_nonce" not in st.session_state:
        st.session_state["product_uploader_nonce"] = 0

    if "active_tab_index" not in st.session_state:
        st.session_state["active_tab_index"] = 0

    if "demo_mode_toggle" not in st.session_state:
        st.session_state["demo_mode_toggle"] = False

    if "sidebar_key_override" not in st.session_state:
        st.session_state["sidebar_key_override"] = ""


init_session_state()

# Determine effective API Key and Demo Mode state
sidebar_key = st.session_state.get("sidebar_key_override", "").strip()
detected_api_key = ai.get_api_key(sidebar_key)
is_demo_mode = st.session_state.get("demo_mode_toggle", False) or (detected_api_key is None)


# =========================================================================
# SIDEBAR
# =========================================================================
with st.sidebar:
    st.markdown("### 📦 PatternProof")
    st.markdown("**Delivery Evidence Coach**")
    st.caption("Structured photographic guidance for delivery disputes")

    st.markdown("---")

    # API Key Status Box
    if detected_api_key:
        st.success("● Gemini Vision Connected")
    else:
        st.info("○ Demo Mode Available (No Key Required)")

    with st.expander("🔑 Gemini API Key Settings"):
        key_input = st.text_input(
            "API Key Override",
            value=st.session_state.get("sidebar_key_override", ""),
            type="password",
            placeholder="AIzaSy...",
            help="Optional override. If blank, uses st.secrets or .env."
        )
        if key_input != st.session_state.get("sidebar_key_override", ""):
            st.session_state["sidebar_key_override"] = key_input
            st.rerun()

    # Demo Mode Toggle
    demo_toggle = st.toggle(
        "Demo mode (simulated AI)",
        value=st.session_state.get("demo_mode_toggle", False),
        help="Simulates AI vision and verification using deterministic responses."
    )
    if demo_toggle != st.session_state.get("demo_mode_toggle", False):
        st.session_state["demo_mode_toggle"] = demo_toggle
        st.rerun()

    st.markdown("---")

    # Order Management Buttons
    if st.button("✨ Load Demo Order", width="stretch"):
        with st.spinner("Generating demo delivery order and checklist..."):
            new_oid = demo.load_demo_order()
            st.session_state["current_order_id"] = new_oid
            st.session_state["active_tab_index"] = 1
            st.success("Demo order loaded successfully!")
            st.rerun()

    if st.button("➕ Start New Order", width="stretch"):
        st.session_state["current_order_id"] = None
        st.session_state["receipt_uploader_nonce"] = st.session_state.get("receipt_uploader_nonce", 0) + 1
        st.session_state["product_uploader_nonce"] = st.session_state.get("product_uploader_nonce", 0) + 1
        for form_key in [
            "form_store", "form_platform", "form_order_id", "form_order_date",
            "form_total_inr", "form_items", "form_claim_type", "form_analysis"
        ]:
            if form_key in st.session_state:
                del st.session_state[form_key]
        st.session_state["active_tab_index"] = 0
        st.success("New order started! All uploads and fields cleared.")
        st.rerun()

    saved_orders = db.list_orders()
    if saved_orders:
        with st.expander("📂 Open Saved Order"):
            order_labels = {
                f"Order #{o['id']} ({o.get('order_id', 'Draft')} - {o.get('store', '')})": o["id"]
                for o in saved_orders
            }
            selected_choice = st.selectbox("Select saved order", options=list(order_labels.keys()), key="sidebar_saved_order_select")
            if st.button("Load Selected Order", width="stretch"):
                st.session_state["current_order_id"] = order_labels[selected_choice]
                for form_key in [
                    "form_store", "form_platform", "form_order_id", "form_order_date",
                    "form_total_inr", "form_items", "form_claim_type", "form_analysis"
                ]:
                    if form_key in st.session_state:
                        del st.session_state[form_key]
                st.rerun()

    with st.expander("🗑️ Delete All Data"):
        st.warning("This will remove all saved orders and uploaded files locally.")
        if st.button("Confirm Delete All", type="primary", width="stretch"):
            db.delete_all_data()
            st.session_state["current_order_id"] = None
            st.session_state["receipt_uploader_nonce"] = st.session_state.get("receipt_uploader_nonce", 0) + 1
            st.session_state["product_uploader_nonce"] = st.session_state.get("product_uploader_nonce", 0) + 1
            for form_key in [
                "form_store", "form_platform", "form_order_id", "form_order_date",
                "form_total_inr", "form_items", "form_claim_type", "form_analysis"
            ]:
                if form_key in st.session_state:
                    del st.session_state[form_key]
            st.session_state["active_tab_index"] = 0
            st.success("All local records removed.")
            st.rerun()

    st.markdown("---")
    st.caption("🔒 **Local Storage Note**: All orders and photos are stored strictly on your local computer (`patternproof.db` and `uploads/`).")


# =========================================================================
# HEADER & DEMO BADGE
# =========================================================================
header_col1, header_col2 = st.columns([4, 2])
with header_col1:
    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">PatternProof <span>Evidence Coach</span></div>'
        '<div class="app-subtitle">Upload your order receipt, receive a tailored photo checklist, and compile an evidence pack.</div>'
        '</div>',
        unsafe_allow_html=True
    )
with header_col2:
    if is_demo_mode:
        st.markdown(
            '<div style="text-align: right; padding-top: 1.5rem;">'
            '<span class="badge-demo">⚡ DEMO MODE: simulated AI</span>'
            '</div>',
            unsafe_allow_html=True
        )

# Fetch Current Order Record
current_order = None
if st.session_state.get("current_order_id"):
    current_order = db.get_order(st.session_state["current_order_id"])

# Main Navigation Tabs
tab_order, tab_tasks, tab_pack = st.tabs([
    "1. Order Details & Receipt",
    "2. Photo Checklist Tasks",
    "3. Evidence Pack Export"
])


# =========================================================================
# TAB 1: ORDER DETAILS & RECEIPT
# =========================================================================
with tab_order:
    st.markdown("### Step 1: Order Information & Primary Proof")

    # Mandatory One-Time Privacy Tip
    st.info("ℹ️ **Privacy Tip**: Hide your address and phone number before uploading receipts.")

    # Receipt Upload Section
    st.markdown("#### 1. Upload Order Receipt Screenshot")
    receipt_nonce = st.session_state.get("receipt_uploader_nonce", 0)
    uploaded_receipt = st.file_uploader(
        "Upload receipt or invoice screenshot (PNG, JPG)",
        type=["png", "jpg", "jpeg"],
        key=f"receipt_file_uploader_{receipt_nonce}",
        help="Capture an order summary or invoice screen from your delivery app."
    )

    # State container for AI-transcribed receipt data
    if "form_store" not in st.session_state:
        st.session_state["form_store"] = current_order.get("store", "") if current_order else ""
    if "form_platform" not in st.session_state:
        st.session_state["form_platform"] = current_order.get("platform", "") if current_order else ""
    if "form_order_id" not in st.session_state:
        st.session_state["form_order_id"] = current_order.get("order_id", "") if current_order else ""
    if "form_order_date" not in st.session_state:
        st.session_state["form_order_date"] = current_order.get("order_date", "") if current_order else ""
    if "form_total_inr" not in st.session_state:
        st.session_state["form_total_inr"] = str(current_order.get("total_inr", "")) if current_order and current_order.get("total_inr") is not None else ""
    if "form_items" not in st.session_state:
        st.session_state["form_items"] = current_order.get("items", []) if current_order else []
    if "form_claim_type" not in st.session_state:
        st.session_state["form_claim_type"] = current_order.get("claim_type", tasks.CLAIM_TYPES[0]) if current_order else tasks.CLAIM_TYPES[0]
    if "form_analysis" not in st.session_state:
        st.session_state["form_analysis"] = current_order.get("product_analysis", {}) if current_order else {}

    receipt_col1, receipt_col2 = st.columns([1, 1])

    # Show preview if available
    receipt_bytes_to_process = None
    if uploaded_receipt is not None:
        receipt_bytes_to_process = uploaded_receipt.getvalue()
        with receipt_col1:
            st.image(receipt_bytes_to_process, caption="Uploaded Receipt Preview", width="stretch")
            if st.button("🗑️ Remove Receipt Photo", key="btn_clear_uploaded_receipt", width="stretch"):
                st.session_state["receipt_uploader_nonce"] = receipt_nonce + 1
                st.rerun()
    elif current_order and current_order.get("receipt_path") and os.path.isfile(current_order["receipt_path"]):
        with receipt_col1:
            st.image(current_order["receipt_path"], caption="Current Saved Receipt", width="stretch")
            if st.button("🗑️ Remove Saved Receipt", key="btn_clear_saved_receipt", width="stretch"):
                with db.get_db_connection() as conn:
                    conn.execute("UPDATE orders SET receipt_path = NULL, receipt_hash = NULL WHERE id = ?", (current_order["id"],))
                    conn.commit()
                st.session_state["receipt_uploader_nonce"] = receipt_nonce + 1
                st.rerun()

    with receipt_col2:
        st.write("Use AI to transcribe store details, order number, total, and itemized lines automatically:")
        if st.button("🤖 Read Receipt with AI", width="stretch", disabled=(receipt_bytes_to_process is None and not (current_order and current_order.get("receipt_path")))):
            target_bytes = receipt_bytes_to_process
            if not target_bytes and current_order and current_order.get("receipt_path"):
                with open(current_order["receipt_path"], "rb") as rf:
                    target_bytes = rf.read()

            if target_bytes:
                ai_receipt, tech_err = ai.read_receipt(
                    target_bytes,
                    api_key=detected_api_key,
                    mock=is_demo_mode
                )
                if tech_err:
                    st.warning("AI reading encountered an issue. You can enter or edit the fields manually below.")
                    with st.expander("Technical Error Detail"):
                        st.code(tech_err)
                else:
                    if ai_receipt.get("store"):
                        st.session_state["form_store"] = str(ai_receipt["store"])
                    if ai_receipt.get("platform"):
                        st.session_state["form_platform"] = str(ai_receipt["platform"])
                    if ai_receipt.get("order_id"):
                        st.session_state["form_order_id"] = str(ai_receipt["order_id"])
                    if ai_receipt.get("order_date"):
                        st.session_state["form_order_date"] = str(ai_receipt["order_date"])
                    if ai_receipt.get("total_inr") is not None:
                        st.session_state["form_total_inr"] = str(ai_receipt["total_inr"])
                    if ai_receipt.get("items"):
                        st.session_state["form_items"] = ai_receipt["items"]
                    st.success("Receipt parsed successfully! Details pre-filled below.")
                    st.rerun()

    st.markdown("---")
    st.markdown("#### 2. Verify & Edit Order Information")

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        val_platform = st.text_input("Platform / App", value=st.session_state.get("form_platform", ""), placeholder="e.g. InstaMart, Zepto, Blinkit")
    with col_meta2:
        val_store = st.text_input("Store Name", value=st.session_state.get("form_store", ""), placeholder="e.g. Fresh Basket, SuperMart")
    with col_meta3:
        val_order_id = st.text_input("Order ID", value=st.session_state.get("form_order_id", ""), placeholder="e.g. ORD-8921-X")

    col_meta4, col_meta5 = st.columns(2)
    with col_meta4:
        val_date_str = st.text_input(
            "Order Date (YYYY-MM-DD)",
            value=st.session_state.get("form_order_date", ""),
            placeholder="YYYY-MM-DD"
        )
        # Validate order date: not in future
        cleaned_date = val_date_str.strip()
        if cleaned_date:
            try:
                parsed_dt = datetime.strptime(cleaned_date, "%Y-%m-%d").date()
                if parsed_dt > date.today():
                    st.warning("Order date cannot be in the future. Field cleared.")
                    cleaned_date = ""
            except ValueError:
                st.warning("Please format date as YYYY-MM-DD.")
                cleaned_date = ""

    with col_meta5:
        val_total_str = st.text_input(
            "Total Amount (INR)",
            value=st.session_state.get("form_total_inr", ""),
            placeholder="e.g. 450.00"
        )
        # Validate total: must be positive numeric
        cleaned_total = None
        if val_total_str.strip():
            try:
                t_float = float(val_total_str.strip())
                if t_float < 0:
                    st.warning("Total amount cannot be negative.")
                else:
                    cleaned_total = t_float
            except ValueError:
                st.warning("Total must be a numeric value.")

    # Items Table Editable via st.data_editor
    st.markdown("##### Billed Line Items")
    current_items = st.session_state.get("form_items", [])
    if not current_items:
        current_items = [{"name": "Sample Item", "quantity": 1, "price_inr": 100.0}]

    items_df = pd.DataFrame(current_items)
    for expected_col in ["name", "quantity", "price_inr"]:
        if expected_col not in items_df.columns:
            items_df[expected_col] = 1 if expected_col == "quantity" else 0.0

    edited_items_df = st.data_editor(
        items_df[["name", "quantity", "price_inr"]],
        num_rows="dynamic",
        width="stretch",
        key="items_data_editor"
    )

    st.markdown("---")

    # Optional Product Photo Upload & Analysis
    st.markdown("#### 3. Optional: Initial Product Photo")
    st.caption("If you have taken a photo of the affected item, upload it here to help tailor the checklist:")

    prod_nonce = st.session_state.get("product_uploader_nonce", 0)
    uploaded_product = st.file_uploader(
        "Upload initial product photo (optional)",
        type=["png", "jpg", "jpeg"],
        key=f"product_file_uploader_{prod_nonce}"
    )

    prod_col1, prod_col2 = st.columns([1, 1])
    product_bytes_to_process = None
    if uploaded_product is not None:
        product_bytes_to_process = uploaded_product.getvalue()
        with prod_col1:
            st.image(product_bytes_to_process, caption="Uploaded Product Photo Preview", width="stretch")
            if st.button("🗑️ Remove Product Photo", key="btn_clear_uploaded_product", width="stretch"):
                st.session_state["product_uploader_nonce"] = prod_nonce + 1
                st.session_state["form_analysis"] = {}
                st.rerun()
    elif current_order and current_order.get("product_photo_path") and os.path.isfile(current_order["product_photo_path"]):
        with prod_col1:
            st.image(current_order["product_photo_path"], caption="Current Saved Product Photo", width="stretch")
            if st.button("🗑️ Remove Saved Product Photo", key="btn_clear_saved_product", width="stretch"):
                with db.get_db_connection() as conn:
                    conn.execute("UPDATE orders SET product_photo_path = NULL, product_hash = NULL WHERE id = ?", (current_order["id"],))
                    conn.commit()
                st.session_state["product_uploader_nonce"] = prod_nonce + 1
                st.session_state["form_analysis"] = {}
                st.rerun()

    with prod_col2:
        if st.button("🔍 Analyse Product Photo with AI", width="stretch", disabled=(product_bytes_to_process is None and not (current_order and current_order.get("product_photo_path")))):
            p_bytes = product_bytes_to_process
            if not p_bytes and current_order and current_order.get("product_photo_path"):
                with open(current_order["product_photo_path"], "rb") as pf:
                    p_bytes = pf.read()

            if p_bytes:
                items_dict_list = edited_items_df.to_dict(orient="records")
                analysis_data, tech_err = ai.analyse_product_photo(
                    p_bytes,
                    receipt_items=items_dict_list,
                    api_key=detected_api_key,
                    mock=is_demo_mode
                )
                if tech_err:
                    st.warning("Could not complete product analysis. You may continue without it.")
                    with st.expander("Technical Error Detail"):
                        st.code(tech_err)
                else:
                    st.session_state["form_analysis"] = analysis_data
                    st.success("Product photo analyzed!")
                    st.rerun()

    # Display editable product analysis summary
    current_analysis = st.session_state.get("form_analysis", {})
    analysis_desc = current_analysis.get("product_description", "")
    edited_summary = st.text_area(
        "AI Observation Summary (Editable)",
        value=analysis_desc,
        placeholder="Factual notes on visible product state...",
        help="Summarizes what is visible in the initial product photo."
    )

    st.markdown("---")

    # Claim Type Selection & Checklist Generation Button
    st.markdown("#### 4. Delivery Issue & Checklist Generation")
    claim_type_idx = 0
    if st.session_state.get("form_claim_type") in tasks.CLAIM_TYPES:
        claim_type_idx = tasks.CLAIM_TYPES.index(st.session_state["form_claim_type"])

    selected_claim_type = st.selectbox(
        "What issue occurred with this order?",
        options=tasks.CLAIM_TYPES,
        index=claim_type_idx
    )

    if st.button("📋 Create My Photo Checklist", type="primary", width="stretch"):
        # Save or update order in DB
        items_dict_list = edited_items_df.to_dict(orient="records")

        # Handle receipt file saving
        saved_receipt_path = current_order.get("receipt_path") if current_order else None
        saved_receipt_hash = current_order.get("receipt_hash") if current_order else None
        if uploaded_receipt is not None:
            r_bytes = uploaded_receipt.getvalue()
            os.makedirs("uploads", exist_ok=True)
            saved_receipt_hash = hashlib.sha256(r_bytes).hexdigest()
            saved_receipt_path = os.path.join("uploads", f"receipt_{saved_receipt_hash[:12]}.jpg")
            with open(saved_receipt_path, "wb") as f:
                f.write(r_bytes)

        # Handle product photo saving
        saved_product_path = current_order.get("product_photo_path") if current_order else None
        saved_product_hash = current_order.get("product_hash") if current_order else None
        if uploaded_product is not None:
            p_bytes = uploaded_product.getvalue()
            os.makedirs("uploads", exist_ok=True)
            saved_product_hash = hashlib.sha256(p_bytes).hexdigest()
            saved_product_path = os.path.join("uploads", f"product_{saved_product_hash[:12]}.jpg")
            with open(saved_product_path, "wb") as f:
                f.write(p_bytes)

        updated_analysis = dict(current_analysis)
        if edited_summary:
            updated_analysis["product_description"] = edited_summary

        order_record = {
            "id": current_order["id"] if current_order else None,
            "store": val_store.strip() or "Delivery Store",
            "platform": val_platform.strip() or "Delivery Platform",
            "order_id": val_order_id.strip() or f"ORD-{int(datetime.now().timestamp())}",
            "order_date": cleaned_date or datetime.now().strftime("%Y-%m-%d"),
            "total_inr": cleaned_total,
            "items": items_dict_list,
            "claim_type": selected_claim_type,
            "receipt_path": saved_receipt_path,
            "receipt_hash": saved_receipt_hash,
            "product_photo_path": saved_product_path,
            "product_hash": saved_product_hash,
            "product_analysis": updated_analysis
        }

        saved_oid = db.save_order(order_record)
        st.session_state["current_order_id"] = saved_oid

        # Generate custom photographic checklist
        with st.spinner("Generating custom photographic evidence tasks..."):
            ai_tasks_resp, tech_err = ai.generate_tasks(
                order_record,
                updated_analysis,
                selected_claim_type,
                api_key=detected_api_key,
                mock=is_demo_mode
            )
            raw_tasks = ai_tasks_resp.get("tasks", []) if isinstance(ai_tasks_resp, dict) else []
            validated_tasks = tasks.validate_ai_tasks(raw_tasks, selected_claim_type, order_record)
            db.save_tasks(saved_oid, validated_tasks)

        st.success("Photo checklist generated! Switched to Step 2.")
        st.session_state["active_tab_index"] = 1
        st.rerun()


# =========================================================================
# TAB 2: PHOTO CHECKLIST TASKS
# =========================================================================
with tab_tasks:
    st.markdown("### Step 2: Custom Photo Checklist")

    if not current_order:
        st.warning("No active order found. Please complete Step 1 or load a demo order from the sidebar.")
    else:
        order_tasks = db.get_tasks_for_order(current_order["id"])
        if not order_tasks:
            st.info("Checklist has not been created yet for this order. Click 'Create My Photo Checklist' in Step 1.")
        else:
            # Metrics & Progress bar
            total_count = len(order_tasks)
            passed_count = sum(1 for t in order_tasks if t.get("status") == "Passed")
            confirmed_count = sum(1 for t in order_tasks if t.get("status") == "User-confirmed")
            partial_count = sum(1 for t in order_tasks if t.get("status") == "Partial")
            retake_count = sum(1 for t in order_tasks if t.get("status") == "Retake")
            open_count = sum(1 for t in order_tasks if t.get("status") == "Open")

            progress_val = (passed_count + confirmed_count) / total_count if total_count > 0 else 0.0
            st.progress(progress_val)

            # Metric Counters
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Passed", f"{passed_count}/{total_count}")
            mc2.metric("User-Confirmed", f"{confirmed_count}")
            mc3.metric("Partial", f"{partial_count}")
            mc4.metric("Retake Suggested", f"{retake_count}")
            mc5.metric("Awaiting Photos", f"{open_count}")

            st.markdown("---")

            # Collect existing hashes for duplicate checking
            existing_order_hashes = db.get_order_hashes(current_order["id"])

            # Render Each Task Card
            for t in order_tasks:
                task_id = t["id"]
                task_code = t.get("task_code", "T")
                title = t.get("title", "Evidence Photo")
                status = t.get("status", "Open")
                attempts = t.get("attempts", 0)

                # Status Badge Markup
                if status == "Passed":
                    badge_class = "badge-passed"
                    status_symbol = "✓"
                elif status == "User-confirmed":
                    badge_class = "badge-confirmed"
                    status_symbol = "★"
                elif status == "Partial":
                    badge_class = "badge-partial"
                    status_symbol = "!"
                elif status == "Retake":
                    badge_class = "badge-retake"
                    status_symbol = "✗"
                else:
                    badge_class = "badge-open"
                    status_symbol = "○"

                st.markdown(
                    f'<div class="evidence-card">'
                    f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                    f'<h4 style="margin: 0; color: #FFFFFF;">{task_code}: {title}</h4>'
                    f'<span class="status-badge {badge_class}">{status_symbol} {status}</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                card_col1, card_col2 = st.columns([1, 1])

                with card_col1:
                    st.markdown(f"**Required Angle**: `{t.get('angle', 'Standard angle')}`")
                    st.markdown(
                        f'<div class="instruction-callout">'
                        f'<strong>Concrete Instruction:</strong><br/>{t.get("instruction", "")}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown("**What must be clearly visible:**")
                    for req in t.get("must_show", []):
                        st.markdown(f"- {req}")

                    if t.get("related_item"):
                        st.caption(f"Tied to item: {t['related_item']}")

                with card_col2:
                    # Tabs for camera input vs file upload
                    input_tab_upload, input_tab_camera = st.tabs(["📁 Upload File", "📷 Live Camera"])

                    new_photo_bytes = None
                    is_camera = False
                    input_filename = ""

                    with input_tab_upload:
                        uploaded_file = st.file_uploader(
                            f"Upload photo for {task_code}",
                            type=["jpg", "jpeg", "png"],
                            key=f"file_uploader_{task_id}"
                        )
                        if uploaded_file is not None:
                            new_photo_bytes = uploaded_file.getvalue()
                            input_filename = uploaded_file.name

                    with input_tab_camera:
                        cam_photo = st.camera_input(
                            f"Take photo for {task_code}",
                            key=f"camera_{task_id}"
                        )
                        if cam_photo is not None:
                            new_photo_bytes = cam_photo.getvalue()
                            is_camera = True
                            input_filename = "camera_capture.jpg"

                    # Quick Demo Mode test shortcuts to simulate good/bad images effortlessly
                    if is_demo_mode:
                        test_btn_col1, test_btn_col2 = st.columns(2)
                        with test_btn_col1:
                            if st.button(f"⚡ Use Good Test Photo", key=f"btn_demo_good_{task_id}", width="stretch"):
                                input_filename, new_photo_bytes = demo.create_demo_task_image("good", t.get("title", "Task"))
                        with test_btn_col2:
                            if st.button(f"⚡ Use Retake Test Photo", key=f"btn_demo_bad_{task_id}", width="stretch"):
                                input_filename, new_photo_bytes = demo.create_demo_task_image("bad", t.get("title", "Task"))

                    # Display existing or newly captured photo
                    existing_photo = t.get("photo_path")
                    if new_photo_bytes:
                        st.image(new_photo_bytes, caption=f"Selected Photo ({input_filename})", width="stretch")
                    elif existing_photo and os.path.isfile(existing_photo):
                        st.image(existing_photo, caption=f"Current Photo: {t.get('captured_at', '')}", width="stretch")

                    # Check photo button
                    if st.button(f"🔍 Check this photo ({task_code})", key=f"btn_verify_{task_id}", width="stretch", disabled=(new_photo_bytes is None and not (existing_photo and os.path.isfile(existing_photo)))):
                        bytes_to_verify = new_photo_bytes
                        if not bytes_to_verify and existing_photo and os.path.isfile(existing_photo):
                            with open(existing_photo, "rb") as ef:
                                bytes_to_verify = ef.read()

                        if bytes_to_verify:
                            # 1. Save photo to disk
                            os.makedirs("uploads", exist_ok=True)
                            p_hash = hashlib.sha256(bytes_to_verify).hexdigest()
                            target_save_path = os.path.join("uploads", f"task_{task_code}_{p_hash[:10]}.jpg")
                            with open(target_save_path, "wb") as pf:
                                pf.write(bytes_to_verify)

                            # 2. Gather hashes & existing task aHashes for similarity checks
                            exclude_set = existing_order_hashes.copy()
                            # Allow re-uploading the same file to the same task without self-duplicate trigger
                            if t.get("photo_hash") in exclude_set:
                                exclude_set.remove(t["photo_hash"])

                            other_ahashes = []
                            for ot in order_tasks:
                                if ot["id"] != task_id and ot.get("photo_path") and os.path.isfile(ot["photo_path"]):
                                    try:
                                        o_img = Image.open(ot["photo_path"])
                                        other_ahashes.append((ot.get("task_code", "other"), verifier.compute_ahash(o_img)))
                                    except Exception:
                                        pass

                            # 3. Call AI Observation
                            fn_for_mock = input_filename or os.path.basename(target_save_path)
                            ai_obs, tech_err = ai.verify_photo(
                                bytes_to_verify,
                                t,
                                current_order,
                                api_key=detected_api_key,
                                mock=is_demo_mode,
                                filename=fn_for_mock
                            )

                            # 4. Run plain Python verification
                            eval_res = verifier.verify_task_photo(
                                bytes_to_verify,
                                t,
                                current_order,
                                ai_result=ai_obs,
                                existing_hashes=exclude_set,
                                other_task_ahashes=other_ahashes,
                                is_camera_input=is_camera
                            )

                            # 5. Update DB
                            new_attempts = attempts + 1
                            db.update_task(task_id, {
                                "status": eval_res["status"],
                                "attempts": new_attempts,
                                "photo_path": target_save_path,
                                "photo_hash": eval_res["photo_hash"],
                                "captured_at": eval_res["captured_at"],
                                "verification": eval_res
                            })

                            st.success(f"Task evaluation complete: {eval_res['status']}")
                            st.rerun()

                # Verification Result Details Panel
                verif_json = t.get("verification")
                if verif_json and isinstance(verif_json, dict):
                    with st.expander(f"📊 Verification Details for {task_code} (Status: {status})", expanded=(status in ["Retake", "Partial"])):
                        st.markdown(f"**Evaluated At**: {verif_json.get('captured_at', '')} | **Attempts**: {attempts}")
                        st.markdown(f"**Original SHA-256**: `{t.get('photo_hash', 'N/A')}`")

                        # Display Check Rows
                        for chk in verif_json.get("checks", []):
                            c_status = chk.get("status", "pass")
                            c_name = chk.get("name", "Check")
                            c_detail = chk.get("detail", "")

                            if c_status == "pass":
                                icon = "✅"
                            elif c_status == "warn":
                                icon = "⚠️"
                            else:
                                icon = "❌"

                            st.markdown(f"{icon} **{c_name}**: {c_detail}")

                        # Actionable Retake Advice Box
                        advice_list = verif_json.get("retake_advice", [])
                        if advice_list:
                            advice_items_html = "".join([f"<li>{adv}</li>" for adv in advice_list])
                            st.markdown(
                                f'<div class="retake-box">'
                                f'<strong style="color: #E74C3C;">Retake Advice:</strong>'
                                f'<ul style="margin: 0.3rem 0 0 1.2rem; color: #E0E6ED;">{advice_items_html}</ul>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                # Option to Mark as User-Confirmed after 3 attempts or if AI unavailable
                ai_failed = verif_json and any("AI check unavailable" in chk.get("detail", "") for chk in verif_json.get("checks", []))
                if attempts >= 3 or ai_failed:
                    if status != "User-confirmed":
                        st.markdown("")
                        if st.button(
                            f"✋ Mark {task_code} as user-confirmed (not machine-verified)",
                            key=f"btn_confirm_{task_id}",
                            help="After multiple attempts or when AI visual analysis is unavailable, you can manually certify this photo."
                        ):
                            db.update_task(task_id, {"status": "User-confirmed"})
                            st.info(f"{task_code} marked as user-confirmed.")
                            st.rerun()

                st.markdown("---")

            # Bottom advance button to Evidence Pack
            if st.button("Proceed to Evidence Pack Export ➔", width="stretch"):
                st.session_state["active_tab_index"] = 2
                st.rerun()


# =========================================================================
# TAB 3: EVIDENCE PACK EXPORT
# =========================================================================
with tab_pack:
    st.markdown("### Step 3: Evidence Pack Summary & Export")

    if not current_order:
        st.warning("No active order found. Please complete Step 1 or load a demo order.")
    else:
        order_tasks = db.get_tasks_for_order(current_order["id"])

        total_tasks = len(order_tasks)
        passed_count = sum(1 for t in order_tasks if t.get("status") == "Passed")
        confirmed_count = sum(1 for t in order_tasks if t.get("status") == "User-confirmed")
        partial_count = sum(1 for t in order_tasks if t.get("status") == "Partial")
        retake_count = sum(1 for t in order_tasks if t.get("status") == "Retake")
        open_count = sum(1 for t in order_tasks if t.get("status") == "Open")

        ready_count = passed_count + confirmed_count
        readiness_pct = int(round((ready_count / total_tasks * 100))) if total_tasks > 0 else 0

        # Readiness Metric Card
        r_col1, r_col2 = st.columns([1, 2])
        with r_col1:
            st.metric("Evidence Readiness", f"{readiness_pct}%")
            if readiness_pct == 100:
                st.success("All evidence checklist tasks completed!")
            elif readiness_pct >= 50:
                st.info("Evidence is partially compiled.")
            else:
                st.warning("More evidence photos are recommended before sharing with support.")

        with r_col2:
            st.markdown(
                f"""
                **Evidence Task Status Breakdown:**
                - Machine-Verified Passed: **{passed_count}**
                - User-Confirmed: **{confirmed_count}**
                - Partial (minor warnings): **{partial_count}**
                - Retake Suggested: **{retake_count}**
                - Awaiting Upload: **{open_count}**
                """
            )

        st.markdown("---")
        st.markdown("#### Evidence Items Summary")

        summary_rows = []
        for t in order_tasks:
            summary_rows.append({
                "Task": t.get("task_code"),
                "Shot Type": t.get("shot_type"),
                "Title": t.get("title"),
                "Status": t.get("status"),
                "Attempts": t.get("attempts", 0),
                "SHA-256 Hash": (t.get("photo_hash")[:16] + "...") if t.get("photo_hash") else "None",
            })

        st.dataframe(pd.DataFrame(summary_rows), width="stretch")

        st.caption("Note: 'User-confirmed' items are recorded as self-attested by the user and not machine-verified.")

        st.markdown("---")
        st.markdown("#### Generate PDF Evidence Pack")

        pdf_path = f"uploads/evidence_pack_{current_order['id']}.pdf"

        if st.button("📄 Generate Evidence PDF", type="primary", width="stretch"):
            with st.spinner("Compiling structured evidence pack PDF..."):
                gen_path = report.generate_evidence_pdf(current_order, order_tasks, pdf_path)
                st.session_state["pdf_ready_path"] = gen_path
                st.success("Evidence PDF compiled successfully!")

        if st.session_state.get("pdf_ready_path") and os.path.isfile(st.session_state["pdf_ready_path"]):
            with open(st.session_state["pdf_ready_path"], "rb") as pf:
                pdf_bytes = pf.read()

            st.download_button(
                label="📥 Download Evidence Pack PDF",
                data=pdf_bytes,
                file_name=f"PatternProof_Evidence_{current_order.get('order_id', 'pack')}.pdf",
                mime="application/pdf",
                width="stretch"
            )

        st.markdown("---")
        st.info("💡 **Next Step**: You may wish to share this PDF evidence pack with the delivery platform's customer support team.")


# =========================================================================
# FOOTER ON EVERY VIEW
# =========================================================================
st.markdown(
    f'<div class="footer-disclaimer">{FOOTER_DISCLAIMER}</div>',
    unsafe_allow_html=True
)

# =========================================================================
# GUIDED DEMO (SIMULATED)
# =========================================================================
from demo_flow import render_guided_demo

render_guided_demo()

# =========================================================================
# AI RETURN ASSISTANT (INTERACTIVE CHATBOT)
# =========================================================================
from chat_assistant import render_chat_assistant

render_chat_assistant()
