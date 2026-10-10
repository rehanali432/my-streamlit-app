# PatternProof: Delivery Evidence Coach 📦

*A guided photographic evidence assistant for consumer delivery orders.*

When a customer experiences a delivery problem (damaged packaging, spoiled or expired goods, wrong items, missing products, or short quantities), food and grocery delivery platforms routinely request clear photographic proof from specific angles. Customers often take rushed or unclear photos that support agents cannot verify.

**PatternProof** acts as a coach:
1. The user uploads their order receipt and (optionally) an initial product photo.
2. The AI reads both and generates a custom 4-to-6 step photo checklist with exact angles, lighting, and required elements tailored to the actual billed items.
3. The user captures or uploads photos for each checklist task.
4. Plain Python code evaluates resolution (min 600 px), sharpness/blur (edge variance), lighting, duplicate files, EXIF capture dates, and AI visual observations to decide whether each shot passes or needs a retake with actionable coaching.
5. The user exports a structured, audit-ready Evidence Pack PDF with original file SHA-256 hashes, thumbnails, and verification logs.

---

## ⚖️ Core Principles & Hard Rules
1. **Plain Python Decisions**: The AI only observes and writes instructions. Plain Python makes every pass/fail decision.
2. **Strictly Neutral & Objective**: Never states or implies a claim is valid, invalid, true, or false. Never assigns fault or names any person or delivery driver. No legal claims.
3. **Objective Phrasing**: Zero usage of judgmental terms. Uses objective wording: "could not confirm", "not clearly visible", "retake suggested".
4. **Mandatory Disclaimer**: Displayed in the app footer and on every PDF page:
   > *"PatternProof organises user-provided evidence. It does not verify authenticity, decide claims, or provide legal advice."*
5. **One-Time Privacy Tip**: Displays a privacy tip advising users to hide addresses and phone numbers before uploading receipts.

---

## 🚀 Quickstart & Run Steps

### 1. Requirements
- Python 3.10+
- Packages in `requirements.txt`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit Application
```bash
python -m streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 🔑 How to Set GEMINI_API_KEY

PatternProof works completely in **Demo Mode (simulated AI)** without requiring an API key. To enable live Google Gemini Flash vision, set your key using either of these methods:

### Method A: Local Development (`.env` file)
Create or edit a `.env` file in the project root:
```ini
GEMINI_API_KEY="your-google-gemini-api-key-here"
```
Do not quote with multiple quotation marks. Strip extra spaces.

### Method B: Streamlit Cloud Secrets
When deploying to Streamlit Cloud:
1. Open your app dashboard on [share.streamlit.io](https://share.streamlit.io).
2. Go to **App Settings** > **Secrets**.
3. Add:
```toml
GEMINI_API_KEY = "your-google-gemini-api-key-here"
```
4. Save the secrets. The app automatically picks it up from `st.secrets["GEMINI_API_KEY"]`.

### Method C: Sidebar Key Override
You can also paste your API key directly into the **🔑 Gemini API Key Settings** box in the app's sidebar during any session.

---

## 🧪 Testing with Mock / Demo Mode
PatternProof includes a fully self-contained deterministic simulation mode that requires no API key and no physical camera:

1. In the sidebar, click **"✨ Load Demo Order"**.
2. A fictional delivery receipt for "Fresh Basket (demo)" and a synthetic drawing of a damaged almond milk carton are automatically drawn using Pillow and inserted into SQLite.
3. Simulated AI generates a tailored 4-task photographic checklist.
4. On any task card, click:
   - **⚡ Use Good Test Photo**: Generates a high-contrast test photo (`good_1.jpg`) and runs verification $\rightarrow$ Evaluates as **Passed**.
   - **⚡ Use Retake Test Photo**: Generates a blurred test photo (`bad_1.jpg`) $\rightarrow$ Evaluates as **Retake Suggested** and produces plain retake advice ("Hold the camera steady...").
5. Uploading the same photo twice flags a duplicate warning via SHA-256 and visual hash distance.
6. After 3 attempts on any task, the option to **"Mark as user-confirmed (not machine-verified)"** appears.
7. Click **"Proceed to Evidence Pack Export"** $\rightarrow$ **"Generate Evidence PDF"** to produce and download the structured PDF evidence pack.

---

## 📂 Project Architecture
```
ProofLoop/
├── app.py               # Streamlit user interface (3 steps: Order, Checklist, Export)
├── streamlit_app.py     # Streamlit Cloud deployment entrypoint
├── db.py                # SQLite database management (orders & tasks tables)
├── ai.py                # Gemini vision helper with Pillow shrinker, backoff retries & mock mode
├── tasks.py             # Claim types, templates, and Python task checklist validation
├── verifier.py          # Plain Python 6-point image verification & advice generator
├── demo.py              # Synthetic receipt & product photo generator (Pillow)
├── report.py            # Evidence Pack PDF generation using fpdf2
├── uploads/             # Local storage for receipts, product photos, and task shots
├── .streamlit/
│   └── config.toml      # Dark theme (#0E1117, #1A1F2C) with orange accent (#FF5C1F)
├── requirements.txt     # Python package dependencies
├── .env.example         # Example environment template
├── .gitignore           # Excludes .env, uploads/, *.db, venv/
└── README.md            # Comprehensive documentation
```

---

## ⚠️ Known Limitations
1. **User-Provided Authenticity**: PatternProof organizes user-submitted files and computes cryptographic SHA-256 hashes of original files. It does not verify whether screenshots or photos were altered prior to upload.
2. **Camera Sensor & EXIF Metadata**: Photos taken directly through web browsers via `st.camera_input` or messaging apps often strip EXIF metadata; in such cases, the app records the server clock timestamp and tags the source as "taken in app".
3. **Unicode / Currency Glyphs in PDF**: To prevent PDF rendering crashes across platforms, rupee currency symbols are converted to `INR` and characters are sanitized for Latin-1 encoding in `report.py`.
