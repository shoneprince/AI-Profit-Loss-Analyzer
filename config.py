"""
Central configuration for the P&L Summarizer pipeline.
Loads environment variables and defines shared constants.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Google AI ──────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY not found. "
        "Create a .env file with GOOGLE_API_KEY=<your_key>"
    )

# ── Model Settings ──────────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite-preview")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# ── Retriever Settings ──────────────────────────────────────────────
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "6"))

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VECTORSTORE_DIR = os.path.join(PROJECT_ROOT, "data", "vectorstore")
