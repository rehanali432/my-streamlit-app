# PatternProof 📦
*Delivery Order Evidence Organizer & Traceable Pattern Analyzer*

PatternProof helps users compile, link, and export structured evidence for food and grocery delivery order issues (Swiggy, Zomato, Blinkit, Zepto, Amazon, etc.). Problems like late deliveries, missing items, damaged goods, and unresolved refund requests often appear isolated on their own, leaving consumers with little documentation when contacting customer support or filing grievances. PatternProof lets a user upload order evidence, add basic details, link related orders, analyze timelines and observable patterns, and export a structured complaint evidence report.

---

## ⚖️ Core Principles & Hard Rules
1. **Never Blame or Identify Individuals**: Never blames or identifies any delivery partner, restaurant staff, or support agent. Never states who is at fault, never determines guilt, and never makes legal claims.
2. **Strictly Neutral Terminology**: Uses terms like "reported issue", "order marked delivered", "refund status shown in screenshot". Never uses words like "scam", "fraud", "cheated", or "guilty".
3. **Complete Metric Traceability**: Every statistic displays the exact order / incident IDs behind it.
4. **Deterministic Plain Python**: All metrics, counts, store frequency, delays, and weekly trends are computed by plain Python code (no AI calculations).
5. **Human-in-the-Loop AI**: AI is used strictly to transcribe visible receipt or chat screenshot text and suggest initial values. The user reviews and edits all fields before saving.
6. **Mandatory Disclaimer**: Displayed in the app footer and on every PDF page:
   > *"PatternProof organises user-provided evidence. It does not verify authenticity, assign blame, or provide legal advice."*

---

## 🚀 Quickstart & Run Steps

### 1. Requirements
- Python 3.10+
- Dependencies in `requirements.txt`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure Gemini API Key
PatternProof runs 100% locally with full manual entry even without an API key. To enable automated screenshot transcription, add your key to `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Run the Streamlit Application
```bash
python -m streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🧪 Testing the Demo Case
1. In the sidebar, click **"📥 Load Demo Case"**.
2. 12 fictional orders across Swiggy, Zomato, and Blinkit will be loaded (spanning 6 weeks with repeat delayed orders from Spice Bowl Kitchen, 3 refund inquiries, and 2 link groups).
3. Explore the **Add Incident**, **Timeline**, **Patterns**, **Report**, and **AI Assistant** tabs.
4. In the **AI Assistant** tab, run preset or custom tasks to see verified answers alongside the 6-point verification panel.
5. In the **Report** tab, optionally include the verified complaint draft in your exported PDF.

---

## 📂 Project Architecture
```
ProofLoop/
├── app.py               # Streamlit user interface (5 tabs)
├── streamlit_app.py     # Streamlit Cloud deployment entrypoint
├── db.py                # SQLite database management (table incidents)
├── patterns.py          # Deterministic pattern computations with ID traceability
├── ai.py                # Gemini screenshot transcription & suggestion engine
├── ai_assistant.py      # AI Assistant task handler & verified template generator
├── verifier.py          # Plain-Python 6-point verification engine
├── report.py            # Structured PDF report generator using fpdf2
├── demo_data.py         # 12 fictional demo orders & synthetic receipts
├── uploads/             # Local evidence screenshot directory
├── .streamlit/
│   └── config.toml      # Modern dark theme with #FF5C1F accent
├── requirements.txt     # Python package requirements
├── .env.example         # Example environment configuration
├── .gitignore           # Excludes .env, uploads/, *.db, venv/
└── README.md            # Documentation and instructions
```

---

## ⚠️ Known Limitations
1. **User-Provided Authenticity**: PatternProof organizes files provided by the user and computes cryptographic hashes (SHA-256) of local files. It does not verify whether screenshots have been altered prior to upload.
2. **Missing Receipt Timestamps**: Screenshots lacking explicit year/date timestamps rely on manual user entry for accurate chronological calculations.
3. **Unicode / Currency Glyphs in PDF**: To prevent PDF rendering crashes across varied operating systems, non-Latin scripts and special symbols (such as currency glyphs) are normalized to standard ASCII/Latin-1 characters in PDF outputs.
