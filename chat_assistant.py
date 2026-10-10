"""AI Return Assistant: Interactive Chatbot for ProofLoop.

Separate interactive conversational section allowing users to:
1. Upload a product photo.
2. Bot displays 'Checking...', then asks for another photo from a different angle (preferably from below).
3. User uploads the requested angle photo.
4. Bot displays 'Checking...', then confirms 'Request verified, return request accepted!'.
"""

import io
import time
from typing import Optional, List, Dict, Any
import streamlit as st
from PIL import Image, ImageDraw


def _make_chat_thumbnail(image_bytes: bytes, max_width: int = 320) -> Optional[Image.Image]:
    """Safely open image in memory, convert to RGB, and resize for chat display."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        img = Image.open(io.BytesIO(image_bytes))
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


def _create_sample_product_image() -> bytes:
    """Generate a clean synthetic top-view product photo in memory for quick testing."""
    width, height = 600, 500
    img = Image.new("RGB", (width, height), color=(30, 36, 48))
    draw = ImageDraw.Draw(img)

    # Surface table
    draw.rectangle([20, 20, width - 20, height - 20], fill=(42, 50, 66), outline=(60, 70, 90), width=2)

    # Product body (Computer Mouse Top View)
    mouse_body = [210, 100, 390, 400]
    draw.ellipse(mouse_body, fill=(230, 235, 245), outline=(180, 190, 205), width=3)

    # Mouse scroll wheel and button split
    draw.line([300, 100, 300, 240], fill=(70, 80, 100), width=3)
    draw.rectangle([290, 140, 310, 200], fill=(255, 92, 31), outline=(200, 60, 10), width=2)

    # Brand emblem
    draw.text((265, 300), "PROOFLOOP", fill=(100, 110, 130))
    draw.text((250, 420), "PRODUCT: Computer Mouse (Top View)", fill=(200, 210, 225))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_sample_underside_image() -> bytes:
    """Generate a clean synthetic underside product photo in memory for quick testing."""
    width, height = 600, 500
    img = Image.new("RGB", (width, height), color=(26, 32, 44))
    draw = ImageDraw.Draw(img)

    # Surface
    draw.rectangle([20, 20, width - 20, height - 20], fill=(36, 44, 60), outline=(55, 65, 85), width=2)

    # Product underside body
    mouse_base = [210, 100, 390, 400]
    draw.ellipse(mouse_base, fill=(45, 52, 68), outline=(120, 130, 150), width=3)

    # Gliding pads
    draw.arc([230, 110, 370, 150], start=180, end=360, fill=(20, 20, 25), width=8)
    draw.arc([240, 360, 360, 390], start=0, end=180, fill=(20, 20, 25), width=8)

    # Optical sensor aperture
    draw.ellipse([285, 230, 315, 270], fill=(255, 92, 31), outline=(255, 255, 255), width=2)
    draw.text((260, 205), "Optical Sensor", fill=(180, 190, 205))

    # Base specification label & damage marker
    draw.rectangle([250, 290, 350, 350], fill=(20, 24, 32), outline=(100, 110, 125))
    draw.text((260, 300), "S/N: PL-8921", fill=(160, 170, 185))
    draw.text((260, 320), "Model: M-100", fill=(160, 170, 185))

    # Visible damage marker near base edge
    draw.rectangle([340, 340, 385, 385], outline=(255, 92, 31), width=2)
    draw.text((290, 420), "UNDERSIDE VIEW (Base & Sensor Visible)", fill=(46, 204, 113))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


# Custom styling for chat assistant section
CHAT_ASSISTANT_CSS = """
<style>
    .chat-assistant-container {
        margin-top: 3.5rem;
        padding-top: 2rem;
        border-top: 2px solid #FF5C1F;
    }
    .chat-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .chat-badge {
        display: inline-block;
        background-color: rgba(255, 92, 31, 0.15);
        color: #FF5C1F;
        border: 1px solid #FF5C1F;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .chat-verified-card {
        background-color: #11261B;
        border: 1px solid #2ECC71;
        border-radius: 8px;
        padding: 1.25rem;
        margin-top: 1rem;
    }
    .chat-step-box {
        background-color: #1A1F2C;
        border: 1px solid #2B3245;
        border-radius: 8px;
        padding: 1.25rem;
        margin: 1rem 0;
    }
</style>
"""


def render_chat_assistant() -> None:
    """Render the AI Return Assistant Chatbot section."""
    st.markdown(CHAT_ASSISTANT_CSS, unsafe_allow_html=True)

    # Initialize chatbot session state keys
    if "cb_step" not in st.session_state:
        st.session_state["cb_step"] = 0  # 0: initial upload, 1: ask 2nd photo, 2: verified
    if "cb_photo1_bytes" not in st.session_state:
        st.session_state["cb_photo1_bytes"] = None
    if "cb_photo2_bytes" not in st.session_state:
        st.session_state["cb_photo2_bytes"] = None
    if "cb_messages" not in st.session_state:
        st.session_state["cb_messages"] = [
            {
                "role": "assistant",
                "content": "Hello! I am your AI Return Assistant. Please upload a photo of the product you are having an issue with to begin.",
                "image": None
            }
        ]

    # Section Header
    st.markdown('<div class="chat-assistant-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="chat-header-bar">'
        '<div>'
        '<h3 style="margin: 0; color: #FFFFFF;">🤖 AI Return Assistant (Interactive Chat)</h3>'
        '<p style="margin: 0.25rem 0 0 0; color: #8E9BAE; font-size: 0.95rem;">'
        'Direct conversational flow: Upload product photo → AI requests alternate angle → Verification confirmed.'
        '</p>'
        '</div>'
        '<span class="chat-badge">Interactive AI Chatbot</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # Render Chat History
    for msg in st.session_state["cb_messages"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("image"):
                thumb = _make_chat_thumbnail(msg["image"], max_width=320)
                if thumb:
                    st.image(thumb, width=320)

    step = st.session_state.get("cb_step", 0)

    # =========================================================================
    # STEP 0: Upload Initial Product Photo
    # =========================================================================
    if step == 0:
        st.markdown(
            '<div class="chat-step-box">'
            '<h5 style="margin: 0 0 0.5rem 0; color: #E0E6ED;">📷 Step 1: Upload Product Photo</h5>'
            '<p style="color: #8E9BAE; font-size: 0.88rem; margin: 0 0 1rem 0;">'
            'Select a photo of the product to send to the chatbot:'
            '</p>',
            unsafe_allow_html=True
        )

        col_up1, col_up2 = st.columns([3, 2])
        with col_up1:
            uploaded_file1 = st.file_uploader(
                "Upload Product Photo",
                type=["png", "jpg", "jpeg"],
                key="cb_uploader_1"
            )

        with col_up2:
            st.caption("Quick test without file search:")
            if st.button("⚡ Use Sample Product Photo", key="cb_btn_sample_1", width="stretch"):
                sample_bytes = _create_sample_product_image()
                st.session_state["cb_photo1_bytes"] = sample_bytes
                st.success("Sample product photo loaded!")
                st.rerun()

        # If file was uploaded via file_uploader
        if uploaded_file1 is not None:
            st.session_state["cb_photo1_bytes"] = uploaded_file1.getvalue()

        # Preview if available
        if st.session_state.get("cb_photo1_bytes"):
            preview_img = _make_chat_thumbnail(st.session_state["cb_photo1_bytes"], max_width=240)
            if preview_img:
                st.image(preview_img, caption="Product Photo Ready to Send", width=240)

        can_send_1 = st.session_state.get("cb_photo1_bytes") is not None
        if st.button("📤 Send Product Photo to Assistant", key="cb_btn_send_1", type="primary", width="stretch", disabled=not can_send_1):
            p1_bytes = st.session_state["cb_photo1_bytes"]

            # Add user message to chat history
            st.session_state["cb_messages"].append({
                "role": "user",
                "content": "Here is the photo of the product.",
                "image": p1_bytes
            })

            # Bot says "Checking..."
            with st.spinner("Assistant is checking your product photo..."):
                time.sleep(1.0)

            # Bot asks for photo from different angle (preferably from below)
            st.session_state["cb_messages"].append({
                "role": "assistant",
                "content": "Checking...\n\nI have received and reviewed your product photo. To proceed with your return, please send another photo from a different angle, preferably from below (showing the base or underside).",
                "image": None
            })

            st.session_state["cb_step"] = 1
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # STEP 1: Upload Second Photo (From Below / Different Angle)
    # =========================================================================
    elif step == 1:
        st.markdown(
            '<div class="chat-step-box">'
            '<h5 style="margin: 0 0 0.5rem 0; color: #E0E6ED;">📷 Step 2: Send Photo From Below / Different Angle</h5>'
            '<p style="color: #8E9BAE; font-size: 0.88rem; margin: 0 0 1rem 0;">'
            'The assistant requested a photo from a different angle, preferably from below:'
            '</p>',
            unsafe_allow_html=True
        )

        col_up3, col_up4 = st.columns([3, 2])
        with col_up3:
            uploaded_file2 = st.file_uploader(
                "Upload Photo from Below / Different Angle",
                type=["png", "jpg", "jpeg"],
                key="cb_uploader_2"
            )

        with col_up4:
            st.caption("Quick test without file search:")
            if st.button("⚡ Use Sample Underside Photo", key="cb_btn_sample_2", width="stretch"):
                sample_bytes_2 = _create_sample_underside_image()
                st.session_state["cb_photo2_bytes"] = sample_bytes_2
                st.success("Sample underside photo loaded!")
                st.rerun()

        if uploaded_file2 is not None:
            st.session_state["cb_photo2_bytes"] = uploaded_file2.getvalue()

        if st.session_state.get("cb_photo2_bytes"):
            preview_img2 = _make_chat_thumbnail(st.session_state["cb_photo2_bytes"], max_width=240)
            if preview_img2:
                st.image(preview_img2, caption="Underside Photo Ready to Send", width=240)

        can_send_2 = st.session_state.get("cb_photo2_bytes") is not None
        if st.button("📤 Send Angle Photo to Assistant", key="cb_btn_send_2", type="primary", width="stretch", disabled=not can_send_2):
            p2_bytes = st.session_state["cb_photo2_bytes"]

            # Add user message with second photo
            st.session_state["cb_messages"].append({
                "role": "user",
                "content": "Here is the photo from below showing the underside.",
                "image": p2_bytes
            })

            # Bot says "Checking..."
            with st.spinner("Assistant is checking the underside photo..."):
                time.sleep(1.0)

            # Bot confirms verification and accepts return
            st.session_state["cb_messages"].append({
                "role": "assistant",
                "content": "Checking...\n\nRequest verified, return request accepted! ✅\n\nBoth required angles (product overview and underside base) have been confirmed.",
                "image": None
            })

            st.session_state["cb_step"] = 2
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # STEP 2: Return Request Accepted Card & Restart
    # =========================================================================
    elif step == 2:
        st.markdown(
            '<div class="chat-verified-card">'
            '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">'
            '<h4 style="margin: 0; color: #2ECC71;">✅ Return Request Accepted</h4>'
            '<span style="background-color: rgba(46, 204, 113, 0.2); color: #2ECC71; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 700; font-size: 0.8rem;">REQUEST VERIFIED</span>'
            '</div>'
            '<p style="color: #E0E6ED; margin: 0 0 0.75rem 0; font-size: 0.95rem;">'
            'Your photographic evidence was reviewed and all requested angles were provided.'
            '</p>'
            '<div style="background-color: rgba(0, 0, 0, 0.2); padding: 0.75rem 1rem; border-radius: 6px;">'
            '<p style="margin: 0; color: #C5D0DE; font-size: 0.88rem;">'
            '• <strong>Product Photo:</strong> Verified ✓<br/>'
            '• <strong>Underside Angle:</strong> Verified ✓<br/>'
            '• <strong>Return Authorization ID:</strong> <code>RET-2026-8921</code>'
            '</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown("")
        if st.button("🔄 Start New Return Chat", key="cb_btn_reset", width="stretch"):
            # Reset all cb_ keys
            for k in list(st.session_state.keys()):
                if k.startswith("cb_"):
                    del st.session_state[k]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
