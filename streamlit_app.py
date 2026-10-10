"""Streamlit Cloud entrypoint for PatternProof.

Redirects execution to app.py.
"""

import runpy

runpy.run_path("app.py")
