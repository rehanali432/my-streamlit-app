"""ProofLoop: Visual Return Assistant.

AI-powered photographic inspection for e-commerce returns and exchanges.
Flow:
1. Customer uploads photo of the product.
2. AI analyzes photo, detects product and current angle, and specifies the missing angle/detail needed.
3. Customer uploads the requested complementary angle photo.
4. AI inspects both photos together and issues the return verdict ('Request verified, return request accepted').
5. Customer downloads official Return Authorization Slip (PDF).
"""

import os
import io
import json
import random
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, List

import streamlit as st
from PIL import Image, ImageDraw

import ai
import report

# Page Configuration
st.set_page_config(
    page_title="ProofLoop: Visual Return Assistant",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme with #FF5C1F ProofLoop orange accent
CUSTOM_CSS = """
<style>
    :root {
        --accent-orange: #FF5C1F;
        --bg-dark: #0E1117;
        --card-bg: #1A1F2C;
        --card-border: #2B3245;
        --text-primary: #E0E6ED;
        --text-muted: #8E9BAE;
        --success-green: #2ECC71;
    }

    .stApp {
        background-color: var(--bg-dark);
        color: var(--text-primary);
    }

    /* Main Header */
    .app-header {
        padding: 0.5rem 0 1.25rem 0;
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
        margin-top: 0.25rem;
    }

    /* Stepper Header */
    .step-pill {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-right: 0.5rem;
    }
    .step-active {
        background-color: rgba(255, 92, 31, 0.2);
        color: var(--accent-orange);
        border: 1px solid var(--accent-orange);
    }
    .step-completed {
        background-color: rgba(46, 204, 113, 0.2);
        color: var(--success-green);
        border: 1px solid var(--success-green);
    }
    .step-pending {
        background-color: rgba(142, 155, 174, 0.1);
        color: var(--text-muted);
        border: 1px solid var(--card-border);
    }

    /* Feature Cards */
    .feature-card {
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 1.35rem;
        margin-bottom: 1.25rem;
    }

    /* AI Task Box */
    .ai-request-box {
        background: linear-gradient(135deg, rgba(255, 92, 31, 0.08) 0%, rgba(26, 31, 44, 0.95) 100%);
        border: 1px solid rgba(255, 92, 31, 0.4);
        border-radius: 10px;
        padding: 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1.25rem;
    }

    /* Success / Accepted Banner */
    .accepted-banner {
        background: linear-gradient(135deg, rgba(46, 204, 113, 0.15) 0%, rgba(26, 31, 44, 0.95) 100%);
        border: 2px solid var(--success-green);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .accepted-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--success-green);
        margin: 0 0 0.5rem 0;
    }
    .rma-badge {
        display: inline-block;
        background-color: rgba(46, 204, 113, 0.2);
        color: #A9DFBF;
        border: 1px solid var(--success-green);
        padding: 0.35rem 1rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 1rem;
        letter-spacing: 0.75px;
    }

    /* Badges */
    .badge-tag {
        display: inline-block;
        background-color: rgba(255, 92, 31, 0.15);
        color: var(--accent-orange);
        border: 1px solid rgba(255, 92, 31, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
    }

    /* Retake Alert */
    .retake-banner {
        background-color: rgba(231, 76, 60, 0.15);
        border: 1px solid #E74C3C;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        color: #FADBD8;
    }

    /* Footer */
    .app-footer {
        text-align: center;
        color: var(--text-muted);
        font-size: 0.82rem;
        padding: 2rem 0 1rem 0;
        border-top: 1px solid var(--card-border);
        margin-top: 3rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================================================================
# SYNTHETIC TEST SAMPLE GENERATORS (FOR 1-CLICK TESTING)
# =========================================================================

def _generate_sample_mouse_top() -> bytes:
    """Generate synthetic top-view computer mouse photo in memory."""
    w, h = 500, 380
    img = Image.new("RGB", (w, h), color=(30, 36, 48))
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, w - 15, h - 15], fill=(40, 48, 64), outline=(70, 82, 105), width=2)
    # Mouse body
    draw.ellipse([170, 50, 330, 310], fill=(235, 240, 248), outline=(180, 195, 210), width=3)
    # Split & scroll wheel
    draw.line([250, 50, 250, 160], fill=(80, 95, 115), width=3)
    draw.rectangle([242, 80, 258, 130], fill=(255, 92, 31), outline=(200, 60, 10), width=2)
    draw.text((205, 210), "PROOFLOOP", fill=(100, 115, 135))
    draw.text((150, 335), "SAMPLE PRODUCT: Mouse (Top View)", fill=(200, 210, 225))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _generate_sample_mouse_underside() -> bytes:
    """Generate synthetic underside computer mouse photo in memory."""
    w, h = 500, 380
    img = Image.new("RGB", (w, h), color=(26, 32, 44))
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, w - 15, h - 15], fill=(36, 44, 60), outline=(60, 72, 95), width=2)
    # Base body
    draw.ellipse([170, 50, 330, 310], fill=(45, 54, 70), outline=(120, 135, 155), width=3)
    # Glides
    draw.arc([190, 60, 310, 95], start=180, end=360, fill=(20, 20, 25), width=6)
    draw.arc([195, 270, 305, 300], start=0, end=180, fill=(20, 20, 25), width=6)
    # Sensor aperture
    draw.ellipse([235, 150, 265, 190], fill=(255, 92, 31), outline=(255, 255, 255), width=2)
    # Specification label
    draw.rectangle([200, 210, 300, 260], fill=(20, 24, 32), outline=(100, 115, 130))
    draw.text((210, 218), "S/N: PL-8921", fill=(170, 180, 195))
    draw.text((210, 235), "Model: M-100", fill=(170, 180, 195))
    draw.text((130, 335), "SAMPLE COMPLEMENTARY: Mouse Underside", fill=(46, 204, 113))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# =========================================================================
# SESSION STATE INITIALIZATION
# =========================================================================

def init_app_state() -> None:
    """Ensure clean session state variables."""
    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 1  # 1: Upload, 2: Angle Request, 3: Verdict

    if "nonce_img1" not in st.session_state:
        st.session_state["nonce_img1"] = 0
    if "nonce_img2" not in st.session_state:
        st.session_state["nonce_img2"] = 0

    if "img1_bytes" not in st.session_state:
        st.session_state["img1_bytes"] = None
    if "img2_bytes" not in st.session_state:
        st.session_state["img2_bytes"] = None

    if "step1_analysis" not in st.session_state:
        st.session_state["step1_analysis"] = None
    if "return_verdict" not in st.session_state:
        st.session_state["return_verdict"] = None

    if "claim_reason" not in st.session_state:
        st.session_state["claim_reason"] = "Damaged during transit"

    if "pdf_download_path" not in st.session_state:
        st.session_state["pdf_download_path"] = None

    if "sidebar_key_override" not in st.session_state:
        st.session_state["sidebar_key_override"] = ""
    if "demo_mode_toggle" not in st.session_state:
        st.session_state["demo_mode_toggle"] = False


init_app_state()

# Determine active API Key and Simulation State
sidebar_key = st.session_state.get("sidebar_key_override", "").strip()
detected_api_key = ai.get_api_key(sidebar_key)
is_demo_mode = st.session_state.get("demo_mode_toggle", False) or (detected_api_key is None)


# =========================================================================
# SIDEBAR
# =========================================================================

with st.sidebar:
    st.markdown("### 🔄 ProofLoop")
    st.markdown("**Visual Return Assistant**")
    st.caption("Multi-angle visual inspection for fast return approval")

    st.markdown("---")

    # API Connection Status
    if detected_api_key:
        st.success("● Gemini Vision Active (3.1 Flash)")
    else:
        st.info("○ Demo Mode (Simulated AI Active)")

    with st.expander("🔑 Gemini API Settings"):
        key_input = st.text_input(
            "API Key Override",
            value=st.session_state.get("sidebar_key_override", ""),
            type="password",
            placeholder="AIzaSy...",
            help="Optional. If left blank, uses system .env or st.secrets."
        )
        if key_input != st.session_state.get("sidebar_key_override", ""):
            st.session_state["sidebar_key_override"] = key_input
            st.rerun()

    demo_toggle = st.toggle(
        "Simulated AI Mode",
        value=st.session_state.get("demo_mode_toggle", False),
        help="Simulates visual inspection with pre-computed smart responses (no API tokens consumed)."
    )
    if demo_toggle != st.session_state.get("demo_mode_toggle", False):
        st.session_state["demo_mode_toggle"] = demo_toggle
        st.rerun()

    st.markdown("---")

    # Quick Sample Loaders for Testing
    st.markdown("#### ⚡ 1-Click Test Scenarios")
    if st.button("Load Sample Mouse (Top View)", width="stretch"):
        st.session_state["img1_bytes"] = _generate_sample_mouse_top()
        st.session_state["img2_bytes"] = None
        st.session_state["step1_analysis"] = None
        st.session_state["return_verdict"] = None
        st.session_state["current_step"] = 1
        st.session_state["nonce_img1"] += 1
        st.session_state["nonce_img2"] += 1
        st.success("Sample computer mouse loaded!")
        st.rerun()

    if st.session_state.get("current_step", 1) >= 2:
        if st.button("Load Sample Underside View", width="stretch"):
            st.session_state["img2_bytes"] = _generate_sample_mouse_underside()
            st.session_state["nonce_img2"] += 1
            st.success("Sample mouse underside loaded!")
            st.rerun()

    st.markdown("---")

    # Global Reset Button
    if st.button("🔄 Start New Return", width="stretch", type="secondary"):
        st.session_state["current_step"] = 1
        st.session_state["img1_bytes"] = None
        st.session_state["img2_bytes"] = None
        st.session_state["step1_analysis"] = None
        st.session_state["return_verdict"] = None
        st.session_state["pdf_download_path"] = None
        st.session_state["nonce_img1"] += 1
        st.session_state["nonce_img2"] += 1
        st.rerun()


# =========================================================================
# HEADER & STEP PROGRESS INDICATOR
# =========================================================================

header_col1, header_col2 = st.columns([4, 2])
with header_col1:
    st.markdown(
        '<div class="app-header">'
        '<div class="app-title">ProofLoop <span>Visual Return Assistant</span></div>'
        '<div class="app-subtitle">Upload product photos, complete the AI-guided angle inspection, and receive an instant verified return decision.</div>'
        '</div>',
        unsafe_allow_html=True
    )
with header_col2:
    if is_demo_mode:
        st.markdown(
            '<div style="text-align: right; padding-top: 1.25rem;">'
            '<span class="step-pill step-active">⚡ DEMO MODE: Simulated AI</span>'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="text-align: right; padding-top: 1.25rem;">'
            '<span class="step-pill step-completed">● LIVE AI: Gemini Vision</span>'
            '</div>',
            unsafe_allow_html=True
        )

# Stepper Visual Bar
step = st.session_state.get("current_step", 1)
s1_class = "step-completed" if step > 1 else ("step-active" if step == 1 else "step-pending")
s2_class = "step-completed" if step > 2 else ("step-active" if step == 2 else "step-pending")
s3_class = "step-completed" if step == 3 else "step-pending"

st.markdown(
    f'<div style="margin-bottom: 1.5rem;">'
    f'<span class="step-pill {s1_class}">1. Product Photo</span>'
    f'<span style="color: #606878; margin-right: 0.5rem;">➔</span>'
    f'<span class="step-pill {s2_class}">2. Missing Angle Inspection</span>'
    f'<span style="color: #606878; margin-right: 0.5rem;">➔</span>'
    f'<span class="step-pill {s3_class}">3. Verified Return Decision</span>'
    f'</div>',
    unsafe_allow_html=True
)


# =========================================================================
# STEP 1: INITIAL PRODUCT PHOTO UPLOAD & ANALYSIS
# =========================================================================

st.markdown('<div class="feature-card">', unsafe_allow_html=True)
st.markdown("### Step 1: Upload Product Photo")
st.caption("Take or upload an initial photo of the product you wish to return or exchange:")

col_form1, col_form2 = st.columns([1, 2])
with col_form1:
    claim_reason_options = [
        "Damaged during transit",
        "Defective / Does not function",
        "Wrong item delivered",
        "Cosmetic defect / Scratched",
        "Broken seal / Leaking packaging"
    ]
    selected_reason = st.selectbox(
        "Return Reason",
        options=claim_reason_options,
        index=claim_reason_options.index(st.session_state.get("claim_reason", claim_reason_options[0]))
    )
    st.session_state["claim_reason"] = selected_reason

with col_form2:
    st.info("💡 **Tip**: Hold the camera 20-30 cm away in good lighting so the product is clearly visible.")

col_upload1, col_upload2 = st.columns([1, 1])

with col_upload1:
    tab_f1, tab_c1 = st.tabs(["📁 Upload Image", "📷 Live Camera"])

    new_img1 = None
    with tab_f1:
        nonce1 = st.session_state.get("nonce_img1", 0)
        up_file1 = st.file_uploader(
            "Select product photo (PNG, JPG)",
            type=["png", "jpg", "jpeg"],
            key=f"uploader_step1_{nonce1}"
        )
        if up_file1 is not None:
            new_img1 = up_file1.getvalue()

    with tab_c1:
        cam_file1 = st.camera_input("Capture product photo", key=f"camera_step1_{nonce1}")
        if cam_file1 is not None:
            new_img1 = cam_file1.getvalue()

    if new_img1:
        st.session_state["img1_bytes"] = new_img1

with col_upload2:
    active_img1 = st.session_state.get("img1_bytes")
    if active_img1:
        st.image(active_img1, caption="Uploaded Product Photo", width="stretch")
        if st.button("🗑️ Remove Photo", key="btn_clear_img1", width="stretch"):
            st.session_state["img1_bytes"] = None
            st.session_state["step1_analysis"] = None
            st.session_state["current_step"] = 1
            st.session_state["nonce_img1"] += 1
            st.rerun()
    else:
        st.markdown(
            '<div style="border: 2px dashed #2B3245; border-radius: 10px; padding: 3rem 1rem; text-align: center; color: #8E9BAE;">'
            '📷 No photo selected yet.<br/>Upload an image on the left or click <strong>Load Sample Mouse</strong> in the sidebar.'
            '</div>',
            unsafe_allow_html=True
        )

# Action button to trigger AI analysis
if active_img1 is not None:
    st.markdown("---")
    btn_col1, btn_col2 = st.columns([2, 1])
    with btn_col1:
        if st.button("🔍 Analyze Product Photo with AI ➔", type="primary", width="stretch"):
            with st.spinner("AI checking photo and detecting product angle..."):
                analysis_res, err = ai.analyze_product_for_return(
                    active_img1,
                    user_claim=selected_reason,
                    api_key=detected_api_key,
                    mock=is_demo_mode
                )
                if err and not is_demo_mode:
                    st.warning("Live AI notice: Falling back to smart analysis engine.")
                st.session_state["step1_analysis"] = analysis_res
                st.session_state["current_step"] = 2
                st.success("Product identified! Unlocking Step 2...")
                st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# STEP 2: AI OBSERVATION & COMPLEMENTARY ANGLE REQUEST
# =========================================================================

step1_data = st.session_state.get("step1_analysis")
if step >= 2 and step1_data:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
    st.markdown("### Step 2: AI Inspection & Requested Missing Angle")

    # Display AI Detection Summary
    obs_col1, obs_col2 = st.columns([1, 2])
    with obs_col1:
        st.markdown(f"**Product Found**: `{step1_data.get('product_name', 'Product')}`")
        st.markdown(f"**Category**: {step1_data.get('category', 'Goods')}")
        st.markdown(f"**Angle Received**: `{step1_data.get('current_angle', 'Top View')}`")

    with obs_col2:
        st.markdown(f"**AI Visual Observation**:")
        st.write(step1_data.get("visible_observations", "Initial perspective recorded."))

    # Interactive AI Request Box
    req_title = step1_data.get("requested_angle_title", "Complementary View")
    req_inst = step1_data.get("requested_angle_instruction", "Please take a photo from below.")
    req_checklist = step1_data.get("required_checklist", ["Clear view", "Underside visible", "Good lighting"])

    checklist_badges = "".join([f'<span class="badge-tag">✓ {item}</span>' for item in req_checklist])

    st.markdown(
        f'<div class="ai-request-box">'
        f'<div style="font-size: 0.82rem; text-transform: uppercase; font-weight: 700; color: #FF5C1F; margin-bottom: 0.3rem;">🤖 AI Verification Bot</div>'
        f'<h4 style="margin: 0 0 0.5rem 0; color: #FFFFFF;">Action Required: {req_title}</h4>'
        f'<p style="color: #E0E6ED; font-size: 0.95rem; margin-bottom: 0.8rem;">{req_inst}</p>'
        f'<div>{checklist_badges}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Angle 2 Upload Interface
    st.markdown("#### Upload Requested Photo")
    up2_col1, up2_col2 = st.columns([1, 1])

    with up2_col1:
        tab_f2, tab_c2 = st.tabs(["📁 Upload Image", "📷 Live Camera"])

        new_img2 = None
        with tab_f2:
            nonce2 = st.session_state.get("nonce_img2", 0)
            up_file2 = st.file_uploader(
                f"Upload photo for: {req_title}",
                type=["png", "jpg", "jpeg"],
                key=f"uploader_step2_{nonce2}"
            )
            if up_file2 is not None:
                new_img2 = up_file2.getvalue()

        with tab_c2:
            cam_file2 = st.camera_input(f"Capture {req_title}", key=f"camera_step2_{nonce2}")
            if cam_file2 is not None:
                new_img2 = cam_file2.getvalue()

        if new_img2:
            st.session_state["img2_bytes"] = new_img2

    with up2_col2:
        active_img2 = st.session_state.get("img2_bytes")
        if active_img2:
            st.image(active_img2, caption=f"Secondary Photo ({req_title})", width="stretch")
            if st.button("🗑️ Remove Angle Photo", key="btn_clear_img2", width="stretch"):
                st.session_state["img2_bytes"] = None
                st.session_state["return_verdict"] = None
                st.session_state["nonce_img2"] += 1
                st.rerun()
        else:
            st.markdown(
                '<div style="border: 2px dashed #2B3245; border-radius: 10px; padding: 2.5rem 1rem; text-align: center; color: #8E9BAE;">'
                '📷 Awaiting requested angle photo.<br/>Upload the photo above or click <strong>Load Sample Underside View</strong> in the sidebar.'
                '</div>',
                unsafe_allow_html=True
            )

    # Verification Trigger Button
    if active_img2 is not None and active_img1 is not None:
        st.markdown("---")
        if st.button("✅ Verify Both Photos & Process Return ➔", type="primary", width="stretch"):
            with st.spinner("AI cross-referencing both photos for physical consistency and return criteria..."):
                verdict, err = ai.verify_both_angles_for_return(
                    active_img1,
                    active_img2,
                    step1_data,
                    api_key=detected_api_key,
                    mock=is_demo_mode
                )
                st.session_state["return_verdict"] = verdict
                st.session_state["current_step"] = 3

                # Pre-generate PDF return slip
                slip_pdf_path = f"uploads/return_slip_{verdict.get('rma_code', 'PL-RET')}.pdf"
                try:
                    report.generate_return_slip_pdf(
                        verdict,
                        step1_data,
                        active_img1,
                        active_img2,
                        output_path=slip_pdf_path
                    )
                    st.session_state["pdf_download_path"] = slip_pdf_path
                except Exception:
                    pass

                st.success("Verification complete!")
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# STEP 3: VERIFIED DECISION & OFFICIAL RETURN SLIP
# =========================================================================

verdict_data = st.session_state.get("return_verdict")
if step == 3 and verdict_data:
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)

    is_accepted = verdict_data.get("decision", "ACCEPTED") == "ACCEPTED"
    rma_number = verdict_data.get("rma_code", f"PL-RET-{random.randint(10000, 99999)}")

    if is_accepted:
        st.markdown(
            f'<div class="accepted-banner">'
            f'<div class="accepted-title">🎉 Request Verified — Return Request Accepted!</div>'
            f'<div style="color: #E0E6ED; font-size: 1.05rem; margin-bottom: 0.8rem;">'
            f'Both photographic angles have been visually validated and cross-referenced.'
            f'</div>'
            f'<span class="rma-badge">AUTHORIZATION RMA: {rma_number}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown(f"**Verification Summary:** {verdict_data.get('summary', '')}")

        # Visual Side-by-Side Comparison
        st.markdown("#### Cross-Referenced Evidence:")
        gal_col1, gal_col2 = st.columns(2)
        with gal_col1:
            if st.session_state.get("img1_bytes"):
                st.image(
                    st.session_state["img1_bytes"],
                    caption=f"1. Initial Angle: {step1_data.get('current_angle', 'Primary')}",
                    width="stretch"
                )
        with gal_col2:
            if st.session_state.get("img2_bytes"):
                st.image(
                    st.session_state["img2_bytes"],
                    caption=f"2. Verified Angle: {step1_data.get('requested_angle_title', 'Complementary')}",
                    width="stretch"
                )

        # Audit Trail Checks
        st.markdown("#### Automated Verification Checks:")
        checks = verdict_data.get("checks", [])
        for chk in checks:
            chk_status = chk.get("status", "pass")
            icon = "✅" if chk_status == "pass" else "❌"
            st.markdown(f"{icon} **{chk.get('name', 'Check')}**: {chk.get('detail', '')}")

        st.markdown("---")

        # Action Buttons: Download PDF Slip or Start New Return
        act_col1, act_col2 = st.columns([1, 1])
        with act_col1:
            pdf_path = st.session_state.get("pdf_download_path")
            if pdf_path and os.path.isfile(pdf_path):
                with open(pdf_path, "rb") as pf:
                    pdf_bytes = pf.read()
                st.download_button(
                    label="📥 Download Return Authorization Slip (PDF)",
                    data=pdf_bytes,
                    file_name=f"ProofLoop_Return_{rma_number}.pdf",
                    mime="application/pdf",
                    type="primary",
                    width="stretch"
                )
            else:
                st.info("Return slip ready for pickup verification.")

        with act_col2:
            if st.button("➕ Start Another Return", width="stretch"):
                st.session_state["current_step"] = 1
                st.session_state["img1_bytes"] = None
                st.session_state["img2_bytes"] = None
                st.session_state["step1_analysis"] = None
                st.session_state["return_verdict"] = None
                st.session_state["pdf_download_path"] = None
                st.session_state["nonce_img1"] += 1
                st.session_state["nonce_img2"] += 1
                st.rerun()

    else:
        # Retake Suggested
        st.markdown(
            f'<div class="retake-banner">'
            f'<h3 style="margin: 0 0 0.5rem 0;">⚠️ Verification Incomplete: Retake Suggested</h3>'
            f'<p>{verdict_data.get("reason", "The provided photos did not meet the clear angle or visibility criteria.")}</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("#### Checks Outcome:")
        for chk in verdict_data.get("checks", []):
            icon = "✅" if chk.get("status") == "pass" else "❌"
            st.markdown(f"{icon} **{chk.get('name', '')}**: {chk.get('detail', '')}")

        st.markdown("---")
        if st.button("🔄 Retake Secondary Photo", type="primary", width="stretch"):
            st.session_state["img2_bytes"] = None
            st.session_state["return_verdict"] = None
            st.session_state["current_step"] = 2
            st.session_state["nonce_img2"] += 1
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================================
# FOOTER
# =========================================================================

st.markdown(
    '<div class="app-footer">'
    'ProofLoop Automated Visual Return System • Built with Gemini Vision & Streamlit'
    '</div>',
    unsafe_allow_html=True
)
