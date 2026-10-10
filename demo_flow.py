"""Simulated ProofLoop Guided Verification Demo.

Interactive, scripted walkthrough demonstrating the product detection and
missing angle request workflow without live AI API calls.
"""

import io
import time
from typing import Optional
import streamlit as st
from PIL import Image

# =========================================================================
# CONSTANTS
# =========================================================================

FIRST_UPLOAD_LABEL = "Upload a photo of the item from above (top view)"

PROCESSING_STEPS = [
    "Reading the photo...",
    "Detecting the product...",
    "Product found: computer mouse (top view)...",
    "Checking which angles are still needed...",
    "Preparing your photo task..."
]

DETECTION_SUMMARY = (
    "Top view received. Product detected: computer mouse. "
    "The top surface and buttons are visible. "
    "The underside is not visible in this photo."
)

TASK_TITLE = "Photograph the underside of the mouse"

TASK_INSTRUCTION = (
    "Turn the mouse over and take a photo of the bottom from about "
    "15 to 25 cm, in even light, with the damaged area, the sensor "
    "opening and the base label in frame."
)

TASK_REQUIREMENTS = [
    "Underside of the mouse is visible",
    "The damaged area is in frame",
    "Sensor opening and base label are in frame",
    "Photo is sharp and well lit"
]

SECOND_UPLOAD_LABEL = "Upload the photo of the underside"

SCANNING_STEPS = [
    "Checking image quality...",
    "Locating the underside of the mouse...",
    "Locating the damaged area...",
    "Comparing against task requirements...",
    "Finalising result..."
]

RESULT_TEXT = (
    "Scanned. This photo is valid for this task: "
    "the underside and the damaged area are in frame."
)

# Custom CSS for the guided demo section
GUIDED_DEMO_CSS = """
<style>
    .gd-container {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 2px dashed #2B3245;
    }
    .gd-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .gd-badge-simulated {
        display: inline-block;
        background-color: rgba(255, 92, 31, 0.15);
        color: #FF5C1F;
        border: 1px solid #FF5C1F;
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
    }
    .gd-badge-angle {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .gd-badge-covered {
        background-color: rgba(46, 204, 113, 0.15);
        color: #2ECC71;
        border: 1px solid #2ECC71;
    }
    .gd-badge-needed {
        background-color: rgba(255, 92, 31, 0.15);
        color: #FF5C1F;
        border: 1px solid #FF5C1F;
    }
    .gd-info-card {
        background-color: #141A28;
        border-left: 4px solid #3498DB;
        border-radius: 6px;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
    }
    .gd-task-card {
        background-color: #1A1F2C;
        border: 1px solid #FF5C1F;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 1rem 0;
    }
    .gd-result-card {
        background-color: #14221A;
        border: 1px solid #2ECC71;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 1rem 0;
    }
    .gd-badge-open {
        background-color: rgba(243, 156, 18, 0.15);
        color: #F39C12;
        border: 1px solid #F39C12;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .gd-badge-valid {
        background-color: rgba(46, 204, 113, 0.2);
        color: #2ECC71;
        border: 1px solid #2ECC71;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
    }
</style>
"""


def _load_and_resize_thumbnail(file_bytes: bytes, max_width: int = 320) -> Optional[Image.Image]:
    """Load image safely from memory, convert to RGB, and resize thumbnail."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        # Re-open after verify
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w > max_width:
            scale = float(max_width) / float(w)
            new_size = (max_width, max(1, int(round(h * scale))))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        return img
    except Exception:
        return None


def render_guided_demo() -> None:
    """Render the Guided Demo (simulated) section at the bottom of the app."""
    # Inject styling
    st.markdown(GUIDED_DEMO_CSS, unsafe_allow_html=True)

    # Initialize guided demo state
    if "gd_step" not in st.session_state:
        st.session_state["gd_step"] = 1
    if "gd_img1_bytes" not in st.session_state:
        st.session_state["gd_img1_bytes"] = None
    if "gd_img2_bytes" not in st.session_state:
        st.session_state["gd_img2_bytes"] = None

    current_step = st.session_state.get("gd_step", 1)

    # Main Section Header
    st.markdown('<div class="gd-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="gd-header">'
        '<h3 style="margin: 0; color: #FFFFFF;">Guided Demo (simulated)</h3>'
        '<span class="gd-badge-simulated">SIMULATED DEMO: scripted output, no live AI</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.caption("This walkthrough shows the flow. The real checks run in the sections above.")
    st.markdown("---")

    # =====================================================================
    # STEP 1: INITIAL PHOTO UPLOAD
    # =====================================================================
    st.markdown("#### Step 1: Initial Item Photo")
    st.write("Upload a top-down overview photo of the computer mouse.")

    uploaded_initial = st.file_uploader(
        FIRST_UPLOAD_LABEL,
        type=["png", "jpg", "jpeg"],
        key="gd_uploader_1"
    )

    if uploaded_initial is not None:
        try:
            raw_bytes = uploaded_initial.getvalue()
            thumb = _load_and_resize_thumbnail(raw_bytes, max_width=320)
            if thumb is not None:
                st.session_state["gd_img1_bytes"] = raw_bytes
                st.image(thumb, caption="Initial Photo Preview (top view)", width=320)
            else:
                st.error("Could not read image file. Please provide an intact PNG or JPEG image.")
                st.session_state["gd_img1_bytes"] = None
        except Exception:
            st.error("Invalid image upload. Please select a valid photo.")
            st.session_state["gd_img1_bytes"] = None
    elif st.session_state.get("gd_img1_bytes"):
        thumb = _load_and_resize_thumbnail(st.session_state["gd_img1_bytes"], max_width=320)
        if thumb is not None:
            st.image(thumb, caption="Initial Photo Preview (top view)", width=320)

    # Step 1 Button: Analyse photo
    if current_step == 1:
        can_analyse = st.session_state.get("gd_img1_bytes") is not None
        if st.button("🔍 Analyse photo", key="gd_btn_analyse", type="primary", width="stretch", disabled=not can_analyse):
            with st.status("Processing...", expanded=True) as status_box:
                for step_text in PROCESSING_STEPS:
                    st.write(step_text)
                    time.sleep(0.7)
                status_box.update(label="Processing complete", state="complete", expanded=False)

            st.session_state["gd_step"] = 2
            st.rerun()

    # =====================================================================
    # STEP 2 & 3: DETECTION SUMMARY (rendered if gd_step >= 2)
    # =====================================================================
    if current_step >= 2:
        st.markdown("---")
        st.markdown("#### Step 2: Product & Angle Detection")

        # Blue info card
        st.markdown(
            f'<div class="gd-info-card">'
            f'<p style="margin: 0 0 0.6rem 0; color: #E0E6ED; line-height: 1.5;">{DETECTION_SUMMARY}</p>'
            f'<div>'
            f'<span class="gd-badge-angle gd-badge-covered">✓ Angle covered: Top</span>'
            f'<span class="gd-badge-angle gd-badge-needed">● Angle needed: Underside</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # =================================================================
        # STEP 4: GENERATED TASK CARD
        # =================================================================
        st.markdown("#### Step 3: Generated Photo Task")

        task_badge_html = '<span class="gd-badge-valid">✓ Completed</span>' if current_step >= 3 else '<span class="gd-badge-open">○ Open</span>'

        checklist_items_html = "".join([f"<li style='margin-bottom: 0.25rem;'>{req}</li>" for req in TASK_REQUIREMENTS])

        st.markdown(
            f'<div class="gd-task-card">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">'
            f'<h4 style="margin: 0; color: #FFFFFF;">{TASK_TITLE}</h4>'
            f'{task_badge_html}'
            f'</div>'
            f'<p style="color: #FF5C1F; font-size: 0.85rem; font-weight: 600; margin: 0 0 0.5rem 0;">Needed: bottom view</p>'
            f'<p style="color: #C5D0DE; font-size: 0.93rem; margin: 0 0 0.75rem 0; line-height: 1.45;">{TASK_INSTRUCTION}</p>'
            f'<strong style="color: #E0E6ED; font-size: 0.88rem;">Task Requirements:</strong>'
            f'<ul style="color: #8E9BAE; font-size: 0.88rem; margin: 0.4rem 0 0 1.2rem;">{checklist_items_html}</ul>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Second Upload Section (Underside Photo)
        if current_step == 2:
            st.markdown("##### Upload Requested Photo")
            uploaded_second = st.file_uploader(
                SECOND_UPLOAD_LABEL,
                type=["png", "jpg", "jpeg"],
                key="gd_uploader_2"
            )

            if uploaded_second is not None:
                try:
                    raw_bytes_2 = uploaded_second.getvalue()
                    thumb_2 = _load_and_resize_thumbnail(raw_bytes_2, max_width=320)
                    if thumb_2 is not None:
                        st.session_state["gd_img2_bytes"] = raw_bytes_2
                        st.image(thumb_2, caption="Underside Photo Preview", width=320)
                    else:
                        st.error("Could not read image file. Please provide an intact PNG or JPEG image.")
                        st.session_state["gd_img2_bytes"] = None
                except Exception:
                    st.error("Invalid image upload. Please select a valid photo.")
                    st.session_state["gd_img2_bytes"] = None
            elif st.session_state.get("gd_img2_bytes"):
                thumb_2 = _load_and_resize_thumbnail(st.session_state["gd_img2_bytes"], max_width=320)
                if thumb_2 is not None:
                    st.image(thumb_2, caption="Underside Photo Preview", width=320)

            # Step 5 Button: Scan photo
            can_scan = st.session_state.get("gd_img2_bytes") is not None
            if st.button("📸 Scan photo", key="gd_btn_scan", type="primary", width="stretch", disabled=not can_scan):
                with st.status("Scanning...", expanded=True) as scan_status:
                    for scan_text in SCANNING_STEPS:
                        st.write(scan_text)
                        time.sleep(0.7)
                    scan_status.update(label="Scan complete", state="complete", expanded=False)

                st.session_state["gd_step"] = 3
                st.rerun()

    # =====================================================================
    # STEP 6: RESULT CARD (rendered if gd_step >= 3)
    # =====================================================================
    if current_step >= 3:
        st.markdown("---")
        st.markdown("#### Step 4: Verification Result")

        # Show second thumbnail if available
        if st.session_state.get("gd_img2_bytes"):
            thumb_2 = _load_and_resize_thumbnail(st.session_state["gd_img2_bytes"], max_width=320)
            if thumb_2 is not None:
                st.image(thumb_2, caption="Verified Photo: Underside View", width=320)

        # Green success card
        completed_checklist_html = "".join([
            f"<li style='color: #2ECC71; margin-bottom: 0.35rem; list-style-type: none;'>"
            f"✓ <span style='color: #E0E6ED;'>{req}</span></li>"
            for req in TASK_REQUIREMENTS
        ])

        st.markdown(
            f'<div class="gd-result-card">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">'
            f'<strong style="color: #2ECC71; font-size: 1.05rem;">Simulated Inspection Complete</strong>'
            f'<span class="gd-badge-valid">Valid</span>'
            f'</div>'
            f'<p style="color: #E0E6ED; margin: 0 0 0.8rem 0; line-height: 1.5;">{RESULT_TEXT}</p>'
            f'<strong style="color: #A0C2AD; font-size: 0.88rem;">Requirements Evaluation:</strong>'
            f'<ul style="margin: 0.4rem 0 0 0.2rem; padding: 0;">{completed_checklist_html}</ul>'
            f'</div>',
            unsafe_allow_html=True
        )

        # Angles covered summary
        st.markdown("**Angles covered: Top, Underside (2 of 2)**")
        st.markdown(
            '<div>'
            '<span class="gd-badge-angle gd-badge-covered">✓ Angle covered: Top</span>'
            '<span class="gd-badge-angle gd-badge-covered">✓ Angle covered: Underside</span>'
            '</div>',
            unsafe_allow_html=True
        )
        st.caption("Note: 'Valid' refers exclusively to completion of this simulated photo task and does not imply claim outcome.")

    # =====================================================================
    # STEP 7: RESTART
    # =====================================================================
    if current_step >= 2:
        st.markdown("---")
        if st.button("🔄 Restart demo", key="gd_btn_restart", width="stretch"):
            # Clear all gd_ session state keys
            keys_to_clear = [k for k in list(st.session_state.keys()) if k.startswith("gd_")]
            for k in keys_to_clear:
                del st.session_state[k]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
